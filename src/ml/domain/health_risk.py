"""
Domain model for Health Risk Prediction
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict
import uuid


class RiskLevel(Enum):
    """Nivel de riesgo predicho"""
    LOW = "low"           # Riesgo bajo - signos vitales estables
    MODERATE = "moderate" # Riesgo moderado - tendencia a deterioro
    HIGH = "high"         # Riesgo alto - requiere atención
    CRITICAL = "critical" # Riesgo crítico - atención inmediata


class RiskCategory(Enum):
    """Categorías de riesgo de salud"""
    CARDIOVASCULAR = "cardiovascular"     # Riesgo cardíaco
    RESPIRATORY = "respiratory"           # Riesgo respiratorio
    METABOLIC = "metabolic"               # Riesgo metabólico
    GENERAL_DETERIORATION = "general"     # Deterioro general
    ACTIVITY_DECLINE = "activity_decline" # Decline de actividad


@dataclass
class RiskFactor:
    """Factor que contribuye al riesgo"""
    category: RiskCategory
    contribution: float  # 0.0 - 1.0
    description: str
    vital_metric: str
    current_value: float
    normal_range: str


@dataclass
class HealthRiskPrediction:
    """
    Predicción de riesgo de salud basada en signos vitales.

    Utiliza un modelo de ML para analizar patrones en los signos vitales
    y predecir el riesgo de eventos adversos de salud.
    """
    id: str
    member_id: str

    # Resultado de la predicción
    risk_level: RiskLevel
    risk_score: float  # 0.0 - 1.0 (probabilidad de evento adverso)
    confidence: float  # 0.0 - 1.0 (confianza del modelo)

    # Desglose por categoría
    cardiovascular_risk: float = 0.0
    respiratory_risk: float = 0.0
    metabolic_risk: float = 0.0
    activity_risk: float = 0.0

    # Factores contribuyentes
    risk_factors: List[RiskFactor] = field(default_factory=list)

    # Recomendaciones generadas
    recommendations: List[str] = field(default_factory=list)

    # Datos de entrada usados
    input_vitals: Dict = field(default_factory=dict)

    # Horizonte de predicción
    prediction_horizon_hours: int = 24  # Predicción para las próximas N horas

    # Metadata
    model_version: str = "1.0.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create(
        member_id: str,
        risk_score: float,
        confidence: float,
        cardiovascular_risk: float = 0.0,
        respiratory_risk: float = 0.0,
        metabolic_risk: float = 0.0,
        activity_risk: float = 0.0,
        input_vitals: Optional[Dict] = None,
        model_version: str = "1.0.0"
    ) -> "HealthRiskPrediction":
        """Factory method para crear una nueva predicción"""

        # Determinar nivel de riesgo basado en score
        if risk_score >= 0.8:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 0.6:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 0.4:
            risk_level = RiskLevel.MODERATE
        else:
            risk_level = RiskLevel.LOW

        prediction = HealthRiskPrediction(
            id=str(uuid.uuid4()),
            member_id=member_id,
            risk_level=risk_level,
            risk_score=risk_score,
            confidence=confidence,
            cardiovascular_risk=cardiovascular_risk,
            respiratory_risk=respiratory_risk,
            metabolic_risk=metabolic_risk,
            activity_risk=activity_risk,
            input_vitals=input_vitals or {},
            model_version=model_version
        )

        prediction._generate_risk_factors()
        prediction._generate_recommendations()

        return prediction

    def _generate_risk_factors(self) -> None:
        """Genera los factores de riesgo basados en las métricas"""
        factors = []

        # Cardiovascular
        if self.cardiovascular_risk > 0.3:
            hr = self.input_vitals.get("heart_rate")
            bp_sys = self.input_vitals.get("blood_pressure_systolic")

            if hr:
                factors.append(RiskFactor(
                    category=RiskCategory.CARDIOVASCULAR,
                    contribution=self.cardiovascular_risk,
                    description="Frecuencia cardíaca fuera de rango óptimo",
                    vital_metric="heart_rate",
                    current_value=hr,
                    normal_range="60-100 bpm"
                ))

        # Respiratory
        if self.respiratory_risk > 0.3:
            spo2 = self.input_vitals.get("oxygen_level")
            rr = self.input_vitals.get("respiratory_rate")

            if spo2:
                factors.append(RiskFactor(
                    category=RiskCategory.RESPIRATORY,
                    contribution=self.respiratory_risk,
                    description="Nivel de oxígeno por debajo del óptimo",
                    vital_metric="oxygen_level",
                    current_value=spo2,
                    normal_range="95-100%"
                ))

        # Metabolic
        if self.metabolic_risk > 0.3:
            temp = self.input_vitals.get("body_temperature")

            if temp:
                factors.append(RiskFactor(
                    category=RiskCategory.METABOLIC,
                    contribution=self.metabolic_risk,
                    description="Temperatura corporal anormal",
                    vital_metric="body_temperature",
                    current_value=temp,
                    normal_range="36.1-37.2°C"
                ))

        # Activity
        if self.activity_risk > 0.3:
            steps = self.input_vitals.get("steps")

            if steps is not None:
                factors.append(RiskFactor(
                    category=RiskCategory.ACTIVITY_DECLINE,
                    contribution=self.activity_risk,
                    description="Nivel de actividad física reducido",
                    vital_metric="steps",
                    current_value=steps,
                    normal_range=">5000 pasos/día"
                ))

        self.risk_factors = factors

    def _generate_recommendations(self) -> None:
        """Genera recomendaciones basadas en el nivel de riesgo"""
        recommendations = []

        if self.risk_level == RiskLevel.CRITICAL:
            recommendations.append("Buscar atención médica inmediata")
            recommendations.append("Contactar al cuidador principal")

        if self.cardiovascular_risk > 0.5:
            recommendations.append("Monitorear frecuencia cardíaca cada hora")
            recommendations.append("Evitar actividades físicas intensas")

        if self.respiratory_risk > 0.5:
            recommendations.append("Verificar saturación de oxígeno frecuentemente")
            recommendations.append("Mantener ambiente ventilado")

        if self.metabolic_risk > 0.5:
            recommendations.append("Monitorear temperatura cada 2 horas")
            recommendations.append("Mantener hidratación adecuada")

        if self.activity_risk > 0.5:
            recommendations.append("Fomentar movimiento ligero si es posible")
            recommendations.append("Evaluar posibles causas de inactividad")

        if self.risk_level == RiskLevel.LOW:
            recommendations.append("Continuar monitoreo rutinario")

        self.recommendations = recommendations

    def is_high_risk(self) -> bool:
        """Verifica si es alto riesgo o crítico"""
        return self.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]

    def get_primary_risk_category(self) -> Optional[RiskCategory]:
        """Obtiene la categoría de riesgo principal"""
        risks = {
            RiskCategory.CARDIOVASCULAR: self.cardiovascular_risk,
            RiskCategory.RESPIRATORY: self.respiratory_risk,
            RiskCategory.METABOLIC: self.metabolic_risk,
            RiskCategory.ACTIVITY_DECLINE: self.activity_risk,
        }

        if not any(risks.values()):
            return None

        return max(risks, key=risks.get)

    def to_dict(self) -> Dict:
        """Convierte la predicción a diccionario"""
        return {
            "id": self.id,
            "member_id": self.member_id,
            "risk_level": self.risk_level.value,
            "risk_score": round(self.risk_score, 3),
            "confidence": round(self.confidence, 3),
            "risks": {
                "cardiovascular": round(self.cardiovascular_risk, 3),
                "respiratory": round(self.respiratory_risk, 3),
                "metabolic": round(self.metabolic_risk, 3),
                "activity": round(self.activity_risk, 3),
            },
            "risk_factors": [
                {
                    "category": f.category.value,
                    "contribution": round(f.contribution, 3),
                    "description": f.description,
                    "metric": f.vital_metric,
                    "value": f.current_value,
                    "normal_range": f.normal_range
                }
                for f in self.risk_factors
            ],
            "recommendations": self.recommendations,
            "prediction_horizon_hours": self.prediction_horizon_hours,
            "model_version": self.model_version,
            "created_at": self.created_at.isoformat()
        }
