from typing import List, Optional
from datetime import datetime, timezone

from src.core.domain.FamilyGroupModel import FamilyGroup, SubscriptionPlan
from src.core.domain.GroupCaregiverModel import GroupCaregiver
from src.core.ports.FamilyGroupRepository import FamilyGroupRepository
from src.core.ports.GroupCaregiverRepository import GroupCaregiverRepository


class FamilyGroupService:
    """
    Servicio de aplicación para gestión de grupos familiares.
    Contiene los casos de uso relacionados con grupos familiares.
    RF-FAM-01, RF-FAM-03, US-05, US-07
    """

    def __init__(
        self,
        family_group_repository: FamilyGroupRepository,
        group_caregiver_repository: GroupCaregiverRepository
    ):
        self.family_group_repository = family_group_repository
        self.group_caregiver_repository = group_caregiver_repository

    async def create_group(
        self,
        name: str,
        admin_id: str,
        description: Optional[str] = None,
        plan: SubscriptionPlan = SubscriptionPlan.FREE
    ) -> FamilyGroup:
        """
        Crea un nuevo grupo familiar.
        RF-FAM-01: Crear grupo familiar
        US-05: Como administrador, quiero crear mi grupo familiar
        """
        group = FamilyGroup.create(
            name=name,
            admin_id=admin_id,
            plan=plan,
            description=description
        )
        return await self.family_group_repository.save(group)

    async def get_group_by_id(self, group_id: str) -> Optional[FamilyGroup]:
        """Obtiene un grupo familiar por su ID"""
        return await self.family_group_repository.get_by_id(group_id)

    async def get_groups_by_admin(self, admin_id: str) -> List[FamilyGroup]:
        """Obtiene todos los grupos de un administrador"""
        return await self.family_group_repository.get_by_admin_id(admin_id)

    async def get_groups_by_caregiver(self, user_id: str) -> List[FamilyGroup]:
        """Obtiene todos los grupos donde el usuario es cuidador"""
        memberships = await self.group_caregiver_repository.get_by_user(user_id)
        groups = []
        for membership in memberships:
            group = await self.family_group_repository.get_by_id(membership.group_id)
            if group:
                groups.append(group)
        return groups

    async def get_all_groups(self, limit: int = 100, offset: int = 0) -> List[FamilyGroup]:
        """Obtiene todos los grupos con paginación"""
        return await self.family_group_repository.get_all(limit, offset)

    async def update_group(self, group: FamilyGroup) -> FamilyGroup:
        """Actualiza un grupo familiar"""
        return await self.family_group_repository.update(group)

    async def delete_group(self, group_id: str) -> bool:
        """Elimina un grupo familiar"""
        return await self.family_group_repository.delete(group_id)

    async def upgrade_plan(
        self,
        group_id: str,
        new_plan: SubscriptionPlan,
        expires_at: Optional[datetime] = None
    ) -> Optional[FamilyGroup]:
        """
        Actualiza el plan de suscripción de un grupo.
        """
        group = await self.family_group_repository.get_by_id(group_id)
        if group is None:
            return None

        group.upgrade_plan(new_plan, expires_at)
        return await self.family_group_repository.update(group)

    async def add_caregiver(
        self,
        group_id: str,
        user_id: str,
        invited_by: str,
        can_acknowledge_alerts: bool = True,
        can_view_history: bool = True,
        can_edit_members: bool = False
    ) -> GroupCaregiver:
        """
        Agrega un cuidador a un grupo familiar.
        RF-FAM-03: Agregar cuidadores
        US-07: Como administrador, quiero invitar cuidadores
        """
        # Verificar si ya existe la relación
        existing = await self.group_caregiver_repository.get_by_user_and_group(user_id, group_id)
        if existing:
            raise ValueError("El usuario ya es cuidador de este grupo")

        caregiver = GroupCaregiver.create(
            group_id=group_id,
            user_id=user_id,
            invited_by=invited_by,
            can_acknowledge_alerts=can_acknowledge_alerts,
            can_view_history=can_view_history,
            can_edit_members=can_edit_members
        )
        return await self.group_caregiver_repository.save(caregiver)

    async def remove_caregiver(self, group_id: str, user_id: str) -> bool:
        """Elimina un cuidador de un grupo"""
        return await self.group_caregiver_repository.delete_by_user_and_group(user_id, group_id)

    async def get_caregivers(self, group_id: str) -> List[GroupCaregiver]:
        """Obtiene todos los cuidadores de un grupo"""
        return await self.group_caregiver_repository.get_by_group(group_id)

    async def update_caregiver_permissions(
        self,
        group_id: str,
        user_id: str,
        can_acknowledge_alerts: Optional[bool] = None,
        can_view_history: Optional[bool] = None,
        can_edit_members: Optional[bool] = None
    ) -> Optional[GroupCaregiver]:
        """Actualiza los permisos de un cuidador"""
        caregiver = await self.group_caregiver_repository.get_by_user_and_group(user_id, group_id)
        if caregiver is None:
            return None

        if can_acknowledge_alerts is not None:
            if can_acknowledge_alerts:
                caregiver.grant_alert_permission()
            else:
                caregiver.revoke_alert_permission()

        if can_view_history is not None:
            if can_view_history:
                caregiver.grant_history_permission()
            else:
                caregiver.revoke_history_permission()

        if can_edit_members is not None:
            if can_edit_members:
                caregiver.grant_edit_permission()
            else:
                caregiver.revoke_edit_permission()

        return await self.group_caregiver_repository.update(caregiver)

    async def is_user_in_group(self, user_id: str, group_id: str) -> bool:
        """Verifica si un usuario tiene acceso a un grupo (como admin o cuidador)"""
        group = await self.family_group_repository.get_by_id(group_id)
        if group and group.admin_id == user_id:
            return True
        return await self.group_caregiver_repository.exists(user_id, group_id)

    async def get_groups_by_plan(self, plan: SubscriptionPlan) -> List[FamilyGroup]:
        """Obtiene grupos por plan de suscripción"""
        return await self.family_group_repository.get_by_plan(plan)

    async def count_groups(self) -> int:
        """Cuenta el total de grupos"""
        return await self.family_group_repository.count()

    async def count_caregivers(self, group_id: str) -> int:
        """Cuenta cuidadores en un grupo"""
        return await self.group_caregiver_repository.count_by_group(group_id)
