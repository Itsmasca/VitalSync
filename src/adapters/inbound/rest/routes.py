"""
Rutas REST para recibir datos de dispositivos IoT (Node-RED).
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.adapters.outbound.persistance import (
    AsyncSessionLocal,
    VitalRepositoryImpl,
    FamilyMemberRepositoryImpl,
    AlertRepositoryImpl
)
from src.core.services import VitalService
from src.adapters.inbound.graphql.broadcaster import broadcaster

router = APIRouter(prefix="/api", tags=["IoT Vitals"])


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
async def record_vital(reading: VitalReadingInput):
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
async def get_latest_vital(device_id: str):
    """
    Obtiene la última lectura de un dispositivo.

    RF-DASH-01: Dashboard en tiempo real
    """
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
