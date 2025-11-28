"""
VitalSync Test Configuration
Fixtures compartidos para todas las pruebas.

IMPORTANT: This file sets up a SQLite in-memory database for testing.
"""
import asyncio
import os
from datetime import datetime, timezone
from typing import AsyncGenerator, Generator, Optional
from unittest.mock import AsyncMock, MagicMock

# Set TESTING environment variable BEFORE any imports
os.environ["TESTING"] = "true"

import pytest

# ============================================================
# Test App Setup - Creates a test app with SQLite in-memory
# ============================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client() -> AsyncGenerator:
    """Creates an async HTTP client for E2E tests with SQLite in-memory"""
    from httpx import AsyncClient, ASGITransport
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from contextlib import asynccontextmanager
    from typing import Optional

    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from strawberry.fastapi import GraphQLRouter

    # Create in-memory SQLite engine
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    TestSessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # Import Base from SQLAlchemy directly (avoid triggering database.py engine creation)
    from sqlalchemy.orm import declarative_base

    # Create our own Base for testing
    TestBase = declarative_base()

    # Import entity classes to get table definitions
    # We need to import these from entity files but map them to our TestBase
    from src.adapters.outbound.persistance.entities import (
        UserEntity, FamilyGroupEntity, FamilyMemberEntity,
        VitalEntity, AlertEntity, GroupCaregiverEntity
    )

    # Create tables using the entity metadata
    async with test_engine.begin() as conn:
        # Use the metadata from the imported entities
        from src.adapters.outbound.persistance.database import Base
        await conn.run_sync(Base.metadata.create_all)

    # Import schema and services
    from src.adapters.inbound.graphql.resolvers import schema
    from src.adapters.outbound.persistance.user_repository_impl import UserRepositoryImpl
    from src.adapters.outbound.persistance.family_group_repository_impl import FamilyGroupRepositoryImpl
    from src.adapters.outbound.persistance.family_member_repository_impl import FamilyMemberRepositoryImpl
    from src.adapters.outbound.persistance.vital_repository_impl import VitalRepositoryImpl
    from src.adapters.outbound.persistance.alert_repository_impl import AlertRepositoryImpl
    from src.adapters.outbound.persistance.group_caregiver_repository_impl import GroupCaregiverRepositoryImpl
    from src.core.services import (
        UserService, FamilyGroupService, FamilyMemberService,
        VitalService, AlertService
    )

    # Create test app
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield

    test_app = FastAPI(
        title="VitalSync Test API",
        lifespan=lifespan
    )

    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Create shared session for all requests in this test
    test_session = TestSessionLocal()

    # REST router with test session
    try:
        rest_router = create_test_router(test_session)
        test_app.include_router(rest_router)
    except Exception:
        # Fallback if create_test_router doesn't exist
        pass

    # GraphQL context
    async def get_context(request: Request) -> dict:
        from src.core.services.auth_service import auth_service

        current_user_id: Optional[str] = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = auth_service.verify_token(token)
            if payload:
                current_user_id = payload.get("sub")

        # Create repositories with test session
        user_repo = UserRepositoryImpl(test_session)
        family_group_repo = FamilyGroupRepositoryImpl(test_session)
        family_member_repo = FamilyMemberRepositoryImpl(test_session)
        vital_repo = VitalRepositoryImpl(test_session)
        alert_repo = AlertRepositoryImpl(test_session)
        group_caregiver_repo = GroupCaregiverRepositoryImpl(test_session)

        # Create services
        user_service = UserService(user_repo)
        family_group_service = FamilyGroupService(family_group_repo, group_caregiver_repo)
        family_member_service = FamilyMemberService(family_member_repo, family_group_repo)
        vital_service = VitalService(vital_repo, family_member_repo, alert_repo)
        alert_service = AlertService(alert_repo)

        return {
            "user_service": user_service,
            "family_group_service": family_group_service,
            "family_member_service": family_member_service,
            "vital_service": vital_service,
            "alert_service": alert_service,
            "current_user_id": current_user_id,
            "db_session": test_session
        }

    graphql_app = GraphQLRouter(
        schema,
        context_getter=get_context
    )
    test_app.include_router(graphql_app, prefix="/graphql")

    # Add REST auth routes manually
    from fastapi import APIRouter, HTTPException, Depends
    from pydantic import BaseModel, EmailStr, Field

    auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

    class RegisterInput(BaseModel):
        email: EmailStr
        password: str = Field(..., min_length=8)
        name: str = Field(..., min_length=1)
        phone: Optional[str] = None

    class LoginInput(BaseModel):
        email: EmailStr
        password: str

    class RefreshInput(BaseModel):
        refresh_token: str

    class TokenResponse(BaseModel):
        access_token: str
        refresh_token: str
        token_type: str = "bearer"
        expires_in: int = 1800

    class UserResponse(BaseModel):
        id: str
        email: str
        name: str
        role: str
        phone: Optional[str] = None
        is_active: bool = True

    @auth_router.post("/register", status_code=201, response_model=TokenResponse)
    async def register(input: RegisterInput):
        from src.core.services.auth_service import auth_service
        from src.core.domain.UserModel import User

        user_repo = UserRepositoryImpl(test_session)
        user_service = UserService(user_repo)

        # Check if user exists
        existing = await user_service.get_user_by_email(input.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email ya registrado")

        # Create user
        password_hash = auth_service.hash_password(input.password)
        user = User.create(
            email=input.email,
            password_hash=password_hash,
            name=input.name,
            phone=input.phone
        )
        await user_service.create_user(user)

        # Generate tokens
        access_token = auth_service.create_access_token(
            user_id=user.id, email=user.email, role=user.role.value
        )
        refresh_token = auth_service.create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=1800
        )

    @auth_router.post("/login", response_model=TokenResponse)
    async def login(input: LoginInput):
        from src.core.services.auth_service import auth_service

        user_repo = UserRepositoryImpl(test_session)
        user_service = UserService(user_repo)

        user = await user_service.authenticate(input.email, input.password)
        if not user:
            raise HTTPException(status_code=401, detail="Credenciales invalidas")

        access_token = auth_service.create_access_token(
            user_id=user.id, email=user.email, role=user.role.value
        )
        refresh_token = auth_service.create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=1800
        )

    @auth_router.get("/me", response_model=UserResponse)
    async def get_me(request: Request):
        from src.core.services.auth_service import auth_service

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Token de autenticacion requerido")

        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Token invalido")

        token = auth_header[7:]
        payload = auth_service.verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Token invalido o expirado")

        user_id = payload.get("sub")
        user_repo = UserRepositoryImpl(test_session)
        user_service = UserService(user_repo)

        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role.value,
            phone=user.phone,
            is_active=user.is_active
        )

    @auth_router.post("/refresh", response_model=TokenResponse)
    async def refresh_token(input: RefreshInput):
        from src.core.services.auth_service import auth_service

        payload = auth_service.verify_token(input.refresh_token)
        if not payload:
            raise HTTPException(status_code=401, detail="Refresh token invalido")

        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Refresh token invalido")

        user_id = payload.get("sub")
        user_repo = UserRepositoryImpl(test_session)
        user_service = UserService(user_repo)

        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")

        access_token = auth_service.create_access_token(
            user_id=user.id, email=user.email, role=user.role.value
        )
        new_refresh_token = auth_service.create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=1800
        )

    test_app.include_router(auth_router)

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test"
    ) as client:
        yield client

    # Cleanup
    await test_session.close()
    await test_engine.dispose()


