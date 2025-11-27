from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.domain.FamilyGroupModel import FamilyGroup, SubscriptionPlan


class FamilyGroupRepository(ABC):
    """
    Puerto (interface) que define el contrato para la persistencia de grupos familiares.

    Esta abstracción permite que el dominio no dependa de ninguna implementación
    específica de base de datos, siguiendo el principio de inversión de dependencias.

    Las implementaciones concretas (adapters) deben estar en:
    src/adapters/outbound/persistance/
    """

    @abstractmethod
    async def save(self, group: FamilyGroup) -> FamilyGroup:
        """
        Persiste un nuevo grupo familiar.

        Args:
            group: Entidad de grupo familiar a guardar

        Returns:
            Grupo familiar guardado con ID asignado
        """
        pass

    @abstractmethod
    async def update(self, group: FamilyGroup) -> FamilyGroup:
        """
        Actualiza un grupo familiar existente.

        Args:
            group: Entidad de grupo familiar con los datos actualizados

        Returns:
            Grupo familiar actualizado
        """
        pass

    @abstractmethod
    async def delete(self, group_id: str) -> bool:
        """
        Elimina un grupo familiar por su ID.

        Args:
            group_id: ID del grupo familiar a eliminar

        Returns:
            True si se eliminó correctamente
        """
        pass

    @abstractmethod
    async def get_by_id(self, group_id: str) -> Optional[FamilyGroup]:
        """
        Obtiene un grupo familiar por su ID.

        Args:
            group_id: ID del grupo familiar

        Returns:
            Grupo familiar encontrado o None si no existe
        """
        pass

    @abstractmethod
    async def get_by_admin_id(self, admin_id: str) -> List[FamilyGroup]:
        """
        Obtiene todos los grupos familiares de un administrador.

        Args:
            admin_id: ID del usuario administrador

        Returns:
            Lista de grupos familiares del administrador
        """
        pass

    @abstractmethod
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[FamilyGroup]:
        """
        Obtiene todos los grupos familiares con paginación.

        Args:
            limit: Número máximo de resultados
            offset: Número de resultados a saltar

        Returns:
            Lista de grupos familiares
        """
        pass

    @abstractmethod
    async def get_by_plan(self, plan: SubscriptionPlan) -> List[FamilyGroup]:
        """
        Obtiene todos los grupos familiares con un plan específico.

        Args:
            plan: Plan de suscripción a filtrar

        Returns:
            Lista de grupos familiares con ese plan
        """
        pass

    @abstractmethod
    async def get_active(self) -> List[FamilyGroup]:
        """
        Obtiene todos los grupos familiares activos.

        Returns:
            Lista de grupos familiares activos
        """
        pass

    @abstractmethod
    async def count(self) -> int:
        """
        Cuenta el total de grupos familiares.

        Returns:
            Número total de grupos familiares
        """
        pass

    @abstractmethod
    async def count_by_plan(self, plan: SubscriptionPlan) -> int:
        """
        Cuenta grupos familiares por plan.

        Args:
            plan: Plan de suscripción a contar

        Returns:
            Número de grupos familiares con ese plan
        """
        pass
