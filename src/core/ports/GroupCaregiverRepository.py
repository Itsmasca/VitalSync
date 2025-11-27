from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.domain.GroupCaregiverModel import GroupCaregiver


class GroupCaregiverRepository(ABC):
    """
    Puerto (interface) que define el contrato para la persistencia de relaciones cuidador-grupo.

    Esta abstracción permite que el dominio no dependa de ninguna implementación
    específica de base de datos, siguiendo el principio de inversión de dependencias.

    Las implementaciones concretas (adapters) deben estar en:
    src/adapters/outbound/persistance/
    """

    @abstractmethod
    async def save(self, caregiver: GroupCaregiver) -> GroupCaregiver:
        """
        Persiste una nueva relación cuidador-grupo.

        Args:
            caregiver: Entidad de relación a guardar

        Returns:
            Relación guardada con ID asignado
        """
        pass

    @abstractmethod
    async def update(self, caregiver: GroupCaregiver) -> GroupCaregiver:
        """
        Actualiza una relación cuidador-grupo existente.

        Args:
            caregiver: Entidad de relación con los datos actualizados

        Returns:
            Relación actualizada
        """
        pass

    @abstractmethod
    async def delete(self, caregiver_id: str) -> bool:
        """
        Elimina una relación cuidador-grupo por su ID.

        Args:
            caregiver_id: ID de la relación a eliminar

        Returns:
            True si se eliminó correctamente
        """
        pass

    @abstractmethod
    async def delete_by_user_and_group(self, user_id: str, group_id: str) -> bool:
        """
        Elimina una relación cuidador-grupo por user_id y group_id.

        Args:
            user_id: ID del usuario
            group_id: ID del grupo

        Returns:
            True si se eliminó correctamente
        """
        pass

    @abstractmethod
    async def get_by_id(self, caregiver_id: str) -> Optional[GroupCaregiver]:
        """
        Obtiene una relación por su ID.

        Args:
            caregiver_id: ID de la relación

        Returns:
            Relación encontrada o None si no existe
        """
        pass

    @abstractmethod
    async def get_by_user_and_group(
        self,
        user_id: str,
        group_id: str
    ) -> Optional[GroupCaregiver]:
        """
        Obtiene una relación por user_id y group_id.

        Args:
            user_id: ID del usuario
            group_id: ID del grupo

        Returns:
            Relación encontrada o None si no existe
        """
        pass

    @abstractmethod
    async def get_by_group(self, group_id: str) -> List[GroupCaregiver]:
        """
        Obtiene todos los cuidadores de un grupo.

        Args:
            group_id: ID del grupo

        Returns:
            Lista de relaciones cuidador-grupo
        """
        pass

    @abstractmethod
    async def get_by_user(self, user_id: str) -> List[GroupCaregiver]:
        """
        Obtiene todos los grupos de un cuidador.

        Args:
            user_id: ID del usuario

        Returns:
            Lista de relaciones cuidador-grupo
        """
        pass

    @abstractmethod
    async def get_with_alert_permission(self, group_id: str) -> List[GroupCaregiver]:
        """
        Obtiene cuidadores con permiso de reconocer alertas en un grupo.

        Args:
            group_id: ID del grupo

        Returns:
            Lista de relaciones con permiso de alertas
        """
        pass

    @abstractmethod
    async def get_with_edit_permission(self, group_id: str) -> List[GroupCaregiver]:
        """
        Obtiene cuidadores con permiso de editar miembros en un grupo.

        Args:
            group_id: ID del grupo

        Returns:
            Lista de relaciones con permiso de edición
        """
        pass

    @abstractmethod
    async def exists(self, user_id: str, group_id: str) -> bool:
        """
        Verifica si existe una relación entre un usuario y un grupo.

        Args:
            user_id: ID del usuario
            group_id: ID del grupo

        Returns:
            True si existe la relación
        """
        pass

    @abstractmethod
    async def count_by_group(self, group_id: str) -> int:
        """
        Cuenta el total de cuidadores en un grupo.

        Args:
            group_id: ID del grupo

        Returns:
            Número de cuidadores en el grupo
        """
        pass

    @abstractmethod
    async def count_by_user(self, user_id: str) -> int:
        """
        Cuenta el total de grupos de un cuidador.

        Args:
            user_id: ID del usuario

        Returns:
            Número de grupos del cuidador
        """
        pass
