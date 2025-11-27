"""
Health Risk Prediction Service

Servicio de aplicación que orquesta la predicción de riesgos de salud
usando el modelo de ML y los datos de signos vitales.
"""
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta

from src.core.domain.VitalModel import Vital
from src.core.ports.VitalRepository import VitalRepository
from src.ml.domain.health_risk import HealthRiskPrediction, RiskLevel
from src.ml.models.vital_risk_network import VitalRiskPredictor, VitalInput


class HealthRiskPredictionService:
    """
    Servicio para predicción de riesgos de salud.

    Integra el modelo de ML con el dominio de VitalSync para:
    - Predecir riesgo basado en última lectura de vitales
    - Predecir riesgo basado en tendencias (múltiples lecturas)
    - Generar alertas predictivas
    """

    def __init__(
        self,
        vital_repository: VitalRepository,
        model_path: Optional[str] = None
    ):
        self.vital_repository = vital_repository
        self.predictor = VitalRiskPredictor(model_path=model_path)

    async def predict_risk_for_member(
        self,
        member_id: str,
        use_latest: bool = True,
        hours_lookback: int = 24
    ) -> HealthRiskPrediction:
        """
        Predice el riesgo de salud para un miembro.

        Args:
            member_id: ID del miembro familiar
            use_latest: Si usar solo la última lectura o promediar
            hours_lookback: Horas hacia atrás para análisis de tendencia

        Returns:
            HealthRiskPrediction con el resultado
        """
        if use_latest:
            # Obtener última lectura
            vitals = await self.vital_repository.get_latest_by_member(member_id)
            if not vitals:
                return self._create_no_data_prediction(member_id)

            vital_input = self._vital_to_input(vitals)
        else:
            # Obtener lecturas del período y promediar
            since = datetime.now(timezone.utc) - timedelta(hours=hours_lookback)
            vitals_list = await self.vital_repository.get_by_member_since(
                member_id, since
            )

            if not vitals_list:
                return self._create_no_data_prediction(member_id)

            vital_input = self._aggregate_vitals(vitals_list)

        # Realizar predicción
        predictions = self.predictor.predict(vital_input)

        # Crear objeto de dominio
        return HealthRiskPrediction.create(
            member_id=member_id,
            risk_score=predictions["risk_score"],
            confidence=predictions["confidence"],
            cardiovascular_risk=predictions["cardiovascular"],
            respiratory_risk=predictions["respiratory"],
            metabolic_risk=predictions["metabolic"],
            activity_risk=predictions["activity"],
            input_vitals=self._input_to_dict(vital_input),
            model_version=self.predictor.MODEL_VERSION
        )

    async def predict_risk_from_vitals(
        self,
        vitals: Vital
    ) -> HealthRiskPrediction:
        """
        Predice riesgo directamente desde un objeto Vital.

        Útil para predicción en tiempo real cuando llega una nueva lectura.
        """
        vital_input = self._vital_to_input(vitals)
        predictions = self.predictor.predict(vital_input)

        return HealthRiskPrediction.create(
            member_id=vitals.member_id,
            risk_score=predictions["risk_score"],
            confidence=predictions["confidence"],
            cardiovascular_risk=predictions["cardiovascular"],
            respiratory_risk=predictions["respiratory"],
            metabolic_risk=predictions["metabolic"],
            activity_risk=predictions["activity"],
            input_vitals=self._input_to_dict(vital_input),
            model_version=self.predictor.MODEL_VERSION
        )

    async def predict_risk_batch(
        self,
        member_ids: List[str]
    ) -> Dict[str, HealthRiskPrediction]:
        """
        Predice riesgo para múltiples miembros.

        Returns:
            Dict mapping member_id -> HealthRiskPrediction
        """
        results = {}

        for member_id in member_ids:
            try:
                prediction = await self.predict_risk_for_member(member_id)
                results[member_id] = prediction
            except Exception:
                results[member_id] = self._create_error_prediction(member_id)

        return results

    async def get_high_risk_members(
        self,
        member_ids: List[str],
        threshold: float = 0.6
    ) -> List[HealthRiskPrediction]:
        """
        Identifica miembros con alto riesgo.

        Returns:
            Lista de predicciones donde risk_score >= threshold
        """
        predictions = await self.predict_risk_batch(member_ids)

        high_risk = [
            pred for pred in predictions.values()
            if pred.risk_score >= threshold
        ]

        # Ordenar por riesgo descendente
        return sorted(high_risk, key=lambda p: p.risk_score, reverse=True)

    async def analyze_trend(
        self,
        member_id: str,
        hours: int = 24,
        interval_hours: int = 4
    ) -> Dict:
        """
        Analiza tendencia de riesgo en el tiempo.

        Returns:
            Dict con trend_direction, predictions_over_time, average_risk
        """
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        vitals_list = await self.vital_repository.get_by_member_since(
            member_id, since
        )

        if len(vitals_list) < 2:
            return {
                "trend_direction": "stable",
                "predictions_over_time": [],
                "average_risk": 0.0,
                "data_points": len(vitals_list)
            }

        # Agrupar por intervalos y predecir
        predictions_over_time = []
        current_time = since

        while current_time < datetime.now(timezone.utc):
            interval_end = current_time + timedelta(hours=interval_hours)

            interval_vitals = [
                v for v in vitals_list
                if current_time <= v.reading_timestamp < interval_end
            ]

            if interval_vitals:
                # Usar el más reciente del intervalo
                latest = max(interval_vitals, key=lambda v: v.reading_timestamp)
                vital_input = self._vital_to_input(latest)
                pred = self.predictor.predict(vital_input)

                predictions_over_time.append({
                    "timestamp": interval_end.isoformat(),
                    "risk_score": pred["risk_score"]
                })

            current_time = interval_end

        if len(predictions_over_time) < 2:
            return {
                "trend_direction": "stable",
                "predictions_over_time": predictions_over_time,
                "average_risk": predictions_over_time[0]["risk_score"] if predictions_over_time else 0.0,
                "data_points": len(vitals_list)
            }

        # Calcular tendencia
        scores = [p["risk_score"] for p in predictions_over_time]
        first_half_avg = sum(scores[:len(scores)//2]) / (len(scores)//2)
        second_half_avg = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)

        if second_half_avg > first_half_avg + 0.1:
            trend = "increasing"
        elif second_half_avg < first_half_avg - 0.1:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "trend_direction": trend,
            "predictions_over_time": predictions_over_time,
            "average_risk": sum(scores) / len(scores),
            "data_points": len(vitals_list)
        }

    def _vital_to_input(self, vital: Vital) -> VitalInput:
        """Convierte Vital domain object a VitalInput para el modelo"""
        return VitalInput(
            heart_rate=vital.heart_rate,
            oxygen_level=vital.oxygen_level,
            body_temperature=vital.body_temperature,
            steps=vital.steps,
            blood_pressure_systolic=vital.blood_pressure_systolic,
            blood_pressure_diastolic=vital.blood_pressure_diastolic,
            respiratory_rate=vital.respiratory_rate
        )

    def _aggregate_vitals(self, vitals_list: List[Vital]) -> VitalInput:
        """Agrega múltiples lecturas (promedio)"""
        def avg(values):
            valid = [v for v in values if v is not None]
            return sum(valid) / len(valid) if valid else None

        return VitalInput(
            heart_rate=avg([v.heart_rate for v in vitals_list]),
            oxygen_level=avg([v.oxygen_level for v in vitals_list]),
            body_temperature=avg([v.body_temperature for v in vitals_list]),
            steps=avg([v.steps for v in vitals_list]),
            blood_pressure_systolic=avg([v.blood_pressure_systolic for v in vitals_list]),
            blood_pressure_diastolic=avg([v.blood_pressure_diastolic for v in vitals_list]),
            respiratory_rate=avg([v.respiratory_rate for v in vitals_list])
        )

    def _input_to_dict(self, vital_input: VitalInput) -> Dict:
        """Convierte VitalInput a dict para almacenar"""
        return {
            "heart_rate": vital_input.heart_rate,
            "oxygen_level": vital_input.oxygen_level,
            "body_temperature": vital_input.body_temperature,
            "steps": vital_input.steps,
            "blood_pressure_systolic": vital_input.blood_pressure_systolic,
            "blood_pressure_diastolic": vital_input.blood_pressure_diastolic,
            "respiratory_rate": vital_input.respiratory_rate
        }

    def _create_no_data_prediction(self, member_id: str) -> HealthRiskPrediction:
        """Crea predicción cuando no hay datos"""
        return HealthRiskPrediction.create(
            member_id=member_id,
            risk_score=0.0,
            confidence=0.0,
            input_vitals={},
            model_version=self.predictor.MODEL_VERSION
        )

    def _create_error_prediction(self, member_id: str) -> HealthRiskPrediction:
        """Crea predicción cuando hay error"""
        return HealthRiskPrediction.create(
            member_id=member_id,
            risk_score=0.5,  # Valor neutro
            confidence=0.0,
            input_vitals={},
            model_version=self.predictor.MODEL_VERSION
        )
