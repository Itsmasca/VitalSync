"""
Mappers para convertir entre entidades de dominio y entidades ORM.
"""
from datetime import date
from typing import Optional
from decimal import Decimal

from src.core.domain.UserModel import User, UserRole
from src.core.domain.FamilyGroupModel import FamilyGroup, SubscriptionPlan
from src.core.domain.FamilyMemberModel import (
    FamilyMember, RelationshipType, DeviceType, Gender, VitalThresholds
)
from src.core.domain.VitalModel import Vital, VitalStatus
from src.core.domain.AlertModel import Alert, AlertStatus, AlertType, ThresholdType
from src.core.domain.GroupCaregiverModel import GroupCaregiver

from src.adapters.outbound.persistance.entities import (
    UserEntity, FamilyGroupEntity, FamilyMemberEntity,
    VitalEntity, AlertEntity, GroupCaregiverEntity,
    UserRoleEnum, SubscriptionPlanEnum, RelationshipTypeEnum,
    DeviceTypeEnum, GenderEnum, VitalStatusEnum, AlertStatusEnum,
    AlertTypeEnum, ThresholdTypeEnum
)


class UserMapper:
    @staticmethod
    def to_entity(domain: User) -> UserEntity:
        return UserEntity(
            id=domain.id,
            email=domain.email,
            password_hash=domain.password_hash,
            name=domain.name,
            phone=domain.phone,
            avatar_url=domain.avatar_url,
            role=UserRoleEnum(domain.role.value),
            is_active=domain.is_active,
            email_verified=domain.email_verified,
            last_login_at=domain.last_login_at,
            password_reset_token=domain.password_reset_token,
            password_reset_expires=domain.password_reset_expires,
            created_at=domain.created_at,
            updated_at=domain.updated_at
        )

    @staticmethod
    def to_domain(entity: UserEntity) -> User:
        return User(
            id=str(entity.id),
            email=entity.email,
            password_hash=entity.password_hash,
            name=entity.name,
            phone=entity.phone,
            avatar_url=entity.avatar_url,
            role=UserRole(entity.role.value),
            is_active=entity.is_active,
            email_verified=entity.email_verified,
            last_login_at=entity.last_login_at,
            password_reset_token=entity.password_reset_token,
            password_reset_expires=entity.password_reset_expires,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )


class FamilyGroupMapper:
    @staticmethod
    def to_entity(domain: FamilyGroup) -> FamilyGroupEntity:
        return FamilyGroupEntity(
            id=domain.id,
            name=domain.name,
            description=domain.description,
            admin_id=domain.admin_id,
            plan=SubscriptionPlanEnum(domain.plan.value),
            plan_started_at=domain.plan_started_at,
            plan_expires_at=domain.plan_expires_at,
            timezone_str=domain.timezone_str,
            is_active=domain.is_active,
            created_at=domain.created_at,
            updated_at=domain.updated_at
        )

    @staticmethod
    def to_domain(entity: FamilyGroupEntity) -> FamilyGroup:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        return FamilyGroup(
            id=str(entity.id),
            name=entity.name,
            description=entity.description,
            admin_id=str(entity.admin_id),
            plan=SubscriptionPlan(entity.plan.value) if entity.plan else SubscriptionPlan.FREE,
            plan_started_at=entity.plan_started_at,
            plan_expires_at=entity.plan_expires_at,
            timezone_str=entity.timezone_str or "America/Mexico_City",
            is_active=entity.is_active if entity.is_active is not None else True,
            created_at=entity.created_at or now,
            updated_at=entity.updated_at or now
        )


