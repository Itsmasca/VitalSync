"""
Unit Tests for UserService
Tests the business logic for user management and authentication.
"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from src.core.domain.UserModel import User, UserRole
from src.core.services.user_service import UserService


class TestUserRegistration:
    """Tests for UserService.register()"""

    @pytest.fixture
    def user_service(self, mock_user_repository):
        return UserService(user_repository=mock_user_repository)

    @pytest.mark.asyncio
    async def test_register_success(
        self,
        user_service: UserService,
        mock_user_repository: AsyncMock
    ):
        """Should register a new user successfully"""
        mock_user_repository.exists_by_email.return_value = False

        user = await user_service.register(
            email="newuser@example.com",
            password="SecurePassword123!",
            name="New User"
        )

        assert user.email == "newuser@example.com"
        assert user.name == "New User"
        assert user.password_hash != "SecurePassword123!"  # Password should be hashed
        mock_user_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_email_already_exists(
        self,
        user_service: UserService,
        mock_user_repository: AsyncMock
    ):
        """Should raise error when email already exists"""
        mock_user_repository.exists_by_email.return_value = True

        with pytest.raises(ValueError) as exc_info:
            await user_service.register(
                email="existing@example.com",
                password="Password123",
                name="User"
            )

        assert "ya registrado" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_register_with_admin_role(
        self,
        user_service: UserService,
        mock_user_repository: AsyncMock
    ):
        """Should register user with specified role"""
        mock_user_repository.exists_by_email.return_value = False

        user = await user_service.register(
            email="admin@example.com",
            password="Password123",
            name="Admin User",
            role=UserRole.ADMIN
        )

        assert user.role == UserRole.ADMIN


class TestUserAuthentication:
    """Tests for UserService.authenticate()"""

    @pytest.fixture
    def user_service(self, mock_user_repository):
        return UserService(user_repository=mock_user_repository)

    @pytest.mark.asyncio
    async def test_authenticate_success(
        self,
        user_service: UserService,
        mock_user_repository: AsyncMock,
        sample_user: User
    ):
        """Should authenticate user with correct credentials"""
        # Set a known password hash
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        sample_user.password_hash = pwd_context.hash("CorrectPassword")
        mock_user_repository.get_by_email.return_value = sample_user

        result = await user_service.authenticate(
            email="test@vitalsync.com",
            password="CorrectPassword"
        )

        assert result is not None
        assert result.email == sample_user.email
        mock_user_repository.save.assert_called()  # Should update last_login_at

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(
        self,
        user_service: UserService,
        mock_user_repository: AsyncMock,
        sample_user: User
    ):
        """Should return None for wrong password"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        sample_user.password_hash = pwd_context.hash("CorrectPassword")
        mock_user_repository.get_by_email.return_value = sample_user

        result = await user_service.authenticate(
            email="test@vitalsync.com",
            password="WrongPassword"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(
        self,
        user_service: UserService,
        mock_user_repository: AsyncMock
    ):
        """Should return None for unknown email"""
        mock_user_repository.get_by_email.return_value = None

        result = await user_service.authenticate(
            email="unknown@example.com",
            password="Password"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(
        self,
        user_service: UserService,
        mock_user_repository: AsyncMock,
        sample_user: User
    ):
        """Should return None for inactive user"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        sample_user.password_hash = pwd_context.hash("Password")
        sample_user.is_active = False
        mock_user_repository.get_by_email.return_value = sample_user

        result = await user_service.authenticate(
            email="test@vitalsync.com",
            password="Password"
        )

        assert result is None


class TestGetUser:
    """Tests for UserService get methods"""

    @pytest.fixture
    def user_service(self, mock_user_repository):
        return UserService(user_repository=mock_user_repository)

    @pytest.mark.asyncio
    async def test_get_user_by_id(
        self,
        user_service: UserService,
        mock_user_repository: AsyncMock,
        sample_user: User
    ):
        """Should get user by ID"""
        mock_user_repository.get_by_id.return_value = sample_user

        result = await user_service.get_user_by_id("user-123")

        assert result == sample_user
        mock_user_repository.get_by_id.assert_called_with("user-123")

    @pytest.mark.asyncio
    async def test_get_user_by_email(
        self,
        user_service: UserService,
        mock_user_repository: AsyncMock,
        sample_user: User
    ):
        """Should get user by email"""
        mock_user_repository.get_by_email.return_value = sample_user

        result = await user_service.get_user_by_email("test@vitalsync.com")

        assert result == sample_user


class TestPasswordManagement:
    """Tests for password management"""

    @pytest.fixture
    def user_service(self, mock_user_repository):
        return UserService(user_repository=mock_user_repository)

    @pytest.mark.asyncio
    async def test_change_password_success(
        self,
        user_service: UserService,
        mock_user_repository: AsyncMock,
        sample_user: User
    ):
        """Should change password successfully"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        sample_user.password_hash = pwd_context.hash("OldPassword")
        mock_user_repository.get_by_id.return_value = sample_user

        result = await user_service.change_password(
            user_id=sample_user.id,
            old_password="OldPassword",
            new_password="NewPassword123"
        )

        assert result is True
        mock_user_repository.save.assert_called()

    @pytest.mark.asyncio
    async def test_change_password_wrong_old_password(
        self,
        user_service: UserService,
        mock_user_repository: AsyncMock,
        sample_user: User
    ):
        """Should fail with wrong old password"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        sample_user.password_hash = pwd_context.hash("OldPassword")
        mock_user_repository.get_by_id.return_value = sample_user

        result = await user_service.change_password(
            user_id=sample_user.id,
            old_password="WrongOldPassword",
            new_password="NewPassword123"
        )

        assert result is False


class TestUserUpdate:
    """Tests for user updates"""

    @pytest.fixture
    def user_service(self, mock_user_repository):
        return UserService(user_repository=mock_user_repository)

    @pytest.mark.asyncio
    async def test_update_profile(
        self,
        user_service: UserService,
        mock_user_repository: AsyncMock,
        sample_user: User
    ):
        """Should update user profile"""
        mock_user_repository.get_by_id.return_value = sample_user

        result = await user_service.update_profile(
            user_id=sample_user.id,
            name="Updated Name",
            phone="+52 55 1111 2222"
        )

        assert result.name == "Updated Name"
        assert result.phone == "+52 55 1111 2222"

    @pytest.mark.asyncio
    async def test_deactivate_user(
        self,
        user_service: UserService,
        mock_user_repository: AsyncMock,
        sample_user: User
    ):
        """Should deactivate user"""
        mock_user_repository.get_by_id.return_value = sample_user

        result = await user_service.deactivate_user(sample_user.id)

        assert result.is_active is False


class TestRoleManagement:
    """Tests for role management"""

    @pytest.fixture
    def user_service(self, mock_user_repository):
        return UserService(user_repository=mock_user_repository)

    @pytest.mark.asyncio
    async def test_update_user_role(
        self,
        user_service: UserService,
        mock_user_repository: AsyncMock,
        sample_user: User
    ):
        """Should update user role"""
        sample_user.role = UserRole.VIEWER
        mock_user_repository.get_by_id.return_value = sample_user

        result = await user_service.update_role(
            user_id=sample_user.id,
            new_role=UserRole.CAREGIVER
        )

        assert result.role == UserRole.CAREGIVER
