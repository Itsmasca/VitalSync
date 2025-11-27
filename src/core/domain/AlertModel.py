from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

from src.core.domain.VitalModel import VitalStatus


class AlertStatus(Enum):
    """Estado de la alerta"""
    ACTIVE = "active"            # Alerta activa, pendiente de atención
    ACKNOWLEDGED = "acknowledged"  # Reconocida por el cuidador
    RESOLVED = "resolved"        # Resuelta/cerrada
    DISMISSED = "dismissed"      # Descartada (falso positivo)


class AlertType(Enum):
    """Tipo de alerta según la métrica"""
    HEART_RATE = "heart_rate"
    OXYGEN_LEVEL = "oxygen_level"
    TEMPERATURE = "temperature"
    STEPS = "steps"


class ThresholdType(Enum):
    """Tipo de umbral que disparó la alerta"""
    MIN = "min"
    MAX = "max"


@dataclass
class Alert:
    """
    Entidad de dominio que representa una alerta del sistema.

    Basado en el DDL de VitalSync - Tabla alerts.
    RF-VIT-05, RF-DASH-05, US-23, US-24, US-26
    """
    id: str
    member_id: str
    alert_type: AlertType
    severity: VitalStatus  # WARNING o CRITICAL
    metric_value: float
    threshold_value: float
    threshold_type: ThresholdType
    message: str
    vital_id: Optional[str] = None
    status: AlertStatus = AlertStatus.ACTIVE
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create(
        member_id: str,
        alert_type: AlertType,
        severity: VitalStatus,
        metric_value: float,
        threshold_value: float,
        threshold_type: ThresholdType,
        message: str,
        vital_id: Optional[str] = None
    ) -> "Alert":
        """Factory method para crear una nueva alerta"""
        return Alert(
            id=str(uuid.uuid4()),
            member_id=member_id,
            alert_type=alert_type,
            severity=severity,
            metric_value=metric_value,
            threshold_value=threshold_value,
            threshold_type=threshold_type,
            message=message,
            vital_id=vital_id,
            status=AlertStatus.ACTIVE,
            created_at=datetime.now(timezone.utc)
        )

    @staticmethod
    def create_heart_rate_alert(
        member_id: str,
        member_name: str,
        heart_rate: int,
        threshold: int,
        is_high: bool,
        vital_id: Optional[str] = None
    ) -> "Alert":
        """Crea una alerta de heart rate"""
        threshold_type = ThresholdType.MAX if is_high else ThresholdType.MIN
        severity = VitalStatus.CRITICAL if (heart_rate > 120 or heart_rate < 50) else VitalStatus.WARNING
        emoji = "🚨" if severity == VitalStatus.CRITICAL else "⚠️"
        direction = "elevado" if is_high else "bajo"

        message = f"{emoji} Heart rate de {member_name} {direction}: {heart_rate} bpm ({'máx' if is_high else 'mín'}: {threshold})"

        return Alert.create(
            member_id=member_id,
            alert_type=AlertType.HEART_RATE,
            severity=severity,
            metric_value=float(heart_rate),
            threshold_value=float(threshold),
            threshold_type=threshold_type,
            message=message,
            vital_id=vital_id
        )

    @staticmethod
    def create_oxygen_alert(
        member_id: str,
        member_name: str,
        oxygen_level: float,
        threshold: float,
        vital_id: Optional[str] = None
    ) -> "Alert":
        """Crea una alerta de nivel de oxígeno"""
        severity = VitalStatus.CRITICAL if oxygen_level < 90 else VitalStatus.WARNING
        emoji = "🚨" if severity == VitalStatus.CRITICAL else "⚠️"

        message = f"{emoji} Oxygen level de {member_name} bajo: {oxygen_level}% (mín: {threshold}%)"

        return Alert.create(
            member_id=member_id,
            alert_type=AlertType.OXYGEN_LEVEL,
            severity=severity,
            metric_value=oxygen_level,
            threshold_value=threshold,
            threshold_type=ThresholdType.MIN,
            message=message,
            vital_id=vital_id
        )

    @staticmethod
    def create_temperature_alert(
        member_id: str,
        member_name: str,
        temperature: float,
        threshold: float,
        is_high: bool,
        vital_id: Optional[str] = None
    ) -> "Alert":
        """Crea una alerta de temperatura"""
        threshold_type = ThresholdType.MAX if is_high else ThresholdType.MIN
        severity = VitalStatus.CRITICAL if (temperature > 38 or temperature < 35) else VitalStatus.WARNING
        emoji = "🚨" if severity == VitalStatus.CRITICAL else "⚠️"
        direction = "elevada" if is_high else "baja"

        message = f"{emoji} Temperatura de {member_name} {direction}: {temperature}°C ({'máx' if is_high else 'mín'}: {threshold}°C)"

        return Alert.create(
            member_id=member_id,
            alert_type=AlertType.TEMPERATURE,
            severity=severity,
            metric_value=temperature,
            threshold_value=threshold,
            threshold_type=threshold_type,
            message=message,
            vital_id=vital_id
        )

    @staticmethod
    def create_steps_alert(
        member_id: str,
        member_name: str,
        steps: int,
        threshold: int,
        vital_id: Optional[str] = None
    ) -> "Alert":
        """Crea una alerta de pasos"""
        severity = VitalStatus.CRITICAL if steps < 2000 else VitalStatus.WARNING
        emoji = "🚨" if severity == VitalStatus.CRITICAL else "⚠️"

        message = f"{emoji} Steps de {member_name} muy bajo: {steps:,} pasos (mín: {threshold:,})"

        return Alert.create(
            member_id=member_id,
            alert_type=AlertType.STEPS,
            severity=severity,
            metric_value=float(steps),
            threshold_value=float(threshold),
            threshold_type=ThresholdType.MIN,
            message=message,
            vital_id=vital_id
        )

    def acknowledge(self, user_id: str) -> None:
        """Marca la alerta como reconocida"""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_by = user_id
        self.acknowledged_at = datetime.now(timezone.utc)

    def resolve(self, notes: Optional[str] = None) -> None:
        """Marca la alerta como resuelta"""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now(timezone.utc)
        self.resolution_notes = notes

    def dismiss(self, notes: Optional[str] = None) -> None:
        """Descarta la alerta (falso positivo)"""
        self.status = AlertStatus.DISMISSED
        self.resolved_at = datetime.now(timezone.utc)
        self.resolution_notes = notes

    def is_active(self) -> bool:
        """Verifica si la alerta está activa"""
        return self.status == AlertStatus.ACTIVE

    def is_critical(self) -> bool:
        """Verifica si la alerta es crítica"""
        return self.severity == VitalStatus.CRITICAL

    def is_warning(self) -> bool:
        """Verifica si la alerta es de advertencia"""
        return self.severity == VitalStatus.WARNING
