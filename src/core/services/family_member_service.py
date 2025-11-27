from typing import List, Optional

from src.core.domain.FamilyMemberModel import (
    FamilyMember, RelationshipType, DeviceType, VitalThresholds
)
from src.core.domain.FamilyGroupModel import FamilyGroup
from src.core.ports.FamilyMemberRepository import FamilyMemberRepository
from src.core.ports.FamilyGroupRepository import FamilyGroupRepository


class FamilyMemberService:
    """
    Servicio de aplicación para gestión de familiares monitoreados.
    Contiene los casos de uso relacionados con familiares.
    RF-FAM-02, RF-FAM-04, US-06, US-08, US-09, US-10, US-21
    """

    def __init__(
        self,
        family_member_repository: FamilyMemberRepository,
        family_group_repository: FamilyGroupRepository
    ):
        self.family_member_repository = family_member_repository
        self.family_group_repository = family_group_repository

    async def create_member(
        self,
        family_id: str,
        member_id: str,
        name: str,
        relationship: RelationshipType,
        device_id: str,
        device_type: DeviceType,
        device_name: Optional[str] = None
    ) -> FamilyMember:
        """
        Registra un nuevo familiar monitoreado.
        RF-FAM-02: Registrar familiar
        US-06: Como administrador, quiero registrar familiares
        """
        # Verificar que el grupo existe y tiene espacio
        group = await self.family_group_repository.get_by_id(family_id)
        if group is None:
            raise ValueError("Grupo familiar no encontrado")

        # Verificar límite del plan
        current_count = await self.family_member_repository.count_by_family(family_id)
        max_members = group.get_max_members()
        if current_count >= max_members:
            raise ValueError(f"El plan {group.plan.value} permite máximo {max_members} familiares")

        # Verificar que member_id y device_id sean únicos
        if await self.family_member_repository.exists_by_member_id(member_id):
            raise ValueError(f"El member_id {member_id} ya está registrado")

        if await self.family_member_repository.exists_by_device_id(device_id):
            raise ValueError(f"El device_id {device_id} ya está registrado")

        member = FamilyMember.create(
            family_id=family_id,
            member_id=member_id,
            name=name,
            relationship=relationship,
            device_id=device_id,
            device_type=device_type,
            device_name=device_name
        )
        return await self.family_member_repository.save(member)

    async def get_member_by_id(self, member_id: str) -> Optional[FamilyMember]:
        """Obtiene un familiar por su ID (UUID)"""
        return await self.family_member_repository.get_by_id(member_id)

    async def get_member_by_member_id(self, member_id: str) -> Optional[FamilyMember]:
        """Obtiene un familiar por su member_id (formato: familia-apellido-relacion)"""
        return await self.family_member_repository.get_by_member_id(member_id)

    async def get_member_by_device_id(self, device_id: str) -> Optional[FamilyMember]:
        """
        Obtiene un familiar por su device_id.
        Útil para recibir datos de IoT.
        """
        return await self.family_member_repository.get_by_device_id(device_id)

    async def get_members_by_family(self, family_id: str) -> List[FamilyMember]:
        """Obtiene todos los familiares de un grupo"""
        return await self.family_member_repository.get_by_family_id(family_id)

    async def get_active_members_by_family(self, family_id: str) -> List[FamilyMember]:
        """Obtiene familiares activos de un grupo"""
        return await self.family_member_repository.get_active_by_family(family_id)

    async def update_member(self, member: FamilyMember) -> FamilyMember:
        """Actualiza un familiar"""
        return await self.family_member_repository.update(member)

    async def delete_member(self, member_id: str) -> bool:
        """Elimina un familiar"""
        return await self.family_member_repository.delete(member_id)

    async def update_device(
        self,
        member_id: str,
        device_id: str,
        device_type: DeviceType,
        device_name: Optional[str] = None
    ) -> Optional[FamilyMember]:
        """
        Actualiza el dispositivo de un familiar.
        US-08: Como administrador, quiero cambiar el dispositivo de un familiar
        """
        member = await self.family_member_repository.get_by_id(member_id)
        if member is None:
            return None

        # Verificar que el nuevo device_id no esté en uso (si es diferente)
        if member.device_id != device_id:
            if await self.family_member_repository.exists_by_device_id(device_id):
                raise ValueError(f"El device_id {device_id} ya está registrado")

        member.update_device(device_id, device_type, device_name)
        return await self.family_member_repository.update(member)

    async def set_custom_thresholds(
        self,
        member_id: str,
        thresholds: VitalThresholds
    ) -> Optional[FamilyMember]:
        """
        Configura umbrales personalizados para un familiar.
        US-21: Como cuidador, quiero configurar umbrales personalizados
        """
        member = await self.family_member_repository.get_by_id(member_id)
        if member is None:
            return None

        member.set_thresholds(thresholds)
        return await self.family_member_repository.update(member)

    async def enable_alerts(self, member_id: str) -> Optional[FamilyMember]:
        """Habilita alertas para un familiar"""
        member = await self.family_member_repository.get_by_id(member_id)
        if member is None:
            return None

        member.enable_alerts()
        return await self.family_member_repository.update(member)

    async def disable_alerts(self, member_id: str) -> Optional[FamilyMember]:
        """Deshabilita alertas para un familiar"""
        member = await self.family_member_repository.get_by_id(member_id)
        if member is None:
            return None

        member.disable_alerts()
        return await self.family_member_repository.update(member)

    async def set_emergency_contact(
        self,
        member_id: str,
        contact: str,
        phone: str
    ) -> Optional[FamilyMember]:
        """
        Configura el contacto de emergencia de un familiar.
        US-09: Como administrador, quiero agregar contacto de emergencia
        """
        member = await self.family_member_repository.get_by_id(member_id)
        if member is None:
            return None

        member.set_emergency_contact(contact, phone)
        return await self.family_member_repository.update(member)

    async def deactivate_member(self, member_id: str) -> Optional[FamilyMember]:
        """Desactiva un familiar"""
        member = await self.family_member_repository.get_by_id(member_id)
        if member is None:
            return None

        member.deactivate()
        return await self.family_member_repository.update(member)

    async def activate_member(self, member_id: str) -> Optional[FamilyMember]:
        """Activa un familiar"""
        member = await self.family_member_repository.get_by_id(member_id)
        if member is None:
            return None

        member.activate()
        return await self.family_member_repository.update(member)

    async def get_members_by_device_type(self, device_type: DeviceType) -> List[FamilyMember]:
        """Obtiene familiares por tipo de dispositivo"""
        return await self.family_member_repository.get_by_device_type(device_type)

    async def get_members_with_alerts_enabled(self, family_id: str) -> List[FamilyMember]:
        """Obtiene familiares con alertas habilitadas"""
        return await self.family_member_repository.get_with_alerts_enabled(family_id)

    async def count_members_by_family(self, family_id: str) -> int:
        """Cuenta familiares en un grupo"""
        return await self.family_member_repository.count_by_family(family_id)