class FamilyMemberMapper:
    @staticmethod
    def to_entity(domain: FamilyMember) -> FamilyMemberEntity:
        return FamilyMemberEntity(
            id=domain.id,
            family_id=domain.family_id,
            member_id=domain.member_id,
            name=domain.name,
            relationship_type=RelationshipTypeEnum(domain.relationship.value),
            date_of_birth=domain.date_of_birth,
            gender=GenderEnum(domain.gender.value) if domain.gender else None,
            device_id=domain.device_id,
            device_type=DeviceTypeEnum(domain.device_type.value),
            device_name=domain.device_name,
            medical_notes=domain.medical_notes,
            emergency_contact=domain.emergency_contact,
            emergency_phone=domain.emergency_phone,
            custom_hr_min=domain.thresholds.hr_min,
            custom_hr_max=domain.thresholds.hr_max,
            custom_spo2_min=Decimal(str(domain.thresholds.spo2_min)) if domain.thresholds.spo2_min else None,
            custom_temp_min=Decimal(str(domain.thresholds.temp_min)) if domain.thresholds.temp_min else None,
            custom_temp_max=Decimal(str(domain.thresholds.temp_max)) if domain.thresholds.temp_max else None,
            custom_steps_min=domain.thresholds.steps_min,
            is_active=domain.is_active,
            alerts_enabled=domain.alerts_enabled,
            avatar_url=domain.avatar_url,
            created_at=domain.created_at,
            updated_at=domain.updated_at
        )

    @staticmethod
    def to_domain(entity: FamilyMemberEntity) -> FamilyMember:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        thresholds = VitalThresholds(
            hr_min=entity.custom_hr_min,
            hr_max=entity.custom_hr_max,
            spo2_min=float(entity.custom_spo2_min) if entity.custom_spo2_min else None,
            temp_min=float(entity.custom_temp_min) if entity.custom_temp_min else None,
            temp_max=float(entity.custom_temp_max) if entity.custom_temp_max else None,
            steps_min=entity.custom_steps_min
        )
        return FamilyMember(
            id=str(entity.id),
            family_id=str(entity.family_id),
            member_id=entity.member_id,
            name=entity.name,
            relationship=RelationshipType(entity.relationship_type.value),
            date_of_birth=entity.date_of_birth,
            gender=Gender(entity.gender.value) if entity.gender else None,
            device_id=entity.device_id,
            device_type=DeviceType(entity.device_type.value) if entity.device_type else DeviceType.SMARTWATCH,
            device_name=entity.device_name,
            medical_notes=entity.medical_notes,
            emergency_contact=entity.emergency_contact,
            emergency_phone=entity.emergency_phone,
            thresholds=thresholds,
            is_active=entity.is_active if entity.is_active is not None else True,
            alerts_enabled=entity.alerts_enabled if entity.alerts_enabled is not None else True,
            avatar_url=entity.avatar_url,
            created_at=entity.created_at or now,
            updated_at=entity.updated_at or now
        )


class VitalMapper:
    @staticmethod
    def to_entity(domain: Vital) -> VitalEntity:
        return VitalEntity(
            id=domain.id,
            member_id=domain.member_id,
            heart_rate=domain.heart_rate,
            oxygen_level=Decimal(str(domain.oxygen_level)) if domain.oxygen_level else None,
            body_temperature=Decimal(str(domain.body_temperature)) if domain.body_temperature else None,
            steps=domain.steps,
            respiratory_rate=domain.respiratory_rate,
            blood_pressure_systolic=domain.blood_pressure_systolic,
            blood_pressure_diastolic=domain.blood_pressure_diastolic,
            calories_burned=domain.calories_burned,
            distance_meters=Decimal(str(domain.distance_meters)) if domain.distance_meters else None,
            heart_rate_status=VitalStatusEnum(domain.heart_rate_status.value),
            oxygen_status=VitalStatusEnum(domain.oxygen_status.value),
            temperature_status=VitalStatusEnum(domain.temperature_status.value),
            steps_status=VitalStatusEnum(domain.steps_status.value),
            overall_status=VitalStatusEnum(domain.overall_status.value),
            is_anomaly=domain.is_anomaly,
            anomaly_source=domain.anomaly_source,
            reading_timestamp=domain.reading_timestamp,
            received_at=domain.received_at,
            reading_date=domain.get_reading_date()
        )

    @staticmethod
    def to_domain(entity: VitalEntity) -> Vital:
        return Vital(
            id=str(entity.id),
            member_id=str(entity.member_id),
            heart_rate=entity.heart_rate,
            oxygen_level=float(entity.oxygen_level) if entity.oxygen_level else None,
            body_temperature=float(entity.body_temperature) if entity.body_temperature else None,
            steps=entity.steps,
            respiratory_rate=entity.respiratory_rate,
            blood_pressure_systolic=entity.blood_pressure_systolic,
            blood_pressure_diastolic=entity.blood_pressure_diastolic,
            calories_burned=entity.calories_burned,
            distance_meters=float(entity.distance_meters) if entity.distance_meters else None,
            heart_rate_status=VitalStatus(entity.heart_rate_status.value),
            oxygen_status=VitalStatus(entity.oxygen_status.value),
            temperature_status=VitalStatus(entity.temperature_status.value),
            steps_status=VitalStatus(entity.steps_status.value),
            overall_status=VitalStatus(entity.overall_status.value),
            is_anomaly=entity.is_anomaly if entity.is_anomaly is not None else False,
            anomaly_source=entity.anomaly_source,
            reading_timestamp=entity.reading_timestamp,
            received_at=entity.received_at
        )


