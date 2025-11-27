from typing import List, Optional
from datetime import datetime, date, timezone, timedelta

from src.core.domain.VitalModel import Vital, VitalStatus
from src.core.domain.FamilyMemberModel import FamilyMember
from src.core.domain.AlertModel import Alert
from src.core.ports.VitalRepository import VitalRepository
from src.core.ports.FamilyMemberRepository import FamilyMemberRepository
from src.core.ports.AlertRepository import AlertRepository


class VitalService:
    """
    Servicio de aplicación para gestión de signos vitales.
    Contiene los casos de uso relacionados con lecturas de vitales.
    RF-VIT-01, RF-VIT-02, RF-VIT-03, RF-VIT-04, RF-VIT-05
    US-11, US-12, US-13, US-14, US-23
    """

    def __init__(
        self,
        vital_repository: VitalRepository,
        family_member_repository: FamilyMemberRepository,
        alert_repository: AlertRepository
    ):
        self.vital_repository = vital_repository
        self.family_member_repository = family_member_repository
        self.alert_repository = alert_repository

    async def record_vital(
        self,
        device_id: str,
        heart_rate: Optional[int] = None,
        oxygen_level: Optional[float] = None,
        body_temperature: Optional[float] = None,
        steps: Optional[int] = None,
        reading_timestamp: Optional[datetime] = None
    ) -> Vital:
        """
        Registra una nueva lectura de signos vitales desde un dispositivo.
        RF-VIT-01: Recepción de datos de dispositivos
        US-11: Como sistema, quiero recibir datos de dispositivos IoT
        """
        # Buscar el familiar por device_id
        member = await self.family_member_repository.get_by_device_id(device_id)
        if member is None:
            raise ValueError(f"No se encontró familiar con device_id: {device_id}")

        # Crear la lectura
        vital = Vital.create(
            member_id=member.id,
            heart_rate=heart_rate,
            oxygen_level=oxygen_level,
            body_temperature=body_temperature,
            steps=steps,
            reading_timestamp=reading_timestamp
        )

        # Calcular estados con umbrales personalizados
        vital.calculate_statuses(
            custom_hr_min=member.thresholds.hr_min,
            custom_hr_max=member.thresholds.hr_max,
            custom_spo2_min=member.thresholds.spo2_min,
            custom_temp_min=member.thresholds.temp_min,
            custom_temp_max=member.thresholds.temp_max,
            custom_steps_min=member.thresholds.steps_min
        )

        # Guardar lectura
        saved_vital = await self.vital_repository.save(vital)

        # Generar alertas si es necesario (RF-VIT-05)
        if member.alerts_enabled:
            await self._generate_alerts_if_needed(saved_vital, member)

        return saved_vital

    async def record_vital_by_member_id(
        self,
        member_id: str,
        heart_rate: Optional[int] = None,
        oxygen_level: Optional[float] = None,
        body_temperature: Optional[float] = None,
        steps: Optional[int] = None,
        reading_timestamp: Optional[datetime] = None
    ) -> Vital:
        """
        Registra una lectura usando el member_id (formato: familia-apellido-relacion).
        """
        member = await self.family_member_repository.get_by_member_id(member_id)
        if member is None:
            raise ValueError(f"No se encontró familiar con member_id: {member_id}")

        return await self.record_vital(
            device_id=member.device_id,
            heart_rate=heart_rate,
            oxygen_level=oxygen_level,
            body_temperature=body_temperature,
            steps=steps,
            reading_timestamp=reading_timestamp
        )

    async def get_latest_vital(self, member_id: str) -> Optional[Vital]:
        """
        Obtiene la última lectura de un familiar.
        RF-DASH-01: Dashboard en tiempo real
        US-16: Como cuidador, quiero ver estado actual
        """
        return await self.vital_repository.get_latest_by_member(member_id)

    async def get_vitals_by_member(
        self,
        member_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Vital]:
        """Obtiene lecturas de un familiar con paginación"""
        return await self.vital_repository.get_by_member(member_id, limit, offset)

    async def get_vitals_by_date_range(
        self,
        member_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Vital]:
        """
        Obtiene lecturas en un rango de fechas.
        RF-VIT-03: Historial de signos vitales
        US-13: Como cuidador, quiero ver historial
        """
        return await self.vital_repository.get_by_member_and_date_range(
            member_id, start_date, end_date
        )

    async def get_rolling_vitals(
        self,
        member_id: str,
        minutes: int = 2
    ) -> List[Vital]:
        """
        Obtiene lecturas de los últimos N minutos.
        RF-DASH-02: Gráfico rolling en tiempo real
        """
        return await self.vital_repository.get_by_member_last_minutes(member_id, minutes)

    async def get_critical_readings(
        self,
        member_id: Optional[str] = None,
        hours: int = 24
    ) -> List[Vital]:
        """
        Obtiene lecturas críticas de las últimas N horas.
        RF-VIT-04: Detección de anomalías
        """
        return await self.vital_repository.get_critical_readings(member_id, hours)

    async def get_anomalies(self, member_id: Optional[str] = None) -> List[Vital]:
        """Obtiene lecturas marcadas como anomalías"""
        return await self.vital_repository.get_anomalies(member_id)

    async def mark_as_anomaly(
        self,
        vital_id: str,
        source: str = "manual"
    ) -> Optional[Vital]:
        """
        Marca una lectura como anomalía.
        US-25: Toggle de anomalía desde Node-RED
        """
        vital = await self.vital_repository.get_by_id(vital_id)
        if vital is None:
            return None

        vital.mark_as_anomaly(source)
        return await self.vital_repository.save(vital)

    async def get_daily_averages(
        self,
        member_id: str,
        start_date: date,
        end_date: date
    ) -> List[dict]:
        """
        Obtiene promedios diarios de métricas.
        Útil para reportes y tendencias.
        """
        return await self.vital_repository.get_daily_averages(
            member_id, start_date, end_date
        )

    async def count_readings_by_member(self, member_id: str) -> int:
        """Cuenta lecturas de un familiar"""
        return await self.vital_repository.count_by_member(member_id)

    async def count_readings_last_hour(self) -> int:
        """Cuenta lecturas de la última hora (health check)"""
        return await self.vital_repository.count_readings_last_hour()

    async def cleanup_old_readings(self, days: int) -> int:
        """
        Elimina lecturas antiguas según el plan de suscripción.
        - Free: 1 día
        - Familiar: 30 días
        - Premium: 365 días
        """
        return await self.vital_repository.delete_old_readings(days)

    async def _generate_alerts_if_needed(
        self,
        vital: Vital,
        member: FamilyMember
    ) -> None:
        """
        Genera alertas si los valores están fuera de rango.
        RF-VIT-05: Generación de alertas
        US-23: Como sistema, quiero generar alertas automáticas
        """
        alerts_to_create = []

        # Heart rate alerts
        if vital.heart_rate_status in [VitalStatus.WARNING, VitalStatus.CRITICAL]:
            if vital.heart_rate is not None:
                hr_min = member.thresholds.hr_min or 60
                hr_max = member.thresholds.hr_max or 100
                is_high = vital.heart_rate > hr_max
                threshold = hr_max if is_high else hr_min

                alert = Alert.create_heart_rate_alert(
                    member_id=member.id,
                    member_name=member.name,
                    heart_rate=vital.heart_rate,
                    threshold=threshold,
                    is_high=is_high,
                    vital_id=vital.id
                )
                alerts_to_create.append(alert)

        # Oxygen alerts
        if vital.oxygen_status in [VitalStatus.WARNING, VitalStatus.CRITICAL]:
            if vital.oxygen_level is not None:
                spo2_min = member.thresholds.spo2_min or 95

                alert = Alert.create_oxygen_alert(
                    member_id=member.id,
                    member_name=member.name,
                    oxygen_level=vital.oxygen_level,
                    threshold=spo2_min,
                    vital_id=vital.id
                )
                alerts_to_create.append(alert)

        # Temperature alerts
        if vital.temperature_status in [VitalStatus.WARNING, VitalStatus.CRITICAL]:
            if vital.body_temperature is not None:
                temp_min = member.thresholds.temp_min or 36.1
                temp_max = member.thresholds.temp_max or 37.2
                is_high = vital.body_temperature > temp_max
                threshold = temp_max if is_high else temp_min

                alert = Alert.create_temperature_alert(
                    member_id=member.id,
                    member_name=member.name,
                    temperature=vital.body_temperature,
                    threshold=threshold,
                    is_high=is_high,
                    vital_id=vital.id
                )
                alerts_to_create.append(alert)

        # Steps alerts
        if vital.steps_status in [VitalStatus.WARNING, VitalStatus.CRITICAL]:
            if vital.steps is not None:
                steps_min = member.thresholds.steps_min or 5000

                alert = Alert.create_steps_alert(
                    member_id=member.id,
                    member_name=member.name,
                    steps=vital.steps,
                    threshold=steps_min,
                    vital_id=vital.id
                )
                alerts_to_create.append(alert)

        # Guardar alertas
        for alert in alerts_to_create:
            await self.alert_repository.save(alert)
