from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


@dataclass
class GroupCaregiver:
    """
    Entidad de dominio que representa la relación entre un grupo familiar y un cuidador.

    Basado en el DDL de VitalSync - Tabla group_caregivers.
    RF-FAM-03, US-07
    """
    id: str
    group_id: str
    user_id: str
    can_acknowledge_alerts: bool = True
    can_view_history: bool = True
    can_edit_members: bool = False
    joined_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    invited_by: Optional[str] = None

    @staticmethod
    def create(
        group_id: str,
        user_id: str,
        invited_by: Optional[str] = None,
        can_acknowledge_alerts: bool = True,
        can_view_history: bool = True,
        can_edit_members: bool = False
    ) -> "GroupCaregiver":
        """Factory method para crear una nueva relación cuidador-grupo"""
        return GroupCaregiver(
            id=str(uuid.uuid4()),
            group_id=group_id,
            user_id=user_id,
            can_acknowledge_alerts=can_acknowledge_alerts,
            can_view_history=can_view_history,
            can_edit_members=can_edit_members,
            joined_at=datetime.now(timezone.utc),
            invited_by=invited_by
        )

    def grant_alert_permission(self) -> None:
        """Otorga permiso para reconocer alertas"""
        self.can_acknowledge_alerts = True

    def revoke_alert_permission(self) -> None:
        """Revoca permiso para reconocer alertas"""
        self.can_acknowledge_alerts = False

    def grant_history_permission(self) -> None:
        """Otorga permiso para ver historial"""
        self.can_view_history = True

    def revoke_history_permission(self) -> None:
        """Revoca permiso para ver historial"""
        self.can_view_history = False

    def grant_edit_permission(self) -> None:
        """Otorga permiso para editar miembros"""
        self.can_edit_members = True

    def revoke_edit_permission(self) -> None:
        """Revoca permiso para editar miembros"""
        self.can_edit_members = False

    def has_full_access(self) -> bool:
        """Verifica si tiene todos los permisos"""
        return self.can_acknowledge_alerts and self.can_view_history and self.can_edit_members
