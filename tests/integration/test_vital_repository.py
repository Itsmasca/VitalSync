"""
Integration Tests for VitalRepository
Tests repository implementations with a real database (SQLite for testing).
"""
import pytest
from datetime import datetime, timezone, timedelta

from src.core.domain.VitalModel import Vital, VitalStatus
from src.core.domain.FamilyMemberModel import FamilyMember, RelationshipType, DeviceType
from src.core.domain.FamilyGroupModel import FamilyGroup, SubscriptionPlan
from src.core.domain.UserModel import User, UserRole


# Note: These tests require aiosqlite package for SQLite async support
# Add to pyproject.toml: "aiosqlite>=0.19.0" in dev dependencies

pytestmark = pytest.mark.asyncio


class TestVitalRepositoryIntegration:
    """Integration tests for VitalRepository with real database"""

    @pytest.fixture
    async def setup_test_data(self, test_db_session):
        """Sets up test data in the database"""
        from src.adapters.outbound.persistance.user_repository_impl import UserRepositoryImpl
        from src.adapters.outbound.persistance.family_group_repository_impl import FamilyGroupRepositoryImpl
        from src.adapters.outbound.persistance.family_member_repository_impl import FamilyMemberRepositoryImpl
        from src.adapters.outbound.persistance.vital_repository_impl import VitalRepositoryImpl

        user_repo = UserRepositoryImpl(test_db_session)
        group_repo = FamilyGroupRepositoryImpl(test_db_session)
        member_repo = FamilyMemberRepositoryImpl(test_db_session)
        vital_repo = VitalRepositoryImpl(test_db_session)

        # Create user
        user = User.create(
            email="test@test.com",
            password_hash="hash",
            name="Test User",
            role=UserRole.ADMIN
        )
        await user_repo.save(user)

        # Create family group
        group = FamilyGroup.create(
            name="Test Family",
            admin_id=user.id,
            plan=SubscriptionPlan.FAMILIAR
        )
        await group_repo.save(group)

        # Create family member
        member = FamilyMember.create(
            family_id=group.id,
            member_id="test-family-papa",
            name="Test Papa",
            relationship=RelationshipType.PADRE,
            device_id="TEST-DEVICE-001",
            device_type=DeviceType.XIAOMI_BAND
        )
        await member_repo.save(member)

        return {
            "user": user,
            "group": group,
            "member": member,
            "vital_repo": vital_repo,
            "member_repo": member_repo
        }

    async def test_save_and_get_vital(self, setup_test_data):
        """Should save and retrieve a vital reading"""
        data = await setup_test_data
        vital_repo = data["vital_repo"]
        member = data["member"]

        # Create and save vital
        vital = Vital.create(
            member_id=member.id,
            heart_rate=72,
            oxygen_level=96.5,
            body_temperature=36.5,
            steps=5000
        )
        saved_vital = await vital_repo.save(vital)

        # Retrieve vital
        retrieved = await vital_repo.get_by_id(saved_vital.id)

        assert retrieved is not None
        assert retrieved.heart_rate == 72
        assert retrieved.oxygen_level == 96.5
        assert retrieved.body_temperature == 36.5
        assert retrieved.steps == 5000

    async def test_get_latest_by_member(self, setup_test_data):
        """Should get the latest vital reading for a member"""
        data = await setup_test_data
        vital_repo = data["vital_repo"]
        member = data["member"]

        # Create multiple vitals
        vital1 = Vital.create(
            member_id=member.id,
            heart_rate=70,
            reading_timestamp=datetime.now(timezone.utc) - timedelta(hours=2)
        )
        vital2 = Vital.create(
            member_id=member.id,
            heart_rate=75,
            reading_timestamp=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        vital3 = Vital.create(
            member_id=member.id,
            heart_rate=80,
            reading_timestamp=datetime.now(timezone.utc)
        )

        await vital_repo.save(vital1)
        await vital_repo.save(vital2)
        await vital_repo.save(vital3)

        # Get latest
        latest = await vital_repo.get_latest_by_member(member.id)

        assert latest is not None
        assert latest.heart_rate == 80

    async def test_get_by_member_with_pagination(self, setup_test_data):
        """Should get vitals by member with pagination"""
        data = await setup_test_data
        vital_repo = data["vital_repo"]
        member = data["member"]

        # Create 5 vitals
        for i in range(5):
            vital = Vital.create(
                member_id=member.id,
                heart_rate=70 + i,
                reading_timestamp=datetime.now(timezone.utc) - timedelta(minutes=i)
            )
            await vital_repo.save(vital)

        # Get with pagination
        page1 = await vital_repo.get_by_member(member.id, limit=2, offset=0)
        page2 = await vital_repo.get_by_member(member.id, limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2

    async def test_get_by_date_range(self, setup_test_data):
        """Should get vitals within date range"""
        data = await setup_test_data
        vital_repo = data["vital_repo"]
        member = data["member"]

        now = datetime.now(timezone.utc)

        # Create vitals at different times
        old_vital = Vital.create(
            member_id=member.id,
            heart_rate=70,
            reading_timestamp=now - timedelta(days=10)
        )
        recent_vital = Vital.create(
            member_id=member.id,
            heart_rate=75,
            reading_timestamp=now - timedelta(hours=1)
        )

        await vital_repo.save(old_vital)
        await vital_repo.save(recent_vital)

        # Query last 24 hours
        start = now - timedelta(days=1)
        end = now
        results = await vital_repo.get_by_member_and_date_range(member.id, start, end)

        assert len(results) == 1
        assert results[0].heart_rate == 75

    async def test_get_critical_readings(self, setup_test_data):
        """Should get only critical readings"""
        data = await setup_test_data
        vital_repo = data["vital_repo"]
        member = data["member"]

        # Create normal vital
        normal = Vital.create(
            member_id=member.id,
            heart_rate=72
        )
        # Create critical vital
        critical = Vital.create(
            member_id=member.id,
            heart_rate=130  # Critical high
        )

        await vital_repo.save(normal)
        await vital_repo.save(critical)

        # Get critical readings
        results = await vital_repo.get_critical_readings(member.id, hours=24)

        assert len(results) == 1
        assert results[0].heart_rate == 130

    async def test_count_by_member(self, setup_test_data):
        """Should count vitals by member"""
        data = await setup_test_data
        vital_repo = data["vital_repo"]
        member = data["member"]

        # Create 3 vitals
        for i in range(3):
            vital = Vital.create(member_id=member.id, heart_rate=70+i)
            await vital_repo.save(vital)

        count = await vital_repo.count_by_member(member.id)

        assert count == 3

    async def test_get_anomalies(self, setup_test_data):
        """Should get anomaly-marked vitals"""
        data = await setup_test_data
        vital_repo = data["vital_repo"]
        member = data["member"]

        # Create normal vital
        normal = Vital.create(member_id=member.id, heart_rate=72)

        # Create anomaly vital
        anomaly = Vital.create(member_id=member.id, heart_rate=72)
        anomaly.mark_as_anomaly("node_red_toggle")

        await vital_repo.save(normal)
        await vital_repo.save(anomaly)

        # Get anomalies
        results = await vital_repo.get_anomalies(member.id)

        assert len(results) == 1
        assert results[0].is_anomaly is True

    async def test_update_vital(self, setup_test_data):
        """Should update an existing vital"""
        data = await setup_test_data
        vital_repo = data["vital_repo"]
        member = data["member"]

        # Create and save vital
        vital = Vital.create(member_id=member.id, heart_rate=72)
        saved = await vital_repo.save(vital)

        # Update vital
        saved.mark_as_anomaly("manual")
        updated = await vital_repo.save(saved)

        # Retrieve and verify
        retrieved = await vital_repo.get_by_id(updated.id)

        assert retrieved.is_anomaly is True
        assert retrieved.anomaly_source == "manual"