class AlertMapper:
    @staticmethod
    def to_entity(domain: Alert) -> AlertEntity:
        return AlertEntity(
            id=domain.id,
            member_id=domain.member_id,
            vital_id=domain.vital_id,
            alert_type=AlertTypeEnum(domain.alert_type.value),
            severity=VitalStatusEnum(domain.severity.value),
            metric_value=Decimal(str(domain.metric_value)),
            threshold_value=Decimal(str(domain.threshold_value)),
            threshold_type=ThresholdTypeEnum(domain.threshold_type.value),
            message=domain.message,
            status=AlertStatusEnum(domain.status.value),
            acknowledged_by=domain.acknowledged_by,
            acknowledged_at=domain.acknowledged_at,
            resolved_at=domain.resolved_at,
            resolution_notes=domain.resolution_notes,
            created_at=domain.created_at
        )

    @staticmethod
    def to_domain(entity: AlertEntity) -> Alert:
        from datetime import datetime, timezone
        return Alert(
            id=str(entity.id),
            member_id=str(entity.member_id),
            vital_id=str(entity.vital_id) if entity.vital_id else None,
            alert_type=AlertType(entity.alert_type.value),
            severity=VitalStatus(entity.severity.value),
            metric_value=float(entity.metric_value),
            threshold_value=float(entity.threshold_value),
            threshold_type=ThresholdType(entity.threshold_type.value),
            message=entity.message,
            status=AlertStatus(entity.status.value),
            acknowledged_by=str(entity.acknowledged_by) if entity.acknowledged_by else None,
            acknowledged_at=entity.acknowledged_at,
            resolved_at=entity.resolved_at,
            resolution_notes=entity.resolution_notes,
            created_at=entity.created_at or datetime.now(timezone.utc)
        )


class GroupCaregiverMapper:
    @staticmethod
    def to_entity(domain: GroupCaregiver) -> GroupCaregiverEntity:
        return GroupCaregiverEntity(
            id=domain.id,
            group_id=domain.group_id,
            user_id=domain.user_id,
            can_acknowledge_alerts=domain.can_acknowledge_alerts,
            can_view_history=domain.can_view_history,
            can_edit_members=domain.can_edit_members,
            joined_at=domain.joined_at,
            invited_by=domain.invited_by
        )

    @staticmethod
    def to_domain(entity: GroupCaregiverEntity) -> GroupCaregiver:
        from datetime import datetime, timezone
        return GroupCaregiver(
            id=str(entity.id),
            group_id=str(entity.group_id),
            user_id=str(entity.user_id),
            can_acknowledge_alerts=entity.can_acknowledge_alerts if entity.can_acknowledge_alerts is not None else True,
            can_view_history=entity.can_view_history if entity.can_view_history is not None else True,
            can_edit_members=entity.can_edit_members if entity.can_edit_members is not None else False,
            joined_at=entity.joined_at or datetime.now(timezone.utc),
            invited_by=str(entity.invited_by) if entity.invited_by else None
        )
