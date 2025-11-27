"""
Servicio de autenticación JWT para VitalSync.
Usa python-jose para manejo de tokens JWT.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from jose import jwt, JWTError, ExpiredSignatureError

from src.config.Settings import settings


class AuthService:
    """
    Servicio para generar y validar tokens JWT.
    RF-AUTH-02: Login con JWT
    """

    def __init__(self):
        self.secret = settings.JWT_SECRET
        self.algorithm = settings.JWT_ALGORITHM
        self.expiration_hours = settings.JWT_EXPIRATION_HOURS

    def create_access_token(self, user_id: str, email: str, role: str) -> str:
        """
        Genera un token JWT para un usuario autenticado.
        """
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=self.expiration_hours)

        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "iat": now,
            "exp": expires,
            "type": "access"
        }

        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """
        Genera un refresh token con mayor duración.
        """
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=7)  # 7 días para refresh

        payload = {
            "sub": user_id,
            "iat": now,
            "exp": expires,
            "type": "refresh"
        }

        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[dict]:
        """
        Verifica y decodifica un token JWT.
        Retorna el payload si es válido, None si no.
        """
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm]
            )
            return payload
        except ExpiredSignatureError:
            return None
        except JWTError:
            return None

    def get_user_id_from_token(self, token: str) -> Optional[str]:
        """
        Extrae el user_id de un token válido.
        """
        payload = self.verify_token(token)
        if payload:
            return payload.get("sub")
        return None

    def is_token_expired(self, token: str) -> bool:
        """
        Verifica si un token ha expirado.
        """
        try:
            jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm]
            )
            return False
        except ExpiredSignatureError:
            return True
        except JWTError:
            return True


# Singleton
auth_service = AuthService()
