"""
VitalSync E2E Tests - GraphQL Endpoints
Tests para queries y mutations GraphQL.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestGraphQLAuth:
    """Tests para autenticacion via GraphQL"""

    async def test_login_mutation_success(self, async_client: AsyncClient):
        """Test login exitoso via GraphQL"""
        # Primero registrar usuario via REST
        await async_client.post(
            "/api/auth/register",
            json={
                "email": "gqluser@vitalsync.com",
                "password": "testpass123",
                "name": "GQL Test User"
            }
        )

        # Login via GraphQL
        query = """
        mutation Login($input: LoginInput!) {
            login(input: $input) {
                accessToken
                refreshToken
                tokenType
                expiresIn
                user {
                    id
                    email
                    name
                    role
                }
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {
                    "input": {
                        "email": "gqluser@vitalsync.com",
                        "password": "testpass123"
                    }
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        login_data = data["data"]["login"]
        assert login_data["accessToken"] is not None
        assert login_data["refreshToken"] is not None
        assert login_data["tokenType"] == "bearer"
        assert login_data["expiresIn"] == 1800
        assert login_data["user"]["email"] == "gqluser@vitalsync.com"

    async def test_login_mutation_wrong_password(self, async_client: AsyncClient):
        """Test login con password incorrecto via GraphQL"""
        # Primero registrar usuario
        await async_client.post(
            "/api/auth/register",
            json={
                "email": "gqlwrong@vitalsync.com",
                "password": "correctpass123",
                "name": "GQL Wrong Pass User"
            }
        )

        query = """
        mutation Login($input: LoginInput!) {
            login(input: $input) {
                accessToken
                user {
                    email
                }
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {
                    "input": {
                        "email": "gqlwrong@vitalsync.com",
                        "password": "wrongpassword"
                    }
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        # Login deberia retornar null para credenciales invalidas
        assert data["data"]["login"] is None

    async def test_me_query_with_token(self, async_client: AsyncClient):
        """Test query me con token valido"""
        # Registrar y obtener token
        register_response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "gqlme@vitalsync.com",
                "password": "testpass123",
                "name": "GQL Me User"
            }
        )
        token = register_response.json()["access_token"]

        query = """
        query Me {
            me {
                id
                email
                name
                role
                isActive
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={"query": query},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        me_data = data["data"]["me"]
        assert me_data["email"] == "gqlme@vitalsync.com"
        assert me_data["name"] == "GQL Me User"
        assert me_data["isActive"] is True

    async def test_me_query_without_token(self, async_client: AsyncClient):
        """Test query me sin token"""
        query = """
        query Me {
            me {
                id
                email
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )

        assert response.status_code == 200
        data = response.json()
        # Sin token, me deberia retornar null
        assert data["data"]["me"] is None


class TestGraphQLUsers:
    """Tests para operaciones de usuarios via GraphQL"""

    async def test_create_user_mutation(self, async_client: AsyncClient):
        """Test crear usuario via GraphQL mutation"""
        query = """
        mutation CreateUser($input: CreateUserInput!) {
            createUser(input: $input) {
                id
                email
                name
                role
                isActive
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {
                    "input": {
                        "email": "newgqluser@vitalsync.com",
                        "password": "securepass123",
                        "name": "New GQL User",
                        "role": "CAREGIVER"
                    }
                }
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        user = data["data"]["createUser"]
        assert user["email"] == "newgqluser@vitalsync.com"
        assert user["name"] == "New GQL User"
        assert user["role"] == "CAREGIVER"
        assert user["isActive"] is True

    async def test_get_user_query(self, async_client: AsyncClient):
        """Test obtener usuario por ID via GraphQL"""
        # Primero crear usuario
        create_query = """
        mutation CreateUser($input: CreateUserInput!) {
            createUser(input: $input) {
                id
                email
            }
        }
        """
        create_response = await async_client.post(
            "/graphql",
            json={
                "query": create_query,
                "variables": {
                    "input": {
                        "email": "getuser@vitalsync.com",
                        "password": "testpass123",
                        "name": "Get User Test"
                    }
                }
            }
        )
        user_id = create_response.json()["data"]["createUser"]["id"]

        # Obtener usuario
        get_query = """
        query GetUser($id: ID!) {
            user(id: $id) {
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
                "query": get_query,
                "variables": {"id": user_id}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert data["data"]["user"]["id"] == user_id
        assert data["data"]["user"]["email"] == "getuser@vitalsync.com"


class TestGraphQLFamilyGroups:
    """Tests para operaciones de grupos familiares via GraphQL"""

    async def test_create_family_group(self, async_client: AsyncClient):
        """Test crear grupo familiar via GraphQL"""
        # Primero crear usuario admin y obtener token
        register_response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "familyadmin@vitalsync.com",
                "password": "testpass123",
                "name": "Family Admin"
            }
        )
        token = register_response.json()["access_token"]

        query = """
        mutation CreateFamilyGroup($input: CreateFamilyGroupInput!) {
            createFamilyGroup(input: $input) {
                id
                name
                description
                plan
                isActive
                maxMembers
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={
                "query": query,
                "variables": {
                    "input": {
                        "name": "Familia Test",
                        "description": "Grupo de prueba",
                        "plan": "FAMILIAR"
                    }
                }
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        group = data["data"]["createFamilyGroup"]
        assert group["name"] == "Familia Test"
        assert group["description"] == "Grupo de prueba"
        assert group["plan"] == "FAMILIAR"
        assert group["isActive"] is True

    async def test_get_family_group(self, async_client: AsyncClient):
        """Test obtener grupo familiar por ID"""
        # Crear usuario y grupo
        register_response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "getgroup@vitalsync.com",
                "password": "testpass123",
                "name": "Get Group Admin"
            }
        )
        token = register_response.json()["access_token"]

        create_query = """
        mutation CreateFamilyGroup($input: CreateFamilyGroupInput!) {
            createFamilyGroup(input: $input) {
                id
                name
            }
        }
        """
        create_response = await async_client.post(
            "/graphql",
            json={
                "query": create_query,
                "variables": {
                    "input": {
                        "name": "Get Group Test"
                    }
                }
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        group_id = create_response.json()["data"]["createFamilyGroup"]["id"]

        # Obtener grupo
        get_query = """
        query GetFamilyGroup($id: ID!) {
            familyGroup(id: $id) {
                id
                name
                plan
                isActive
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={
                "query": get_query,
                "variables": {"id": group_id}
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        assert data["data"]["familyGroup"]["id"] == group_id
        assert data["data"]["familyGroup"]["name"] == "Get Group Test"


class TestGraphQLFamilyMembers:
    """Tests para operaciones de miembros familiares via GraphQL"""

    async def test_create_family_member(self, async_client: AsyncClient):
        """Test crear miembro familiar via GraphQL"""
        # Setup: crear usuario, grupo
        register_response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "memberadmin@vitalsync.com",
                "password": "testpass123",
                "name": "Member Admin"
            }
        )
        token = register_response.json()["access_token"]

        # Crear grupo
        create_group_query = """
        mutation CreateFamilyGroup($input: CreateFamilyGroupInput!) {
            createFamilyGroup(input: $input) {
                id
            }
        }
        """
        group_response = await async_client.post(
            "/graphql",
            json={
                "query": create_group_query,
                "variables": {"input": {"name": "Member Test Family"}}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        family_id = group_response.json()["data"]["createFamilyGroup"]["id"]

        # Crear miembro
        create_member_query = """
        mutation CreateFamilyMember($input: CreateFamilyMemberInput!) {
            createFamilyMember(input: $input) {
                id
                memberId
                name
                relationship
                deviceId
                deviceType
                isActive
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={
                "query": create_member_query,
                "variables": {
                    "input": {
                        "familyId": family_id,
                        "memberId": "papa-garcia",
                        "name": "Roberto Garcia",
                        "relationship": "PADRE",
                        "deviceId": "XIAOMI-001",
                        "deviceType": "XIAOMI_BAND",
                        "deviceName": "Xiaomi Mi Band 8"
                    }
                }
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        member = data["data"]["createFamilyMember"]
        assert member["memberId"] == "papa-garcia"
        assert member["name"] == "Roberto Garcia"
        assert member["relationship"] == "PADRE"
        assert member["deviceId"] == "XIAOMI-001"
        assert member["deviceType"] == "XIAOMI_BAND"
        assert member["isActive"] is True


class TestGraphQLVitals:
    """Tests para operaciones de signos vitales via GraphQL"""

    async def test_record_vital(self, async_client: AsyncClient):
        """Test registrar signos vitales via GraphQL"""
        # Setup completo: usuario, grupo, miembro
        register_response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "vitaladmin@vitalsync.com",
                "password": "testpass123",
                "name": "Vital Admin"
            }
        )
        token = register_response.json()["access_token"]

        # Crear grupo
        create_group_query = """
        mutation CreateFamilyGroup($input: CreateFamilyGroupInput!) {
            createFamilyGroup(input: $input) {
                id
            }
        }
        """
        group_response = await async_client.post(
            "/graphql",
            json={
                "query": create_group_query,
                "variables": {"input": {"name": "Vital Test Family"}}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        family_id = group_response.json()["data"]["createFamilyGroup"]["id"]

        # Crear miembro
        create_member_query = """
        mutation CreateFamilyMember($input: CreateFamilyMemberInput!) {
            createFamilyMember(input: $input) {
                id
                deviceId
            }
        }
        """
        member_response = await async_client.post(
            "/graphql",
            json={
                "query": create_member_query,
                "variables": {
                    "input": {
                        "familyId": family_id,
                        "memberId": "vital-test-member",
                        "name": "Vital Test Member",
                        "relationship": "SELF",
                        "deviceId": "VITAL-DEVICE-001",
                        "deviceType": "NODE_RED_SIM"
                    }
                }
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        device_id = member_response.json()["data"]["createFamilyMember"]["deviceId"]

        # Registrar vital
        record_vital_query = """
        mutation RecordVital($input: RecordVitalInput!) {
            recordVital(input: $input) {
                id
                memberId
                heartRate
                oxygenLevel
                bodyTemperature
                steps
                heartRateStatus
                overallStatus
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={
                "query": record_vital_query,
                "variables": {
                    "input": {
                        "deviceId": device_id,
                        "heartRate": 72,
                        "oxygenLevel": 98.5,
                        "bodyTemperature": 36.5,
                        "steps": 5000
                    }
                }
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        vital = data["data"]["recordVital"]
        assert vital["heartRate"] == 72
        assert vital["oxygenLevel"] == 98.5
        assert vital["bodyTemperature"] == 36.5
        assert vital["steps"] == 5000

    async def test_get_member_vitals(self, async_client: AsyncClient):
        """Test obtener historial de vitales de un miembro"""
        # Setup: crear todo y registrar algunos vitales
        register_response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "historytest@vitalsync.com",
                "password": "testpass123",
                "name": "History Test"
            }
        )
        token = register_response.json()["access_token"]

        # Crear grupo y miembro
        create_group_query = """
        mutation CreateFamilyGroup($input: CreateFamilyGroupInput!) {
            createFamilyGroup(input: $input) {
                id
            }
        }
        """
        group_response = await async_client.post(
            "/graphql",
            json={
                "query": create_group_query,
                "variables": {"input": {"name": "History Test Family"}}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        family_id = group_response.json()["data"]["createFamilyGroup"]["id"]

        create_member_query = """
        mutation CreateFamilyMember($input: CreateFamilyMemberInput!) {
            createFamilyMember(input: $input) {
                id
                deviceId
            }
        }
        """
        member_response = await async_client.post(
            "/graphql",
            json={
                "query": create_member_query,
                "variables": {
                    "input": {
                        "familyId": family_id,
                        "memberId": "history-member",
                        "name": "History Member",
                        "relationship": "SELF",
                        "deviceId": "HISTORY-DEVICE-001",
                        "deviceType": "NODE_RED_SIM"
                    }
                }
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        member_id = member_response.json()["data"]["createFamilyMember"]["id"]
        device_id = member_response.json()["data"]["createFamilyMember"]["deviceId"]

        # Registrar varios vitales
        record_vital_query = """
        mutation RecordVital($input: RecordVitalInput!) {
            recordVital(input: $input) {
                id
            }
        }
        """
        for hr in [70, 75, 80]:
            await async_client.post(
                "/graphql",
                json={
                    "query": record_vital_query,
                    "variables": {
                        "input": {
                            "deviceId": device_id,
                            "heartRate": hr,
                            "oxygenLevel": 98.0
                        }
                    }
                },
                headers={"Authorization": f"Bearer {token}"}
            )

        # Obtener vitales del miembro
        get_vitals_query = """
        query GetMemberVitals($memberId: ID!, $limit: Int) {
            memberVitals(memberId: $memberId, limit: $limit) {
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
                "query": get_vitals_query,
                "variables": {
                    "memberId": member_id,
                    "limit": 10
                }
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        vitals = data["data"]["memberVitals"]
        assert len(vitals) >= 3


class TestGraphQLAlerts:
    """Tests para operaciones de alertas via GraphQL"""

    async def test_get_active_alerts(self, async_client: AsyncClient):
        """Test obtener alertas activas"""
        # Setup usuario
        register_response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "alertstest@vitalsync.com",
                "password": "testpass123",
                "name": "Alerts Test"
            }
        )
        token = register_response.json()["access_token"]

        query = """
        query GetActiveAlerts($limit: Int) {
            activeAlerts(limit: $limit) {
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
                "variables": {"limit": 10}
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        # Deberia retornar lista (vacia o con alertas)
        assert isinstance(data["data"]["activeAlerts"], list)


class TestGraphQLSystemHealth:
    """Tests para verificar salud del sistema via GraphQL"""

    async def test_system_health_query(self, async_client: AsyncClient):
        """Test obtener estado de salud del sistema"""
        query = """
        query SystemHealth {
            systemHealth {
                status
                timestamp
                activeUsers
                activeMembers
                readingsLastHour
                activeAlerts
                version
            }
        }
        """
        response = await async_client.post(
            "/graphql",
            json={"query": query}
        )

        assert response.status_code == 200
        data = response.json()
        assert "errors" not in data
        health = data["data"]["systemHealth"]
        assert health["status"] == "healthy"
        assert health["version"] is not None


class TestGraphQLIntrospection:
    """Tests para verificar el schema GraphQL"""

    async def test_introspection_query(self, async_client: AsyncClient):
        """Test query de introspeccion del schema"""
        query = """
        query IntrospectionQuery {
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
        assert "errors" not in data
        types = data["data"]["__schema"]["types"]
        type_names = [t["name"] for t in types]

        # Verificar tipos principales existen
        assert "UserType" in type_names
        assert "VitalType" in type_names
        assert "AlertType" in type_names
        assert "AuthPayload" in type_names
