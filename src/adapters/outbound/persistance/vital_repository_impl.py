from datetime import datetime, date, timezone, timedelta
from typing import List, Optional
from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.domain.VitalModel import Vital, VitalStatus
from src.core.ports.VitalRepository import VitalRepository
from src.adapters.outbound.persistance.entities import VitalEntity, VitalStatusEnum
from src.adapters.outbound.persistance.mappers import VitalMapper


class VitalRepositoryImpl(VitalRepository):
    """Implementación del repositorio de signos vitales con SQLAlchemy"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, vital: Vital) -> Vital:
        entity = VitalMapper.to_entity(vital)
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return VitalMapper.to_domain(entity)

    async def save_batch(self, vitals: List[Vital]) -> List[Vital]:
        entities = [VitalMapper.to_entity(v) for v in vitals]
        self.session.add_all(entities)
        await self.session.commit()
        for entity in entities:
            await self.session.refresh(entity)
        return [VitalMapper.to_domain(e) for e in entities]

    async def get_by_id(self, vital_id: str) -> Optional[Vital]:
        stmt = select(VitalEntity).where(VitalEntity.id == vital_id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()
        return VitalMapper.to_domain(entity) if entity else None

    async def get_latest_by_member(self, member_id: str) -> Optional[Vital]:
        stmt = (
            select(VitalEntity)
            .where(VitalEntity.member_id == member_id)
            .order_by(VitalEntity.reading_timestamp.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()
        return VitalMapper.to_domain(entity) if entity else None

    async def get_by_member(
        self,
        member_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Vital]:
        stmt = (
            select(VitalEntity)
            .where(VitalEntity.member_id == member_id)
            .order_by(VitalEntity.reading_timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [VitalMapper.to_domain(e) for e in entities]

    async def get_by_member_and_date_range(
        self,
        member_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Vital]:
        stmt = (
            select(VitalEntity)
            .where(
                and_(
                    VitalEntity.member_id == member_id,
                    VitalEntity.reading_timestamp >= start_date,
                    VitalEntity.reading_timestamp <= end_date
                )
            )
            .order_by(VitalEntity.reading_timestamp.desc())
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [VitalMapper.to_domain(e) for e in entities]

    async def get_by_member_last_minutes(
        self,
        member_id: str,
        minutes: int = 2
    ) -> List[Vital]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        stmt = (
            select(VitalEntity)
            .where(
                and_(
                    VitalEntity.member_id == member_id,
                    VitalEntity.received_at >= cutoff
                )
            )
            .order_by(VitalEntity.received_at.desc())
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [VitalMapper.to_domain(e) for e in entities]

    async def get_by_status(self, status: VitalStatus) -> List[Vital]:
        stmt = (
            select(VitalEntity)
            .where(VitalEntity.overall_status == VitalStatusEnum(status.value))
            .order_by(VitalEntity.reading_timestamp.desc())
        )
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [VitalMapper.to_domain(e) for e in entities]

    async def get_anomalies(self, member_id: Optional[str] = None) -> List[Vital]:
        stmt = select(VitalEntity).where(VitalEntity.is_anomaly == True)
        if member_id:
            stmt = stmt.where(VitalEntity.member_id == member_id)
        stmt = stmt.order_by(VitalEntity.reading_timestamp.desc())
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [VitalMapper.to_domain(e) for e in entities]

    async def get_critical_readings(
        self,
        member_id: Optional[str] = None,
        hours: int = 24
    ) -> List[Vital]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = (
            select(VitalEntity)
            .where(
                and_(
                    VitalEntity.overall_status == VitalStatusEnum.CRITICAL,
                    VitalEntity.reading_timestamp >= cutoff
                )
            )
        )
        if member_id:
            stmt = stmt.where(VitalEntity.member_id == member_id)
        stmt = stmt.order_by(VitalEntity.reading_timestamp.desc())
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [VitalMapper.to_domain(e) for e in entities]

    async def count_by_member(self, member_id: str) -> int:
        stmt = select(func.count()).select_from(VitalEntity).where(
            VitalEntity.member_id == member_id
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def count_by_date(self, reading_date: date) -> int:
        stmt = select(func.count()).select_from(VitalEntity).where(
            VitalEntity.reading_date == reading_date
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def count_readings_last_hour(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        stmt = select(func.count()).select_from(VitalEntity).where(
            VitalEntity.received_at >= cutoff
        )
        result = await self.session.execute(stmt)
        return result.scalar()

    async def delete_old_readings(self, days: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = delete(VitalEntity).where(VitalEntity.reading_timestamp < cutoff)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def get_daily_averages(
        self,
        member_id: str,
        start_date: date,
        end_date: date
    ) -> List[dict]:
        stmt = (
            select(
                VitalEntity.reading_date,
                func.avg(VitalEntity.heart_rate).label('avg_heart_rate'),
                func.avg(VitalEntity.oxygen_level).label('avg_oxygen_level'),
                func.avg(VitalEntity.body_temperature).label('avg_body_temperature'),
                func.max(VitalEntity.steps).label('max_steps'),
                func.count().label('reading_count')
            )
            .where(
                and_(
                    VitalEntity.member_id == member_id,
                    VitalEntity.reading_date >= start_date,
                    VitalEntity.reading_date <= end_date
                )
            )
            .group_by(VitalEntity.reading_date)
            .order_by(VitalEntity.reading_date)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                'date': row.reading_date,
                'avg_heart_rate': float(row.avg_heart_rate) if row.avg_heart_rate else None,
                'avg_oxygen_level': float(row.avg_oxygen_level) if row.avg_oxygen_level else None,
                'avg_body_temperature': float(row.avg_body_temperature) if row.avg_body_temperature else None,
                'max_steps': row.max_steps,
                'reading_count': row.reading_count
            }
            for row in rows
        ]
