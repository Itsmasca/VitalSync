from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from src.core.domain.AlertModel import Alert, AlertStatus, AlertType
from src.core.domain.VitalModel import VitalStatus


class AlertRepository(ABC):
    """
    Puerto (interface) que define el contrato para la persistencia de alertas.

    Esta abstracción permite que el dominio no dependa de ninguna implementación
    específica de base de datos, siguiendo el principio de inversión de dependencias.

    Las implementaciones concretas (adapters) deben estar en:
    src/adapters/outbound/persistance/
    """

    @abstractmethod
    async def save(self, alert: Alert) -> Alert:
        """
        Persiste una nueva alerta.

        Args:
            alert: Entidad de alerta a guardar

        Returns:
            Alerta guardada con ID asignado
        """
        pass

    @abstractmethod
    async def update(self, alert: Alert) -> Alert:
        """
        Actualiza una alerta existente.

        Args:
            alert: Entidad de alerta con los datos actualizados

        Returns:
            Alerta actualizada
        """
        pass

    @abstractmethod
    async def get_by_id(self, alert_id: str) -> Optional[Alert]:
        """
        Obtiene una alerta por su ID.

        Args:
            alert_id: ID de la alerta

        Returns:
            Alerta encontrada o None si no existe
        """
        pass

    @abstractmethod
    async def get_by_member(
        self,
        member_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Alert]:
        """
        Obtiene alertas de un familiar con paginación.

        Args:
            member_id: ID del familiar
            limit: Número máximo de resultados
            offset: Número de resultados a saltar

        Returns:
            Lista de alertas del familiar
        """
        pass

    @abstractmethod
    async def get_active(self) -> List[Alert]:
        """
        Obtiene todas las alertas activas.

        Returns:
            Lista de alertas activas
        """
        pass

    @abstractmethod
    async def get_active_by_member(self, member_id: str) -> List[Alert]:
        """
        Obtiene alertas activas de un familiar específico.

        Args:
            member_id: ID del familiar

        Returns:
            Lista de alertas activas del familiar
        """
        pass

    @abstractmethod
    async def get_active_by_family_group(self, family_group_id: str) -> List[Alert]:
        """
        Obtiene alertas activas de todos los familiares de un grupo.

        Args:
            family_group_id: ID del grupo familiar

        Returns:
            Lista de alertas activas del grupo
        """
        pass

    @abstractmethod
    async def get_by_status(self, status: AlertStatus) -> List[Alert]:
        """
        Obtiene alertas con un estado específico.

        Args:
            status: Estado a filtrar

        Returns:
            Lista de alertas con ese estado
        """
        pass

    @abstractmethod
    async def get_by_severity(self, severity: VitalStatus) -> List[Alert]:
        """
        Obtiene alertas con una severidad específica.

        Args:
            severity: Severidad a filtrar (WARNING o CRITICAL)

        Returns:
            Lista de alertas con esa severidad
        """
        pass

    @abstractmethod
    async def get_by_type(self, alert_type: AlertType) -> List[Alert]:
        """
        Obtiene alertas de un tipo específico.

        Args:
            alert_type: Tipo de alerta a filtrar

        Returns:
            Lista de alertas de ese tipo
        """
        pass

    @abstractmethod
    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        member_id: Optional[str] = None
    ) -> List[Alert]:
        """
        Obtiene alertas en un rango de fechas.

        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            member_id: ID del familiar (opcional)

        Returns:
            Lista de alertas en el rango
        """
        pass

    @abstractmethod
    async def get_recent(
        self,
        hours: int = 24,
        member_id: Optional[str] = None
    ) -> List[Alert]:
        """
        Obtiene alertas de las últimas N horas.

        Args:
            hours: Número de horas hacia atrás
            member_id: ID del familiar (opcional)

        Returns:
            Lista de alertas recientes
        """
        pass

    @abstractmethod
    async def count_active(self) -> int:
        """
        Cuenta el total de alertas activas.

        Returns:
            Número de alertas activas
        """
        pass

    @abstractmethod
    async def count_by_status(self, status: AlertStatus) -> int:
        """
        Cuenta alertas por estado.

        Args:
            status: Estado a contar

        Returns:
            Número de alertas con ese estado
        """
        pass

    @abstractmethod
    async def count_by_severity(self, severity: VitalStatus) -> int:
        """
        Cuenta alertas por severidad.

        Args:
            severity: Severidad a contar

        Returns:
            Número de alertas con esa severidad
        """
        pass

    @abstractmethod
    async def count_by_member(self, member_id: str) -> int:
        """
        Cuenta alertas de un familiar.

        Args:
            member_id: ID del familiar

        Returns:
            Número de alertas del familiar
        """
        pass

    @abstractmethod
    async def acknowledge_by_id(self, alert_id: str, user_id: str) -> Optional[Alert]:
        """
        Marca una alerta como reconocida.

        Args:
            alert_id: ID de la alerta
            user_id: ID del usuario que reconoce

        Returns:
            Alerta actualizada o None si no existe
        """
        pass

    @abstractmethod
    async def resolve_by_id(
        self,
        alert_id: str,
        notes: Optional[str] = None
    ) -> Optional[Alert]:
        """
        Marca una alerta como resuelta.

        Args:
            alert_id: ID de la alerta
            notes: Notas de resolución

        Returns:
            Alerta actualizada o None si no existe
        """
        pass

    @abstractmethod
    async def dismiss_by_id(
        self,
        alert_id: str,
        notes: Optional[str] = None
    ) -> Optional[Alert]:
        """
        Descarta una alerta (falso positivo).

        Args:
            alert_id: ID de la alerta
            notes: Notas de descarte

        Returns:
            Alerta actualizada o None si no existe
        """
        pass
