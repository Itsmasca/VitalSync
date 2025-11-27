"""
Generador de datos sintéticos para entrenamiento del modelo de riesgo.

Genera datos basados en los umbrales definidos en VitalSync:
- Heart Rate: Normal 60-100, Warning 50-59/101-120, Critical <50/>120
- Oxygen Level: Normal 95-100, Warning 90-94, Critical <90
- Temperature: Normal 36.1-37.2, Warning 37.3-38/<36.1, Critical >38/<35
- Steps: Normal >5000, Warning 2000-5000, Critical <2000
"""
import numpy as np
from dataclasses import dataclass
from typing import Tuple, List, Dict
import torch
from torch.utils.data import Dataset, DataLoader


@dataclass
class VitalRanges:
    """Rangos fisiológicos para generación de datos"""
    # Heart Rate (bpm)
    HR_NORMAL = (60, 100)
    HR_WARNING_LOW = (50, 59)
    HR_WARNING_HIGH = (101, 120)
    HR_CRITICAL_LOW = (30, 49)
    HR_CRITICAL_HIGH = (121, 180)

    # Oxygen Level (%)
    SPO2_NORMAL = (95, 100)
    SPO2_WARNING = (90, 94)
    SPO2_CRITICAL = (70, 89)

    # Temperature (°C)
    TEMP_NORMAL = (36.1, 37.2)
    TEMP_WARNING_LOW = (35.0, 36.0)
    TEMP_WARNING_HIGH = (37.3, 38.0)
    TEMP_CRITICAL_LOW = (33.0, 34.9)
    TEMP_CRITICAL_HIGH = (38.1, 42.0)

    # Steps
    STEPS_NORMAL = (5000, 15000)
    STEPS_WARNING = (2000, 4999)
    STEPS_CRITICAL = (0, 1999)

    # Blood Pressure Systolic
    BP_SYS_NORMAL = (90, 120)
    BP_SYS_WARNING = (121, 139)
    BP_SYS_CRITICAL = (140, 180)

    # Blood Pressure Diastolic
    BP_DIA_NORMAL = (60, 80)
    BP_DIA_WARNING = (81, 89)
    BP_DIA_CRITICAL = (90, 120)

    # Respiratory Rate
    RR_NORMAL = (12, 20)
    RR_WARNING = (21, 24)
    RR_CRITICAL = (25, 40)


