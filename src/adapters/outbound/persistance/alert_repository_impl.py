from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.domain.AlertModel import Alert, AlertStatus, AlertType
from src.core.domain.VitalModel import VitalStatus
from src.core.ports.AlertRepository import AlertRepository
from src.adapters.outbound.persistance.entities import (
    AlertEntity, AlertStatusEnum, AlertTypeEnum, VitalStatusEnum, FamilyMemberEntity
)
from src.adapters.outbound.persistance.mappers import AlertMapper


class AlertRepositoryImpl(AlertRepository):
    """Implementación del repositorio de alertas con SQLAlchemy"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, alert: Alert) -> Alert:
        entity = AlertMapper.to_entity(alert)
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return AlertMapper.to_domain(entity)

    async def update(self, alert: Alert) -> Alert:
        stmt = select(AlertEntity).where(AlertEntity.id == alert.id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity is None:
            raise ValueError(f"Alert with id {alert.id} not found")

        entity.status = AlertStatusEnum(alert.status.value)
        entity.acknowledged_by = alert.acknowledged_by
        entity.acknowledged_at = alert.acknowledged_at
        entity.resolved_at = alert.resolved_at
        entity.resolution_notes = alert.resolution_notes

        await self.session.commit()
        await self.session.refresh(entity)
        return AlertMapper.to_domain(entity)

    async def get_by_id(self, alert_id: str) -> Optional[Alert]:
        stmt = select(AlertEntity).where(AlertEntity.id == alert_id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()
        return AlertMapper.to_domain(entity) if entity else None

    async def get_by_member(
        self,
        member_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Alert]:
        stmt = (
            select(AlertEntity)
            .where(AlertEntity.member_id == member_id)
            .order_by(AlertEntity.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [AlertMapper.to_domain(e) for e in entities]

    async def get_active(self) -> List[Alert]:
        stmt = (
            select(AlertEntity)
            .where(AlertEntity.status == AlertStatusEnum.ACTIVE)
            .order_by(AlertEntity.created_at.desc())
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [AlertMapper.to_domain(e) for e in entities]

    async def get_active_by_member(self, member_id: str) -> List[Alert]:
        stmt = (
            select(AlertEntity)
            .where(
                and_(
                    AlertEntity.member_id == member_id,
                    AlertEntity.status == AlertStatusEnum.ACTIVE
                )
            )
            .order_by(AlertEntity.created_at.desc())
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [AlertMapper.to_domain(e) for e in entities]

    async def get_active_by_family_group(self, family_group_id: str) -> List[Alert]:
        stmt = (
            select(AlertEntity)
            .join(FamilyMemberEntity, AlertEntity.member_id == FamilyMemberEntity.id)
            .where(
                and_(
                    FamilyMemberEntity.family_id == family_group_id,
                    AlertEntity.status == AlertStatusEnum.ACTIVE
                )
            )
            .order_by(AlertEntity.created_at.desc())
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [AlertMapper.to_domain(e) for e in entities]

    async def get_by_status(self, status: AlertStatus) -> List[Alert]:
        stmt = (
            select(AlertEntity)
            .where(AlertEntity.status == AlertStatusEnum(status.value))
            .order_by(AlertEntity.created_at.desc())
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [AlertMapper.to_domain(e) for e in entities]

    async def get_by_severity(self, severity: VitalStatus) -> List[Alert]:
        stmt = (
            select(AlertEntity)
            .where(AlertEntity.severity == VitalStatusEnum(severity.value))
            .order_by(AlertEntity.created_at.desc())
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [AlertMapper.to_domain(e) for e in entities]

    async def get_by_type(self, alert_type: AlertType) -> List[Alert]:
        stmt = (
            select(AlertEntity)
            .where(AlertEntity.alert_type == AlertTypeEnum(alert_type.value))
            .order_by(AlertEntity.created_at.desc())
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [AlertMapper.to_domain(e) for e in entities]

    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        member_id: Optional[str] = None
    ) -> List[Alert]:
        stmt = (
            select(AlertEntity)
            .where(
                and_(
                    AlertEntity.created_at >= start_date,
                    AlertEntity.created_at <= end_date
                )
            )
        )
        if member_id:
            stmt = stmt.where(AlertEntity.member_id == member_id)
        stmt = stmt.order_by(AlertEntity.created_at.desc())
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [AlertMapper.to_domain(e) for e in entities]

    async def get_recent(
        self,
        hours: int = 24,
        member_id: Optional[str] = None
    ) -> List[Alert]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = select(AlertEntity).where(AlertEntity.created_at >= cutoff)
        if member_id:
            stmt = stmt.where(AlertEntity.member_id == member_id)
        stmt = stmt.order_by(AlertEntity.created_at.desc())
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [AlertMapper.to_domain(e) for e in entities]

    async def count_active(self) -> int:
        stmt = select(func.count()).select_from(AlertEntity).where(
            AlertEntity.status == AlertStatusEnum.ACTIVE
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def count_by_status(self, status: AlertStatus) -> int:
        stmt = select(func.count()).select_from(AlertEntity).where(
            AlertEntity.status == AlertStatusEnum(status.value)
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def count_by_severity(self, severity: VitalStatus) -> int:
        stmt = select(func.count()).select_from(AlertEntity).where(
            AlertEntity.severity == VitalStatusEnum(severity.value)
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def count_by_member(self, member_id: str) -> int:
        stmt = select(func.count()).select_from(AlertEntity).where(
            AlertEntity.member_id == member_id
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def acknowledge_by_id(self, alert_id: str, user_id: str) -> Optional[Alert]:
        alert = await self.get_by_id(alert_id)
        if alert is None:
            return None
        alert.acknowledge(user_id)
        return await self.update(alert)

    async def resolve_by_id(
        self,
        alert_id: str,
        notes: Optional[str] = None
    ) -> Optional[Alert]:
        alert = await self.get_by_id(alert_id)
        if alert is None:
            return None
        alert.resolve(notes)
        return await self.update(alert)

    async def dismiss_by_id(
        self,
        alert_id: str,
        notes: Optional[str] = None
    ) -> Optional[Alert]:
        alert = await self.get_by_id(alert_id)
        if alert is None:
            return None
        alert.dismiss(notes)
        return await self.update(alert)
