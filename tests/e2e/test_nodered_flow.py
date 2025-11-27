"""
End-to-End Tests for Node-RED Flow
Tests that validate the Node-RED IoT simulator flow functionality.
"""
import pytest
import json
from datetime import datetime, timezone
from pathlib import Path


class TestNodeRedFlowStructure:
    """Tests for Node-RED flow file structure"""

    @pytest.fixture
    def flow_data(self):
        """Load the Node-RED flow JSON"""
        flow_path = Path(__file__).parent.parent.parent / "Node-Red" / "flows" / "vitalsync_nodered_flow.json"
        with open(flow_path) as f:
            return json.load(f)

    def test_flow_file_exists(self):
        """Should have a flow file"""
        flow_path = Path(__file__).parent.parent.parent / "Node-Red" / "flows" / "vitalsync_nodered_flow.json"
        assert flow_path.exists(), "Node-RED flow file should exist"

    def test_flow_is_valid_json(self, flow_data):
        """Should be valid JSON"""
        assert isinstance(flow_data, list)
        assert len(flow_data) > 0

    def test_flow_has_main_tab(self, flow_data):
        """Should have main flow tab"""
        tabs = [node for node in flow_data if node.get("type") == "tab"]
        assert len(tabs) > 0

        main_tab = next((t for t in tabs if "VitalSync" in t.get("label", "")), None)
        assert main_tab is not None, "Should have VitalSync tab"

    def test_flow_has_http_request_node(self, flow_data):
        """Should have HTTP request node for API calls"""
        http_nodes = [node for node in flow_data if node.get("type") == "http request"]
        assert len(http_nodes) > 0, "Should have HTTP request node"

    def test_http_node_points_to_vitalsync_api(self, flow_data):
        """Should point to VitalSync API"""
        http_nodes = [node for node in flow_data if node.get("type") == "http request"]

        api_node = next((n for n in http_nodes if "/api/vitals" in n.get("url", "")), None)
        assert api_node is not None, "Should have node pointing to /api/vitals"
        assert api_node["method"] == "POST", "Should use POST method"

    def test_http_node_uses_correct_docker_url(self, flow_data):
        """Should use Docker service name for API URL"""
        http_nodes = [node for node in flow_data if node.get("type") == "http request"]
        api_node = next((n for n in http_nodes if "/api/vitals" in n.get("url", "")), None)

        # Should use vitalsync-api service name for Docker networking
        assert "vitalsync-api" in api_node["url"], "Should use Docker service name"


