from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.domain.FamilyGroupModel import FamilyGroup, SubscriptionPlan
from src.core.ports.FamilyGroupRepository import FamilyGroupRepository
from src.adapters.outbound.persistance.entities import FamilyGroupEntity, SubscriptionPlanEnum
from src.adapters.outbound.persistance.mappers import FamilyGroupMapper


class FamilyGroupRepositoryImpl(FamilyGroupRepository):
    """Implementación del repositorio de grupos familiares con SQLAlchemy"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, group: FamilyGroup) -> FamilyGroup:
        entity = FamilyGroupMapper.to_entity(group)
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return FamilyGroupMapper.to_domain(entity)

    async def update(self, group: FamilyGroup) -> FamilyGroup:
        stmt = select(FamilyGroupEntity).where(FamilyGroupEntity.id == group.id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity is None:
            raise ValueError(f"FamilyGroup with id {group.id} not found")

        entity.name = group.name
        entity.description = group.description
        entity.admin_id = group.admin_id
        entity.plan = SubscriptionPlanEnum(group.plan.value)
        entity.plan_started_at = group.plan_started_at
        entity.plan_expires_at = group.plan_expires_at
        entity.timezone_str = group.timezone_str
        entity.is_active = group.is_active
        entity.updated_at = group.updated_at

        await self.session.commit()
        await self.session.refresh(entity)
        return FamilyGroupMapper.to_domain(entity)

    async def delete(self, group_id: str) -> bool:
        stmt = select(FamilyGroupEntity).where(FamilyGroupEntity.id == group_id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity is None:
            return False

        await self.session.delete(entity)
        await self.session.commit()
        return True

    async def get_by_id(self, group_id: str) -> Optional[FamilyGroup]:
        stmt = select(FamilyGroupEntity).where(FamilyGroupEntity.id == group_id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()
        return FamilyGroupMapper.to_domain(entity) if entity else None

    async def get_by_admin_id(self, admin_id: str) -> List[FamilyGroup]:
        stmt = select(FamilyGroupEntity).where(FamilyGroupEntity.admin_id == admin_id)
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [FamilyGroupMapper.to_domain(e) for e in entities]

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[FamilyGroup]:
        stmt = select(FamilyGroupEntity).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [FamilyGroupMapper.to_domain(e) for e in entities]

    async def get_by_plan(self, plan: SubscriptionPlan) -> List[FamilyGroup]:
        stmt = select(FamilyGroupEntity).where(
            FamilyGroupEntity.plan == SubscriptionPlanEnum(plan.value)
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [FamilyGroupMapper.to_domain(e) for e in entities]

    async def get_active(self) -> List[FamilyGroup]:
        stmt = select(FamilyGroupEntity).where(FamilyGroupEntity.is_active == True)
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [FamilyGroupMapper.to_domain(e) for e in entities]

    async def count(self) -> int:
        stmt = select(func.count()).select_from(FamilyGroupEntity)
        result = await self.session.execute(stmt)
        return result.scalar()

    async def count_by_plan(self, plan: SubscriptionPlan) -> int:
        stmt = select(func.count()).select_from(FamilyGroupEntity).where(
            FamilyGroupEntity.plan == SubscriptionPlanEnum(plan.value)
        )
        result = await self.session.execute(stmt)
        return result.scalar()
