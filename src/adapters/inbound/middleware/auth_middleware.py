"""
Middleware y dependencias de autenticación JWT para FastAPI.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.core.services.auth_service import auth_service


# Esquema de seguridad Bearer
security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    Dependencia que extrae el user_id del token JWT.
    Retorna None si no hay token (para rutas opcionales).
    """
    if credentials is None:
        return None

    token = credentials.credentials
    user_id = auth_service.get_user_id_from_token(token)
    return user_id


async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    Dependencia que requiere autenticación.
    Lanza HTTPException 401 si no hay token válido.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    payload = auth_service.verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return payload["sub"]  # user_id


async def get_current_user_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Dependencia que retorna el payload completo del token.
    Útil cuando necesitas email, role, etc.
    """
    if credentials is None:
        return None

    token = credentials.credentials
    return auth_service.verify_token(token)


def require_role(allowed_roles: list[str]):
    """
    Factory de dependencia que verifica roles específicos.
    Uso: Depends(require_role(["admin", "caregiver"]))
    """
    async def role_checker(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> str:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de autenticación requerido",
                headers={"WWW-Authenticate": "Bearer"}
            )

        token = credentials.credentials
        payload = auth_service.verify_token(token)

        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"}
            )

        user_role = payload.get("role")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol: {', '.join(allowed_roles)}"
            )

        return payload["sub"]

    return role_checker
