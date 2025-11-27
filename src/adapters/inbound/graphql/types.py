"""
Tipos GraphQL para VitalSync usando Strawberry.
"""
import strawberry
from datetime import datetime, date
from typing import Optional, List
from enum import Enum


# Enums
@strawberry.enum
class UserRoleGQL(Enum):
    ADMIN = "admin"
    CAREGIVER = "caregiver"
    VIEWER = "viewer"


@strawberry.enum
class SubscriptionPlanGQL(Enum):
    FREE = "free"
    FAMILIAR = "familiar"
    PREMIUM = "premium"


@strawberry.enum
class RelationshipTypeGQL(Enum):
    SELF = "self"
    PADRE = "padre"
    MADRE = "madre"
    HIJO = "hijo"
    ABUELO = "abuelo"
    ESPOSO = "esposo"
    HERMANO = "hermano"
    OTRO = "otro"


@strawberry.enum
class DeviceTypeGQL(Enum):
    APPLE_WATCH = "apple_watch"
    XIAOMI_BAND = "xiaomi_band"
    FITBIT = "fitbit"
    GARMIN = "garmin"
    SAMSUNG_WATCH = "samsung_watch"
    HUAWEI_BAND = "huawei_band"
    NODE_RED_SIM = "node_red_sim"
    OTHER = "other"


@strawberry.enum
class VitalStatusGQL(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@strawberry.enum
class AlertStatusGQL(Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


@strawberry.enum
class AlertTypeGQL(Enum):
    HEART_RATE = "heart_rate"
    OXYGEN_LEVEL = "oxygen_level"
    TEMPERATURE = "temperature"
    STEPS = "steps"


# Types
@strawberry.type
class UserType:
    id: str
    email: str
    name: str
    role: UserRoleGQL
    phone: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    email_verified: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class FamilyGroupType:
    id: str
    name: str
    description: Optional[str]
    admin_id: str
    plan: SubscriptionPlanGQL
    plan_started_at: datetime
    plan_expires_at: Optional[datetime]
    timezone_str: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    max_members: int


@strawberry.type
class VitalThresholdsType:
    hr_min: Optional[int]
    hr_max: Optional[int]
    spo2_min: Optional[float]
    temp_min: Optional[float]
    temp_max: Optional[float]
    steps_min: Optional[int]


@strawberry.type
class FamilyMemberType:
    id: str
    family_id: str
    member_id: str
    name: str
    relationship: RelationshipTypeGQL
    date_of_birth: Optional[date]
    gender: Optional[str]
    device_id: str
    device_type: DeviceTypeGQL
    device_name: Optional[str]
    medical_notes: Optional[str]
    emergency_contact: Optional[str]
    emergency_phone: Optional[str]
    thresholds: VitalThresholdsType
    is_active: bool
    alerts_enabled: bool
    avatar_url: Optional[str]
    age: Optional[int]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class VitalType:
    id: str
    member_id: str
    heart_rate: Optional[int]
    oxygen_level: Optional[float]
    body_temperature: Optional[float]
    steps: Optional[int]
    respiratory_rate: Optional[int]
    blood_pressure_systolic: Optional[int]
    blood_pressure_diastolic: Optional[int]
    calories_burned: Optional[int]
    distance_meters: Optional[float]
    heart_rate_status: VitalStatusGQL
    oxygen_status: VitalStatusGQL
    temperature_status: VitalStatusGQL
    steps_status: VitalStatusGQL
    overall_status: VitalStatusGQL
    is_anomaly: bool
    anomaly_source: Optional[str]
    reading_timestamp: datetime
    received_at: datetime


@strawberry.type
class AlertType:
    id: str
    member_id: str
    vital_id: Optional[str]
    alert_type: AlertTypeGQL
    severity: VitalStatusGQL
    metric_value: float
    threshold_value: float
    threshold_type: str
    message: str
    status: AlertStatusGQL
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    created_at: datetime


@strawberry.type
class GroupCaregiverType:
    id: str
    group_id: str
    user_id: str
    can_acknowledge_alerts: bool
    can_view_history: bool
    can_edit_members: bool
    joined_at: datetime
    invited_by: Optional[str]


@strawberry.type
class AuthPayload:
    token: str
    user: UserType


@strawberry.type
class SystemHealthType:
    status: str
    timestamp: datetime
    active_users: int
    active_members: int
    readings_last_hour: int
    active_alerts: int
    version: str


@strawberry.type
class DailyAverageType:
    date: date
    avg_heart_rate: Optional[float]
    avg_oxygen_level: Optional[float]
    avg_body_temperature: Optional[float]
    max_steps: Optional[int]
    reading_count: int


# Input Types
@strawberry.input
class CreateUserInput:
    email: str
    password: str
    name: str
    role: UserRoleGQL = UserRoleGQL.CAREGIVER
    phone: Optional[str] = None


@strawberry.input
class LoginInput:
    email: str
    password: str


@strawberry.input
class CreateFamilyGroupInput:
    name: str
    description: Optional[str] = None
    plan: SubscriptionPlanGQL = SubscriptionPlanGQL.FREE


@strawberry.input
class CreateFamilyMemberInput:
    family_id: str
    member_id: str
    name: str
    relationship: RelationshipTypeGQL
    device_id: str
    device_type: DeviceTypeGQL
    device_name: Optional[str] = None


@strawberry.input
class RecordVitalInput:
    device_id: str
    heart_rate: Optional[int] = None
    oxygen_level: Optional[float] = None
    body_temperature: Optional[float] = None
    steps: Optional[int] = None
    reading_timestamp: Optional[datetime] = None


@strawberry.input
class VitalThresholdsInput:
    hr_min: Optional[int] = None
    hr_max: Optional[int] = None
    spo2_min: Optional[float] = None
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    steps_min: Optional[int] = None


@strawberry.input
class AddCaregiverInput:
    group_id: str
    user_id: str
    can_acknowledge_alerts: bool = True
    can_view_history: bool = True
    can_edit_members: bool = False


# ML Types
@strawberry.enum
class RiskLevelGQL(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@strawberry.type
class RiskFactorType:
    category: str
    contribution: float
    description: str
    metric: str
    value: float
    normal_range: str


@strawberry.type
class HealthRiskPredictionType:
    id: str
    member_id: str
    risk_level: RiskLevelGQL
    risk_score: float
    confidence: float
    cardiovascular_risk: float
    respiratory_risk: float
    metabolic_risk: float
    activity_risk: float
    risk_factors: List[RiskFactorType]
    recommendations: List[str]
    model_version: str
    created_at: datetime


@strawberry.type
class TrendPointType:
    timestamp: str
    risk_score: float


@strawberry.type
class RiskTrendType:
    member_id: str
    trend_direction: str
    average_risk: float
    data_points: int
    predictions_over_time: List[TrendPointType]
