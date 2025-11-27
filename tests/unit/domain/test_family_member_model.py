"""
Unit Tests for FamilyMemberModel
Tests the domain logic for family member management.
"""
import pytest
from datetime import date, datetime, timezone

from src.core.domain.FamilyMemberModel import (
    FamilyMember, RelationshipType, DeviceType, Gender, VitalThresholds
)


class TestFamilyMemberCreate:
    """Tests for FamilyMember.create() factory method"""

    def test_create_family_member(self):
        """Should create a family member with required fields"""
        member = FamilyMember.create(
            family_id="family-123",
            member_id="familia-garcia-papa",
            name="Roberto García",
            relationship=RelationshipType.PADRE,
            device_id="XIAOMI-PAPA-001",
            device_type=DeviceType.XIAOMI_BAND
        )

        assert member.family_id == "family-123"
        assert member.member_id == "familia-garcia-papa"
        assert member.name == "Roberto García"
        assert member.relationship == RelationshipType.PADRE
        assert member.device_id == "XIAOMI-PAPA-001"
        assert member.device_type == DeviceType.XIAOMI_BAND
        assert member.is_active is True
        assert member.alerts_enabled is True
        assert member.id is not None

    def test_create_family_member_with_device_name(self):
        """Should create a family member with device name"""
        member = FamilyMember.create(
            family_id="family-123",
            member_id="familia-garcia-mama",
            name="Elena García",
            relationship=RelationshipType.MADRE,
            device_id="APPLE-MAMA-002",
            device_type=DeviceType.APPLE_WATCH,
            device_name="Apple Watch Series 9"
        )

        assert member.device_name == "Apple Watch Series 9"


class TestRelationshipTypes:
    """Tests for different relationship types"""

    @pytest.mark.parametrize("relationship", [
        RelationshipType.SELF,
        RelationshipType.PADRE,
        RelationshipType.MADRE,
        RelationshipType.HIJO,
        RelationshipType.ABUELO,
        RelationshipType.ESPOSO,
        RelationshipType.HERMANO,
        RelationshipType.OTRO,
    ])
    def test_all_relationship_types(self, relationship):
        """Should support all relationship types"""
        member = FamilyMember.create(
            family_id="family-123",
            member_id=f"familia-garcia-{relationship.value}",
            name="Test Member",
            relationship=relationship,
            device_id="TEST-001",
            device_type=DeviceType.OTHER
        )

        assert member.relationship == relationship


class TestDeviceTypes:
    """Tests for different device types"""

    @pytest.mark.parametrize("device_type", [
        DeviceType.APPLE_WATCH,
        DeviceType.XIAOMI_BAND,
        DeviceType.FITBIT,
        DeviceType.GARMIN,
        DeviceType.SAMSUNG_WATCH,
        DeviceType.HUAWEI_BAND,
        DeviceType.NODE_RED_SIM,
        DeviceType.OTHER,
    ])
    def test_all_device_types(self, device_type):
        """Should support all device types"""
        member = FamilyMember.create(
            family_id="family-123",
            member_id="familia-garcia-test",
            name="Test Member",
            relationship=RelationshipType.OTRO,
            device_id="TEST-001",
            device_type=device_type
        )

        assert member.device_type == device_type


class TestAgeCalculation:
    """Tests for age calculation"""

    def test_get_age_returns_correct_age(self):
        """Should calculate correct age"""
        member = FamilyMember.create(
            family_id="family-123",
            member_id="familia-garcia-papa",
            name="Roberto",
            relationship=RelationshipType.PADRE,
            device_id="TEST-001",
            device_type=DeviceType.OTHER
        )
        # Set DOB to 50 years ago
        today = date.today()
        member.date_of_birth = date(today.year - 50, today.month, today.day)

        assert member.get_age() == 50

    def test_get_age_handles_birthday_not_yet(self):
        """Should handle when birthday hasn't occurred this year"""
        member = FamilyMember.create(
            family_id="family-123",
            member_id="familia-garcia-papa",
            name="Roberto",
            relationship=RelationshipType.PADRE,
            device_id="TEST-001",
            device_type=DeviceType.OTHER
        )
        # Set DOB to 50 years ago, but birthday is in the future this year
        today = date.today()
        future_month = (today.month % 12) + 1
        member.date_of_birth = date(today.year - 50, future_month, 15)

        assert member.get_age() == 49

    def test_get_age_returns_none_when_no_dob(self):
        """Should return None when date of birth is not set"""
        member = FamilyMember.create(
            family_id="family-123",
            member_id="familia-garcia-papa",
            name="Roberto",
            relationship=RelationshipType.PADRE,
            device_id="TEST-001",
            device_type=DeviceType.OTHER
        )

        assert member.get_age() is None


