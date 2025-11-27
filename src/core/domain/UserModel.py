from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class UserRole(Enum):
    """Roles disponibles para usuarios del sistema VitalSync"""
    ADMIN = "admin"        # Administrador familiar (gestiona grupo y suscripción)
    CAREGIVER = "caregiver"  # Cuidador (monitorea pero no administra)
    VIEWER = "viewer"      # Solo lectura (familiares con acceso limitado)


@dataclass
class User:
    """
    Entidad de dominio que representa un usuario del sistema VitalSync.

    Basado en el DDL de VitalSync - Tabla users.
    RF-AUTH-01, RF-AUTH-02, RF-AUTH-03, RF-AUTH-04
    """
    id: str
    email: str
    password_hash: str
    name: str
    role: UserRole = UserRole.CAREGIVER
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    email_verified: bool = False
    last_login_at: Optional[datetime] = None
    password_reset_token: Optional[str] = None
    password_reset_expires: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @staticmethod
    def create(
        email: str,
        password_hash: str,
        name: str,
        role: UserRole = UserRole.CAREGIVER,
        phone: Optional[str] = None
    ) -> "User":
        """Factory method para crear un nuevo usuario"""
        return User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=password_hash,
            name=name,
            role=role,
            phone=phone,
            is_active=True,
            email_verified=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    def is_admin(self) -> bool:
        """Verifica si el usuario tiene rol de administrador"""
        return self.role == UserRole.ADMIN

    def can_access(self) -> bool:
        """Verifica si el usuario puede acceder al sistema"""
        return self.is_active

    def activate(self) -> None:
        """Activa el usuario"""
        self.is_active = True
        self._update_timestamp()

    def deactivate(self) -> None:
        """Desactiva el usuario"""
        self.is_active = False
        self._update_timestamp()

    def verify_email(self) -> None:
        """Marca el email como verificado"""
        self.email_verified = True
        self._update_timestamp()

    def update_role(self, new_role: UserRole) -> None:
        """Actualiza el rol del usuario"""
        self.role = new_role
        self._update_timestamp()

    def register_login(self) -> None:
        """Registra un nuevo login del usuario"""
        self.last_login_at = datetime.utcnow()
        self._update_timestamp()

    def set_password_reset_token(self, token: str, expires_at: datetime) -> None:
        """Establece el token de reset de contraseña"""
        self.password_reset_token = token
        self.password_reset_expires = expires_at
        self._update_timestamp()

    def clear_password_reset_token(self) -> None:
        """Limpia el token de reset de contraseña"""
        self.password_reset_token = None
        self.password_reset_expires = None
        self._update_timestamp()

    def update_password(self, new_password_hash: str) -> None:
        """Actualiza el hash de la contraseña"""
        self.password_hash = new_password_hash
        self.clear_password_reset_token()

    def _update_timestamp(self) -> None:
        """Actualiza el timestamp de modificación"""
        self.updated_at = datetime.utcnow()
