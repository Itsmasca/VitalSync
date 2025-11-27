"""
Unit Tests for VitalModel
Tests the domain logic for vital signs calculations and status determination.
"""
import pytest
from datetime import datetime, timezone

from src.core.domain.VitalModel import Vital, VitalStatus


class TestVitalCreate:
    """Tests for Vital.create() factory method"""

    def test_create_vital_with_all_metrics(self):
        """Should create a vital with all metrics"""
        vital = Vital.create(
            member_id="member-123",
            heart_rate=72,
            oxygen_level=96.5,
            body_temperature=36.5,
            steps=5000
        )

        assert vital.member_id == "member-123"
        assert vital.heart_rate == 72
        assert vital.oxygen_level == 96.5
        assert vital.body_temperature == 36.5
        assert vital.steps == 5000
        assert vital.id is not None
        assert vital.reading_timestamp is not None
        assert vital.received_at is not None

    def test_create_vital_with_partial_metrics(self):
        """Should create a vital with only some metrics"""
        vital = Vital.create(
            member_id="member-123",
            heart_rate=72
        )

        assert vital.heart_rate == 72
        assert vital.oxygen_level is None
        assert vital.body_temperature is None
        assert vital.steps is None

    def test_create_vital_with_custom_timestamp(self):
        """Should create a vital with custom reading timestamp"""
        custom_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        vital = Vital.create(
            member_id="member-123",
            heart_rate=72,
            reading_timestamp=custom_time
        )

        assert vital.reading_timestamp == custom_time


class TestHeartRateStatus:
    """Tests for heart rate status calculation"""

    @pytest.mark.parametrize("heart_rate,expected_status", [
        (70, VitalStatus.NORMAL),    # Normal range
        (60, VitalStatus.NORMAL),    # Boundary normal low
        (100, VitalStatus.NORMAL),   # Boundary normal high
        (55, VitalStatus.WARNING),   # Warning low
        (110, VitalStatus.WARNING),  # Warning high
        (45, VitalStatus.CRITICAL),  # Critical low
        (130, VitalStatus.CRITICAL), # Critical high
        (50, VitalStatus.CRITICAL),  # Boundary critical low
        (120, VitalStatus.CRITICAL), # Boundary critical high
    ])
    def test_heart_rate_status_default_thresholds(self, heart_rate, expected_status):
        """Should calculate correct heart rate status with default thresholds"""
        vital = Vital.create(member_id="test", heart_rate=heart_rate)
        assert vital.heart_rate_status == expected_status

    def test_heart_rate_with_custom_thresholds(self):
        """Should use custom thresholds when provided"""
        vital = Vital.create(member_id="test", heart_rate=55)
        # Default: 55 is WARNING
        assert vital.heart_rate_status == VitalStatus.WARNING

        # Recalculate with custom thresholds (55-90 is normal for this person)
        vital.calculate_statuses(custom_hr_min=55, custom_hr_max=90)
        assert vital.heart_rate_status == VitalStatus.NORMAL

    def test_none_heart_rate_is_normal(self):
        """Should return NORMAL when heart rate is None"""
        vital = Vital.create(member_id="test", heart_rate=None)
        assert vital.heart_rate_status == VitalStatus.NORMAL


class TestOxygenStatus:
    """Tests for oxygen level status calculation"""

    @pytest.mark.parametrize("oxygen_level,expected_status", [
        (98, VitalStatus.NORMAL),    # Normal
        (95, VitalStatus.NORMAL),    # Boundary normal
        (92, VitalStatus.WARNING),   # Warning
        (90, VitalStatus.CRITICAL),  # Boundary critical
        (85, VitalStatus.CRITICAL),  # Critical
    ])
    def test_oxygen_status_default_thresholds(self, oxygen_level, expected_status):
        """Should calculate correct oxygen status with default thresholds"""
        vital = Vital.create(member_id="test", oxygen_level=oxygen_level)
        assert vital.oxygen_status == expected_status

    def test_oxygen_with_custom_threshold(self):
        """Should use custom minimum threshold when provided"""
        vital = Vital.create(member_id="test", oxygen_level=88)
        # Default: 88 is CRITICAL (<90)
        assert vital.oxygen_status == VitalStatus.CRITICAL

        # Recalculate with custom threshold (88 is warning for this person)
        vital.calculate_statuses(custom_spo2_min=85)
        assert vital.oxygen_status == VitalStatus.WARNING