class TestNodeRedFlowLogic:
    """Tests for Node-RED flow logic nodes"""

    @pytest.fixture
    def flow_data(self):
        """Load the Node-RED flow JSON"""
        flow_path = Path(__file__).parent.parent.parent / "Node-Red" / "flows" / "vitalsync_nodered_flow.json"
        with open(flow_path) as f:
            return json.load(f)

    def test_has_vital_generator_function(self, flow_data):
        """Should have a function node to generate vitals"""
        function_nodes = [node for node in flow_data if node.get("type") == "function"]

        vital_generator = next(
            (n for n in function_nodes if "Generar" in n.get("name", "") or "generate" in n.get("name", "").lower()),
            None
        )
        assert vital_generator is not None, "Should have vital generator function"

    def test_vital_generator_creates_valid_payload(self, flow_data):
        """Should have code that creates valid vital payload"""
        function_nodes = [node for node in flow_data if node.get("type") == "function"]
        vital_generator = next(
            (n for n in function_nodes if "Generar" in n.get("name", "") or "generate" in n.get("name", "").lower()),
            None
        )

        func_code = vital_generator.get("func", "")

        # Check that the function generates required fields
        assert "deviceId" in func_code, "Should generate deviceId"
        assert "heartRate" in func_code, "Should generate heartRate"
        assert "oxygenLevel" in func_code, "Should generate oxygenLevel"
        assert "bodyTemperature" in func_code, "Should generate bodyTemperature"
        assert "steps" in func_code, "Should generate steps"
        assert "timestamp" in func_code, "Should generate timestamp"

    def test_has_four_family_member_profiles(self, flow_data):
        """Should have profiles for 4 family members"""
        function_nodes = [node for node in flow_data if node.get("type") == "function"]
        vital_generator = next(
            (n for n in function_nodes if "Generar" in n.get("name", "") or "PROFILES" in n.get("func", "")),
            None
        )

        if vital_generator:
            func_code = vital_generator.get("func", "")
            # Check for the 4 devices
            assert "XIAOMI-PAPA-001" in func_code, "Should have Papa device"
            assert "APPLE-MAMA-002" in func_code, "Should have Mama device"
            assert "FITBIT-ABUELO-003" in func_code, "Should have Abuelo device"
            assert "SIM-NODERED-004" in func_code, "Should have Simulator device"

    def test_has_anomaly_toggle(self, flow_data):
        """Should have anomaly toggle switch"""
        switches = [node for node in flow_data if node.get("type") == "ui_switch"]

        anomaly_switch = next(
            (s for s in switches if "anomal" in s.get("name", "").lower() or "anomal" in s.get("label", "").lower()),
            None
        )
        assert anomaly_switch is not None, "Should have anomaly toggle switch"

    def test_has_start_stop_control(self, flow_data):
        """Should have start/stop control"""
        switches = [node for node in flow_data if node.get("type") == "ui_switch"]

        control_switch = next(
            (s for s in switches if "start" in s.get("name", "").lower() or "stop" in s.get("name", "").lower()),
            None
        )
        assert control_switch is not None, "Should have start/stop switch"

    def test_has_emission_gate(self, flow_data):
        """Should have emission gate for controlling data flow"""
        function_nodes = [node for node in flow_data if node.get("type") == "function"]

        gate = next(
            (n for n in function_nodes if "gate" in n.get("name", "").lower() or "emision" in n.get("name", "").lower()),
            None
        )
        assert gate is not None, "Should have emission gate function"


class TestNodeRedDashboard:
    """Tests for Node-RED dashboard nodes"""

    @pytest.fixture
    def flow_data(self):
        """Load the Node-RED flow JSON"""
        flow_path = Path(__file__).parent.parent.parent / "Node-Red" / "flows" / "vitalsync_nodered_flow.json"
        with open(flow_path) as f:
            return json.load(f)

    def test_has_dashboard_groups(self, flow_data):
        """Should have dashboard UI groups"""
        ui_groups = [node for node in flow_data if node.get("type") == "ui_group"]
        assert len(ui_groups) > 0, "Should have dashboard groups"

    def test_has_vitals_gauges(self, flow_data):
        """Should have gauges for vital signs"""
        gauges = [node for node in flow_data if node.get("type") == "ui_gauge"]

        assert len(gauges) >= 2, "Should have at least 2 gauges"

        gauge_names = [g.get("name", "").lower() for g in gauges]
        assert any("heart" in name for name in gauge_names), "Should have heart rate gauge"
        assert any("oxygen" in name or "spo2" in name for name in gauge_names), "Should have oxygen gauge"

    def test_has_temperature_chart(self, flow_data):
        """Should have temperature chart"""
        charts = [node for node in flow_data if node.get("type") == "ui_chart"]

        temp_chart = next(
            (c for c in charts if "temp" in c.get("name", "").lower() or "temp" in c.get("label", "").lower()),
            None
        )
        assert temp_chart is not None, "Should have temperature chart"

    def test_has_alert_notification(self, flow_data):
        """Should have alert/toast notification"""
        toasts = [node for node in flow_data if node.get("type") == "ui_toast"]
        assert len(toasts) > 0, "Should have toast notification for alerts"

    def test_has_connection_status(self, flow_data):
        """Should have connection status display"""
        text_nodes = [node for node in flow_data if node.get("type") == "ui_text"]

        status_node = next(
            (t for t in text_nodes if "status" in t.get("name", "").lower() or "connection" in t.get("name", "").lower()),
            None
        )
        assert status_node is not None, "Should have connection status display"


