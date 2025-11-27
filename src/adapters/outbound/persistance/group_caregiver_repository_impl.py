from typing import List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.domain.GroupCaregiverModel import GroupCaregiver
from src.core.ports.GroupCaregiverRepository import GroupCaregiverRepository
from src.adapters.outbound.persistance.entities import GroupCaregiverEntity
from src.adapters.outbound.persistance.mappers import GroupCaregiverMapper


class GroupCaregiverRepositoryImpl(GroupCaregiverRepository):
    """Implementación del repositorio de relaciones cuidador-grupo con SQLAlchemy"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, caregiver: GroupCaregiver) -> GroupCaregiver:
        entity = GroupCaregiverMapper.to_entity(caregiver)
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return GroupCaregiverMapper.to_domain(entity)

    async def update(self, caregiver: GroupCaregiver) -> GroupCaregiver:
        stmt = select(GroupCaregiverEntity).where(GroupCaregiverEntity.id == caregiver.id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity is None:
            raise ValueError(f"GroupCaregiver with id {caregiver.id} not found")

        entity.can_acknowledge_alerts = caregiver.can_acknowledge_alerts
        entity.can_view_history = caregiver.can_view_history
        entity.can_edit_members = caregiver.can_edit_members

        await self.session.commit()
        await self.session.refresh(entity)
        return GroupCaregiverMapper.to_domain(entity)

    async def delete(self, caregiver_id: str) -> bool:
        stmt = select(GroupCaregiverEntity).where(GroupCaregiverEntity.id == caregiver_id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity is None:
            return False

        await self.session.delete(entity)
        await self.session.commit()
        return True

    async def delete_by_user_and_group(self, user_id: str, group_id: str) -> bool:
        stmt = select(GroupCaregiverEntity).where(
            and_(
                GroupCaregiverEntity.user_id == user_id,
                GroupCaregiverEntity.group_id == group_id
            )
        )
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity is None:
            return False

        await self.session.delete(entity)
        await self.session.commit()
        return True

    async def get_by_id(self, caregiver_id: str) -> Optional[GroupCaregiver]:
        stmt = select(GroupCaregiverEntity).where(GroupCaregiverEntity.id == caregiver_id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()
        return GroupCaregiverMapper.to_domain(entity) if entity else None

    async def get_by_user_and_group(
        self,
        user_id: str,
        group_id: str
    ) -> Optional[GroupCaregiver]:
        stmt = select(GroupCaregiverEntity).where(
            and_(
                GroupCaregiverEntity.user_id == user_id,
                GroupCaregiverEntity.group_id == group_id
            )
        )
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()
        return GroupCaregiverMapper.to_domain(entity) if entity else None

    async def get_by_group(self, group_id: str) -> List[GroupCaregiver]:
        stmt = select(GroupCaregiverEntity).where(GroupCaregiverEntity.group_id == group_id)
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [GroupCaregiverMapper.to_domain(e) for e in entities]

    async def get_by_user(self, user_id: str) -> List[GroupCaregiver]:
        stmt = select(GroupCaregiverEntity).where(GroupCaregiverEntity.user_id == user_id)
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [GroupCaregiverMapper.to_domain(e) for e in entities]

    async def get_with_alert_permission(self, group_id: str) -> List[GroupCaregiver]:
        stmt = select(GroupCaregiverEntity).where(
            and_(
                GroupCaregiverEntity.group_id == group_id,
                GroupCaregiverEntity.can_acknowledge_alerts == True
            )
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [GroupCaregiverMapper.to_domain(e) for e in entities]

    async def get_with_edit_permission(self, group_id: str) -> List[GroupCaregiver]:
        stmt = select(GroupCaregiverEntity).where(
            and_(
                GroupCaregiverEntity.group_id == group_id,
                GroupCaregiverEntity.can_edit_members == True
            )
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [GroupCaregiverMapper.to_domain(e) for e in entities]

    async def exists(self, user_id: str, group_id: str) -> bool:
        stmt = select(func.count()).select_from(GroupCaregiverEntity).where(
            and_(
                GroupCaregiverEntity.user_id == user_id,
                GroupCaregiverEntity.group_id == group_id
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() > 0

    async def count_by_group(self, group_id: str) -> int:
        stmt = select(func.count()).select_from(GroupCaregiverEntity).where(
            GroupCaregiverEntity.group_id == group_id
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def count_by_user(self, user_id: str) -> int:
        stmt = select(func.count()).select_from(GroupCaregiverEntity).where(
            GroupCaregiverEntity.user_id == user_id
        )
        result = await self.session.execute(stmt)
        return result.scalar()