# ============================================================
# Domain Model Fixtures
# ============================================================

@pytest.fixture
def sample_user():
    """Creates a sample user for testing"""
    from src.core.domain.UserModel import User, UserRole
    return User.create(
        email="test@vitalsync.com",
        password_hash="hashed_password_123",
        name="Test User",
        role=UserRole.ADMIN,
        phone="+52 55 1234 5678"
    )


@pytest.fixture
def sample_family_group(sample_user):
    """Creates a sample family group for testing"""
    from src.core.domain.FamilyGroupModel import FamilyGroup, SubscriptionPlan
    return FamilyGroup.create(
        name="Familia Garcia",
        admin_id=sample_user.id,
        plan=SubscriptionPlan.FAMILIAR
    )


@pytest.fixture
def sample_family_member(sample_family_group):
    """Creates a sample family member for testing"""
    from src.core.domain.FamilyMemberModel import (
        FamilyMember, RelationshipType, DeviceType, VitalThresholds
    )
    member = FamilyMember.create(
        family_id=sample_family_group.id,
        member_id="familia-garcia-papa",
        name="Roberto Garcia",
        relationship=RelationshipType.PADRE,
        device_id="XIAOMI-PAPA-001",
        device_type=DeviceType.XIAOMI_BAND,
        device_name="Xiaomi Mi Band 8"
    )
    member.thresholds = VitalThresholds(
        hr_min=60,
        hr_max=100,
        spo2_min=95,
        temp_min=36.0,
        temp_max=37.5,
        steps_min=5000
    )
    return member


