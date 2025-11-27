"""
Unit Tests for AlertModel
Tests the domain logic for alert creation and status management.
"""
import pytest
from datetime import datetime, timezone

from src.core.domain.AlertModel import Alert, AlertStatus, AlertType, ThresholdType
from src.core.domain.VitalModel import VitalStatus


class TestAlertCreate:
    """Tests for Alert.create() factory method"""

    def test_create_alert(self):
        """Should create an alert with all required fields"""
        alert = Alert.create(
            member_id="member-123",
            alert_type=AlertType.HEART_RATE,
            severity=VitalStatus.WARNING,
            metric_value=110.0,
            threshold_value=100.0,
            threshold_type=ThresholdType.MAX,
            message="Heart rate elevated"
        )

        assert alert.member_id == "member-123"
        assert alert.alert_type == AlertType.HEART_RATE
        assert alert.severity == VitalStatus.WARNING
        assert alert.metric_value == 110.0
        assert alert.threshold_value == 100.0
        assert alert.threshold_type == ThresholdType.MAX
        assert alert.status == AlertStatus.ACTIVE
        assert alert.id is not None
        assert alert.created_at is not None

    def test_create_alert_with_vital_id(self):
        """Should create an alert linked to a vital reading"""
        alert = Alert.create(
            member_id="member-123",
            alert_type=AlertType.OXYGEN_LEVEL,
            severity=VitalStatus.CRITICAL,
            metric_value=85.0,
            threshold_value=90.0,
            threshold_type=ThresholdType.MIN,
            message="Oxygen critical",
            vital_id="vital-456"
        )

        assert alert.vital_id == "vital-456"


class TestHeartRateAlert:
    """Tests for heart rate alert creation"""

    def test_create_high_heart_rate_warning_alert(self):
        """Should create warning alert for elevated heart rate"""
        alert = Alert.create_heart_rate_alert(
            member_id="member-123",
            member_name="Roberto",
            heart_rate=110,
            threshold=100,
            is_high=True
        )

        assert alert.alert_type == AlertType.HEART_RATE
        assert alert.severity == VitalStatus.WARNING
        assert alert.threshold_type == ThresholdType.MAX
        assert alert.metric_value == 110.0
        assert alert.threshold_value == 100.0
        assert "Roberto" in alert.message
        assert "elevado" in alert.message

    def test_create_low_heart_rate_warning_alert(self):
        """Should create warning alert for low heart rate"""
        alert = Alert.create_heart_rate_alert(
            member_id="member-123",
            member_name="Roberto",
            heart_rate=55,
            threshold=60,
            is_high=False
        )

        assert alert.severity == VitalStatus.WARNING
        assert alert.threshold_type == ThresholdType.MIN
        assert "bajo" in alert.message

    def test_create_critical_high_heart_rate_alert(self):
        """Should create critical alert for very high heart rate (>120)"""
        alert = Alert.create_heart_rate_alert(
            member_id="member-123",
            member_name="Roberto",
            heart_rate=130,
            threshold=100,
            is_high=True
        )

        assert alert.severity == VitalStatus.CRITICAL

    def test_create_critical_low_heart_rate_alert(self):
        """Should create critical alert for very low heart rate (<50)"""
        alert = Alert.create_heart_rate_alert(
            member_id="member-123",
            member_name="Roberto",
            heart_rate=45,
            threshold=60,
            is_high=False
        )

        assert alert.severity == VitalStatus.CRITICAL


class TestOxygenAlert:
    """Tests for oxygen level alert creation"""

    def test_create_oxygen_warning_alert(self):
        """Should create warning alert for low oxygen (90-94)"""
        alert = Alert.create_oxygen_alert(
            member_id="member-123",
            member_name="Elena",
            oxygen_level=92,
            threshold=95
        )

        assert alert.alert_type == AlertType.OXYGEN_LEVEL
        assert alert.severity == VitalStatus.WARNING
        assert alert.threshold_type == ThresholdType.MIN
        assert "Elena" in alert.message
        assert "92" in alert.message

    def test_create_oxygen_critical_alert(self):
        """Should create critical alert for very low oxygen (<90)"""
        alert = Alert.create_oxygen_alert(
            member_id="member-123",
            member_name="Elena",
            oxygen_level=85,
            threshold=95
        )

        assert alert.severity == VitalStatus.CRITICAL