class TestTemperatureStatus:
    """Tests for body temperature status calculation"""

    @pytest.mark.parametrize("temperature,expected_status", [
        (36.5, VitalStatus.NORMAL),   # Normal
        (36.1, VitalStatus.NORMAL),   # Boundary normal low
        (37.2, VitalStatus.NORMAL),   # Boundary normal high
        (36.0, VitalStatus.WARNING),  # Warning low
        (37.5, VitalStatus.WARNING),  # Warning high
        (34.5, VitalStatus.CRITICAL), # Critical low (hypothermia)
        (38.5, VitalStatus.CRITICAL), # Critical high (fever)
    ])
    def test_temperature_status_default_thresholds(self, temperature, expected_status):
        """Should calculate correct temperature status with default thresholds"""
        vital = Vital.create(member_id="test", body_temperature=temperature)
        assert vital.temperature_status == expected_status


class TestStepsStatus:
    """Tests for steps status calculation"""

    @pytest.mark.parametrize("steps,expected_status", [
        (8000, VitalStatus.NORMAL),   # Normal (>5000)
        (5000, VitalStatus.NORMAL),   # Boundary normal
        (3500, VitalStatus.WARNING),  # Warning
        (2000, VitalStatus.CRITICAL), # Boundary critical
        (1000, VitalStatus.CRITICAL), # Critical
    ])
    def test_steps_status_default_thresholds(self, steps, expected_status):
        """Should calculate correct steps status with default thresholds"""
        vital = Vital.create(member_id="test", steps=steps)
        assert vital.steps_status == expected_status


class TestOverallStatus:
    """Tests for overall status calculation"""

    def test_all_normal_gives_normal_overall(self):
        """Should return NORMAL when all metrics are normal"""
        vital = Vital.create(
            member_id="test",
            heart_rate=72,
            oxygen_level=98,
            body_temperature=36.5,
            steps=8000
        )
        assert vital.overall_status == VitalStatus.NORMAL

    def test_one_warning_gives_warning_overall(self):
        """Should return WARNING when at least one metric is warning"""
        vital = Vital.create(
            member_id="test",
            heart_rate=72,      # Normal
            oxygen_level=92,    # Warning
            body_temperature=36.5,
            steps=8000
        )
        assert vital.overall_status == VitalStatus.WARNING

    def test_one_critical_gives_critical_overall(self):
        """Should return CRITICAL when at least one metric is critical"""
        vital = Vital.create(
            member_id="test",
            heart_rate=72,      # Normal
            oxygen_level=98,    # Normal
            body_temperature=39.0,  # Critical
            steps=8000
        )
        assert vital.overall_status == VitalStatus.CRITICAL

    def test_critical_overrides_warning(self):
        """Should return CRITICAL even if there are warnings"""
        vital = Vital.create(
            member_id="test",
            heart_rate=55,      # Warning
            oxygen_level=85,    # Critical
            body_temperature=36.5,
            steps=8000
        )
        assert vital.overall_status == VitalStatus.CRITICAL


class TestAnomalyMarking:
    """Tests for anomaly marking functionality"""

    def test_mark_as_anomaly(self):
        """Should mark vital as anomaly"""
        vital = Vital.create(member_id="test", heart_rate=72)
        assert vital.is_anomaly is False

        vital.mark_as_anomaly("node_red_toggle")

        assert vital.is_anomaly is True
        assert vital.anomaly_source == "node_red_toggle"

    def test_is_critical_method(self):
        """Should return True for critical readings"""
        normal_vital = Vital.create(member_id="test", heart_rate=72)
        critical_vital = Vital.create(member_id="test", heart_rate=130)

        assert normal_vital.is_critical() is False
        assert critical_vital.is_critical() is True

    def test_is_warning_method(self):
        """Should return True for warning readings"""
        normal_vital = Vital.create(member_id="test", heart_rate=72)
        warning_vital = Vital.create(member_id="test", heart_rate=105)

        assert normal_vital.is_warning() is False
        assert warning_vital.is_warning() is True


class TestVitalHelperMethods:
    """Tests for helper methods"""

    def test_get_reading_date(self):
        """Should return date from reading timestamp"""
        timestamp = datetime(2025, 6, 15, 14, 30, 0, tzinfo=timezone.utc)
        vital = Vital.create(
            member_id="test",
            heart_rate=72,
            reading_timestamp=timestamp
        )

        assert vital.get_reading_date().year == 2025
        assert vital.get_reading_date().month == 6
        assert vital.get_reading_date().day == 15

    def test_has_blood_pressure(self):
        """Should check if blood pressure data exists"""
        vital_without_bp = Vital.create(member_id="test", heart_rate=72)
        assert vital_without_bp.has_blood_pressure() is False

        vital_with_bp = Vital.create(member_id="test", heart_rate=72)
        vital_with_bp.blood_pressure_systolic = 120
        vital_with_bp.blood_pressure_diastolic = 80
        assert vital_with_bp.has_blood_pressure() is True
