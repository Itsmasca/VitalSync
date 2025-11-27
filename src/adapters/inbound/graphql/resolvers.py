"""
Resolvers GraphQL para VitalSync.
"""
import strawberry
from typing import List, Optional
from datetime import datetime, date, timezone

from src.adapters.inbound.graphql.types import (
    UserType, FamilyGroupType, FamilyMemberType, VitalType, AlertType,
    GroupCaregiverType, AuthPayload, SystemHealthType, DailyAverageType,
    CreateUserInput, LoginInput, CreateFamilyGroupInput, CreateFamilyMemberInput,
    RecordVitalInput, VitalThresholdsInput, AddCaregiverInput,
    UserRoleGQL, SubscriptionPlanGQL, RelationshipTypeGQL, DeviceTypeGQL,
    VitalStatusGQL, AlertStatusGQL, AlertTypeGQL, VitalThresholdsType
)
from src.core.domain.UserModel import UserRole
from src.core.domain.FamilyGroupModel import SubscriptionPlan
from src.core.domain.FamilyMemberModel import RelationshipType, DeviceType, VitalThresholds
from src.core.domain.VitalModel import VitalStatus
from src.core.domain.AlertModel import AlertStatus, AlertType as AlertTypeEnum


def user_to_gql(user) -> UserType:
    """Convierte User de dominio a UserType GraphQL"""
    return UserType(
        id=user.id,
        email=user.email,
        name=user.name,
        role=UserRoleGQL(user.role.value),
        phone=user.phone,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        email_verified=user.email_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


def family_group_to_gql(group) -> FamilyGroupType:
    """Convierte FamilyGroup de dominio a FamilyGroupType GraphQL"""
    return FamilyGroupType(
        id=group.id,
        name=group.name,
        description=group.description,
        admin_id=group.admin_id,
        plan=SubscriptionPlanGQL(group.plan.value),
        plan_started_at=group.plan_started_at,
        plan_expires_at=group.plan_expires_at,
        timezone_str=group.timezone_str,
        is_active=group.is_active,
        created_at=group.created_at,
        updated_at=group.updated_at,
        max_members=group.get_max_members()
    )


def family_member_to_gql(member) -> FamilyMemberType:
    """Convierte FamilyMember de dominio a FamilyMemberType GraphQL"""
    return FamilyMemberType(
        id=member.id,
        family_id=member.family_id,
        member_id=member.member_id,
        name=member.name,
        relationship=RelationshipTypeGQL(member.relationship.value),
        date_of_birth=member.date_of_birth,
        gender=member.gender.value if member.gender else None,
        device_id=member.device_id,
        device_type=DeviceTypeGQL(member.device_type.value),
        device_name=member.device_name,
        medical_notes=member.medical_notes,
        emergency_contact=member.emergency_contact,
        emergency_phone=member.emergency_phone,
        thresholds=VitalThresholdsType(
            hr_min=member.thresholds.hr_min,
            hr_max=member.thresholds.hr_max,
            spo2_min=member.thresholds.spo2_min,
            temp_min=member.thresholds.temp_min,
            temp_max=member.thresholds.temp_max,
            steps_min=member.thresholds.steps_min
        ),
        is_active=member.is_active,
        alerts_enabled=member.alerts_enabled,
        avatar_url=member.avatar_url,
        age=member.get_age(),
        created_at=member.created_at,
        updated_at=member.updated_at
    )


def vital_to_gql(vital) -> VitalType:
    """Convierte Vital de dominio a VitalType GraphQL"""
    return VitalType(
        id=vital.id,
        member_id=vital.member_id,
        heart_rate=vital.heart_rate,
        oxygen_level=vital.oxygen_level,
        body_temperature=vital.body_temperature,
        steps=vital.steps,
        respiratory_rate=vital.respiratory_rate,
        blood_pressure_systolic=vital.blood_pressure_systolic,
        blood_pressure_diastolic=vital.blood_pressure_diastolic,
        calories_burned=vital.calories_burned,
        distance_meters=vital.distance_meters,
        heart_rate_status=VitalStatusGQL(vital.heart_rate_status.value),
        oxygen_status=VitalStatusGQL(vital.oxygen_status.value),
        temperature_status=VitalStatusGQL(vital.temperature_status.value),
        steps_status=VitalStatusGQL(vital.steps_status.value),
        overall_status=VitalStatusGQL(vital.overall_status.value),
        is_anomaly=vital.is_anomaly,
        anomaly_source=vital.anomaly_source,
        reading_timestamp=vital.reading_timestamp,
        received_at=vital.received_at
    )


def alert_to_gql(alert) -> AlertType:
    """Convierte Alert de dominio a AlertType GraphQL"""
    return AlertType(
        id=alert.id,
        member_id=alert.member_id,
        vital_id=alert.vital_id,
        alert_type=AlertTypeGQL(alert.alert_type.value),
        severity=VitalStatusGQL(alert.severity.value),
        metric_value=alert.metric_value,
        threshold_value=alert.threshold_value,
        threshold_type=alert.threshold_type.value,
        message=alert.message,
        status=AlertStatusGQL(alert.status.value),
        acknowledged_by=alert.acknowledged_by,
        acknowledged_at=alert.acknowledged_at,
        resolved_at=alert.resolved_at,
        resolution_notes=alert.resolution_notes,
        created_at=alert.created_at
    )


def caregiver_to_gql(caregiver) -> GroupCaregiverType:
    """Convierte GroupCaregiver de dominio a GroupCaregiverType GraphQL"""
    return GroupCaregiverType(
        id=caregiver.id,
        group_id=caregiver.group_id,
        user_id=caregiver.user_id,
        can_acknowledge_alerts=caregiver.can_acknowledge_alerts,
        can_view_history=caregiver.can_view_history,
        can_edit_members=caregiver.can_edit_members,
        joined_at=caregiver.joined_at,
        invited_by=caregiver.invited_by
    )


# Context type for dependency injection
@strawberry.type
class Context:
    user_service: any
    family_group_service: any
    family_member_service: any
    vital_service: any
    alert_service: any
    current_user_id: Optional[str] = None


def get_context(info) -> Context:
    return info.context


@strawberry.type
class Query:
    # Users
    @strawberry.field
    async def me(self, info) -> Optional[UserType]:
        """Obtiene el usuario actual autenticado"""
        ctx = get_context(info)
        if not ctx.current_user_id:
            return None
        user = await ctx.user_service.get_user_by_id(ctx.current_user_id)
        return user_to_gql(user) if user else None

    @strawberry.field
    async def user(self, info, id: str) -> Optional[UserType]:
        """Obtiene un usuario por ID"""
        ctx = get_context(info)
        user = await ctx.user_service.get_user_by_id(id)
        return user_to_gql(user) if user else None

    @strawberry.field
    async def users(self, info, limit: int = 100, offset: int = 0) -> List[UserType]:
        """Obtiene todos los usuarios"""
        ctx = get_context(info)
        users = await ctx.user_service.get_all_users(limit, offset)
        return [user_to_gql(u) for u in users]

    # Family Groups
    @strawberry.field
    async def family_group(self, info, id: str) -> Optional[FamilyGroupType]:
        """Obtiene un grupo familiar por ID"""
        ctx = get_context(info)
        group = await ctx.family_group_service.get_group_by_id(id)
        return family_group_to_gql(group) if group else None

    @strawberry.field
    async def my_family_groups(self, info) -> List[FamilyGroupType]:
        """Obtiene grupos donde el usuario es admin o cuidador"""
        ctx = get_context(info)
        if not ctx.current_user_id:
            return []
        admin_groups = await ctx.family_group_service.get_groups_by_admin(ctx.current_user_id)
        caregiver_groups = await ctx.family_group_service.get_groups_by_caregiver(ctx.current_user_id)
        all_groups = {g.id: g for g in admin_groups + caregiver_groups}
        return [family_group_to_gql(g) for g in all_groups.values()]

    @strawberry.field
    async def family_groups(self, info, limit: int = 100, offset: int = 0) -> List[FamilyGroupType]:
        """Obtiene todos los grupos familiares"""
        ctx = get_context(info)
        groups = await ctx.family_group_service.get_all_groups(limit, offset)
        return [family_group_to_gql(g) for g in groups]

    # Family Members
    @strawberry.field
    async def family_member(self, info, id: str) -> Optional[FamilyMemberType]:
        """Obtiene un familiar por ID"""
        ctx = get_context(info)
        member = await ctx.family_member_service.get_member_by_id(id)
        return family_member_to_gql(member) if member else None

    @strawberry.field
    async def family_member_by_device(self, info, device_id: str) -> Optional[FamilyMemberType]:
        """Obtiene un familiar por device_id"""
        ctx = get_context(info)
        member = await ctx.family_member_service.get_member_by_device_id(device_id)
        return family_member_to_gql(member) if member else None

    @strawberry.field
    async def family_members(self, info, family_id: str) -> List[FamilyMemberType]:
        """Obtiene familiares de un grupo"""
        ctx = get_context(info)
        members = await ctx.family_member_service.get_members_by_family(family_id)
        return [family_member_to_gql(m) for m in members]

    # Vitals
    @strawberry.field
    async def latest_vital(self, info, member_id: str) -> Optional[VitalType]:
        """Obtiene la última lectura de un familiar"""
        ctx = get_context(info)
        vital = await ctx.vital_service.get_latest_vital(member_id)
        return vital_to_gql(vital) if vital else None

    @strawberry.field
    async def vitals(
        self, info, member_id: str, limit: int = 100, offset: int = 0
    ) -> List[VitalType]:
        """Obtiene lecturas de un familiar"""
        ctx = get_context(info)
        vitals = await ctx.vital_service.get_vitals_by_member(member_id, limit, offset)
        return [vital_to_gql(v) for v in vitals]

    @strawberry.field
    async def rolling_vitals(self, info, member_id: str, minutes: int = 2) -> List[VitalType]:
        """Obtiene lecturas de los últimos N minutos (para gráfico rolling)"""
        ctx = get_context(info)
        vitals = await ctx.vital_service.get_rolling_vitals(member_id, minutes)
        return [vital_to_gql(v) for v in vitals]

    @strawberry.field
    async def daily_averages(
        self, info, member_id: str, start_date: date, end_date: date
    ) -> List[DailyAverageType]:
        """Obtiene promedios diarios de métricas"""
        ctx = get_context(info)
        averages = await ctx.vital_service.get_daily_averages(member_id, start_date, end_date)
        return [
            DailyAverageType(
                date=a['date'],
                avg_heart_rate=a['avg_heart_rate'],
                avg_oxygen_level=a['avg_oxygen_level'],
                avg_body_temperature=a['avg_body_temperature'],
                max_steps=a['max_steps'],
                reading_count=a['reading_count']
            )
            for a in averages
        ]

    # Alerts
    @strawberry.field
    async def active_alerts(self, info) -> List[AlertType]:
        """Obtiene todas las alertas activas"""
        ctx = get_context(info)
        alerts = await ctx.alert_service.get_active_alerts()
        return [alert_to_gql(a) for a in alerts]

    @strawberry.field
    async def alerts_by_member(
        self, info, member_id: str, limit: int = 100, offset: int = 0
    ) -> List[AlertType]:
        """Obtiene alertas de un familiar"""
        ctx = get_context(info)
        alerts = await ctx.alert_service.get_alerts_by_member(member_id, limit, offset)
        return [alert_to_gql(a) for a in alerts]

    @strawberry.field
    async def recent_alerts(self, info, hours: int = 24) -> List[AlertType]:
        """Obtiene alertas de las últimas N horas"""
        ctx = get_context(info)
        alerts = await ctx.alert_service.get_recent_alerts(hours)
        return [alert_to_gql(a) for a in alerts]

    # Caregivers
    @strawberry.field
    async def caregivers(self, info, group_id: str) -> List[GroupCaregiverType]:
        """Obtiene cuidadores de un grupo"""
        ctx = get_context(info)
        caregivers = await ctx.family_group_service.get_caregivers(group_id)
        return [caregiver_to_gql(c) for c in caregivers]

    # System Health
    @strawberry.field
    async def system_health(self, info) -> SystemHealthType:
        """Health check del sistema"""
        ctx = get_context(info)
        return SystemHealthType(
            status="healthy",
            timestamp=datetime.now(timezone.utc),
            active_users=await ctx.user_service.count_users(),
            active_members=0,  # TODO: implementar
            readings_last_hour=await ctx.vital_service.count_readings_last_hour(),
            active_alerts=await ctx.alert_service.count_active_alerts(),
            version="VitalSync MVP"
        )


@strawberry.type
class Mutation:
    # Auth
    @strawberry.mutation
    async def register(self, info, input: CreateUserInput) -> UserType:
        """Registra un nuevo usuario"""
        ctx = get_context(info)
        user = await ctx.user_service.create_user(
            email=input.email,
            password=input.password,
            name=input.name,
            role=UserRole(input.role.value),
            phone=input.phone
        )
        return user_to_gql(user)

    @strawberry.mutation
    async def login(self, info, input: LoginInput) -> Optional[AuthPayload]:
        """Inicia sesión y retorna token JWT"""
        ctx = get_context(info)
        user = await ctx.user_service.authenticate(input.email, input.password)
        if not user:
            return None
        # TODO: Generar JWT real
        token = f"jwt-token-for-{user.id}"
        return AuthPayload(token=token, user=user_to_gql(user))

    # Family Groups
    @strawberry.mutation
    async def create_family_group(self, info, input: CreateFamilyGroupInput) -> FamilyGroupType:
        """Crea un nuevo grupo familiar"""
        ctx = get_context(info)
        if not ctx.current_user_id:
            raise Exception("No autenticado")
        group = await ctx.family_group_service.create_group(
            name=input.name,
            admin_id=ctx.current_user_id,
            description=input.description,
            plan=SubscriptionPlan(input.plan.value)
        )
        return family_group_to_gql(group)

    @strawberry.mutation
    async def add_caregiver(self, info, input: AddCaregiverInput) -> GroupCaregiverType:
        """Agrega un cuidador a un grupo"""
        ctx = get_context(info)
        if not ctx.current_user_id:
            raise Exception("No autenticado")
        caregiver = await ctx.family_group_service.add_caregiver(
            group_id=input.group_id,
            user_id=input.user_id,
            invited_by=ctx.current_user_id,
            can_acknowledge_alerts=input.can_acknowledge_alerts,
            can_view_history=input.can_view_history,
            can_edit_members=input.can_edit_members
        )
        return caregiver_to_gql(caregiver)

    # Family Members
    @strawberry.mutation
    async def create_family_member(self, info, input: CreateFamilyMemberInput) -> FamilyMemberType:
        """Registra un nuevo familiar monitoreado"""
        ctx = get_context(info)
        member = await ctx.family_member_service.create_member(
            family_id=input.family_id,
            member_id=input.member_id,
            name=input.name,
            relationship=RelationshipType(input.relationship.value),
            device_id=input.device_id,
            device_type=DeviceType(input.device_type.value),
            device_name=input.device_name
        )
        return family_member_to_gql(member)

    @strawberry.mutation
    async def set_member_thresholds(
        self, info, member_id: str, thresholds: VitalThresholdsInput
    ) -> Optional[FamilyMemberType]:
        """Configura umbrales personalizados"""
        ctx = get_context(info)
        domain_thresholds = VitalThresholds(
            hr_min=thresholds.hr_min,
            hr_max=thresholds.hr_max,
            spo2_min=thresholds.spo2_min,
            temp_min=thresholds.temp_min,
            temp_max=thresholds.temp_max,
            steps_min=thresholds.steps_min
        )
        member = await ctx.family_member_service.set_custom_thresholds(member_id, domain_thresholds)
        return family_member_to_gql(member) if member else None

    @strawberry.mutation
    async def toggle_member_alerts(self, info, member_id: str, enabled: bool) -> Optional[FamilyMemberType]:
        """Habilita/deshabilita alertas de un familiar"""
        ctx = get_context(info)
        if enabled:
            member = await ctx.family_member_service.enable_alerts(member_id)
        else:
            member = await ctx.family_member_service.disable_alerts(member_id)
        return family_member_to_gql(member) if member else None

    # Vitals
    @strawberry.mutation
    async def record_vital(self, info, input: RecordVitalInput) -> VitalType:
        """Registra una nueva lectura de signos vitales"""
        ctx = get_context(info)
        vital = await ctx.vital_service.record_vital(
            device_id=input.device_id,
            heart_rate=input.heart_rate,
            oxygen_level=input.oxygen_level,
            body_temperature=input.body_temperature,
            steps=input.steps,
            reading_timestamp=input.reading_timestamp
        )
        return vital_to_gql(vital)

    # Alerts
    @strawberry.mutation
    async def acknowledge_alert(self, info, alert_id: str) -> Optional[AlertType]:
        """Reconoce una alerta"""
        ctx = get_context(info)
        if not ctx.current_user_id:
            raise Exception("No autenticado")
        alert = await ctx.alert_service.acknowledge_alert(alert_id, ctx.current_user_id)
        return alert_to_gql(alert) if alert else None

    @strawberry.mutation
    async def resolve_alert(self, info, alert_id: str, notes: Optional[str] = None) -> Optional[AlertType]:
        """Resuelve una alerta"""
        ctx = get_context(info)
        alert = await ctx.alert_service.resolve_alert(alert_id, notes)
        return alert_to_gql(alert) if alert else None

    @strawberry.mutation
    async def dismiss_alert(self, info, alert_id: str, notes: Optional[str] = None) -> Optional[AlertType]:
        """Descarta una alerta (falso positivo)"""
        ctx = get_context(info)
        alert = await ctx.alert_service.dismiss_alert(alert_id, notes)
        return alert_to_gql(alert) if alert else None


# Schema
schema = strawberry.Schema(query=Query, mutation=Mutation)
