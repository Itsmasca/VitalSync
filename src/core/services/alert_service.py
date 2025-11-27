from typing import List, Optional
from datetime import datetime

from src.core.domain.AlertModel import Alert, AlertStatus, AlertType
from src.core.domain.VitalModel import VitalStatus
from src.core.ports.AlertRepository import AlertRepository


class AlertService:
    """
    Servicio de aplicación para gestión de alertas.
    Contiene los casos de uso relacionados con alertas.
    RF-VIT-05, RF-DASH-05, US-23, US-24, US-26
    """

    def __init__(self, alert_repository: AlertRepository):
        self.alert_repository = alert_repository

    async def get_alert_by_id(self, alert_id: str) -> Optional[Alert]:
        """Obtiene una alerta por su ID"""
        return await self.alert_repository.get_by_id(alert_id)

    async def get_active_alerts(self) -> List[Alert]:
        """
        Obtiene todas las alertas activas.
        RF-DASH-05: Panel de alertas
        US-24: Como cuidador, quiero ver alertas activas
        """
        return await self.alert_repository.get_active()

    async def get_active_alerts_by_member(self, member_id: str) -> List[Alert]:
        """Obtiene alertas activas de un familiar"""
        return await self.alert_repository.get_active_by_member(member_id)

    async def get_active_alerts_by_family(self, family_group_id: str) -> List[Alert]:
        """Obtiene alertas activas de un grupo familiar"""
        return await self.alert_repository.get_active_by_family_group(family_group_id)

    async def get_alerts_by_member(
        self,
        member_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Alert]:
        """Obtiene alertas de un familiar con paginación"""
        return await self.alert_repository.get_by_member(member_id, limit, offset)

    async def get_alerts_by_status(self, status: AlertStatus) -> List[Alert]:
        """Obtiene alertas por estado"""
        return await self.alert_repository.get_by_status(status)

    async def get_alerts_by_severity(self, severity: VitalStatus) -> List[Alert]:
        """Obtiene alertas por severidad (WARNING o CRITICAL)"""
        return await self.alert_repository.get_by_severity(severity)

    async def get_alerts_by_type(self, alert_type: AlertType) -> List[Alert]:
        """Obtiene alertas por tipo"""
        return await self.alert_repository.get_by_type(alert_type)

    async def get_alerts_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        member_id: Optional[str] = None
    ) -> List[Alert]:
        """
        Obtiene alertas en un rango de fechas.
        US-26: Como cuidador, quiero ver historial de alertas
        """
        return await self.alert_repository.get_by_date_range(
            start_date, end_date, member_id
        )

    async def get_recent_alerts(
        self,
        hours: int = 24,
        member_id: Optional[str] = None
    ) -> List[Alert]:
        """Obtiene alertas de las últimas N horas"""
        return await self.alert_repository.get_recent(hours, member_id)

    async def acknowledge_alert(self, alert_id: str, user_id: str) -> Optional[Alert]:
        """
        Marca una alerta como reconocida por un usuario.
        US-24: Como cuidador, quiero reconocer alertas
        """
        return await self.alert_repository.acknowledge_by_id(alert_id, user_id)

    async def resolve_alert(
        self,
        alert_id: str,
        notes: Optional[str] = None
    ) -> Optional[Alert]:
        """
        Marca una alerta como resuelta.
        """
        return await self.alert_repository.resolve_by_id(alert_id, notes)

    async def dismiss_alert(
        self,
        alert_id: str,
        notes: Optional[str] = None
    ) -> Optional[Alert]:
        """
        Descarta una alerta (falso positivo).
        """
        return await self.alert_repository.dismiss_by_id(alert_id, notes)

    async def count_active_alerts(self) -> int:
        """Cuenta alertas activas (para health check y dashboard)"""
        return await self.alert_repository.count_active()

    async def count_alerts_by_status(self, status: AlertStatus) -> int:
        """Cuenta alertas por estado"""
        return await self.alert_repository.count_by_status(status)

    async def count_alerts_by_severity(self, severity: VitalStatus) -> int:
        """Cuenta alertas por severidad"""
        return await self.alert_repository.count_by_severity(severity)

    async def count_alerts_by_member(self, member_id: str) -> int:
        """Cuenta alertas de un familiar"""
        return await self.alert_repository.count_by_member(member_id)

    async def get_critical_alerts(self) -> List[Alert]:
        """Obtiene alertas críticas activas (prioridad máxima)"""
        alerts = await self.alert_repository.get_active()
        return [a for a in alerts if a.is_critical()]

    async def get_warning_alerts(self) -> List[Alert]:
        """Obtiene alertas de advertencia activas"""
        alerts = await self.alert_repository.get_active()
        return [a for a in alerts if a.is_warning()]
