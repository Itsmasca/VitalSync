"""
Rutas REST para VitalSync - IoT y Autenticacion.
"""
import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, EmailStr
import bcrypt

from src.adapters.outbound.persistance import (
    AsyncSessionLocal,
    VitalRepositoryImpl,
    FamilyMemberRepositoryImpl,
    AlertRepositoryImpl,
    UserRepositoryImpl
)
from src.core.services import VitalService
from src.core.services.auth_service import auth_service
from src.core.events import broadcaster
from src.core.domain.UserModel import User, UserRole
from src.adapters.inbound.middleware.auth_middleware import (
    require_auth,
    get_current_user_payload
)

router = APIRouter(prefix="/api", tags=["VitalSync API"])


# ============== AUTH SCHEMAS ==============

class RegisterInput(BaseModel):
    """Schema para registro de usuario"""
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=2)
    phone: Optional[str] = None


class LoginInput(BaseModel):
    """Schema para login"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Respuesta con tokens JWT"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 min en segundos


class RefreshInput(BaseModel):
    """Schema para refresh token"""
    refresh_token: str


class PasswordResetInput(BaseModel):
    """Schema para reset de contraseña"""
    email: EmailStr


class UserResponse(BaseModel):
    """Respuesta con datos del usuario"""
    id: str
    email: str
    name: str
    role: str
    phone: Optional[str]
    is_active: bool
    email_verified: bool


# ============== AUTH ENDPOINTS ==============

@router.post("/auth/register", response_model=TokenResponse, status_code=201, tags=["Auth"])
async def register(data: RegisterInput):
    """
    Registra un nuevo usuario en el sistema.
    RF-AUTH-01: Registro de usuarios
    """
    async with AsyncSessionLocal() as session:
        user_repo = UserRepositoryImpl(session)

        # Verificar si el email ya existe
        existing = await user_repo.get_by_email(data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya esta registrado"
            )

        # Hash de la contraseña
        password_hash = bcrypt.hashpw(
            data.password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        # Crear usuario
        user = User.create(
            email=data.email,
            password_hash=password_hash,
            name=data.name,
            role=UserRole.CAREGIVER,
            phone=data.phone
        )

        # Guardar
        user = await user_repo.save(user)

        # Generar tokens
        access_token = auth_service.create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role.value
        )
        refresh_token = auth_service.create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )


@router.post("/auth/login", response_model=TokenResponse, tags=["Auth"])
async def login(data: LoginInput):
    """
    Autentica un usuario y retorna tokens JWT.
    RF-AUTH-02: Login con JWT
    """
    async with AsyncSessionLocal() as session:
        user_repo = UserRepositoryImpl(session)

        # Buscar usuario
        user = await user_repo.get_by_email(data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales invalidas"
            )

        # Verificar contraseña
        if not bcrypt.checkpw(
            data.password.encode('utf-8'),
            user.password_hash.encode('utf-8')
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales invalidas"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario desactivado"
            )

        # Registrar login
        user.register_login()
        await user_repo.update(user)

        # Generar tokens
        access_token = auth_service.create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role.value
        )
        refresh_token = auth_service.create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )


@router.get("/auth/me", response_model=UserResponse, tags=["Auth"])
async def get_current_user(user_id: str = Depends(require_auth)):
    """
    Obtiene la informacion del usuario autenticado.
    RF-AUTH-03: Perfil de usuario
    """
    async with AsyncSessionLocal() as session:
        user_repo = UserRepositoryImpl(session)

        user = await user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role.value,
            phone=user.phone,
            is_active=user.is_active,
            email_verified=user.email_verified
        )


@router.post("/auth/refresh", response_model=TokenResponse, tags=["Auth"])
async def refresh_token(data: RefreshInput):
    """
    Renueva el access token usando un refresh token valido.
    RF-AUTH-04: Refresh de tokens
    """
    # Verificar refresh token
    payload = auth_service.verify_token(data.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido o expirado"
        )

    user_id = payload.get("sub")

    async with AsyncSessionLocal() as session:
        user_repo = UserRepositoryImpl(session)
        user = await user_repo.get_by_id(user_id)

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no valido"
            )

        # Generar nuevos tokens
        access_token = auth_service.create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role.value
        )
        refresh_token = auth_service.create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )


@router.post("/auth/password-reset", status_code=200, tags=["Auth"])
async def reset_password(data: PasswordResetInput):
    """
    Resetea la contraseña de un usuario a un valor por defecto.
    RF-AUTH-05: Reset de contraseña
    """
    async with AsyncSessionLocal() as session:
        user_repo = UserRepositoryImpl(session)

        user = await user_repo.get_by_email(data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        # Obtener contraseña por defecto de variable de entorno
        default_password = os.getenv("DEFAULT_PASSWORD", "VitalSync123!")

        # Hash de la contraseña por defecto
        new_password_hash = bcrypt.hashpw(
            default_password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        user.password_hash = new_password_hash
        await user_repo.update(user)

        return {"message": "Contraseña reseteada exitosamente"}


# ============== IOT VITALS SCHEMAS ==============


class VitalReadingInput(BaseModel):
    """Schema para recibir lecturas de Node-RED"""
    deviceId: str = Field(..., description="ID del dispositivo (ej: XIAOMI-PAPA-001)")
    memberId: Optional[str] = Field(None, description="ID del familiar (ej: familia-garcia-papa)")
    memberName: Optional[str] = Field(None, description="Nombre del familiar")
    relationship: Optional[str] = Field(None, description="Relación familiar")
    heartRate: Optional[int] = Field(None, ge=20, le=250, description="Frecuencia cardíaca (bpm)")
    oxygenLevel: Optional[float] = Field(None, ge=50, le=100, description="Nivel de oxígeno (%)")
    bodyTemperature: Optional[float] = Field(None, ge=30, le=45, description="Temperatura corporal (°C)")
    steps: Optional[int] = Field(None, ge=0, description="Pasos acumulados")
    timestamp: Optional[datetime] = Field(None, description="Timestamp de la lectura")
    isAnomaly: Optional[bool] = Field(False, description="Flag de anomalía desde Node-RED")

    class Config:
        json_schema_extra = {
            "example": {
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
        }


class VitalReadingResponse(BaseModel):
    """Respuesta al guardar una lectura"""
    id: str
    member_id: str
    device_id: str
    heart_rate: Optional[int]
    oxygen_level: Optional[float]
    body_temperature: Optional[float]
    steps: Optional[int]
    overall_status: str
    is_anomaly: bool
    reading_timestamp: datetime
    received_at: datetime
    alerts_generated: int


class HealthResponse(BaseModel):
    """Respuesta del health check"""
    status: str
    timestamp: datetime
    version: str
    readings_last_hour: int
    active_alerts: int


@router.post("/vitals", response_model=VitalReadingResponse, status_code=201)
async def record_vital(
    reading: VitalReadingInput,
    custom_user: str = Depends(require_auth)
    ):
    """
    Recibe una lectura de signos vitales desde un dispositivo IoT (Node-RED).

    Este endpoint es llamado por el simulador Node-RED cada vez que genera
    una nueva lectura de signos vitales.

    RF-VIT-01: Recepción de datos de dispositivos
    US-11: Como sistema, quiero recibir datos de dispositivos IoT
    """
    async with AsyncSessionLocal() as session:
        # Crear repositorios
        vital_repo = VitalRepositoryImpl(session)
        family_member_repo = FamilyMemberRepositoryImpl(session)
        alert_repo = AlertRepositoryImpl(session)

        # Crear servicio
        vital_service = VitalService(vital_repo, family_member_repo, alert_repo)

        try:
            # Contar alertas antes de guardar
            alerts_before = await alert_repo.count_active()

            # Registrar lectura
            vital = await vital_service.record_vital(
                device_id=reading.deviceId,
                heart_rate=reading.heartRate,
                oxygen_level=reading.oxygenLevel,
                body_temperature=reading.bodyTemperature,
                steps=reading.steps,
                reading_timestamp=reading.timestamp
            )

            # Si Node-RED marcó como anomalía, actualizar
            if reading.isAnomaly:
                vital.mark_as_anomaly("node_red_toggle")
                vital = await vital_repo.save(vital)

            # Contar alertas después para saber cuántas se generaron
            alerts_after = await alert_repo.count_active()
            alerts_generated = alerts_after - alerts_before

            # Obtener el member para el device_id
            member = await family_member_repo.get_by_device_id(reading.deviceId)

            # Publicar evento para subscriptions en tiempo real
            await broadcaster.publish_vital(
                vital_data=vital,
                member_id=vital.member_id,
                family_id=member.family_id if member else None
            )

            # Si se generaron alertas, publicarlas también
            if alerts_generated > 0:
                new_alerts = await alert_repo.get_by_member(vital.member_id, limit=alerts_generated)
                for alert in new_alerts:
                    await broadcaster.publish_alert(
                        alert_data=alert,
                        member_id=alert.member_id,
                        family_id=member.family_id if member else None
                    )

            return VitalReadingResponse(
                id=vital.id,
                member_id=vital.member_id,
                device_id=member.device_id if member else reading.deviceId,
                heart_rate=vital.heart_rate,
                oxygen_level=vital.oxygen_level,
                body_temperature=vital.body_temperature,
                steps=vital.steps,
                overall_status=vital.overall_status.value,
                is_anomaly=vital.is_anomaly,
                reading_timestamp=vital.reading_timestamp,
                received_at=vital.received_at,
                alerts_generated=max(0, alerts_generated)
            )

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/vitals/latest/{device_id}", response_model=Optional[VitalReadingResponse])
async def get_latest_vital(
    device_id: str,
    customer_user: str = Depends(require_auth)
):
    """
    Obtiene la última lectura de un dispositivo.

    RF-DASH-01: Dashboard en tiempo real
    """
    if customer_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido",
            headers={"WWW-Authenticate": "Bearer"}
        )
    async with AsyncSessionLocal() as session:
        family_member_repo = FamilyMemberRepositoryImpl(session)
        vital_repo = VitalRepositoryImpl(session)

        # Buscar el member por device_id
        member = await family_member_repo.get_by_device_id(device_id)
        if not member:
            raise HTTPException(status_code=404, detail=f"Device {device_id} no encontrado")

        # Obtener última lectura
        vital = await vital_repo.get_latest_by_member(member.id)
        if not vital:
            return None

        return VitalReadingResponse(
            id=vital.id,
            member_id=vital.member_id,
            device_id=device_id,
            heart_rate=vital.heart_rate,
            oxygen_level=vital.oxygen_level,
            body_temperature=vital.body_temperature,
            steps=vital.steps,
            overall_status=vital.overall_status.value,
            is_anomaly=vital.is_anomaly,
            reading_timestamp=vital.reading_timestamp,
            received_at=vital.received_at,
            alerts_generated=0
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check del sistema.

    RNF-09: Endpoint de health check
    """
    async with AsyncSessionLocal() as session:
        vital_repo = VitalRepositoryImpl(session)
        alert_repo = AlertRepositoryImpl(session)

        readings_last_hour = await vital_repo.count_readings_last_hour()
        active_alerts = await alert_repo.count_active()

        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(timezone.utc),
            version="VitalSync MVP 0.1.0",
            readings_last_hour=readings_last_hour,
            active_alerts=active_alerts
        )
