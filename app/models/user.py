"""
User models - Simple admin user management.
For now, we'll use a simple single-admin system suitable for elderly users.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, validator
from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.core.database import Base


# SQLAlchemy Model
class UserDB(Base):
    """SQLAlchemy model for users (admin accounts)."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)

    # User status
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=True)  # For now, all users are admins

    # Login tracking
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0)

    # Account metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Preferences for elderly-friendly UI
    ui_large_text = Column(Boolean, default=True)
    ui_high_contrast = Column(Boolean, default=True)
    ui_simple_mode = Column(Boolean, default=True)

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"


# Pydantic Schemas
class UserBase(BaseModel):
    """Base user schema."""

    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: bool = True
    ui_large_text: bool = True
    ui_high_contrast: bool = True
    ui_simple_mode: bool = True

    @validator("username")
    def validate_username(cls, v):
        """Validate username."""
        if not v or len(v.strip()) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if not v.isalnum():
            raise ValueError("Username must contain only letters and numbers")
        return v.strip().lower()

    @validator("full_name")
    def validate_full_name(cls, v):
        """Validate full name."""
        if v and len(v.strip()) < 2:
            raise ValueError("Full name must be at least 2 characters long")
        return v.strip() if v else None


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str

    @validator("password")
    def validate_password(cls, v):
        """Validate password."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    ui_large_text: Optional[bool] = None
    ui_high_contrast: Optional[bool] = None
    ui_simple_mode: Optional[bool] = None

    @validator("full_name")
    def validate_full_name(cls, v):
        """Validate full name."""
        if v and len(v.strip()) < 2:
            raise ValueError("Full name must be at least 2 characters long")
        return v.strip() if v else None


class UserUpdatePassword(BaseModel):
    """Schema for updating user password."""

    current_password: str
    new_password: str

    @validator("new_password")
    def validate_new_password(cls, v):
        """Validate new password."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserInDB(UserBase):
    """Schema for user as stored in database."""

    id: int
    is_admin: bool
    last_login: Optional[datetime] = None
    login_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserResponse(UserInDB):
    """Schema for user API responses (without sensitive data)."""

    @property
    def display_name(self) -> str:
        """Get display name for UI."""
        return self.full_name or self.username.title()

    @property
    def last_login_display(self) -> str:
        """Get formatted last login for elderly-friendly display."""
        if self.last_login:
            return self.last_login.strftime("%B %d, %Y at %I:%M %p")
        return "Never"


# Authentication schemas
class UserLogin(BaseModel):
    """Schema for user login."""

    username: str
    password: str
    remember_me: bool = False

    @validator("username")
    def validate_username(cls, v):
        """Validate username."""
        if not v or len(v.strip()) < 3:
            raise ValueError("Username is required")
        return v.strip().lower()

    @validator("password")
    def validate_password(cls, v):
        """Validate password."""
        if not v:
            raise ValueError("Password is required")
        return v


class UserLoginResponse(BaseModel):
    """Schema for login response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class Token(BaseModel):
    """Schema for JWT token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Schema for token payload data."""

    username: Optional[str] = None
    exp: Optional[datetime] = None


# Session management for elderly-friendly interface
class UserSession(BaseModel):
    """Schema for user session information."""

    user_id: int
    username: str
    full_name: Optional[str] = None
    is_admin: bool
    ui_preferences: dict
    session_start: datetime
    last_activity: datetime

    @property
    def session_duration_minutes(self) -> int:
        """Get session duration in minutes."""
        if self.last_activity and self.session_start:
            delta = self.last_activity - self.session_start
            return int(delta.total_seconds() / 60)
        return 0
