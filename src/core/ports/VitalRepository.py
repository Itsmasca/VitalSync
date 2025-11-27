from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import List, Optional

from src.core.domain.VitalModel import Vital, VitalStatus


class VitalRepository(ABC):
    """
    Puerto (interface) que define el contrato para la persistencia de lecturas de signos vitales.

    Esta abstracción permite que el dominio no dependa de ninguna implementación
    específica de base de datos, siguiendo el principio de inversión de dependencias.

    Las implementaciones concretas (adapters) deben estar en:
    src/adapters/outbound/persistance/
    """

    @abstractmethod
    async def save(self, vital: Vital) -> Vital:
        """
        Persiste una nueva lectura de signos vitales.

        Args:
            vital: Entidad de lectura vital a guardar

        Returns:
            Lectura guardada con ID asignado
        """
        pass

    @abstractmethod
    async def save_batch(self, vitals: List[Vital]) -> List[Vital]:
        """
        Persiste múltiples lecturas de signos vitales en batch.

        Args:
            vitals: Lista de lecturas vitales a guardar

        Returns:
            Lista de lecturas guardadas
        """
        pass

    @abstractmethod
    async def get_by_id(self, vital_id: str) -> Optional[Vital]:
        """
        Obtiene una lectura de signos vitales por su ID.

        Args:
            vital_id: ID de la lectura

        Returns:
            Lectura encontrada o None si no existe
        """
        pass

    @abstractmethod
    async def get_latest_by_member(self, member_id: str) -> Optional[Vital]:
        """
        Obtiene la última lectura de un familiar monitoreado.

        Args:
            member_id: ID del familiar

        Returns:
            Última lectura del familiar o None
        """
        pass

    @abstractmethod
    async def get_by_member(
        self,
        member_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Vital]:
        """
        Obtiene lecturas de un familiar con paginación.

        Args:
            member_id: ID del familiar
            limit: Número máximo de resultados
            offset: Número de resultados a saltar

        Returns:
            Lista de lecturas del familiar
        """
        pass

    @abstractmethod
    async def get_by_member_and_date_range(
        self,
        member_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Vital]:
        """
        Obtiene lecturas de un familiar en un rango de fechas.

        Args:
            member_id: ID del familiar
            start_date: Fecha de inicio
            end_date: Fecha de fin

        Returns:
            Lista de lecturas en el rango
        """
        pass

    @abstractmethod
    async def get_by_member_since(
        self,
        member_id: str,
        since: datetime
    ) -> List[Vital]:
        """
        Obtiene lecturas de un familiar desde una fecha específica.
        Útil para análisis de tendencias en ML.

        Args:
            member_id: ID del familiar
            since: Fecha desde la cual obtener lecturas

        Returns:
            Lista de lecturas desde esa fecha
        """
        pass

    @abstractmethod
    async def get_by_member_last_minutes(
        self,
        member_id: str,
        minutes: int = 2
    ) -> List[Vital]:
        """
        Obtiene lecturas de un familiar de los últimos N minutos.
        Útil para el gráfico rolling del dashboard (RF-DASH-02).

        Args:
            member_id: ID del familiar
            minutes: Número de minutos hacia atrás

        Returns:
            Lista de lecturas en ese período
        """
        pass

    @abstractmethod
    async def get_by_status(self, status: VitalStatus) -> List[Vital]:
        """
        Obtiene lecturas con un estado específico.

        Args:
            status: Estado a filtrar

        Returns:
            Lista de lecturas con ese estado
        """
        pass

    @abstractmethod
    async def get_anomalies(self, member_id: Optional[str] = None) -> List[Vital]:
        """
        Obtiene lecturas marcadas como anomalías.

        Args:
            member_id: ID del familiar (opcional, si no se pasa trae todas)

        Returns:
            Lista de lecturas anómalas
        """
        pass

    @abstractmethod
    async def get_critical_readings(
        self,
        member_id: Optional[str] = None,
        hours: int = 24
    ) -> List[Vital]:
        """
        Obtiene lecturas críticas de las últimas N horas.

        Args:
            member_id: ID del familiar (opcional)
            hours: Número de horas hacia atrás

        Returns:
            Lista de lecturas críticas
        """
        pass

    @abstractmethod
    async def count_by_member(self, member_id: str) -> int:
        """
        Cuenta el total de lecturas de un familiar.

        Args:
            member_id: ID del familiar

        Returns:
            Número total de lecturas
        """
        pass

    @abstractmethod
    async def count_by_date(self, reading_date: date) -> int:
        """
        Cuenta lecturas por fecha.

        Args:
            reading_date: Fecha a contar

        Returns:
            Número de lecturas en esa fecha
        """
        pass

    @abstractmethod
    async def count_readings_last_hour(self) -> int:
        """
        Cuenta lecturas de la última hora (para health check).

        Returns:
            Número de lecturas en la última hora
        """
        pass

    @abstractmethod
    async def delete_old_readings(self, days: int) -> int:
        """
        Elimina lecturas más antiguas que N días.
        Útil para limpieza según el plan de suscripción.

        Args:
            days: Número de días de antigüedad

        Returns:
            Número de lecturas eliminadas
        """
        pass

    @abstractmethod
    async def get_daily_averages(
        self,
        member_id: str,
        start_date: date,
        end_date: date
    ) -> List[dict]:
        """
        Obtiene promedios diarios de métricas para un familiar.

        Args:
            member_id: ID del familiar
            start_date: Fecha de inicio
            end_date: Fecha de fin

        Returns:
            Lista de diccionarios con promedios por día
        """
        pass
