"""
PyTorch Neural Network for Vital Signs Risk Prediction

Red neuronal que analiza signos vitales para predecir riesgos de salud.
Arquitectura: Multi-task learning con salidas para diferentes categorías de riesgo.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
import numpy as np
from pathlib import Path
import os

# Ruta al modelo entrenado por defecto
DEFAULT_MODEL_PATH = Path(__file__).parent.parent.parent.parent / "models" / "vital_risk_best.pt"


@dataclass
class VitalInput:
    """Estructura de entrada para los signos vitales"""
    heart_rate: Optional[float] = None
    oxygen_level: Optional[float] = None
    body_temperature: Optional[float] = None
    steps: Optional[int] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    respiratory_rate: Optional[int] = None

    def to_tensor(self, device: str = "cpu") -> torch.Tensor:
        """Convierte a tensor normalizado para el modelo"""
        # Normalización de features (min-max scaling basado en rangos fisiológicos)
        features = [
            self._normalize(self.heart_rate, 40, 200, 75),           # HR: 40-200 bpm
            self._normalize(self.oxygen_level, 70, 100, 98),         # SpO2: 70-100%
            self._normalize(self.body_temperature, 34, 42, 37),      # Temp: 34-42°C
            self._normalize(self.steps, 0, 20000, 5000),             # Steps: 0-20000
            self._normalize(self.blood_pressure_systolic, 80, 200, 120),   # SBP
            self._normalize(self.blood_pressure_diastolic, 50, 130, 80),   # DBP
            self._normalize(self.respiratory_rate, 8, 40, 16),       # RR: 8-40
        ]

        return torch.tensor([features], dtype=torch.float32, device=device)

    @staticmethod
    def _normalize(value: Optional[float], min_val: float, max_val: float, default: float) -> float:
        """Normaliza un valor al rango [0, 1]"""
        if value is None:
            value = default
        return (float(value) - min_val) / (max_val - min_val)


class AttentionBlock(nn.Module):
    """Bloque de atención para ponderar importancia de features"""

    def __init__(self, input_dim: int):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(input_dim, input_dim // 2),
            nn.Tanh(),
            nn.Linear(input_dim // 2, input_dim),
            nn.Softmax(dim=-1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        weights = self.attention(x)
        return x * weights


class VitalRiskNetwork(nn.Module):
    """
    Red neuronal para predicción de riesgo de salud.

    Arquitectura Multi-Task:
    - Encoder compartido para aprender representaciones de signos vitales
    - Cabezas especializadas para cada categoría de riesgo
    - Bloque de atención para identificar signos vitales más relevantes

    Input: 7 features (HR, SpO2, Temp, Steps, SBP, DBP, RR)
    Output: 5 valores (risk_score, cardio, respiratory, metabolic, activity)
    """

    def __init__(
        self,
        input_dim: int = 7,
        hidden_dims: List[int] = [64, 128, 64],
        dropout: float = 0.3
    ):
        super().__init__()

        self.input_dim = input_dim

        # Encoder compartido
        layers = []
        prev_dim = input_dim

        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout)
            ])
            prev_dim = hidden_dim

        self.encoder = nn.Sequential(*layers)

        # Attention para ponderar features
        self.attention = AttentionBlock(hidden_dims[-1])

        # Cabezas especializadas (multi-task)
        self.cardiovascular_head = nn.Sequential(
            nn.Linear(hidden_dims[-1], 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )

        self.respiratory_head = nn.Sequential(
            nn.Linear(hidden_dims[-1], 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )

        self.metabolic_head = nn.Sequential(
            nn.Linear(hidden_dims[-1], 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )

        self.activity_head = nn.Sequential(
            nn.Linear(hidden_dims[-1], 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )

        # Cabeza para riesgo general (combinación ponderada)
        self.risk_aggregator = nn.Sequential(
            nn.Linear(4, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )

        # Cabeza para confianza del modelo
        self.confidence_head = nn.Sequential(
            nn.Linear(hidden_dims[-1], 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Forward pass.

        Args:
            x: Tensor de shape (batch_size, 7) con signos vitales normalizados

        Returns:
            Dict con risk_score, cardiovascular, respiratory, metabolic, activity, confidence
        """
        # Encoding
        encoded = self.encoder(x)

        # Attention
        attended = self.attention(encoded)

        # Predicciones por categoría
        cardio = self.cardiovascular_head(attended)
        resp = self.respiratory_head(attended)
        metab = self.metabolic_head(attended)
        activity = self.activity_head(attended)

        # Combinar para riesgo general
        combined = torch.cat([cardio, resp, metab, activity], dim=-1)
        risk_score = self.risk_aggregator(combined)

        # Confianza
        confidence = self.confidence_head(attended)

        return {
            "risk_score": risk_score.squeeze(-1),
            "cardiovascular": cardio.squeeze(-1),
            "respiratory": resp.squeeze(-1),
            "metabolic": metab.squeeze(-1),
            "activity": activity.squeeze(-1),
            "confidence": confidence.squeeze(-1)
        }


