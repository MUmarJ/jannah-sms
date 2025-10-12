"""
Tenant models - SQLAlchemy and Pydantic schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, validator
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.core.database import Base
from app.utils import format_phone, normalize_phone


# SQLAlchemy Model
class TenantDB(Base):
    """SQLAlchemy model for tenants."""

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    contact = Column(String(20), nullable=False)
    rent = Column(Integer, nullable=True)
    due_date = Column(String(50), nullable=True)
    building = Column(String(255), nullable=True)
    tenant_type = Column(String(50), default="residential")
    active = Column(Boolean, default=True)

    # Payment tracking fields
    is_current_month_rent_paid = Column(Boolean, default=False)
    last_payment_date = Column(DateTime, nullable=True)
    late_fee_applicable = Column(Boolean, default=False)

    # SMS opt-in tracking for A2P compliance
    sms_opt_in_status = Column(
        String(20), default="pending"
    )  # pending, opted_in, opted_out
    sms_opt_in_date = Column(DateTime, nullable=True)
    sms_opt_out_date = Column(DateTime, nullable=True)
    initial_opt_in_message_sent = Column(Boolean, default=False)
    initial_opt_in_sent_date = Column(DateTime, nullable=True)

    # Additional metadata
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Properties for web form compatibility
    @property
    def email(self):
        return None

    @property
    def phone(self):
        return self.contact

    @property
    def unit_number(self):
        return self.building

    @property
    def rent_amount(self):
        return self.rent

    @property
    def emergency_contact(self):
        return None

    @property
    def lease_start_date(self):
        return None

    @property
    def lease_end_date(self):
        return None

    def __repr__(self):
        return f"<Tenant(name='{self.name}', contact='{self.contact}')>"


# Pydantic Schemas for API
class TenantBase(BaseModel):
    """Base tenant schema with common fields."""

    name: str
    contact: str
    rent: Optional[int] = None
    due_date: Optional[str] = None
    building: Optional[str] = None
    tenant_type: str = "residential"
    active: bool = True
    is_current_month_rent_paid: bool = False
    late_fee_applicable: bool = False
    sms_opt_in_status: str = "pending"  # pending, opted_in, opted_out
    notes: Optional[str] = None

    @validator("contact")
    def validate_contact(cls, v):
        """Validate contact number format."""
        if v:
            cleaned = normalize_phone(v)
            if len(cleaned) < 10:
                raise ValueError("Contact number must be at least 10 digits")
        return v

    @validator("name")
    def validate_name(cls, v):
        """Validate tenant name."""
        if not v or len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters long")
        return v.strip()

    @validator("tenant_type")
    def validate_tenant_type(cls, v):
        """Validate tenant type."""
        allowed_types = ["residential", "commercial", "mixed"]
        if v not in allowed_types:
            raise ValueError(f"Tenant type must be one of: {allowed_types}")
        return v


class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""


class TenantUpdate(BaseModel):
    """Schema for updating a tenant."""

    name: Optional[str] = None
    contact: Optional[str] = None
    rent: Optional[int] = None
    due_date: Optional[str] = None
    building: Optional[str] = None
    tenant_type: Optional[str] = None
    active: Optional[bool] = None
    is_current_month_rent_paid: Optional[bool] = None
    late_fee_applicable: Optional[bool] = None
    sms_opt_in_status: Optional[str] = None
    notes: Optional[str] = None

    @validator("contact", pre=True, always=True)
    def validate_contact(cls, v):
        """Validate contact number format."""
        if v:
            cleaned = normalize_phone(v)
            if len(cleaned) < 10:
                raise ValueError("Contact number must be at least 10 digits")
        return v


class TenantInDB(TenantBase):
    """Schema for tenant as stored in database."""

    id: int
    last_payment_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # For Pydantic v2


class TenantResponse(TenantInDB):
    """Schema for tenant API responses."""

    # Computed fields
    days_since_last_payment: Optional[int] = None
    payment_status: str = "unknown"

    @property
    def formatted_contact(self) -> str:
        """Format contact number for display."""
        return format_phone(self.contact) if self.contact else ""

    @property
    def display_name(self) -> str:
        """Get display name for elderly-friendly interfaces."""
        return self.name.title()


# Bulk operations schemas
class TenantBulkUpdate(BaseModel):
    """Schema for bulk updating tenant payment status."""

    tenant_ids: list[int]
    is_current_month_rent_paid: Optional[bool] = None
    late_fee_applicable: Optional[bool] = None
    notes: Optional[str] = None


class TenantImport(BaseModel):
    """Schema for importing tenants from CSV/Excel."""

    tenants: list[TenantCreate]
    overwrite_existing: bool = False

    @validator("tenants")
    def validate_tenants(cls, v):
        """Ensure we have at least one tenant."""
        if not v or len(v) == 0:
            raise ValueError("At least one tenant must be provided")
        return v


class TenantStats(BaseModel):
    """Schema for tenant statistics."""

    total: int
    paid: int
    unpaid: int
    late_fees: int


# Schema alias for API compatibility
Tenant = TenantDB
