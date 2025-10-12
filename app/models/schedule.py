"""
Schedule models - SQLAlchemy and Pydantic schemas for SMS scheduling.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, validator
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text

from app.core.database import Base


class ScheduleType(str, Enum):
    """Types of scheduling."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CRON = "cron"


class ScheduleStatus(str, Enum):
    """Schedule status."""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


# SQLAlchemy Model
class ScheduleDB(Base):
    """SQLAlchemy model for scheduled messages."""

    __tablename__ = "scheduled_messages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    message_template = Column(Text, nullable=False)

    # Scheduling configuration
    schedule_type = Column(String(20), nullable=False)
    schedule_value = Column(
        String(255), nullable=False
    )  # e.g., "09:00", "monday 10:00", "5 14:00"
    cron_expression = Column(String(100), nullable=True)  # For complex cron schedules

    # Conditional logic
    conditions = Column(JSON, nullable=True)  # JSON object with conditions
    target_tenant_types = Column(JSON, nullable=True)  # List of tenant types to target

    # Status and metadata
    status = Column(String(20), default=ScheduleStatus.ACTIVE.value)
    active = Column(Boolean, default=True)

    # Execution tracking
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    run_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)

    # APScheduler job ID for tracking
    job_id = Column(String(255), nullable=True, unique=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<Schedule(name='{self.name}', type='{self.schedule_type}')>"


# Pydantic Schemas
class ScheduleBase(BaseModel):
    """Base schedule schema."""

    name: str
    message_template: str
    schedule_type: ScheduleType
    schedule_value: str
    conditions: Optional[dict[str, Any]] = None
    target_tenant_types: Optional[list[str]] = None
    status: ScheduleStatus = ScheduleStatus.ACTIVE

    @validator("name")
    def validate_name(cls, v):
        """Validate schedule name."""
        if not v or len(v.strip()) < 3:
            raise ValueError("Schedule name must be at least 3 characters long")
        return v.strip()

    @validator("message_template")
    def validate_message_template(cls, v):
        """Validate message template."""
        if not v or len(v.strip()) < 10:
            raise ValueError("Message template must be at least 10 characters long")
        return v.strip()

    @validator("schedule_value")
    def validate_schedule_value(cls, v, values):
        """Validate schedule value based on schedule type."""
        schedule_type = values.get("schedule_type")

        if schedule_type == ScheduleType.DAILY:
            # Should be in format "HH:MM"
            try:
                time_parts = v.split(":")
                if len(time_parts) != 2:
                    raise ValueError
                hour, minute = int(time_parts[0]), int(time_parts[1])
                if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                    raise ValueError
            except (ValueError, AttributeError):
                raise ValueError(
                    'Daily schedule must be in format "HH:MM" (e.g., "09:30")'
                )

        elif schedule_type == ScheduleType.WEEKLY:
            # Should be in format "DAYNAME HH:MM"
            try:
                parts = v.split()
                if len(parts) != 2:
                    raise ValueError
                day, time = parts[0].lower(), parts[1]

                valid_days = [
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                ]
                if day not in valid_days:
                    raise ValueError

                time_parts = time.split(":")
                if len(time_parts) != 2:
                    raise ValueError
                hour, minute = int(time_parts[0]), int(time_parts[1])
                if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                    raise ValueError
            except (ValueError, AttributeError):
                raise ValueError(
                    'Weekly schedule must be in format "DAYNAME HH:MM" (e.g., "monday 09:30")'
                )

        elif schedule_type == ScheduleType.MONTHLY:
            # Should be in format "DD HH:MM"
            try:
                parts = v.split()
                if len(parts) != 2:
                    raise ValueError
                day, time = int(parts[0]), parts[1]

                if not (1 <= day <= 31):
                    raise ValueError

                time_parts = time.split(":")
                if len(time_parts) != 2:
                    raise ValueError
                hour, minute = int(time_parts[0]), int(time_parts[1])
                if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                    raise ValueError
            except (ValueError, AttributeError):
                raise ValueError(
                    'Monthly schedule must be in format "DD HH:MM" (e.g., "5 14:30")'
                )

        return v

    @validator("conditions")
    def validate_conditions(cls, v):
        """Validate conditions JSON."""
        if v is not None:
            # Ensure it's a valid dictionary
            if not isinstance(v, dict):
                raise ValueError("Conditions must be a valid dictionary")

            # Validate known condition types
            valid_conditions = [
                "isCurrentMonthRentPaid",
                "daysSinceLastPayment",
                "tenantType",
                "isLateFeeApplicable",
                "building",
                "rentAmount",
            ]

            for key in v.keys():
                if key not in valid_conditions:
                    raise ValueError(
                        f"Unknown condition: {key}. Valid conditions are: {valid_conditions}"
                    )

        return v


class ScheduleCreate(ScheduleBase):
    """Schema for creating a new schedule."""


class ScheduleUpdate(BaseModel):
    """Schema for updating a schedule."""

    name: Optional[str] = None
    message_template: Optional[str] = None
    schedule_type: Optional[ScheduleType] = None
    schedule_value: Optional[str] = None
    conditions: Optional[dict[str, Any]] = None
    target_tenant_types: Optional[list[str]] = None
    status: Optional[ScheduleStatus] = None


class ScheduleInDB(ScheduleBase):
    """Schema for schedule as stored in database."""

    id: int
    cron_expression: Optional[str] = None
    active: bool
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int
    success_count: int
    failure_count: int
    job_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None

    class Config:
        from_attributes = True


class ScheduleResponse(ScheduleInDB):
    """Schema for schedule API responses."""

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.run_count == 0:
            return 0.0
        return round((self.success_count / self.run_count) * 100, 2)

    @property
    def status_display(self) -> str:
        """Get user-friendly status display."""
        status_map = {
            ScheduleStatus.ACTIVE: "✅ Active",
            ScheduleStatus.PAUSED: "⏸️ Paused",
            ScheduleStatus.DISABLED: "❌ Disabled",
        }
        return status_map.get(self.status, self.status)

    @property
    def schedule_display(self) -> str:
        """Get user-friendly schedule description."""
        if self.schedule_type == ScheduleType.DAILY:
            return f"Daily at {self.schedule_value}"
        elif self.schedule_type == ScheduleType.WEEKLY:
            day, time = self.schedule_value.split()
            return f"Every {day.capitalize()} at {time}"
        elif self.schedule_type == ScheduleType.MONTHLY:
            day, time = self.schedule_value.split()
            suffix = (
                "th"
                if 11 <= int(day) <= 13
                else {1: "st", 2: "nd", 3: "rd"}.get(int(day) % 10, "th")
            )
            return f"Monthly on the {day}{suffix} at {time}"
        else:
            return f"{self.schedule_type.capitalize()}: {self.schedule_value}"


# Bulk operations
class ScheduleBulkAction(BaseModel):
    """Schema for bulk schedule actions."""

    schedule_ids: list[int]
    action: str  # 'activate', 'pause', 'disable', 'delete'

    @validator("action")
    def validate_action(cls, v):
        """Validate bulk action type."""
        valid_actions = ["activate", "pause", "disable", "delete"]
        if v not in valid_actions:
            raise ValueError(f"Action must be one of: {valid_actions}")
        return v


# Schedule execution results
class ScheduleExecution(BaseModel):
    """Schema for schedule execution tracking."""

    schedule_id: int
    execution_time: datetime
    tenant_count: int
    success_count: int
    failure_count: int
    messages_sent: list[str]  # List of tenant names who received messages
    errors: list[str]  # List of error messages
    conditions_checked: Optional[dict[str, Any]] = None


class ScheduleStats(BaseModel):
    """Schema for schedule statistics."""

    active_schedules: int
    paused_schedules: int
    total_schedules: int
    total_executions: int


# Schema alias for API compatibility
Schedule = ScheduleDB
