"""
Unit Tests for VitalService
Tests the business logic for vital signs management.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.core.domain.VitalModel import Vital, VitalStatus
from src.core.domain.FamilyMemberModel import FamilyMember, RelationshipType, DeviceType, VitalThresholds
from src.core.domain.AlertModel import Alert, AlertType
from src.core.services.vital_service import VitalService


class TestRecordVital:
    """Tests for VitalService.record_vital()"""

    @pytest.fixture
    def vital_service(self, mock_vital_repository, mock_family_member_repository, mock_alert_repository):
        """Creates a VitalService with mock repositories"""
        return VitalService(
            vital_repository=mock_vital_repository,
            family_member_repository=mock_family_member_repository,
            alert_repository=mock_alert_repository
        )

    @pytest.mark.asyncio
    async def test_record_vital_success(
        self,
        vital_service: VitalService,
        mock_family_member_repository: AsyncMock,
        sample_family_member: FamilyMember
    ):
        """Should record a vital reading successfully"""
        mock_family_member_repository.get_by_device_id.return_value = sample_family_member

        vital = await vital_service.record_vital(
            device_id="XIAOMI-PAPA-001",
            heart_rate=72,
            oxygen_level=96.5,
            body_temperature=36.5,
            steps=5000
        )

        assert vital.member_id == sample_family_member.id
        assert vital.heart_rate == 72
        assert vital.oxygen_level == 96.5
        assert vital.body_temperature == 36.5
        assert vital.steps == 5000

    @pytest.mark.asyncio
    async def test_record_vital_device_not_found(
        self,
        vital_service: VitalService,
        mock_family_member_repository: AsyncMock
    ):
        """Should raise error when device not found"""
        mock_family_member_repository.get_by_device_id.return_value = None

        with pytest.raises(ValueError) as exc_info:
            await vital_service.record_vital(
                device_id="UNKNOWN-DEVICE",
                heart_rate=72
            )

        assert "No se encontró familiar" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_record_vital_with_custom_thresholds(
        self,
        vital_service: VitalService,
        mock_family_member_repository: AsyncMock,
        sample_family_member: FamilyMember
    ):
        """Should use custom thresholds for status calculation"""
        # Set custom thresholds
        sample_family_member.thresholds = VitalThresholds(
            hr_min=55,  # Lower than default 60
            hr_max=110,  # Higher than default 100
            spo2_min=92,
            temp_min=35.5,
            temp_max=38.0,
            steps_min=3000
        )
        mock_family_member_repository.get_by_device_id.return_value = sample_family_member

        # Heart rate 55 is WARNING with default thresholds, but NORMAL with custom
        vital = await vital_service.record_vital(
            device_id="XIAOMI-PAPA-001",
            heart_rate=55
        )

        assert vital.heart_rate_status == VitalStatus.NORMAL

    @pytest.mark.asyncio
    async def test_record_vital_generates_alerts_for_critical(
        self,
        vital_service: VitalService,
        mock_family_member_repository: AsyncMock,
        mock_alert_repository: AsyncMock,
        sample_family_member: FamilyMember
    ):
        """Should generate alerts for critical readings"""
        sample_family_member.alerts_enabled = True
        mock_family_member_repository.get_by_device_id.return_value = sample_family_member

        await vital_service.record_vital(
            device_id="XIAOMI-PAPA-001",
            heart_rate=130  # Critical high
        )

        # Should have called save on alert repository
        mock_alert_repository.save.assert_called()
        saved_alert = mock_alert_repository.save.call_args[0][0]
        assert saved_alert.alert_type == AlertType.HEART_RATE

    @pytest.mark.asyncio
    async def test_record_vital_no_alerts_when_disabled(
        self,
        vital_service: VitalService,
        mock_family_member_repository: AsyncMock,
        mock_alert_repository: AsyncMock,
        sample_family_member: FamilyMember
    ):
        """Should not generate alerts when alerts are disabled"""
        sample_family_member.alerts_enabled = False
        mock_family_member_repository.get_by_device_id.return_value = sample_family_member

        await vital_service.record_vital(
            device_id="XIAOMI-PAPA-001",
            heart_rate=130  # Critical high
        )

        # Should NOT have called save on alert repository
        mock_alert_repository.save.assert_not_called()


class TestGetVitals:
    """Tests for VitalService get methods"""

    @pytest.fixture
    def vital_service(self, mock_vital_repository, mock_family_member_repository, mock_alert_repository):
        return VitalService(
            vital_repository=mock_vital_repository,
            family_member_repository=mock_family_member_repository,
            alert_repository=mock_alert_repository
        )

    @pytest.mark.asyncio
    async def test_get_latest_vital(
        self,
        vital_service: VitalService,
        mock_vital_repository: AsyncMock,
        sample_vital: Vital
    ):
        """Should get latest vital for member"""
        mock_vital_repository.get_latest_by_member.return_value = sample_vital

        result = await vital_service.get_latest_vital("member-123")

        assert result == sample_vital
        mock_vital_repository.get_latest_by_member.assert_called_with("member-123")

    @pytest.mark.asyncio
    async def test_get_vitals_by_member(
        self,
        vital_service: VitalService,
        mock_vital_repository: AsyncMock,
        sample_vital: Vital
    ):
        """Should get vitals by member with pagination"""
        mock_vital_repository.get_by_member.return_value = [sample_vital]

        result = await vital_service.get_vitals_by_member("member-123", limit=10, offset=0)

        assert len(result) == 1
        mock_vital_repository.get_by_member.assert_called_with("member-123", 10, 0)

    @pytest.mark.asyncio
    async def test_get_vitals_by_date_range(
        self,
        vital_service: VitalService,
        mock_vital_repository: AsyncMock,
        sample_vital: Vital
    ):
        """Should get vitals within date range"""
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        mock_vital_repository.get_by_member_and_date_range.return_value = [sample_vital]

        result = await vital_service.get_vitals_by_date_range("member-123", start, end)

        assert len(result) == 1
        mock_vital_repository.get_by_member_and_date_range.assert_called_with(
            "member-123", start, end
        )

    @pytest.mark.asyncio
    async def test_get_rolling_vitals(
        self,
        vital_service: VitalService,
        mock_vital_repository: AsyncMock,
        sample_vital: Vital
    ):
        """Should get rolling vitals for specified minutes"""
        mock_vital_repository.get_by_member_last_minutes.return_value = [sample_vital]

        result = await vital_service.get_rolling_vitals("member-123", minutes=5)

        assert len(result) == 1
        mock_vital_repository.get_by_member_last_minutes.assert_called_with("member-123", 5)

    @pytest.mark.asyncio
    async def test_get_critical_readings(
        self,
        vital_service: VitalService,
        mock_vital_repository: AsyncMock,
        critical_vital: Vital
    ):
        """Should get critical readings"""
        mock_vital_repository.get_critical_readings.return_value = [critical_vital]

        result = await vital_service.get_critical_readings(member_id="member-123", hours=24)

        assert len(result) == 1
        mock_vital_repository.get_critical_readings.assert_called_with("member-123", 24)


class TestAnomalyManagement:
    """Tests for anomaly marking"""

    @pytest.fixture
    def vital_service(self, mock_vital_repository, mock_family_member_repository, mock_alert_repository):
        return VitalService(
            vital_repository=mock_vital_repository,
            family_member_repository=mock_family_member_repository,
            alert_repository=mock_alert_repository
        )

    @pytest.mark.asyncio
    async def test_mark_as_anomaly(
        self,
        vital_service: VitalService,
        mock_vital_repository: AsyncMock,
        sample_vital: Vital
    ):
        """Should mark vital as anomaly"""
        mock_vital_repository.get_by_id.return_value = sample_vital

        result = await vital_service.mark_as_anomaly("vital-123", "node_red_toggle")

        assert result.is_anomaly is True
        assert result.anomaly_source == "node_red_toggle"

    @pytest.mark.asyncio
    async def test_mark_as_anomaly_not_found(
        self,
        vital_service: VitalService,
        mock_vital_repository: AsyncMock
    ):
        """Should return None when vital not found"""
        mock_vital_repository.get_by_id.return_value = None

        result = await vital_service.mark_as_anomaly("unknown-vital", "manual")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_anomalies(
        self,
        vital_service: VitalService,
        mock_vital_repository: AsyncMock,
        sample_vital: Vital
    ):
        """Should get anomalies"""
        sample_vital.is_anomaly = True
        mock_vital_repository.get_anomalies.return_value = [sample_vital]

        result = await vital_service.get_anomalies("member-123")

        assert len(result) == 1
        assert result[0].is_anomaly is True


class TestStatistics:
    """Tests for statistics methods"""

    @pytest.fixture
    def vital_service(self, mock_vital_repository, mock_family_member_repository, mock_alert_repository):
        return VitalService(
            vital_repository=mock_vital_repository,
            family_member_repository=mock_family_member_repository,
            alert_repository=mock_alert_repository
        )

    @pytest.mark.asyncio
    async def test_count_readings_by_member(
        self,
        vital_service: VitalService,
        mock_vital_repository: AsyncMock
    ):
        """Should count readings by member"""
        mock_vital_repository.count_by_member.return_value = 100

        result = await vital_service.count_readings_by_member("member-123")

        assert result == 100

    @pytest.mark.asyncio
    async def test_count_readings_last_hour(
        self,
        vital_service: VitalService,
        mock_vital_repository: AsyncMock
    ):
        """Should count readings in last hour"""
        mock_vital_repository.count_readings_last_hour.return_value = 50

        result = await vital_service.count_readings_last_hour()

        assert result == 50


class TestAlertGeneration:
    """Tests for alert generation logic"""

    @pytest.fixture
    def vital_service(self, mock_vital_repository, mock_family_member_repository, mock_alert_repository):
        return VitalService(
            vital_repository=mock_vital_repository,
            family_member_repository=mock_family_member_repository,
            alert_repository=mock_alert_repository
        )

    @pytest.mark.asyncio
    async def test_generates_heart_rate_high_alert(
        self,
        vital_service: VitalService,
        mock_family_member_repository: AsyncMock,
        mock_alert_repository: AsyncMock,
        sample_family_member: FamilyMember
    ):
        """Should generate high heart rate alert"""
        sample_family_member.alerts_enabled = True
        mock_family_member_repository.get_by_device_id.return_value = sample_family_member

        await vital_service.record_vital(
            device_id="XIAOMI-PAPA-001",
            heart_rate=125
        )

        mock_alert_repository.save.assert_called()

    @pytest.mark.asyncio
    async def test_generates_oxygen_alert(
        self,
        vital_service: VitalService,
        mock_family_member_repository: AsyncMock,
        mock_alert_repository: AsyncMock,
        sample_family_member: FamilyMember
    ):
        """Should generate low oxygen alert"""
        sample_family_member.alerts_enabled = True
        mock_family_member_repository.get_by_device_id.return_value = sample_family_member

        await vital_service.record_vital(
            device_id="XIAOMI-PAPA-001",
            oxygen_level=88
        )

        mock_alert_repository.save.assert_called()

    @pytest.mark.asyncio
    async def test_generates_temperature_alert(
        self,
        vital_service: VitalService,
        mock_family_member_repository: AsyncMock,
        mock_alert_repository: AsyncMock,
        sample_family_member: FamilyMember
    ):
        """Should generate high temperature alert"""
        sample_family_member.alerts_enabled = True
        mock_family_member_repository.get_by_device_id.return_value = sample_family_member

        await vital_service.record_vital(
            device_id="XIAOMI-PAPA-001",
            body_temperature=39.0
        )

        mock_alert_repository.save.assert_called()

    @pytest.mark.asyncio
    async def test_generates_steps_alert(
        self,
        vital_service: VitalService,
        mock_family_member_repository: AsyncMock,
        mock_alert_repository: AsyncMock,
        sample_family_member: FamilyMember
    ):
        """Should generate low steps alert"""
        sample_family_member.alerts_enabled = True
        mock_family_member_repository.get_by_device_id.return_value = sample_family_member

        await vital_service.record_vital(
            device_id="XIAOMI-PAPA-001",
            steps=1500
        )

        mock_alert_repository.save.assert_called()

    @pytest.mark.asyncio
    async def test_no_alert_for_normal_readings(
        self,
        vital_service: VitalService,
        mock_family_member_repository: AsyncMock,
        mock_alert_repository: AsyncMock,
        sample_family_member: FamilyMember
    ):
        """Should not generate alerts for normal readings"""
        sample_family_member.alerts_enabled = True
        mock_family_member_repository.get_by_device_id.return_value = sample_family_member

        await vital_service.record_vital(
            device_id="XIAOMI-PAPA-001",
            heart_rate=72,
            oxygen_level=98,
            body_temperature=36.5,
            steps=8000
        )

        mock_alert_repository.save.assert_not_called()
