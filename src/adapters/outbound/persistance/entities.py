from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer,
    ForeignKey, Numeric, Date, Enum as SQLEnum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from src.adapters.outbound.persistance.database import Base

# Enums como tipos de PostgreSQL
import enum


class UserRoleEnum(str, enum.Enum):
    ADMIN = "admin"
    CAREGIVER = "caregiver"
    VIEWER = "viewer"


class SubscriptionPlanEnum(str, enum.Enum):
    FREE = "free"
    FAMILIAR = "familiar"
    PREMIUM = "premium"


class RelationshipTypeEnum(str, enum.Enum):
    SELF = "self"
    PADRE = "padre"
    MADRE = "madre"
    HIJO = "hijo"
    ABUELO = "abuelo"
    ESPOSO = "esposo"
    HERMANO = "hermano"
    OTRO = "otro"


class DeviceTypeEnum(str, enum.Enum):
    APPLE_WATCH = "apple_watch"
    XIAOMI_BAND = "xiaomi_band"
    FITBIT = "fitbit"
    GARMIN = "garmin"
    SAMSUNG_WATCH = "samsung_watch"
    HUAWEI_BAND = "huawei_band"
    NODE_RED_SIM = "node_red_sim"
    OTHER = "other"


class GenderEnum(str, enum.Enum):
    M = "M"
    F = "F"
    O = "O"


