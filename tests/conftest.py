"""
VitalSync Test Configuration
Fixtures compartidos para todas las pruebas.
"""
import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from src.core.domain.UserModel import User, UserRole
from src.core.domain.FamilyGroupModel import FamilyGroup, SubscriptionPlan
from src.core.domain.FamilyMemberModel import (
    FamilyMember, RelationshipType, DeviceType, VitalThresholds
)
from src.core.domain.VitalModel import Vital, VitalStatus
from src.core.domain.AlertModel import Alert, AlertType, AlertStatus, ThresholdType

from src.core.ports.UserRepository import UserRepository
from src.core.ports.FamilyGroupRepository import FamilyGroupRepository
from src.core.ports.FamilyMemberRepository import FamilyMemberRepository
from src.core.ports.VitalRepository import VitalRepository
from src.core.ports.AlertRepository import AlertRepository


# ============================================================
# Pytest Configuration
# ============================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================
# Domain Model Fixtures
# ============================================================

@pytest.fixture
def sample_user() -> User:
    """Creates a sample user for testing"""
    return User.create(
        email="test@vitalsync.com",
        password_hash="hashed_password_123",
        name="Test User",
        role=UserRole.ADMIN,
        phone="+52 55 1234 5678"
    )


@pytest.fixture
def sample_family_group(sample_user: User) -> FamilyGroup:
    """Creates a sample family group for testing"""
    return FamilyGroup.create(
        name="Familia García",
        admin_id=sample_user.id,
        plan=SubscriptionPlan.FAMILIAR
    )


@pytest.fixture
def sample_family_member(sample_family_group: FamilyGroup) -> FamilyMember:
    """Creates a sample family member for testing"""
    member = FamilyMember.create(
        family_id=sample_family_group.id,
        member_id="familia-garcia-papa",
        name="Roberto García",
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
def sample_vital(sample_family_member: FamilyMember) -> Vital:
    """Creates a sample vital reading for testing"""
    return Vital.create(
        member_id=sample_family_member.id,
        heart_rate=72,
        oxygen_level=96.5,
        body_temperature=36.5,
        steps=3500,
        reading_timestamp=datetime.now(timezone.utc)
    )


@pytest.fixture
def critical_vital(sample_family_member: FamilyMember) -> Vital:
    """Creates a critical vital reading for testing alerts"""
    return Vital.create(
        member_id=sample_family_member.id,
        heart_rate=130,  # Critical high
        oxygen_level=85,  # Critical low
        body_temperature=39.5,  # Critical high
        steps=500,  # Critical low
        reading_timestamp=datetime.now(timezone.utc)
    )


@pytest.fixture
def warning_vital(sample_family_member: FamilyMember) -> Vital:
    """Creates a warning vital reading for testing"""
    return Vital.create(
        member_id=sample_family_member.id,
        heart_rate=105,  # Warning high
        oxygen_level=92,  # Warning low
        body_temperature=37.5,  # Warning high
        steps=3000,  # Warning low
        reading_timestamp=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_alert(sample_family_member: FamilyMember, sample_vital: Vital) -> Alert:
    """Creates a sample alert for testing"""
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
    repo = AsyncMock(spec=FamilyGroupRepository)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.save = AsyncMock(side_effect=lambda group: group)
    repo.delete = AsyncMock(return_value=True)
    repo.get_by_admin = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_family_member_repository(sample_family_member: FamilyMember) -> AsyncMock:
    """Creates a mock family member repository"""
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
    repo = AsyncMock(spec=AlertRepository)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.save = AsyncMock(side_effect=lambda alert: alert)
    repo.get_active = AsyncMock(return_value=[])
    repo.get_by_member = AsyncMock(return_value=[])
    repo.count_active = AsyncMock(return_value=0)
    return repo


# ============================================================
# HTTP Client Fixtures for E2E Tests
# ============================================================

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Creates an async HTTP client for E2E tests"""
    from src.adapters.inbound.graphql.server import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


# ============================================================
# Database Fixtures for Integration Tests
# ============================================================

@pytest.fixture
async def test_db_session():
    """Creates a test database session (integration tests)"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

    # Use SQLite for testing
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )

    # Import and create tables
    from src.adapters.outbound.persistance.database import Base
    from src.adapters.outbound.persistance import entities  # noqa: F401

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with TestSessionLocal() as session:
        yield session

    await test_engine.dispose()
