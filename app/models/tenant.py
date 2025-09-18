"""
Tenant models - SQLAlchemy and Pydantic schemas.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Date
from pydantic import BaseModel, validator
import re

from app.core.database import Base


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
    notes: Optional[str] = None

    @validator("contact")
    def validate_contact(cls, v):
        """Validate contact number format."""
        if v:
            # Remove any non-digit characters
            cleaned = re.sub(r"[^0-9]", "", v)
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

    pass


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
    notes: Optional[str] = None

    @validator("contact", pre=True, always=True)
    def validate_contact(cls, v):
        """Validate contact number format."""
        if v:
            # Remove any non-digit characters
            cleaned = re.sub(r"[^0-9]", "", v)
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
        if self.contact:
            # Format as (XXX) XXX-XXXX
            cleaned = re.sub(r"[^0-9]", "", self.contact)
            if len(cleaned) == 10:
                return f"({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"
            elif len(cleaned) == 11 and cleaned[0] == "1":
                return f"+1 ({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:]}"
        return self.contact

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