class VitalStatusEnum(str, enum.Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatusEnum(str, enum.Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AlertTypeEnum(str, enum.Enum):
    HEART_RATE = "heart_rate"
    OXYGEN_LEVEL = "oxygen_level"
    TEMPERATURE = "temperature"
    STEPS = "steps"


class ThresholdTypeEnum(str, enum.Enum):
    MIN = "min"
    MAX = "max"


class UserEntity(Base):
    """Entidad ORM para usuarios del sistema"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    role = Column(SQLEnum(UserRoleEnum), nullable=False, default=UserRoleEnum.CAREGIVER)
    is_active = Column(Boolean, default=True, index=True)
    email_verified = Column(Boolean, default=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    administered_groups = relationship("FamilyGroupEntity", back_populates="admin")
    caregiver_memberships = relationship("GroupCaregiverEntity", back_populates="user", foreign_keys="GroupCaregiverEntity.user_id")
    acknowledged_alerts = relationship("AlertEntity", back_populates="acknowledged_by_user", foreign_keys="AlertEntity.acknowledged_by")


class FamilyGroupEntity(Base):
    """Entidad ORM para grupos familiares"""
    __tablename__ = "family_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    plan = Column(SQLEnum(SubscriptionPlanEnum), nullable=False, default=SubscriptionPlanEnum.FREE, index=True)
    plan_started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    plan_expires_at = Column(DateTime(timezone=True), nullable=True)
    timezone_str = Column(String(50), default="America/Mexico_City")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    admin = relationship("UserEntity", back_populates="administered_groups")
    members = relationship("FamilyMemberEntity", back_populates="family_group", cascade="all, delete-orphan")
    caregivers = relationship("GroupCaregiverEntity", back_populates="group", cascade="all, delete-orphan")


class FamilyMemberEntity(Base):
    """Entidad ORM para familiares monitoreados"""
    __tablename__ = "family_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id = Column(UUID(as_uuid=True), ForeignKey("family_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(150), nullable=False)
    relationship = Column(SQLEnum(RelationshipTypeEnum), nullable=False, index=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(SQLEnum(GenderEnum), nullable=True)
    device_id = Column(String(50), nullable=False, unique=True, index=True)
    device_type = Column(SQLEnum(DeviceTypeEnum), nullable=False)
    device_name = Column(String(100), nullable=True)
    medical_notes = Column(Text, nullable=True)
    emergency_contact = Column(String(150), nullable=True)
    emergency_phone = Column(String(20), nullable=True)
    # Custom thresholds
    custom_hr_min = Column(Integer, nullable=True)
    custom_hr_max = Column(Integer, nullable=True)
    custom_spo2_min = Column(Numeric(4, 1), nullable=True)
    custom_temp_min = Column(Numeric(4, 2), nullable=True)
    custom_temp_max = Column(Numeric(4, 2), nullable=True)
    custom_steps_min = Column(Integer, nullable=True)
    # Status
    is_active = Column(Boolean, default=True, index=True)
    alerts_enabled = Column(Boolean, default=True)
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    family_group = relationship("FamilyGroupEntity", back_populates="members")
    vitals = relationship("VitalEntity", back_populates="member", cascade="all, delete-orphan")
    alerts = relationship("AlertEntity", back_populates="member", cascade="all, delete-orphan")


class VitalEntity(Base):
    """Entidad ORM para lecturas de signos vitales"""
    __tablename__ = "vitals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id = Column(UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False, index=True)

    # Main metrics
    heart_rate = Column(Integer, nullable=True)
    oxygen_level = Column(Numeric(4, 1), nullable=True)
    body_temperature = Column(Numeric(4, 2), nullable=True)
    steps = Column(Integer, nullable=True)

    # Additional metrics
    respiratory_rate = Column(Integer, nullable=True)
    blood_pressure_systolic = Column(Integer, nullable=True)
    blood_pressure_diastolic = Column(Integer, nullable=True)
    calories_burned = Column(Integer, nullable=True)
    distance_meters = Column(Numeric(10, 2), nullable=True)

    # Status fields
    heart_rate_status = Column(SQLEnum(VitalStatusEnum), default=VitalStatusEnum.NORMAL)
    oxygen_status = Column(SQLEnum(VitalStatusEnum), default=VitalStatusEnum.NORMAL)
    temperature_status = Column(SQLEnum(VitalStatusEnum), default=VitalStatusEnum.NORMAL)
    steps_status = Column(SQLEnum(VitalStatusEnum), default=VitalStatusEnum.NORMAL)
    overall_status = Column(SQLEnum(VitalStatusEnum), default=VitalStatusEnum.NORMAL, index=True)

    # Anomaly flags
    is_anomaly = Column(Boolean, default=False, index=True)
    anomaly_source = Column(String(50), nullable=True)

    # Timestamps
    reading_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    reading_date = Column(Date, nullable=True, index=True)

    # Relationships
    member = relationship("FamilyMemberEntity", back_populates="vitals")
    alerts = relationship("AlertEntity", back_populates="vital")


class AlertEntity(Base):
    """Entidad ORM para alertas del sistema"""
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id = Column(UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False, index=True)
    vital_id = Column(UUID(as_uuid=True), ForeignKey("vitals.id", ondelete="SET NULL"), nullable=True)
    alert_type = Column(SQLEnum(AlertTypeEnum), nullable=False)
    severity = Column(SQLEnum(VitalStatusEnum), nullable=False, index=True)
    metric_value = Column(Numeric(10, 2), nullable=False)
    threshold_value = Column(Numeric(10, 2), nullable=False)
    threshold_type = Column(SQLEnum(ThresholdTypeEnum), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(SQLEnum(AlertStatusEnum), default=AlertStatusEnum.ACTIVE, index=True)
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    member = relationship("FamilyMemberEntity", back_populates="alerts")
    vital = relationship("VitalEntity", back_populates="alerts")
    acknowledged_by_user = relationship("UserEntity", back_populates="acknowledged_alerts", foreign_keys=[acknowledged_by])


class GroupCaregiverEntity(Base):
    """Entidad ORM para relación cuidador-grupo"""
    __tablename__ = "group_caregivers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("family_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    can_acknowledge_alerts = Column(Boolean, default=True)
    can_view_history = Column(Boolean, default=True)
    can_edit_members = Column(Boolean, default=False)
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Unique constraint
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_user"),
    )

    # Relationships
    group = relationship("FamilyGroupEntity", back_populates="caregivers")
    user = relationship("UserEntity", back_populates="caregiver_memberships", foreign_keys=[user_id])
    inviter = relationship("UserEntity", foreign_keys=[invited_by])
