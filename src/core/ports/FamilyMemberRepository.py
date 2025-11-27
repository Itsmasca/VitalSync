from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.domain.FamilyMemberModel import FamilyMember, RelationshipType, DeviceType


class FamilyMemberRepository(ABC):
    """
    Puerto (interface) que define el contrato para la persistencia de familiares monitoreados.

    Esta abstracción permite que el dominio no dependa de ninguna implementación
    específica de base de datos, siguiendo el principio de inversión de dependencias.

    Las implementaciones concretas (adapters) deben estar en:
    src/adapters/outbound/persistance/
    """

    @abstractmethod
    async def save(self, member: FamilyMember) -> FamilyMember:
        """
        Persiste un nuevo familiar monitoreado.

        Args:
            member: Entidad de familiar a guardar

        Returns:
            Familiar guardado con ID asignado
        """
        pass

    @abstractmethod
    async def update(self, member: FamilyMember) -> FamilyMember:
        """
        Actualiza un familiar monitoreado existente.

        Args:
            member: Entidad de familiar con los datos actualizados

        Returns:
            Familiar actualizado
        """
        pass

    @abstractmethod
    async def delete(self, member_id: str) -> bool:
        """
        Elimina un familiar monitoreado por su ID.

        Args:
            member_id: ID del familiar a eliminar

        Returns:
            True si se eliminó correctamente
        """
        pass

    @abstractmethod
    async def get_by_id(self, member_id: str) -> Optional[FamilyMember]:
        """
        Obtiene un familiar monitoreado por su ID (UUID).

        Args:
            member_id: ID del familiar

        Returns:
            Familiar encontrado o None si no existe
        """
        pass

    @abstractmethod
    async def get_by_member_id(self, member_id: str) -> Optional[FamilyMember]:
        """
        Obtiene un familiar monitoreado por su member_id (formato: "familia-apellido-relacion").

        Args:
            member_id: Member ID del familiar

        Returns:
            Familiar encontrado o None si no existe
        """
        pass

    @abstractmethod
    async def get_by_device_id(self, device_id: str) -> Optional[FamilyMember]:
        """
        Obtiene un familiar monitoreado por su device_id.

        Args:
            device_id: ID del dispositivo

        Returns:
            Familiar encontrado o None si no existe
        """
        pass

    @abstractmethod
    async def get_by_family_id(self, family_id: str) -> List[FamilyMember]:
        """
        Obtiene todos los familiares monitoreados de un grupo familiar.

        Args:
            family_id: ID del grupo familiar

        Returns:
            Lista de familiares del grupo
        """
        pass

    @abstractmethod
    async def get_by_relationship(
        self,
        family_id: str,
        relationship: RelationshipType
    ) -> List[FamilyMember]:
        """
        Obtiene familiares de un grupo por tipo de relación.

        Args:
            family_id: ID del grupo familiar
            relationship: Tipo de relación a filtrar

        Returns:
            Lista de familiares con esa relación
        """
        pass

    @abstractmethod
    async def get_by_device_type(self, device_type: DeviceType) -> List[FamilyMember]:
        """
        Obtiene todos los familiares con un tipo de dispositivo específico.

        Args:
            device_type: Tipo de dispositivo a filtrar

        Returns:
            Lista de familiares con ese tipo de dispositivo
        """
        pass

    @abstractmethod
    async def get_active_by_family(self, family_id: str) -> List[FamilyMember]:
        """
        Obtiene todos los familiares activos de un grupo familiar.

        Args:
            family_id: ID del grupo familiar

        Returns:
            Lista de familiares activos del grupo
        """
        pass

    @abstractmethod
    async def get_with_alerts_enabled(self, family_id: str) -> List[FamilyMember]:
        """
        Obtiene familiares con alertas habilitadas de un grupo.

        Args:
            family_id: ID del grupo familiar

        Returns:
            Lista de familiares con alertas habilitadas
        """
        pass

    @abstractmethod
    async def count_by_family(self, family_id: str) -> int:
        """
        Cuenta el total de familiares de un grupo.

        Args:
            family_id: ID del grupo familiar

        Returns:
            Número total de familiares en el grupo
        """
        pass

    @abstractmethod
    async def exists_by_device_id(self, device_id: str) -> bool:
        """
        Verifica si existe un familiar con el device_id dado.

        Args:
            device_id: Device ID a verificar

        Returns:
            True si existe, False en caso contrario
        """
        pass

    @abstractmethod
    async def exists_by_member_id(self, member_id: str) -> bool:
        """
        Verifica si existe un familiar con el member_id dado.

        Args:
            member_id: Member ID a verificar

        Returns:
            True si existe, False en caso contrario
        """
        pass
