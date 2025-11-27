from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.domain.FamilyMemberModel import FamilyMember, RelationshipType, DeviceType
from src.core.ports.FamilyMemberRepository import FamilyMemberRepository
from src.adapters.outbound.persistance.entities import (
    FamilyMemberEntity, RelationshipTypeEnum, DeviceTypeEnum
)
from src.adapters.outbound.persistance.mappers import FamilyMemberMapper


class FamilyMemberRepositoryImpl(FamilyMemberRepository):
    """Implementación del repositorio de familiares monitoreados con SQLAlchemy"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, member: FamilyMember) -> FamilyMember:
        entity = FamilyMemberMapper.to_entity(member)
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return FamilyMemberMapper.to_domain(entity)

    async def update(self, member: FamilyMember) -> FamilyMember:
        stmt = select(FamilyMemberEntity).where(FamilyMemberEntity.id == member.id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity is None:
            raise ValueError(f"FamilyMember with id {member.id} not found")

        entity.family_id = member.family_id
        entity.member_id = member.member_id
        entity.name = member.name
        entity.relationship_type = RelationshipTypeEnum(member.relationship.value)
        entity.date_of_birth = member.date_of_birth
        entity.gender = member.gender.value if member.gender else None
        entity.device_id = member.device_id
        entity.device_type = DeviceTypeEnum(member.device_type.value)
        entity.device_name = member.device_name
        entity.medical_notes = member.medical_notes
        entity.emergency_contact = member.emergency_contact
        entity.emergency_phone = member.emergency_phone
        entity.custom_hr_min = member.thresholds.hr_min
        entity.custom_hr_max = member.thresholds.hr_max
        entity.custom_spo2_min = member.thresholds.spo2_min
        entity.custom_temp_min = member.thresholds.temp_min
        entity.custom_temp_max = member.thresholds.temp_max
        entity.custom_steps_min = member.thresholds.steps_min
        entity.is_active = member.is_active
        entity.alerts_enabled = member.alerts_enabled
        entity.avatar_url = member.avatar_url
        entity.updated_at = member.updated_at

        await self.session.commit()
        await self.session.refresh(entity)
        return FamilyMemberMapper.to_domain(entity)

    async def delete(self, member_id: str) -> bool:
        stmt = select(FamilyMemberEntity).where(FamilyMemberEntity.id == member_id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity is None:
            return False

        await self.session.delete(entity)
        await self.session.commit()
        return True

    async def get_by_id(self, member_id: str) -> Optional[FamilyMember]:
        stmt = select(FamilyMemberEntity).where(FamilyMemberEntity.id == member_id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()
        return FamilyMemberMapper.to_domain(entity) if entity else None

    async def get_by_member_id(self, member_id: str) -> Optional[FamilyMember]:
        stmt = select(FamilyMemberEntity).where(FamilyMemberEntity.member_id == member_id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()
        return FamilyMemberMapper.to_domain(entity) if entity else None

    async def get_by_device_id(self, device_id: str) -> Optional[FamilyMember]:
        stmt = select(FamilyMemberEntity).where(FamilyMemberEntity.device_id == device_id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()
        return FamilyMemberMapper.to_domain(entity) if entity else None

    async def get_by_family_id(self, family_id: str) -> List[FamilyMember]:
        stmt = select(FamilyMemberEntity).where(FamilyMemberEntity.family_id == family_id)
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [FamilyMemberMapper.to_domain(e) for e in entities]

    async def get_by_relationship(
        self,
        family_id: str,
        relationship: RelationshipType
    ) -> List[FamilyMember]:
        stmt = select(FamilyMemberEntity).where(
            FamilyMemberEntity.family_id == family_id,
            FamilyMemberEntity.relationship_type == RelationshipTypeEnum(relationship.value)
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [FamilyMemberMapper.to_domain(e) for e in entities]

    async def get_by_device_type(self, device_type: DeviceType) -> List[FamilyMember]:
        stmt = select(FamilyMemberEntity).where(
            FamilyMemberEntity.device_type == DeviceTypeEnum(device_type.value)
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [FamilyMemberMapper.to_domain(e) for e in entities]

    async def get_active_by_family(self, family_id: str) -> List[FamilyMember]:
        stmt = select(FamilyMemberEntity).where(
            FamilyMemberEntity.family_id == family_id,
            FamilyMemberEntity.is_active == True
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [FamilyMemberMapper.to_domain(e) for e in entities]

    async def get_with_alerts_enabled(self, family_id: str) -> List[FamilyMember]:
        stmt = select(FamilyMemberEntity).where(
            FamilyMemberEntity.family_id == family_id,
            FamilyMemberEntity.alerts_enabled == True
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [FamilyMemberMapper.to_domain(e) for e in entities]

    async def count_by_family(self, family_id: str) -> int:
        stmt = select(func.count()).select_from(FamilyMemberEntity).where(
            FamilyMemberEntity.family_id == family_id
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def exists_by_device_id(self, device_id: str) -> bool:
        stmt = select(func.count()).select_from(FamilyMemberEntity).where(
            FamilyMemberEntity.device_id == device_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() > 0

    async def exists_by_member_id(self, member_id: str) -> bool:
        stmt = select(func.count()).select_from(FamilyMemberEntity).where(
            FamilyMemberEntity.member_id == member_id
        )
        result = await self.session.execute(stmt)
        return result.scalar() > 0
