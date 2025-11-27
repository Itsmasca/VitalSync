from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from enum import Enum
from typing import Optional
import uuid


class RelationshipType(Enum):
    """Tipo de relación con el familiar monitoreado"""
    SELF = "self"        # El propio usuario monitoreado
    PADRE = "padre"      # Padre
    MADRE = "madre"      # Madre
    HIJO = "hijo"        # Hijo/Hija
    ABUELO = "abuelo"    # Abuelo/Abuela
    ESPOSO = "esposo"    # Esposo/Esposa
    HERMANO = "hermano"  # Hermano/Hermana
    OTRO = "otro"        # Otra relación


class DeviceType(Enum):
    """Tipo de dispositivo wearable"""
    APPLE_WATCH = "apple_watch"
    XIAOMI_BAND = "xiaomi_band"
    FITBIT = "fitbit"
    GARMIN = "garmin"
    SAMSUNG_WATCH = "samsung_watch"
    HUAWEI_BAND = "huawei_band"
    NODE_RED_SIM = "node_red_sim"  # Simulador Node-RED para MVP
    OTHER = "other"


class Gender(Enum):
    """Género del familiar"""
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"


@dataclass
class VitalThresholds:
    """Umbrales personalizados de signos vitales"""
    hr_min: Optional[int] = None      # Heart Rate mínimo (default: 50)
    hr_max: Optional[int] = None      # Heart Rate máximo (default: 120)
    spo2_min: Optional[float] = None  # Oxygen Level mínimo (default: 90)
    temp_min: Optional[float] = None  # Temperature mínimo (default: 35.0)
    temp_max: Optional[float] = None  # Temperature máximo (default: 38.0)
    steps_min: Optional[int] = None   # Steps mínimo diario (default: 2000)


@dataclass
class FamilyMember:
    """
    Entidad de dominio que representa un familiar monitoreado.

    Basado en el DDL de VitalSync - Tabla family_members.
    RF-FAM-02, RF-FAM-04, US-06, US-08, US-09, US-10, US-21
    """
    id: str
    family_id: str
    member_id: str  # Formato: "familia-apellido-relacion"
    name: str
    relationship: RelationshipType
    device_id: str  # Formato: "MARCA-PERSONA-###"
    device_type: DeviceType
    device_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    medical_notes: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    thresholds: VitalThresholds = field(default_factory=VitalThresholds)
    is_active: bool = True
    alerts_enabled: bool = True
    avatar_url: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create(
        family_id: str,
        member_id: str,
        name: str,
        relationship: RelationshipType,
        device_id: str,
        device_type: DeviceType,
        device_name: Optional[str] = None
    ) -> "FamilyMember":
        """Factory method para crear un nuevo familiar monitoreado"""
        now = datetime.now(timezone.utc)
        return FamilyMember(
            id=str(uuid.uuid4()),
            family_id=family_id,
            member_id=member_id,
            name=name,
            relationship=relationship,
            device_id=device_id,
            device_type=device_type,
            device_name=device_name,
            is_active=True,
            alerts_enabled=True,
            created_at=now,
            updated_at=now
        )

    def get_age(self) -> Optional[int]:
        """Calcula la edad del familiar"""
        if self.date_of_birth is None:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    def set_thresholds(self, thresholds: VitalThresholds) -> None:
        """Establece umbrales personalizados"""
        self.thresholds = thresholds
        self._update_timestamp()

    def enable_alerts(self) -> None:
        """Habilita las alertas para este familiar"""
        self.alerts_enabled = True
        self._update_timestamp()

    def disable_alerts(self) -> None:
        """Deshabilita las alertas para este familiar"""
        self.alerts_enabled = False
        self._update_timestamp()

    def deactivate(self) -> None:
        """Desactiva el familiar monitoreado"""
        self.is_active = False
        self._update_timestamp()

    def activate(self) -> None:
        """Activa el familiar monitoreado"""
        self.is_active = True
        self._update_timestamp()

    def update_device(self, device_id: str, device_type: DeviceType, device_name: Optional[str] = None) -> None:
        """Actualiza la información del dispositivo"""
        self.device_id = device_id
        self.device_type = device_type
        self.device_name = device_name
        self._update_timestamp()

    def set_emergency_contact(self, contact: str, phone: str) -> None:
        """Establece el contacto de emergencia"""
        self.emergency_contact = contact
        self.emergency_phone = phone
        self._update_timestamp()

    def _update_timestamp(self) -> None:
        """Actualiza el timestamp de modificación"""
        self.updated_at = datetime.now(timezone.utc)
