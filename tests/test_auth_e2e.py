"""
VitalSync E2E Tests - REST Auth Endpoints
Tests para /api/auth/register, /api/auth/login, /api/auth/me, /api/auth/refresh
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestAuthRegister:
    """Tests para POST /api/auth/register"""

    async def test_register_success(self, async_client: AsyncClient):
        """Test registro exitoso de usuario nuevo"""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "newuser@vitalsync.com",
                "password": "securepass123",
                "name": "New User",
                "phone": "+52 55 1234 5678"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 1800

    async def test_register_invalid_email(self, async_client: AsyncClient):
        """Test registro con email invalido"""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "invalid-email",
                "password": "securepass123",
                "name": "Test User"
            }
        )

        assert response.status_code == 422  # Validation error

    async def test_register_short_password(self, async_client: AsyncClient):
        """Test registro con password muy corto"""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "test@vitalsync.com",
                "password": "123",  # Too short
                "name": "Test User"
            }
        )

        assert response.status_code == 422  # Validation error

    async def test_register_missing_name(self, async_client: AsyncClient):
        """Test registro sin nombre"""
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "test@vitalsync.com",
                "password": "securepass123"
            }
        )

        assert response.status_code == 422  # Validation error


class TestAuthLogin:
    """Tests para POST /api/auth/login"""

    async def test_login_success(self, async_client: AsyncClient):
        """Test login exitoso con credenciales correctas"""
        # Primero registrar usuario
        await async_client.post(
            "/api/auth/register",
            json={
                "email": "logintest@vitalsync.com",
                "password": "testpass123",
                "name": "Login Test User"
            }
        )

        # Luego hacer login
        response = await async_client.post(
            "/api/auth/login",
            json={
                "email": "logintest@vitalsync.com",
                "password": "testpass123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, async_client: AsyncClient):
        """Test login con password incorrecto"""
        # Primero registrar usuario
        await async_client.post(
            "/api/auth/register",
            json={
                "email": "wrongpasstest@vitalsync.com",
                "password": "correctpass123",
                "name": "Wrong Pass Test"
            }
        )

        # Intentar login con password incorrecto
        response = await async_client.post(
            "/api/auth/login",
            json={
                "email": "wrongpasstest@vitalsync.com",
                "password": "wrongpassword"
            }
        )

        assert response.status_code == 401
        assert "Credenciales invalidas" in response.json()["detail"]

    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Test login con usuario que no existe"""
        response = await async_client.post(
            "/api/auth/login",
            json={
                "email": "nonexistent@vitalsync.com",
                "password": "somepassword"
            }
        )

        assert response.status_code == 401
        assert "Credenciales invalidas" in response.json()["detail"]

    async def test_login_invalid_email_format(self, async_client: AsyncClient):
        """Test login con formato de email invalido"""
        response = await async_client.post(
            "/api/auth/login",
            json={
                "email": "not-an-email",
                "password": "somepassword"
            }
        )

        assert response.status_code == 422  # Validation error


class TestAuthMe:
    """Tests para GET /api/auth/me"""

    async def test_me_with_valid_token(self, async_client: AsyncClient):
        """Test obtener usuario actual con token valido"""
        # Registrar y obtener token
        register_response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "metest@vitalsync.com",
                "password": "testpass123",
                "name": "Me Test User"
            }
        )
        token = register_response.json()["access_token"]

        # Obtener info del usuario
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "metest@vitalsync.com"
        assert data["name"] == "Me Test User"
        assert data["role"] == "caregiver"  # Default role
        assert data["is_active"] is True

    async def test_me_without_token(self, async_client: AsyncClient):
        """Test obtener usuario sin token"""
        response = await async_client.get("/api/auth/me")

        assert response.status_code == 401
        assert "Token de autenticacion requerido" in response.json()["detail"]

    async def test_me_with_invalid_token(self, async_client: AsyncClient):
        """Test obtener usuario con token invalido"""
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )

        assert response.status_code == 401
        assert "Token invalido o expirado" in response.json()["detail"]

    async def test_me_with_malformed_header(self, async_client: AsyncClient):
        """Test obtener usuario con header Authorization malformado"""
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": "NotBearer sometoken"}
        )

        assert response.status_code == 401


class TestAuthRefresh:
    """Tests para POST /api/auth/refresh"""

    async def test_refresh_with_valid_token(self, async_client: AsyncClient):
        """Test refresh token valido"""
        # Registrar y obtener tokens
        register_response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "refreshtest@vitalsync.com",
                "password": "testpass123",
                "name": "Refresh Test User"
            }
        )
        refresh_token = register_response.json()["refresh_token"]

        # Hacer refresh
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # Los nuevos tokens deben ser diferentes
        assert data["refresh_token"] != refresh_token

    async def test_refresh_with_access_token(self, async_client: AsyncClient):
        """Test refresh usando access token en vez de refresh token"""
        # Registrar y obtener tokens
        register_response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "wrongrefresh@vitalsync.com",
                "password": "testpass123",
                "name": "Wrong Refresh Test"
            }
        )
        access_token = register_response.json()["access_token"]

        # Intentar refresh con access token
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": access_token}
        )

        assert response.status_code == 401
        assert "Refresh token invalido" in response.json()["detail"]

    async def test_refresh_with_invalid_token(self, async_client: AsyncClient):
        """Test refresh con token invalido"""
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"}
        )

        assert response.status_code == 401


class TestAuthFlow:
    """Tests de flujo completo de autenticacion"""

    async def test_full_auth_flow(self, async_client: AsyncClient):
        """Test flujo completo: register -> login -> me -> refresh"""
        # 1. Register
        register_response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "flowtest@vitalsync.com",
                "password": "testpass123",
                "name": "Flow Test User",
                "phone": "+52 55 9999 8888"
            }
        )
        assert register_response.status_code == 201
        initial_tokens = register_response.json()

        # 2. Login con las mismas credenciales
        login_response = await async_client.post(
            "/api/auth/login",
            json={
                "email": "flowtest@vitalsync.com",
                "password": "testpass123"
            }
        )
        assert login_response.status_code == 200
        login_tokens = login_response.json()

        # 3. Get me con access token
        me_response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {login_tokens['access_token']}"}
        )
        assert me_response.status_code == 200
        user_data = me_response.json()
        assert user_data["email"] == "flowtest@vitalsync.com"
        assert user_data["name"] == "Flow Test User"
        assert user_data["phone"] == "+52 55 9999 8888"

        # 4. Refresh token
        refresh_response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": login_tokens["refresh_token"]}
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()

        # 5. Me con nuevo access token
        new_me_response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"}
        )
        assert new_me_response.status_code == 200
        assert new_me_response.json()["email"] == "flowtest@vitalsync.com"