class TestThresholds:
    """Tests for custom thresholds"""

    def test_set_thresholds(self):
        """Should set custom thresholds"""
        member = FamilyMember.create(
            family_id="family-123",
            member_id="familia-garcia-papa",
            name="Roberto",
            relationship=RelationshipType.PADRE,
            device_id="TEST-001",
            device_type=DeviceType.OTHER
        )

        custom_thresholds = VitalThresholds(
            hr_min=55,
            hr_max=90,
            spo2_min=92,
            temp_min=35.5,
            temp_max=37.8,
            steps_min=3000
        )

        member.set_thresholds(custom_thresholds)

        assert member.thresholds.hr_min == 55
        assert member.thresholds.hr_max == 90
        assert member.thresholds.spo2_min == 92
        assert member.thresholds.temp_min == 35.5
        assert member.thresholds.temp_max == 37.8
        assert member.thresholds.steps_min == 3000

    def test_default_thresholds_are_none(self):
        """Should have None thresholds by default (use system defaults)"""
        member = FamilyMember.create(
            family_id="family-123",
            member_id="familia-garcia-papa",
            name="Roberto",
            relationship=RelationshipType.PADRE,
            device_id="TEST-001",
            device_type=DeviceType.OTHER
        )

        assert member.thresholds.hr_min is None
        assert member.thresholds.hr_max is None
        assert member.thresholds.spo2_min is None


class TestAlertManagement:
    """Tests for alert enable/disable"""

    def test_disable_alerts(self):
        """Should disable alerts"""
        member = FamilyMember.create(
            family_id="family-123",
            member_id="familia-garcia-papa",
            name="Roberto",
            relationship=RelationshipType.PADRE,
            device_id="TEST-001",
            device_type=DeviceType.OTHER
        )

        member.disable_alerts()

        assert member.alerts_enabled is False

    def test_enable_alerts(self):
        """Should enable alerts"""
        member = FamilyMember.create(
            family_id="family-123",
            member_id="familia-garcia-papa",
            name="Roberto",
            relationship=RelationshipType.PADRE,
            device_id="TEST-001",
            device_type=DeviceType.OTHER
        )
        member.disable_alerts()

        member.enable_alerts()

        assert member.alerts_enabled is True


class TestActivation:
    """Tests for member activation/deactivation"""

    def test_deactivate_member(self):
        """Should deactivate member"""
        member = FamilyMember.create(
            family_id="family-123",
            member_id="familia-garcia-papa",
            name="Roberto",
            relationship=RelationshipType.PADRE,
            device_id="TEST-001",
            device_type=DeviceType.OTHER
        )

        member.deactivate()

        assert member.is_active is False

    def test_activate_member(self):
        """Should activate member"""
        member = FamilyMember.create(
            family_id="family-123",
            member_id="familia-garcia-papa",
            name="Roberto",
            relationship=RelationshipType.PADRE,
            device_id="TEST-001",
            device_type=DeviceType.OTHER
        )
        member.deactivate()

        member.activate()

        assert member.is_active is True


class TestDeviceUpdate:
    """Tests for device updates"""

    def test_update_device(self):
        """Should update device information"""
        member = FamilyMember.create(
            family_id="family-123",
            member_id="familia-garcia-papa",
            name="Roberto",
            relationship=RelationshipType.PADRE,
            device_id="OLD-DEVICE-001",
            device_type=DeviceType.XIAOMI_BAND
        )
        original_updated_at = member.updated_at

        member.update_device(
            device_id="NEW-DEVICE-002",
            device_type=DeviceType.APPLE_WATCH,
            device_name="Apple Watch Ultra"
        )

        assert member.device_id == "NEW-DEVICE-002"
        assert member.device_type == DeviceType.APPLE_WATCH
        assert member.device_name == "Apple Watch Ultra"
        assert member.updated_at >= original_updated_at


class TestEmergencyContact:
    """Tests for emergency contact"""

    def test_set_emergency_contact(self):
        """Should set emergency contact"""
        member = FamilyMember.create(
            family_id="family-123",
            member_id="familia-garcia-papa",
            name="Roberto",
            relationship=RelationshipType.PADRE,
            device_id="TEST-001",
            device_type=DeviceType.OTHER
        )

        member.set_emergency_contact(
            contact="Dr. Juan Pérez",
            phone="+52 55 9876 5432"
        )

        assert member.emergency_contact == "Dr. Juan Pérez"
        assert member.emergency_phone == "+52 55 9876 5432"
