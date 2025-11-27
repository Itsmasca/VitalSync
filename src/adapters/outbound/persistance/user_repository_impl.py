from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.domain.UserModel import User, UserRole
from src.core.ports.UserRepository import UserRepository
from src.adapters.outbound.persistance.entities import UserEntity, UserRoleEnum
from src.adapters.outbound.persistance.mappers import UserMapper


class UserRepositoryImpl(UserRepository):
    """Implementación del repositorio de usuarios con SQLAlchemy"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, user: User) -> User:
        entity = UserMapper.to_entity(user)
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return UserMapper.to_domain(entity)

    async def update(self, user: User) -> User:
        stmt = select(UserEntity).where(UserEntity.id == user.id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity is None:
            raise ValueError(f"User with id {user.id} not found")

        entity.email = user.email
        entity.password_hash = user.password_hash
        entity.name = user.name
        entity.phone = user.phone
        entity.avatar_url = user.avatar_url
        entity.role = UserRoleEnum(user.role.value)
        entity.is_active = user.is_active
        entity.email_verified = user.email_verified
        entity.last_login_at = user.last_login_at
        entity.password_reset_token = user.password_reset_token
        entity.password_reset_expires = user.password_reset_expires
        entity.updated_at = user.updated_at

        await self.session.commit()
        await self.session.refresh(entity)
        return UserMapper.to_domain(entity)

    async def delete(self, user_id: str) -> bool:
        stmt = select(UserEntity).where(UserEntity.id == user_id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity is None:
            return False

        await self.session.delete(entity)
        await self.session.commit()
        return True

    async def get_by_id(self, user_id: str) -> Optional[User]:
        stmt = select(UserEntity).where(UserEntity.id == user_id)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()
        return UserMapper.to_domain(entity) if entity else None

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(UserEntity).where(UserEntity.email == email)
        result = await self.session.execute(stmt)
        entity = result.scalar_one_or_none()
        return UserMapper.to_domain(entity) if entity else None

    async def get_by_device_id(self, device_id: str) -> Optional[User]:
        # Users don't have device_id directly, this is handled via FamilyMember
        # Returning None as users don't have device_id
        return None

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[User]:
        stmt = select(UserEntity).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [UserMapper.to_domain(e) for e in entities]

    async def get_by_role(self, role: UserRole) -> List[User]:
        stmt = select(UserEntity).where(UserEntity.role == UserRoleEnum(role.value))
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [UserMapper.to_domain(e) for e in entities]

    async def get_by_status(self, status) -> List[User]:
        # UserStatus was removed, using is_active instead
        stmt = select(UserEntity).where(UserEntity.is_active == True)
        result = await self.session.execute(stmt)
        entities = result.scalars().all()
        return [UserMapper.to_domain(e) for e in entities]

    async def exists_by_email(self, email: str) -> bool:
        stmt = select(func.count()).select_from(UserEntity).where(UserEntity.email == email)
        result = await self.session.execute(stmt)
        count = result.scalar()
        return count > 0

    async def count(self) -> int:
        stmt = select(func.count()).select_from(UserEntity)
        result = await self.session.execute(stmt)
        return result.scalar()

    async def count_by_status(self, status) -> int:
        # Using is_active instead of status
        stmt = select(func.count()).select_from(UserEntity).where(UserEntity.is_active == True)
        result = await self.session.execute(stmt)
        return result.scalar()
