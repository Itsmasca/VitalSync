from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class SubscriptionPlan(Enum):
    """Planes de suscripción de VitalSync"""
    FREE = "free"          # 1 familiar, 24h historial, alertas básicas
    FAMILIAR = "familiar"  # $99 MXN/mes - 5 familiares, 30 días historial
    PREMIUM = "premium"    # $199 MXN/mes - Ilimitados, 1 año historial


@dataclass
class FamilyGroup:
    """
    Entidad de dominio que representa un grupo familiar.

    Basado en el DDL de VitalSync - Tabla family_groups.
    RF-FAM-01, US-05
    """
    id: str
    name: str
    admin_id: str
    plan: SubscriptionPlan = SubscriptionPlan.FREE
    description: Optional[str] = None
    plan_started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    plan_expires_at: Optional[datetime] = None
    timezone_str: str = "America/Mexico_City"
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create(
        name: str,
        admin_id: str,
        plan: SubscriptionPlan = SubscriptionPlan.FREE,
        description: Optional[str] = None
    ) -> "FamilyGroup":
        """Factory method para crear un nuevo grupo familiar"""
        now = datetime.now(timezone.utc)
        return FamilyGroup(
            id=str(uuid.uuid4()),
            name=name,
            admin_id=admin_id,
            plan=plan,
            description=description,
            plan_started_at=now,
            is_active=True,
            created_at=now,
            updated_at=now
        )

    def get_max_members(self) -> int:
        """Retorna el máximo de familiares según el plan"""
        limits = {
            SubscriptionPlan.FREE: 1,
            SubscriptionPlan.FAMILIAR: 5,
            SubscriptionPlan.PREMIUM: 999  # Ilimitados
        }
        return limits.get(self.plan, 1)

    def upgrade_plan(self, new_plan: SubscriptionPlan, expires_at: Optional[datetime] = None) -> None:
        """Actualiza el plan de suscripción"""
        self.plan = new_plan
        self.plan_started_at = datetime.now(timezone.utc)
        self.plan_expires_at = expires_at
        self._update_timestamp()

    def deactivate(self) -> None:
        """Desactiva el grupo familiar"""
        self.is_active = False
        self._update_timestamp()

    def activate(self) -> None:
        """Activa el grupo familiar"""
        self.is_active = True
        self._update_timestamp()

    def is_plan_expired(self) -> bool:
        """Verifica si el plan ha expirado"""
        if self.plan_expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.plan_expires_at

    def _update_timestamp(self) -> None:
        """Actualiza el timestamp de modificación"""
        self.updated_at = datetime.now(timezone.utc)
