"""
Rutas REST para recibir datos de dispositivos IoT (Node-RED).
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.adapters.outbound.persistance import (
    AsyncSessionLocal,
    VitalRepositoryImpl,
    FamilyMemberRepositoryImpl,
    AlertRepositoryImpl
)
from src.core.services import VitalService
from src.ml.services.prediction_service import HealthRiskPredictionService

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


# ============================================================================
# ML PREDICTION ENDPOINTS
# ============================================================================

class RiskPredictionResponse(BaseModel):
    """Respuesta de predicción de riesgo"""
    id: str
    member_id: str
    risk_level: str
    risk_score: float
    confidence: float
    risks: Dict[str, float]
    risk_factors: List[Dict[str, Any]]
    recommendations: List[str]
    model_version: str
    created_at: datetime


class TrendAnalysisResponse(BaseModel):
    """Respuesta de análisis de tendencia"""
    member_id: str
    trend_direction: str
    average_risk: float
    data_points: int
    predictions_over_time: List[Dict[str, Any]]


@router.get("/ml/predict/{member_id}", response_model=RiskPredictionResponse)
async def predict_health_risk(member_id: str, use_trend: bool = False):
    """
    Predice el riesgo de salud para un miembro familiar.

    Usa el modelo de ML para analizar los signos vitales y predecir
    la probabilidad de eventos adversos en las próximas 24 horas.

    Args:
        member_id: ID del miembro familiar
        use_trend: Si usar análisis de tendencia (últimas 24h) o solo última lectura
    """
    async with AsyncSessionLocal() as session:
        vital_repo = VitalRepositoryImpl(session)
        ml_service = HealthRiskPredictionService(vital_repo)

        try:
            prediction = await ml_service.predict_risk_for_member(
                member_id=member_id,
                use_latest=not use_trend
            )

            if prediction.confidence == 0.0 and not prediction.input_vitals:
                raise HTTPException(
                    status_code=404,
                    detail=f"No hay datos de signos vitales para el miembro {member_id}"
                )

            return RiskPredictionResponse(
                id=prediction.id,
                member_id=prediction.member_id,
                risk_level=prediction.risk_level.value,
                risk_score=prediction.risk_score,
                confidence=prediction.confidence,
                risks={
                    "cardiovascular": prediction.cardiovascular_risk,
                    "respiratory": prediction.respiratory_risk,
                    "metabolic": prediction.metabolic_risk,
                    "activity": prediction.activity_risk
                },
                risk_factors=[
                    {
                        "category": f.category.value,
                        "contribution": f.contribution,
                        "description": f.description,
                        "metric": f.vital_metric,
                        "value": f.current_value,
                        "normal_range": f.normal_range
                    }
                    for f in prediction.risk_factors
                ],
                recommendations=prediction.recommendations,
                model_version=prediction.model_version,
                created_at=prediction.created_at
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error en predicción: {str(e)}")


@router.get("/ml/trend/{member_id}", response_model=TrendAnalysisResponse)
async def analyze_risk_trend(member_id: str, hours: int = 24):
    """
    Analiza la tendencia de riesgo de un miembro en el tiempo.

    Args:
        member_id: ID del miembro familiar
        hours: Horas hacia atrás para el análisis (default: 24)
    """
    async with AsyncSessionLocal() as session:
        vital_repo = VitalRepositoryImpl(session)
        ml_service = HealthRiskPredictionService(vital_repo)

        try:
            trend = await ml_service.analyze_trend(
                member_id=member_id,
                hours=hours
            )

            return TrendAnalysisResponse(
                member_id=member_id,
                trend_direction=trend["trend_direction"],
                average_risk=trend["average_risk"],
                data_points=trend["data_points"],
                predictions_over_time=trend["predictions_over_time"]
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error en análisis: {str(e)}")


@router.post("/ml/predict/batch", response_model=Dict[str, RiskPredictionResponse])
async def predict_batch(member_ids: List[str]):
    """
    Predice riesgo para múltiples miembros.

    Útil para obtener el estado de riesgo de toda una familia.
    """
    async with AsyncSessionLocal() as session:
        vital_repo = VitalRepositoryImpl(session)
        ml_service = HealthRiskPredictionService(vital_repo)

        try:
            predictions = await ml_service.predict_risk_batch(member_ids)

            return {
                member_id: RiskPredictionResponse(
                    id=pred.id,
                    member_id=pred.member_id,
                    risk_level=pred.risk_level.value,
                    risk_score=pred.risk_score,
                    confidence=pred.confidence,
                    risks={
                        "cardiovascular": pred.cardiovascular_risk,
                        "respiratory": pred.respiratory_risk,
                        "metabolic": pred.metabolic_risk,
                        "activity": pred.activity_risk
                    },
                    risk_factors=[
                        {
                            "category": f.category.value,
                            "contribution": f.contribution,
                            "description": f.description,
                            "metric": f.vital_metric,
                            "value": f.current_value,
                            "normal_range": f.normal_range
                        }
                        for f in pred.risk_factors
                    ],
                    recommendations=pred.recommendations,
                    model_version=pred.model_version,
                    created_at=pred.created_at
                )
                for member_id, pred in predictions.items()
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error en predicción batch: {str(e)}")
