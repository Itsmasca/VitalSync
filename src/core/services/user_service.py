from typing import List, Optional
from datetime import datetime, timezone, timedelta
import secrets
import hashlib

from src.core.domain.UserModel import User, UserRole
from src.core.ports.UserRepository import UserRepository


class UserService:
    """
    Servicio de aplicación para gestión de usuarios.
    Contiene los casos de uso relacionados con usuarios.
    RF-AUTH-01, RF-AUTH-02, RF-AUTH-03, RF-AUTH-04
    """

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def create_user(
        self,
        email: str,
        password: str,
        name: str,
        role: UserRole = UserRole.CAREGIVER,
        phone: Optional[str] = None
    ) -> User:
        """
        Crea un nuevo usuario en el sistema.
        RF-AUTH-01: Registro de usuarios
        """
        # Verificar si el email ya existe
        if await self.user_repository.exists_by_email(email):
            raise ValueError(f"El email {email} ya está registrado")

        # Hash de la contraseña (bcrypt en producción)
        password_hash = self._hash_password(password)

        # Crear usuario
        user = User.create(
            email=email,
            password_hash=password_hash,
            name=name,
            role=role,
            phone=phone
        )

        return await self.user_repository.save(user)

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """
        Autentica un usuario por email y contraseña.
        RF-AUTH-02: Login con JWT
        """
        user = await self.user_repository.get_by_email(email)
        if user is None:
            return None

        if not user.can_access():
            return None

        if not self._verify_password(password, user.password_hash):
            return None

        # Registrar login
        user.register_login()
        await self.user_repository.update(user)

        return user

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Obtiene un usuario por su ID"""
        return await self.user_repository.get_by_id(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Obtiene un usuario por su email"""
        return await self.user_repository.get_by_email(email)

    async def get_all_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """Obtiene todos los usuarios con paginación"""
        return await self.user_repository.get_all(limit, offset)

    async def get_users_by_role(self, role: UserRole) -> List[User]:
        """Obtiene usuarios por rol"""
        return await self.user_repository.get_by_role(role)

    async def update_user(self, user: User) -> User:
        """Actualiza un usuario existente"""
        return await self.user_repository.update(user)

    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Cambia la contraseña de un usuario.
        RF-AUTH-03: Cambio de contraseña
        """
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            return False

        if not self._verify_password(current_password, user.password_hash):
            return False

        new_hash = self._hash_password(new_password)
        user.update_password(new_hash)
        await self.user_repository.update(user)
        return True

    async def request_password_reset(self, email: str) -> Optional[str]:
        """
        Genera un token para resetear la contraseña.
        RF-AUTH-04: Recuperación de contraseña
        """
        user = await self.user_repository.get_by_email(email)
        if user is None:
            return None

        # Generar token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        user.set_password_reset_token(token, expires_at)
        await self.user_repository.update(user)

        return token

    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Resetea la contraseña usando un token válido.
        RF-AUTH-04: Recuperación de contraseña
        """
        # Buscar usuario con este token (simplificado, en producción buscar por token)
        users = await self.user_repository.get_all(limit=1000)
        user = None
        for u in users:
            if u.password_reset_token == token:
                user = u
                break

        if user is None:
            return False

        # Verificar expiración
        if user.password_reset_expires is None:
            return False
        if datetime.now(timezone.utc) > user.password_reset_expires:
            return False

        # Actualizar contraseña
        new_hash = self._hash_password(new_password)
        user.update_password(new_hash)
        await self.user_repository.update(user)
        return True

    async def verify_email(self, user_id: str) -> bool:
        """Verifica el email de un usuario"""
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            return False

        user.verify_email()
        await self.user_repository.update(user)
        return True

    async def deactivate_user(self, user_id: str) -> bool:
        """Desactiva un usuario"""
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            return False

        user.deactivate()
        await self.user_repository.update(user)
        return True

    async def activate_user(self, user_id: str) -> bool:
        """Activa un usuario"""
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            return False

        user.activate()
        await self.user_repository.update(user)
        return True

    async def update_role(self, user_id: str, new_role: UserRole) -> bool:
        """Actualiza el rol de un usuario"""
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            return False

        user.update_role(new_role)
        await self.user_repository.update(user)
        return True

    async def count_users(self) -> int:
        """Cuenta el total de usuarios"""
        return await self.user_repository.count()

    def _hash_password(self, password: str) -> str:
        """Hash de contraseña (simplificado, usar bcrypt en producción)"""
        # En producción usar: bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        return hashlib.sha256(password.encode()).hexdigest()

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verifica contraseña (simplificado, usar bcrypt en producción)"""
        # En producción usar: bcrypt.checkpw(password.encode(), password_hash.encode())
        return self._hash_password(password) == password_hash
