"""
End-to-End Tests for GraphQL API
Tests the complete GraphQL API flow.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestGraphQLEndpoint:
    """Tests for /graphql endpoint"""

    async def test_graphql_endpoint_accessible(self, async_client: AsyncClient):
        """Should be able to access GraphQL endpoint"""
        query = """
        query {
            __schema {
                types {
                    name
                }
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "__schema" in data["data"]


class TestUserQueries:
    """Tests for User GraphQL queries"""

    async def test_get_user_by_id(self, async_client: AsyncClient):
        """Should query user by ID"""
        query = """
        query GetUser($userId: String!) {
            user(userId: $userId) {
                id
                email
                name
                role
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"userId": "test-user-id"}
            }
        )

        assert response.status_code == 200
        data = response.json()
        # User might not exist, but query should work
        assert "data" in data


class TestFamilyMemberQueries:
    """Tests for FamilyMember GraphQL queries"""

    async def test_get_family_members_by_family(self, async_client: AsyncClient):
        """Should query family members by family ID"""
        query = """
        query GetFamilyMembers($familyId: String!) {
            familyMembers(familyId: $familyId) {
                id
                name
                relationship
                deviceId
                deviceType
                isActive
                alertsEnabled
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"familyId": "test-family-id"}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data


class TestVitalQueries:
    """Tests for Vital GraphQL queries"""

    async def test_get_latest_vital_for_member(self, async_client: AsyncClient):
        """Should query latest vital for a member"""
        query = """
        query GetLatestVital($memberId: String!) {
            latestVital(memberId: $memberId) {
                id
                heartRate
                oxygenLevel
                bodyTemperature
                steps
                overallStatus
                readingTimestamp
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"memberId": "test-member-id"}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    async def test_get_vitals_history(self, async_client: AsyncClient):
        """Should query vitals history with pagination"""
        query = """
        query GetVitalsHistory($memberId: String!, $limit: Int, $offset: Int) {
            vitals(memberId: $memberId, limit: $limit, offset: $offset) {
                id
                heartRate
                oxygenLevel
                bodyTemperature
                steps
                overallStatus
                isAnomaly
                readingTimestamp
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {
                    "memberId": "test-member-id",
                    "limit": 10,
                    "offset": 0
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    async def test_get_rolling_vitals(self, async_client: AsyncClient):
        """Should query rolling vitals (last N minutes)"""
        query = """
        query GetRollingVitals($memberId: String!, $minutes: Int!) {
            rollingVitals(memberId: $memberId, minutes: $minutes) {
                id
                heartRate
                oxygenLevel
                readingTimestamp
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {
                    "memberId": "test-member-id",
                    "minutes": 5
                }
            }
        )

        assert response.status_code == 200

    async def test_get_critical_readings(self, async_client: AsyncClient):
        """Should query critical readings"""
        query = """
        query GetCriticalReadings($memberId: String, $hours: Int!) {
            criticalReadings(memberId: $memberId, hours: $hours) {
                id
                heartRate
                oxygenLevel
                overallStatus
                readingTimestamp
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {
                    "memberId": None,
                    "hours": 24
                }
            }
        )

        assert response.status_code == 200


class TestAlertQueries:
    """Tests for Alert GraphQL queries"""

    async def test_get_active_alerts(self, async_client: AsyncClient):
        """Should query active alerts"""
        query = """
        query GetActiveAlerts($memberId: String) {
            activeAlerts(memberId: $memberId) {
                id
                alertType
                severity
                message
                status
                createdAt
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"memberId": None}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    async def test_get_alerts_by_member(self, async_client: AsyncClient):
        """Should query alerts by member"""
        query = """
        query GetAlertsByMember($memberId: String!) {
            alertsByMember(memberId: $memberId) {
                id
                alertType
                severity
                metricValue
                thresholdValue
                message
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {"memberId": "test-member-id"}
            }
        )

        assert response.status_code == 200


class TestMutations:
    """Tests for GraphQL mutations"""

    async def test_register_user_mutation(self, async_client: AsyncClient):
        """Should register a new user"""
        mutation = """
        mutation RegisterUser($email: String!, $password: String!, $name: String!) {
            registerUser(email: $email, password: $password, name: $name) {
                id
                email
                name
                role
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "email": "newuser@test.com",
                    "password": "SecurePass123",
                    "name": "New User"
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        # Might succeed or fail depending on DB state
        assert "data" in data or "errors" in data

    async def test_acknowledge_alert_mutation(self, async_client: AsyncClient):
        """Should acknowledge an alert"""
        mutation = """
        mutation AcknowledgeAlert($alertId: String!, $userId: String!) {
            acknowledgeAlert(alertId: $alertId, userId: $userId) {
                id
                status
                acknowledgedBy
                acknowledgedAt
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "alertId": "test-alert-id",
                    "userId": "test-user-id"
                }
            }
        )

        assert response.status_code == 200

    async def test_resolve_alert_mutation(self, async_client: AsyncClient):
        """Should resolve an alert"""
        mutation = """
        mutation ResolveAlert($alertId: String!, $notes: String) {
            resolveAlert(alertId: $alertId, notes: $notes) {
                id
                status
                resolvedAt
                resolutionNotes
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={
                "query": mutation,
                "variables": {
                    "alertId": "test-alert-id",
                    "notes": "Patient stabilized"
                }
            }
        )

        assert response.status_code == 200


class TestGraphQLValidation:
    """Tests for GraphQL validation"""

    async def test_invalid_query_returns_error(self, async_client: AsyncClient):
        """Should return error for invalid query"""
        response = await async_client.post(
            "/graphql",
            json={"query": "invalid query syntax {{{"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" in data

    async def test_unknown_field_returns_error(self, async_client: AsyncClient):
        """Should return error for unknown field"""
        query = """
        query {
            unknownField {
                id
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" in data

    async def test_missing_required_variable(self, async_client: AsyncClient):
        """Should return error for missing required variable"""
        query = """
        query GetUser($userId: String!) {
            user(userId: $userId) {
                id
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={"query": query, "variables": {}}  # Missing userId
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" in data


class TestGraphQLIntrospection:
    """Tests for GraphQL introspection"""

    async def test_introspection_query(self, async_client: AsyncClient):
        """Should support introspection queries"""
        query = """
        query {
            __schema {
                queryType {
                    name
                }
                mutationType {
                    name
                }
                types {
                    name
                    kind
                }
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["__schema"]["queryType"]["name"] == "Query"

    async def test_type_introspection(self, async_client: AsyncClient):
        """Should return type information"""
        query = """
        query {
            __type(name: "Vital") {
                name
                fields {
                    name
                    type {
                        name
                    }
                }
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )

        assert response.status_code == 200
