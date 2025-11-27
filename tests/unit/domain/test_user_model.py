"""
Unit Tests for UserModel
Tests the domain logic for user management.
"""
import pytest
from datetime import datetime, timedelta

from src.core.domain.UserModel import User, UserRole


class TestUserCreate:
    """Tests for User.create() factory method"""

    def test_create_user_with_defaults(self):
        """Should create a user with default values"""
        user = User.create(
            email="test@example.com",
            password_hash="hashed_password",
            name="Test User"
        )

        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password"
        assert user.name == "Test User"
        assert user.role == UserRole.CAREGIVER  # Default role
        assert user.is_active is True
        assert user.email_verified is False
        assert user.id is not None
        assert user.created_at is not None

    def test_create_user_with_admin_role(self):
        """Should create a user with admin role"""
        user = User.create(
            email="admin@example.com",
            password_hash="hashed_password",
            name="Admin User",
            role=UserRole.ADMIN
        )

        assert user.role == UserRole.ADMIN

    def test_create_user_with_phone(self):
        """Should create a user with phone number"""
        user = User.create(
            email="test@example.com",
            password_hash="hashed_password",
            name="Test User",
            phone="+52 55 1234 5678"
        )

        assert user.phone == "+52 55 1234 5678"


class TestUserRoles:
    """Tests for user role checking"""

    def test_is_admin_returns_true_for_admin(self):
        """Should return True for admin users"""
        user = User.create(
            email="admin@example.com",
            password_hash="hash",
            name="Admin",
            role=UserRole.ADMIN
        )

        assert user.is_admin() is True

    def test_is_admin_returns_false_for_caregiver(self):
        """Should return False for caregiver users"""
        user = User.create(
            email="caregiver@example.com",
            password_hash="hash",
            name="Caregiver",
            role=UserRole.CAREGIVER
        )

        assert user.is_admin() is False

    def test_is_admin_returns_false_for_viewer(self):
        """Should return False for viewer users"""
        user = User.create(
            email="viewer@example.com",
            password_hash="hash",
            name="Viewer",
            role=UserRole.VIEWER
        )

        assert user.is_admin() is False


class TestUserAccess:
    """Tests for user access control"""

    def test_can_access_returns_true_for_active_user(self):
        """Should return True for active users"""
        user = User.create(
            email="test@example.com",
            password_hash="hash",
            name="Test"
        )

        assert user.can_access() is True

    def test_can_access_returns_false_for_inactive_user(self):
        """Should return False for inactive users"""
        user = User.create(
            email="test@example.com",
            password_hash="hash",
            name="Test"
        )
        user.deactivate()

        assert user.can_access() is False


class TestUserActivation:
    """Tests for user activation/deactivation"""

    def test_deactivate_user(self):
        """Should deactivate user"""
        user = User.create(
            email="test@example.com",
            password_hash="hash",
            name="Test"
        )
        original_updated_at = user.updated_at

        user.deactivate()

        assert user.is_active is False
        assert user.updated_at >= original_updated_at

    def test_activate_user(self):
        """Should activate user"""
        user = User.create(
            email="test@example.com",
            password_hash="hash",
            name="Test"
        )
        user.deactivate()

        user.activate()

        assert user.is_active is True


class TestEmailVerification:
    """Tests for email verification"""

    def test_verify_email(self):
        """Should mark email as verified"""
        user = User.create(
            email="test@example.com",
            password_hash="hash",
            name="Test"
        )

        user.verify_email()

        assert user.email_verified is True


class TestRoleUpdate:
    """Tests for role updates"""

    def test_update_role(self):
        """Should update user role"""
        user = User.create(
            email="test@example.com",
            password_hash="hash",
            name="Test",
            role=UserRole.VIEWER
        )

        user.update_role(UserRole.CAREGIVER)

        assert user.role == UserRole.CAREGIVER

    def test_promote_to_admin(self):
        """Should promote user to admin"""
        user = User.create(
            email="test@example.com",
            password_hash="hash",
            name="Test"
        )

        user.update_role(UserRole.ADMIN)

        assert user.is_admin() is True


class TestLoginTracking:
    """Tests for login tracking"""

    def test_register_login(self):
        """Should register login timestamp"""
        user = User.create(
            email="test@example.com",
            password_hash="hash",
            name="Test"
        )
        assert user.last_login_at is None

        user.register_login()

        assert user.last_login_at is not None


class TestPasswordReset:
    """Tests for password reset functionality"""

    def test_set_password_reset_token(self):
        """Should set password reset token and expiry"""
        user = User.create(
            email="test@example.com",
            password_hash="hash",
            name="Test"
        )
        expires_at = datetime.utcnow() + timedelta(hours=1)

        user.set_password_reset_token("reset-token-123", expires_at)

        assert user.password_reset_token == "reset-token-123"
        assert user.password_reset_expires == expires_at

    def test_clear_password_reset_token(self):
        """Should clear password reset token"""
        user = User.create(
            email="test@example.com",
            password_hash="hash",
            name="Test"
        )
        expires_at = datetime.utcnow() + timedelta(hours=1)
        user.set_password_reset_token("reset-token-123", expires_at)

        user.clear_password_reset_token()

        assert user.password_reset_token is None
        assert user.password_reset_expires is None

    def test_update_password(self):
        """Should update password and clear reset token"""
        user = User.create(
            email="test@example.com",
            password_hash="old_hash",
            name="Test"
        )
        expires_at = datetime.utcnow() + timedelta(hours=1)
        user.set_password_reset_token("reset-token-123", expires_at)

        user.update_password("new_hash")

        assert user.password_hash == "new_hash"
        assert user.password_reset_token is None
        assert user.password_reset_expires is None