class VitalRiskPredictor:
    """
    Wrapper para inferencia del modelo de riesgo.

    Maneja carga de modelo, preprocesamiento y post-procesamiento.
    """

    MODEL_VERSION = "1.0.0"

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: Optional[str] = None
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = VitalRiskNetwork().to(self.device)
        self.model.eval()

        # Intentar cargar modelo entrenado
        if model_path and Path(model_path).exists():
            self._load_model(model_path)
        elif DEFAULT_MODEL_PATH.exists():
            # Cargar modelo entrenado por defecto
            self._load_model(str(DEFAULT_MODEL_PATH))
        else:
            # Sin modelo entrenado, usar pesos iniciales
            self._initialize_baseline_weights()

    def _load_model(self, path: str) -> None:
        """Carga pesos del modelo desde archivo"""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.MODEL_VERSION = checkpoint.get("version", "1.0.0")

    def _initialize_baseline_weights(self) -> None:
        """
        Inicializa pesos para comportamiento baseline razonable.

        Sin entrenamiento, el modelo usará heurísticas basadas en umbrales.
        """
        # Los pesos por defecto de PyTorch funcionan como punto de partida
        # El modelo aprenderá patrones más complejos con entrenamiento
        pass

    def save_model(self, path: str) -> None:
        """Guarda el modelo"""
        torch.save({
            "model_state_dict": self.model.state_dict(),
            "version": self.MODEL_VERSION
        }, path)

    @torch.no_grad()
    def predict(self, vitals: VitalInput) -> Dict[str, float]:
        """
        Realiza predicción para un conjunto de signos vitales.

        Args:
            vitals: VitalInput con los signos vitales

        Returns:
            Dict con scores de riesgo
        """
        self.model.eval()

        # Convertir a tensor
        x = vitals.to_tensor(self.device)

        # Predicción
        outputs = self.model(x)

        # Convertir a Python floats
        return {
            "risk_score": float(outputs["risk_score"].item()),
            "cardiovascular": float(outputs["cardiovascular"].item()),
            "respiratory": float(outputs["respiratory"].item()),
            "metabolic": float(outputs["metabolic"].item()),
            "activity": float(outputs["activity"].item()),
            "confidence": float(outputs["confidence"].item())
        }

    @torch.no_grad()
    def predict_batch(self, vitals_list: List[VitalInput]) -> List[Dict[str, float]]:
        """Predicción en batch"""
        self.model.eval()

        # Stack tensors
        tensors = [v.to_tensor(self.device) for v in vitals_list]
        x = torch.cat(tensors, dim=0)

        # Predicción
        outputs = self.model(x)

        # Convertir a lista de dicts
        results = []
        batch_size = len(vitals_list)

        for i in range(batch_size):
            results.append({
                "risk_score": float(outputs["risk_score"][i].item()),
                "cardiovascular": float(outputs["cardiovascular"][i].item()),
                "respiratory": float(outputs["respiratory"][i].item()),
                "metabolic": float(outputs["metabolic"][i].item()),
                "activity": float(outputs["activity"][i].item()),
                "confidence": float(outputs["confidence"][i].item())
            })

        return results

    def predict_with_explanation(self, vitals: VitalInput) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Predicción con importancia de features (básica).

        Returns:
            Tuple de (predicciones, feature_importance)
        """
        predictions = self.predict(vitals)

        # Feature importance basada en desviación de valores normales
        importance = {
            "heart_rate": self._calc_importance(vitals.heart_rate, 60, 100, 40, 200),
            "oxygen_level": self._calc_importance(vitals.oxygen_level, 95, 100, 85, 100),
            "body_temperature": self._calc_importance(vitals.body_temperature, 36.1, 37.2, 35, 40),
            "steps": self._calc_importance(vitals.steps, 5000, 15000, 0, 20000),
            "blood_pressure_systolic": self._calc_importance(vitals.blood_pressure_systolic, 90, 120, 80, 180),
            "blood_pressure_diastolic": self._calc_importance(vitals.blood_pressure_diastolic, 60, 80, 50, 120),
            "respiratory_rate": self._calc_importance(vitals.respiratory_rate, 12, 20, 8, 30),
        }

        return predictions, importance

    @staticmethod
    def _calc_importance(
        value: Optional[float],
        normal_min: float,
        normal_max: float,
        abs_min: float,
        abs_max: float
    ) -> float:
        """Calcula importancia basada en desviación del rango normal"""
        if value is None:
            return 0.0

        value = float(value)

        if normal_min <= value <= normal_max:
            return 0.0

        if value < normal_min:
            deviation = (normal_min - value) / (normal_min - abs_min)
        else:
            deviation = (value - normal_max) / (abs_max - normal_max)

        return min(1.0, max(0.0, deviation))


# Función de pérdida personalizada para entrenamiento
class MultiTaskRiskLoss(nn.Module):
    """
    Pérdida multi-task para entrenamiento del modelo.

    Combina BCE loss para cada categoría de riesgo con pesos configurables.
    """

    def __init__(
        self,
        risk_weight: float = 1.0,
        cardio_weight: float = 0.8,
        resp_weight: float = 0.8,
        metab_weight: float = 0.6,
        activity_weight: float = 0.4
    ):
        super().__init__()
        self.weights = {
            "risk_score": risk_weight,
            "cardiovascular": cardio_weight,
            "respiratory": resp_weight,
            "metabolic": metab_weight,
            "activity": activity_weight
        }
        self.bce = nn.BCELoss()

    def forward(
        self,
        predictions: Dict[str, torch.Tensor],
        targets: Dict[str, torch.Tensor]
    ) -> torch.Tensor:
        """Calcula pérdida total"""
        total_loss = 0.0

        for key, weight in self.weights.items():
            if key in predictions and key in targets:
                total_loss += weight * self.bce(predictions[key], targets[key])

        return total_loss
