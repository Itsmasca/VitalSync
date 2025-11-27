from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from enum import Enum
from typing import Optional
import uuid


class VitalStatus(Enum):
    """Estado del signo vital según umbrales"""
    NORMAL = "normal"      # Dentro del rango normal
    WARNING = "warning"    # En rango de alerta (amarillo)
    CRITICAL = "critical"  # En rango crítico (rojo)


@dataclass
class Vital:
    """
    Entidad de dominio que representa una lectura de signos vitales.

    Basado en el DDL de VitalSync - Tabla vitals.
    RF-VIT-01, RF-VIT-02, RF-VIT-03, RF-VIT-04, US-11, US-12, US-13, US-14

    Métricas monitoreadas (del Product Design):
    - Heart Rate: Normal 60-100, Warning 50-59/101-120, Critical <50/>120
    - Oxygen Level: Normal 95-100, Warning 90-94, Critical <90
    - Temperature: Normal 36.1-37.2, Warning 37.3-38, Critical >38/<35
    - Steps: Normal >5000, Warning 2000-5000, Critical <2000
    """
    id: str
    member_id: str

    # Métricas principales (requeridas por el proyecto)
    heart_rate: Optional[int] = None           # bpm
    oxygen_level: Optional[float] = None       # %
    body_temperature: Optional[float] = None   # °C
    steps: Optional[int] = None                # conteo diario

    # Métricas adicionales (inspiradas en watchOS 11)
    respiratory_rate: Optional[int] = None     # respiraciones/min
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    calories_burned: Optional[int] = None
    distance_meters: Optional[float] = None

    # Estados calculados de cada métrica
    heart_rate_status: VitalStatus = VitalStatus.NORMAL
    oxygen_status: VitalStatus = VitalStatus.NORMAL
    temperature_status: VitalStatus = VitalStatus.NORMAL
    steps_status: VitalStatus = VitalStatus.NORMAL
    overall_status: VitalStatus = VitalStatus.NORMAL

    # Flag para anomalías (toggle de Node-RED - US-25)
    is_anomaly: bool = False
    anomaly_source: Optional[str] = None  # 'manual', 'node_red_toggle', 'threshold'

    # Timestamps
    reading_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create(
        member_id: str,
        heart_rate: Optional[int] = None,
        oxygen_level: Optional[float] = None,
        body_temperature: Optional[float] = None,
        steps: Optional[int] = None,
        reading_timestamp: Optional[datetime] = None
    ) -> "Vital":
        """Factory method para crear una nueva lectura de vitales"""
        now = datetime.now(timezone.utc)
        vital = Vital(
            id=str(uuid.uuid4()),
            member_id=member_id,
            heart_rate=heart_rate,
            oxygen_level=oxygen_level,
            body_temperature=body_temperature,
            steps=steps,
            reading_timestamp=reading_timestamp or now,
            received_at=now
        )
        vital.calculate_statuses()
        return vital

    def calculate_statuses(
        self,
        custom_hr_min: Optional[int] = None,
        custom_hr_max: Optional[int] = None,
        custom_spo2_min: Optional[float] = None,
        custom_temp_min: Optional[float] = None,
        custom_temp_max: Optional[float] = None,
        custom_steps_min: Optional[int] = None
    ) -> None:
        """Calcula los estados de cada métrica basado en umbrales"""
        self.heart_rate_status = self._calculate_heart_rate_status(custom_hr_min, custom_hr_max)
        self.oxygen_status = self._calculate_oxygen_status(custom_spo2_min)
        self.temperature_status = self._calculate_temperature_status(custom_temp_min, custom_temp_max)
        self.steps_status = self._calculate_steps_status(custom_steps_min)
        self.overall_status = self._calculate_overall_status()

    def _calculate_heart_rate_status(
        self,
        custom_min: Optional[int] = None,
        custom_max: Optional[int] = None
    ) -> VitalStatus:
        """Calcula el estado del heart rate"""
        if self.heart_rate is None:
            return VitalStatus.NORMAL

        min_critical = 50
        min_warning = custom_min or 60
        max_warning = custom_max or 100
        max_critical = 120

        if self.heart_rate < min_critical or self.heart_rate > max_critical:
            return VitalStatus.CRITICAL
        if self.heart_rate < min_warning or self.heart_rate > max_warning:
            return VitalStatus.WARNING
        return VitalStatus.NORMAL

    def _calculate_oxygen_status(self, custom_min: Optional[float] = None) -> VitalStatus:
        """Calcula el estado del nivel de oxígeno"""
        if self.oxygen_level is None:
            return VitalStatus.NORMAL

        min_critical = custom_min or 90
        min_warning = 95

        if self.oxygen_level < min_critical:
            return VitalStatus.CRITICAL
        if self.oxygen_level < min_warning:
            return VitalStatus.WARNING
        return VitalStatus.NORMAL

    def _calculate_temperature_status(
        self,
        custom_min: Optional[float] = None,
        custom_max: Optional[float] = None
    ) -> VitalStatus:
        """Calcula el estado de la temperatura"""
        if self.body_temperature is None:
            return VitalStatus.NORMAL

        min_critical = custom_min or 35.0
        min_warning = 36.1
        max_warning = 37.2
        max_critical = custom_max or 38.0

        if self.body_temperature < min_critical or self.body_temperature > max_critical:
            return VitalStatus.CRITICAL
        if self.body_temperature < min_warning or self.body_temperature > max_warning:
            return VitalStatus.WARNING
        return VitalStatus.NORMAL

    def _calculate_steps_status(self, custom_min: Optional[int] = None) -> VitalStatus:
        """Calcula el estado de los pasos"""
        if self.steps is None:
            return VitalStatus.NORMAL

        min_critical = custom_min or 2000
        min_warning = 5000

        if self.steps < min_critical:
            return VitalStatus.CRITICAL
        if self.steps < min_warning:
            return VitalStatus.WARNING
        return VitalStatus.NORMAL

    def _calculate_overall_status(self) -> VitalStatus:
        """Calcula el estado general (el peor de todos)"""
        statuses = [
            self.heart_rate_status,
            self.oxygen_status,
            self.temperature_status,
            self.steps_status
        ]

        if VitalStatus.CRITICAL in statuses:
            return VitalStatus.CRITICAL
        if VitalStatus.WARNING in statuses:
            return VitalStatus.WARNING
        return VitalStatus.NORMAL

    def mark_as_anomaly(self, source: str = "manual") -> None:
        """Marca la lectura como anomalía"""
        self.is_anomaly = True
        self.anomaly_source = source

    def get_reading_date(self) -> date:
        """Obtiene la fecha de la lectura (para agregaciones)"""
        return self.reading_timestamp.date()

    def is_critical(self) -> bool:
        """Verifica si la lectura tiene algún valor crítico"""
        return self.overall_status == VitalStatus.CRITICAL

    def is_warning(self) -> bool:
        """Verifica si la lectura tiene algún valor en warning"""
        return self.overall_status == VitalStatus.WARNING

    def has_blood_pressure(self) -> bool:
        """Verifica si la lectura tiene datos de presión arterial"""
        return self.blood_pressure_systolic is not None and self.blood_pressure_diastolic is not None