@pytest.fixture
def sample_vital(sample_family_member):
    """Creates a sample vital reading for testing"""
    from src.core.domain.VitalModel import Vital
    return Vital.create(
        member_id=sample_family_member.id,
        heart_rate=72,
        oxygen_level=96.5,
        body_temperature=36.5,
        steps=3500,
        reading_timestamp=datetime.now(timezone.utc)
    )


@pytest.fixture
def critical_vital(sample_family_member):
    """Creates a critical vital reading for testing alerts"""
    from src.core.domain.VitalModel import Vital
    return Vital.create(
        member_id=sample_family_member.id,
        heart_rate=130,
        oxygen_level=85,
        body_temperature=39.5,
        steps=500,
        reading_timestamp=datetime.now(timezone.utc)
    )


@pytest.fixture
def warning_vital(sample_family_member):
    """Creates a warning vital reading for testing"""
    from src.core.domain.VitalModel import Vital
    return Vital.create(
        member_id=sample_family_member.id,
        heart_rate=105,
        oxygen_level=92,
        body_temperature=37.5,
        steps=3000,
        reading_timestamp=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_alert(sample_family_member, sample_vital):
    """Creates a sample alert for testing"""
    from src.core.domain.AlertModel import Alert
    return Alert.create_heart_rate_alert(
        member_id=sample_family_member.id,
        member_name=sample_family_member.name,
        heart_rate=130,
        threshold=100,
        is_high=True,
        vital_id=sample_vital.id
    )


# ============================================================
# Mock Repository Fixtures
# ============================================================

@pytest.fixture
def mock_user_repository() -> AsyncMock:
    """Creates a mock user repository"""
    from src.core.ports.UserRepository import UserRepository
    repo = AsyncMock(spec=UserRepository)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_email = AsyncMock(return_value=None)
    repo.save = AsyncMock(side_effect=lambda user: user)
    repo.delete = AsyncMock(return_value=True)
    repo.exists_by_email = AsyncMock(return_value=False)
    return repo


@pytest.fixture
def mock_family_group_repository() -> AsyncMock:
    """Creates a mock family group repository"""
    from src.core.ports.FamilyGroupRepository import FamilyGroupRepository
    repo = AsyncMock(spec=FamilyGroupRepository)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.save = AsyncMock(side_effect=lambda group: group)
    repo.delete = AsyncMock(return_value=True)
    repo.get_by_admin = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_family_member_repository(sample_family_member) -> AsyncMock:
    """Creates a mock family member repository"""
    from src.core.ports.FamilyMemberRepository import FamilyMemberRepository
    repo = AsyncMock(spec=FamilyMemberRepository)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_device_id = AsyncMock(return_value=sample_family_member)
    repo.get_by_member_id = AsyncMock(return_value=sample_family_member)
    repo.save = AsyncMock(side_effect=lambda member: member)
    repo.delete = AsyncMock(return_value=True)
    repo.get_by_family = AsyncMock(return_value=[sample_family_member])
    return repo


@pytest.fixture
def mock_vital_repository() -> AsyncMock:
    """Creates a mock vital repository"""
    from src.core.ports.VitalRepository import VitalRepository
    repo = AsyncMock(spec=VitalRepository)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.save = AsyncMock(side_effect=lambda vital: vital)
    repo.get_latest_by_member = AsyncMock(return_value=None)
    repo.get_by_member = AsyncMock(return_value=[])
    repo.get_by_member_and_date_range = AsyncMock(return_value=[])
    repo.get_by_member_last_minutes = AsyncMock(return_value=[])
    repo.get_critical_readings = AsyncMock(return_value=[])
    repo.get_anomalies = AsyncMock(return_value=[])
    repo.count_by_member = AsyncMock(return_value=0)
    repo.count_readings_last_hour = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def mock_alert_repository() -> AsyncMock:
    """Creates a mock alert repository"""
    from src.core.ports.AlertRepository import AlertRepository
    repo = AsyncMock(spec=AlertRepository)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.save = AsyncMock(side_effect=lambda alert: alert)
    repo.get_active = AsyncMock(return_value=[])
    repo.get_by_member = AsyncMock(return_value=[])
    repo.count_active = AsyncMock(return_value=0)
    return repo