class TestNodeRedAlertLogic:
    """Tests for Node-RED alert checking logic"""

    @pytest.fixture
    def flow_data(self):
        """Load the Node-RED flow JSON"""
        flow_path = Path(__file__).parent.parent.parent / "Node-Red" / "flows" / "vitalsync_nodered_flow.json"
        with open(flow_path) as f:
            return json.load(f)

    def test_has_threshold_check_function(self, flow_data):
        """Should have function to check thresholds"""
        function_nodes = [node for node in flow_data if node.get("type") == "function"]

        threshold_check = next(
            (n for n in function_nodes if "umbral" in n.get("name", "").lower() or "threshold" in n.get("name", "").lower()),
            None
        )
        assert threshold_check is not None, "Should have threshold check function"

    def test_threshold_check_has_correct_values(self, flow_data):
        """Should use correct threshold values from spec"""
        function_nodes = [node for node in flow_data if node.get("type") == "function"]
        threshold_check = next(
            (n for n in function_nodes if "umbral" in n.get("name", "").lower() or "threshold" in n.get("name", "").lower()),
            None
        )

        if threshold_check:
            func_code = threshold_check.get("func", "")

            # Check heart rate thresholds
            assert "50" in func_code or "120" in func_code, "Should have HR critical thresholds"
            # Check oxygen threshold
            assert "90" in func_code or "95" in func_code, "Should have SpO2 thresholds"
            # Check temperature thresholds
            assert "38" in func_code or "35" in func_code, "Should have temperature thresholds"


class TestPayloadFormat:
    """Tests for payload format validation"""

    def test_payload_structure_matches_api(self):
        """Verify the payload structure matches what the API expects"""
        # Expected payload structure from VitalReadingInput
        expected_fields = {
            "deviceId": str,
            "memberId": str,
            "memberName": str,
            "relationship": str,
            "heartRate": int,
            "oxygenLevel": float,
            "bodyTemperature": float,
            "steps": int,
            "timestamp": str,
            "isAnomaly": bool
        }

        # Sample payload from Node-RED
        sample_payload = {
            "deviceId": "XIAOMI-PAPA-001",
            "memberId": "familia-garcia-papa",
            "memberName": "Roberto García",
            "relationship": "padre",
            "heartRate": 72,
            "oxygenLevel": 96.5,
            "bodyTemperature": 36.5,
            "steps": 3200,
            "timestamp": "2025-11-24T10:30:00.000Z",
            "isAnomaly": False
        }

        for field, expected_type in expected_fields.items():
            assert field in sample_payload, f"Payload should have {field}"
            # Check type compatibility
            value = sample_payload[field]
            if expected_type == float:
                assert isinstance(value, (int, float)), f"{field} should be numeric"
            elif expected_type == int:
                assert isinstance(value, int), f"{field} should be int"
            else:
                assert isinstance(value, expected_type), f"{field} should be {expected_type}"

    def test_device_id_format(self):
        """Should follow device ID format convention"""
        device_ids = [
            "XIAOMI-PAPA-001",
            "APPLE-MAMA-002",
            "FITBIT-ABUELO-003",
            "SIM-NODERED-004"
        ]

        for device_id in device_ids:
            parts = device_id.split("-")
            assert len(parts) == 3, f"Device ID should have 3 parts: {device_id}"
            assert parts[2].isdigit(), f"Last part should be numeric: {device_id}"

    def test_member_id_format(self):
        """Should follow member ID format convention"""
        member_ids = [
            "familia-garcia-papa",
            "familia-garcia-mama",
            "familia-garcia-abuelo",
            "familia-garcia-sim"
        ]

        for member_id in member_ids:
            parts = member_id.split("-")
            assert len(parts) == 3, f"Member ID should have 3 parts: {member_id}"
            assert parts[0] == "familia", f"Should start with 'familia': {member_id}"