class VitalSyncDataGenerator:
    """
    Genera datos sintéticos para entrenamiento del modelo.

    Crea muestras balanceadas de casos normales, warning y críticos
    con etiquetas de riesgo correspondientes.
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.ranges = VitalRanges()

    def generate_dataset(
        self,
        n_samples: int = 10000,
        normal_ratio: float = 0.5,
        warning_ratio: float = 0.3,
        critical_ratio: float = 0.2
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """
        Genera un dataset completo.

        Args:
            n_samples: Número total de muestras
            normal_ratio: Proporción de casos normales
            warning_ratio: Proporción de casos warning
            critical_ratio: Proporción de casos críticos

        Returns:
            Tuple de (features, labels_dict)
        """
        n_normal = int(n_samples * normal_ratio)
        n_warning = int(n_samples * warning_ratio)
        n_critical = n_samples - n_normal - n_warning

        # Generar cada tipo
        normal_samples, normal_labels = self._generate_normal_samples(n_normal)
        warning_samples, warning_labels = self._generate_warning_samples(n_warning)
        critical_samples, critical_labels = self._generate_critical_samples(n_critical)

        # Combinar
        features = np.vstack([normal_samples, warning_samples, critical_samples])
        labels = {
            key: np.concatenate([normal_labels[key], warning_labels[key], critical_labels[key]])
            for key in normal_labels.keys()
        }

        # Shuffle
        indices = self.rng.permutation(len(features))
        features = features[indices]
        labels = {key: val[indices] for key, val in labels.items()}

        return features, labels

    def _generate_normal_samples(self, n: int) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """Genera muestras con signos vitales normales"""
        features = np.zeros((n, 7))

        # Heart rate normal
        features[:, 0] = self._sample_range(self.ranges.HR_NORMAL, n)
        # SpO2 normal
        features[:, 1] = self._sample_range(self.ranges.SPO2_NORMAL, n)
        # Temperature normal
        features[:, 2] = self._sample_range(self.ranges.TEMP_NORMAL, n)
        # Steps normal
        features[:, 3] = self._sample_range(self.ranges.STEPS_NORMAL, n)
        # BP Systolic normal
        features[:, 4] = self._sample_range(self.ranges.BP_SYS_NORMAL, n)
        # BP Diastolic normal
        features[:, 5] = self._sample_range(self.ranges.BP_DIA_NORMAL, n)
        # Respiratory rate normal
        features[:, 6] = self._sample_range(self.ranges.RR_NORMAL, n)

        # Normalizar features
        features = self._normalize_features(features)

        # Labels: bajo riesgo
        labels = {
            "risk_score": np.random.uniform(0.0, 0.3, n),
            "cardiovascular": np.random.uniform(0.0, 0.2, n),
            "respiratory": np.random.uniform(0.0, 0.2, n),
            "metabolic": np.random.uniform(0.0, 0.2, n),
            "activity": np.random.uniform(0.0, 0.2, n),
        }

        return features, labels

    def _generate_warning_samples(self, n: int) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """Genera muestras con algunos signos vitales en warning"""
        features = np.zeros((n, 7))
        cardio_risk = np.zeros(n)
        resp_risk = np.zeros(n)
        metab_risk = np.zeros(n)
        activity_risk = np.zeros(n)

        for i in range(n):
            # Decidir qué métricas están en warning (1-2 métricas)
            warning_metrics = self.rng.choice(4, size=self.rng.integers(1, 3), replace=False)

            # Heart rate
            if 0 in warning_metrics:
                if self.rng.random() > 0.5:
                    features[i, 0] = self._sample_range(self.ranges.HR_WARNING_HIGH, 1)[0]
                else:
                    features[i, 0] = self._sample_range(self.ranges.HR_WARNING_LOW, 1)[0]
                cardio_risk[i] = self.rng.uniform(0.4, 0.7)
            else:
                features[i, 0] = self._sample_range(self.ranges.HR_NORMAL, 1)[0]
                cardio_risk[i] = self.rng.uniform(0.0, 0.2)

            # SpO2
            if 1 in warning_metrics:
                features[i, 1] = self._sample_range(self.ranges.SPO2_WARNING, 1)[0]
                resp_risk[i] = self.rng.uniform(0.4, 0.7)
            else:
                features[i, 1] = self._sample_range(self.ranges.SPO2_NORMAL, 1)[0]
                resp_risk[i] = self.rng.uniform(0.0, 0.2)

            # Temperature
            if 2 in warning_metrics:
                if self.rng.random() > 0.5:
                    features[i, 2] = self._sample_range(self.ranges.TEMP_WARNING_HIGH, 1)[0]
                else:
                    features[i, 2] = self._sample_range(self.ranges.TEMP_WARNING_LOW, 1)[0]
                metab_risk[i] = self.rng.uniform(0.4, 0.7)
            else:
                features[i, 2] = self._sample_range(self.ranges.TEMP_NORMAL, 1)[0]
                metab_risk[i] = self.rng.uniform(0.0, 0.2)

            # Steps
            if 3 in warning_metrics:
                features[i, 3] = self._sample_range(self.ranges.STEPS_WARNING, 1)[0]
                activity_risk[i] = self.rng.uniform(0.4, 0.7)
            else:
                features[i, 3] = self._sample_range(self.ranges.STEPS_NORMAL, 1)[0]
                activity_risk[i] = self.rng.uniform(0.0, 0.2)

            # BP y RR normales para simplificar
            features[i, 4] = self._sample_range(self.ranges.BP_SYS_NORMAL, 1)[0]
            features[i, 5] = self._sample_range(self.ranges.BP_DIA_NORMAL, 1)[0]
            features[i, 6] = self._sample_range(self.ranges.RR_NORMAL, 1)[0]

        features = self._normalize_features(features)

        # Risk score es el máximo de los riesgos individuales
        risk_scores = np.maximum.reduce([cardio_risk, resp_risk, metab_risk, activity_risk])
        risk_scores = np.clip(risk_scores + self.rng.uniform(-0.1, 0.1, n), 0.3, 0.7)

        labels = {
            "risk_score": risk_scores,
            "cardiovascular": cardio_risk,
            "respiratory": resp_risk,
            "metabolic": metab_risk,
            "activity": activity_risk,
        }

        return features, labels

    def _generate_critical_samples(self, n: int) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """Genera muestras con signos vitales críticos"""
        features = np.zeros((n, 7))
        cardio_risk = np.zeros(n)
        resp_risk = np.zeros(n)
        metab_risk = np.zeros(n)
        activity_risk = np.zeros(n)

        for i in range(n):
            # Decidir qué métricas están en crítico (1-3 métricas)
            critical_metrics = self.rng.choice(4, size=self.rng.integers(1, 4), replace=False)

            # Heart rate
            if 0 in critical_metrics:
                if self.rng.random() > 0.5:
                    features[i, 0] = self._sample_range(self.ranges.HR_CRITICAL_HIGH, 1)[0]
                else:
                    features[i, 0] = self._sample_range(self.ranges.HR_CRITICAL_LOW, 1)[0]
                cardio_risk[i] = self.rng.uniform(0.7, 1.0)
            else:
                features[i, 0] = self._sample_range(self.ranges.HR_NORMAL, 1)[0]
                cardio_risk[i] = self.rng.uniform(0.0, 0.3)

            # SpO2
            if 1 in critical_metrics:
                features[i, 1] = self._sample_range(self.ranges.SPO2_CRITICAL, 1)[0]
                resp_risk[i] = self.rng.uniform(0.7, 1.0)
            else:
                features[i, 1] = self._sample_range(self.ranges.SPO2_NORMAL, 1)[0]
                resp_risk[i] = self.rng.uniform(0.0, 0.3)

            # Temperature
            if 2 in critical_metrics:
                if self.rng.random() > 0.5:
                    features[i, 2] = self._sample_range(self.ranges.TEMP_CRITICAL_HIGH, 1)[0]
                else:
                    features[i, 2] = self._sample_range(self.ranges.TEMP_CRITICAL_LOW, 1)[0]
                metab_risk[i] = self.rng.uniform(0.7, 1.0)
            else:
                features[i, 2] = self._sample_range(self.ranges.TEMP_NORMAL, 1)[0]
                metab_risk[i] = self.rng.uniform(0.0, 0.3)

            # Steps
            if 3 in critical_metrics:
                features[i, 3] = self._sample_range(self.ranges.STEPS_CRITICAL, 1)[0]
                activity_risk[i] = self.rng.uniform(0.7, 1.0)
            else:
                features[i, 3] = self._sample_range(self.ranges.STEPS_NORMAL, 1)[0]
                activity_risk[i] = self.rng.uniform(0.0, 0.3)

            # BP puede estar elevado en casos críticos
            if 0 in critical_metrics:  # Si hay problema cardíaco
                features[i, 4] = self._sample_range(self.ranges.BP_SYS_CRITICAL, 1)[0]
                features[i, 5] = self._sample_range(self.ranges.BP_DIA_CRITICAL, 1)[0]
            else:
                features[i, 4] = self._sample_range(self.ranges.BP_SYS_NORMAL, 1)[0]
                features[i, 5] = self._sample_range(self.ranges.BP_DIA_NORMAL, 1)[0]

            # RR elevado si hay problema respiratorio
            if 1 in critical_metrics:
                features[i, 6] = self._sample_range(self.ranges.RR_CRITICAL, 1)[0]
            else:
                features[i, 6] = self._sample_range(self.ranges.RR_NORMAL, 1)[0]

        features = self._normalize_features(features)

        # Risk score alto
        risk_scores = np.maximum.reduce([cardio_risk, resp_risk, metab_risk, activity_risk])
        risk_scores = np.clip(risk_scores + self.rng.uniform(-0.05, 0.1, n), 0.6, 1.0)

        labels = {
            "risk_score": risk_scores,
            "cardiovascular": cardio_risk,
            "respiratory": resp_risk,
            "metabolic": metab_risk,
            "activity": activity_risk,
        }

        return features, labels

    def _sample_range(self, range_tuple: Tuple[float, float], n: int) -> np.ndarray:
        """Genera muestras uniformes en un rango"""
        return self.rng.uniform(range_tuple[0], range_tuple[1], n)

    def _normalize_features(self, features: np.ndarray) -> np.ndarray:
        """Normaliza features al rango [0, 1]"""
        # Rangos de normalización (min, max)
        norm_ranges = [
            (40, 200),    # HR
            (70, 100),    # SpO2
            (34, 42),     # Temp
            (0, 20000),   # Steps
            (80, 200),    # BP Sys
            (50, 130),    # BP Dia
            (8, 40),      # RR
        ]

        normalized = features.copy()
        for i, (min_val, max_val) in enumerate(norm_ranges):
            normalized[:, i] = (features[:, i] - min_val) / (max_val - min_val)

        return np.clip(normalized, 0, 1)


class VitalRiskDataset(Dataset):
    """PyTorch Dataset para entrenamiento"""

    def __init__(self, features: np.ndarray, labels: Dict[str, np.ndarray]):
        self.features = torch.tensor(features, dtype=torch.float32)
        self.labels = {
            key: torch.tensor(val, dtype=torch.float32)
            for key, val in labels.items()
        }

    def __len__(self) -> int:
        return len(self.features)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        return (
            self.features[idx],
            {key: val[idx] for key, val in self.labels.items()}
        )


def create_dataloaders(
    n_samples: int = 10000,
    batch_size: int = 64,
    train_ratio: float = 0.8,
    seed: int = 42
) -> Tuple[DataLoader, DataLoader]:
    """
    Crea DataLoaders de entrenamiento y validación.

    Returns:
        Tuple de (train_loader, val_loader)
    """
    generator = VitalSyncDataGenerator(seed=seed)
    features, labels = generator.generate_dataset(n_samples)

    # Split train/val
    n_train = int(len(features) * train_ratio)

    train_features = features[:n_train]
    train_labels = {key: val[:n_train] for key, val in labels.items()}

    val_features = features[n_train:]
    val_labels = {key: val[n_train:] for key, val in labels.items()}

    train_dataset = VitalRiskDataset(train_features, train_labels)
    val_dataset = VitalRiskDataset(val_features, val_labels)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0
    )

    return train_loader, val_loader