class TestTemperatureAlert:
    """Tests for temperature alert creation"""

    def test_create_high_temperature_warning_alert(self):
        """Should create warning alert for elevated temperature"""
        alert = Alert.create_temperature_alert(
            member_id="member-123",
            member_name="José",
            temperature=37.8,
            threshold=37.2,
            is_high=True
        )

        assert alert.alert_type == AlertType.TEMPERATURE
        assert alert.severity == VitalStatus.WARNING
        assert alert.threshold_type == ThresholdType.MAX
        assert "elevada" in alert.message

    def test_create_low_temperature_warning_alert(self):
        """Should create warning alert for low temperature"""
        alert = Alert.create_temperature_alert(
            member_id="member-123",
            member_name="José",
            temperature=35.5,
            threshold=36.1,
            is_high=False
        )

        assert alert.severity == VitalStatus.WARNING
        assert "baja" in alert.message

    def test_create_critical_fever_alert(self):
        """Should create critical alert for fever (>38)"""
        alert = Alert.create_temperature_alert(
            member_id="member-123",
            member_name="José",
            temperature=39.0,
            threshold=37.2,
            is_high=True
        )

        assert alert.severity == VitalStatus.CRITICAL

    def test_create_critical_hypothermia_alert(self):
        """Should create critical alert for hypothermia (<35)"""
        alert = Alert.create_temperature_alert(
            member_id="member-123",
            member_name="José",
            temperature=34.5,
            threshold=36.1,
            is_high=False
        )

        assert alert.severity == VitalStatus.CRITICAL


class TestStepsAlert:
    """Tests for steps alert creation"""

    def test_create_steps_warning_alert(self):
        """Should create warning alert for low steps"""
        alert = Alert.create_steps_alert(
            member_id="member-123",
            member_name="Roberto",
            steps=3500,
            threshold=5000
        )

        assert alert.alert_type == AlertType.STEPS
        assert alert.severity == VitalStatus.WARNING
        assert alert.threshold_type == ThresholdType.MIN
        assert "3,500" in alert.message

    def test_create_steps_critical_alert(self):
        """Should create critical alert for very low steps (<2000)"""
        alert = Alert.create_steps_alert(
            member_id="member-123",
            member_name="Roberto",
            steps=1000,
            threshold=5000
        )

        assert alert.severity == VitalStatus.CRITICAL


class TestAlertStatusManagement:
    """Tests for alert status transitions"""

    def test_acknowledge_alert(self):
        """Should acknowledge an alert"""
        alert = Alert.create_heart_rate_alert(
            member_id="member-123",
            member_name="Test",
            heart_rate=110,
            threshold=100,
            is_high=True
        )

        alert.acknowledge("user-456")

        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_by == "user-456"
        assert alert.acknowledged_at is not None

    def test_resolve_alert(self):
        """Should resolve an alert"""
        alert = Alert.create_heart_rate_alert(
            member_id="member-123",
            member_name="Test",
            heart_rate=110,
            threshold=100,
            is_high=True
        )

        alert.resolve("Patient stabilized")

        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_at is not None
        assert alert.resolution_notes == "Patient stabilized"

    def test_dismiss_alert(self):
        """Should dismiss an alert as false positive"""
        alert = Alert.create_heart_rate_alert(
            member_id="member-123",
            member_name="Test",
            heart_rate=110,
            threshold=100,
            is_high=True
        )

        alert.dismiss("False positive - device malfunction")

        assert alert.status == AlertStatus.DISMISSED
        assert alert.resolved_at is not None
        assert alert.resolution_notes == "False positive - device malfunction"


class TestAlertHelperMethods:
    """Tests for alert helper methods"""

    def test_is_active(self):
        """Should check if alert is active"""
        alert = Alert.create_heart_rate_alert(
            member_id="member-123",
            member_name="Test",
            heart_rate=110,
            threshold=100,
            is_high=True
        )

        assert alert.is_active() is True

        alert.acknowledge("user-123")
        assert alert.is_active() is False

    def test_is_critical(self):
        """Should check if alert is critical severity"""
        warning_alert = Alert.create_heart_rate_alert(
            member_id="member-123",
            member_name="Test",
            heart_rate=110,
            threshold=100,
            is_high=True
        )
        critical_alert = Alert.create_heart_rate_alert(
            member_id="member-123",
            member_name="Test",
            heart_rate=130,
            threshold=100,
            is_high=True
        )

        assert warning_alert.is_critical() is False
        assert critical_alert.is_critical() is True

    def test_is_warning(self):
        """Should check if alert is warning severity"""
        warning_alert = Alert.create_heart_rate_alert(
            member_id="member-123",
            member_name="Test",
            heart_rate=110,
            threshold=100,
            is_high=True
        )
        critical_alert = Alert.create_heart_rate_alert(
            member_id="member-123",
            member_name="Test",
            heart_rate=130,
            threshold=100,
            is_high=True
        )

        assert warning_alert.is_warning() is True
        assert critical_alert.is_warning() is False
