"""
Message models - SQLAlchemy and Pydantic schemas for SMS messages and logs.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, validator
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from app.core.database import Base


class MessageStatus(str, Enum):
    """Message delivery status."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class MessageType(str, Enum):
    """Types of messages."""

    MANUAL = "manual"  # Sent manually by admin
    SCHEDULED = "scheduled"  # Sent by scheduled job
    BULK = "bulk"  # Bulk message to multiple tenants
    TEST = "test"  # Test message


# SQLAlchemy Model
class Message(Base):
    """SQLAlchemy model for message logs."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)

    # Recipient information
    tenant_id = Column(Integer, nullable=False, index=True)

    # Message content
    content = Column(Text, nullable=False)

    # Message status
    status = Column(String(20), default=MessageStatus.PENDING.value)

    # Scheduling information
    scheduled_for = Column(DateTime, nullable=True)

    # Delivery tracking
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # API response data
    message_id = Column(String(255), nullable=True)  # External message ID
    error_message = Column(Text, nullable=True)

    # Test mode flag
    test_mode = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Message(id={self.id}, tenant_id={self.tenant_id}, status='{self.status}')>"


# SMS Reply storage
class MessageReply(Base):
    """SQLAlchemy model for SMS replies."""

    __tablename__ = "message_replies"

    id = Column(Integer, primary_key=True, index=True)

    # Link to original message
    original_message_id = Column(
        Integer, ForeignKey("messages.id"), nullable=False, index=True
    )
    text_id = Column(String(255), nullable=False, index=True)  # TextBelt message ID

    # Reply details
    from_number = Column(String(20), nullable=False)
    reply_text = Column(Text, nullable=False)

    # Metadata
    received_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False)

    def __repr__(self):
        return f"<MessageReply(id={self.id}, text_id='{self.text_id}', from_number='{self.from_number}')>"


# Message template storage
class MessageTemplateDB(Base):
    """SQLAlchemy model for message templates."""

    __tablename__ = "message_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    category = Column(String(50), nullable=False)  # rent, maintenance, general
    template_content = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    # Template variables
    variables = Column(
        JSON, nullable=True
    )  # List of variables like ["TENANT_NAME", "DUE_DATE"]

    # Metadata
    active = Column(String(10), default="true")  # "true" or "false"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<MessageTemplate(name='{self.name}', category='{self.category}')>"


# Pydantic Schemas
class MessageLogBase(BaseModel):
    """Base message log schema."""

    tenant_name: str
    tenant_contact: str
    message_content: str
    message_template: Optional[str] = None
    message_type: MessageType = MessageType.MANUAL
    status: MessageStatus = MessageStatus.PENDING
    scheduled_message_id: Optional[int] = None
    is_test_mode: bool = False

    @validator("tenant_name")
    def validate_tenant_name(cls, v):
        """Validate tenant name."""
        if not v or len(v.strip()) < 2:
            raise ValueError("Tenant name must be at least 2 characters long")
        return v.strip()

    @validator("message_content")
    def validate_message_content(cls, v):
        """Validate message content."""
        if not v or len(v.strip()) < 5:
            raise ValueError("Message content must be at least 5 characters long")
        if len(v) > 1600:  # SMS length limit
            raise ValueError("Message content must be less than 1600 characters")
        return v.strip()


class MessageLogCreate(MessageLogBase):
    """Schema for creating a new message log."""

    tenant_id: Optional[int] = None
    conditions_met: Optional[dict[str, Any]] = None
    created_by: Optional[str] = None


class MessageLogUpdate(BaseModel):
    """Schema for updating a message log."""

    status: Optional[MessageStatus] = None
    error_message: Optional[str] = None
    api_response: Optional[dict[str, Any]] = None
    delivered_at: Optional[datetime] = None


class MessageLogInDB(MessageLogBase):
    """Schema for message log as stored in database."""

    id: int
    tenant_id: Optional[int] = None
    job_id: Optional[str] = None
    api_response: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    conditions_met: Optional[dict[str, Any]] = None
    condition_evaluation: Optional[dict[str, Any]] = None
    sent_at: datetime
    delivered_at: Optional[datetime] = None
    created_by: Optional[str] = None
    retry_count: int = 0

    class Config:
        from_attributes = True


class MessageLogResponse(MessageLogInDB):
    """Schema for message log API responses."""

    @property
    def status_display(self) -> str:
        """Get user-friendly status display."""
        status_map = {
            MessageStatus.PENDING: "⏳ Pending",
            MessageStatus.SENT: "✅ Sent",
            MessageStatus.FAILED: "❌ Failed",
            MessageStatus.DELIVERED: "📱 Delivered",
            MessageStatus.UNKNOWN: "❓ Unknown",
            MessageStatus.SCHEDULED: "⏰ Scheduled",
            MessageStatus.CANCELLED: "❌ Cancelled",
        }
        return status_map.get(self.status, self.status)

    @property
    def type_display(self) -> str:
        """Get user-friendly message type display."""
        type_map = {
            MessageType.MANUAL: "👤 Manual",
            MessageType.SCHEDULED: "⏰ Scheduled",
            MessageType.BULK: "📢 Bulk",
            MessageType.TEST: "🧪 Test",
        }
        return type_map.get(self.message_type, self.message_type)

    @property
    def formatted_sent_at(self) -> str:
        """Get formatted sent time for elderly-friendly display."""
        if self.sent_at:
            return self.sent_at.strftime("%B %d, %Y at %I:%M %p")
        return "Not sent"


# Message Template Schemas
class MessageTemplateBase(BaseModel):
    """Base message template schema."""

    name: str
    category: str
    template_content: str
    description: Optional[str] = None
    variables: Optional[list[str]] = None
    active: bool = True

    @validator("name")
    def validate_name(cls, v):
        """Validate template name."""
        if not v or len(v.strip()) < 3:
            raise ValueError("Template name must be at least 3 characters long")
        return v.strip()

    @validator("category")
    def validate_category(cls, v):
        """Validate template category."""
        valid_categories = ["rent", "maintenance", "general", "late_fees", "notices"]
        if v not in valid_categories:
            raise ValueError(f"Category must be one of: {valid_categories}")
        return v

    @validator("template_content")
    def validate_template_content(cls, v):
        """Validate template content."""
        if not v or len(v.strip()) < 10:
            raise ValueError("Template content must be at least 10 characters long")
        return v.strip()


class MessageTemplateCreate(MessageTemplateBase):
    """Schema for creating a new message template."""


class MessageTemplateUpdate(BaseModel):
    """Schema for updating a message template."""

    name: Optional[str] = None
    category: Optional[str] = None
    template_content: Optional[str] = None
    description: Optional[str] = None
    variables: Optional[list[str]] = None
    active: Optional[bool] = None


class MessageTemplateInDB(MessageTemplateBase):
    """Schema for message template as stored in database."""

    id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None

    class Config:
        from_attributes = True


class MessageTemplateResponse(MessageTemplateInDB):
    """Schema for message template API responses."""


# Bulk messaging
class BulkMessageRequest(BaseModel):
    """Schema for bulk messaging requests."""

    tenant_ids: list[int]
    message_template_id: Optional[int] = None
    custom_message: Optional[str] = None
    message_type: MessageType = MessageType.BULK
    is_test_mode: bool = True  # Default to test mode for safety

    @validator("tenant_ids")
    def validate_tenant_ids(cls, v):
        """Validate tenant IDs list."""
        if not v or len(v) == 0:
            raise ValueError("At least one tenant must be selected")
        if len(v) > 100:  # Reasonable limit
            raise ValueError("Cannot send to more than 100 tenants at once")
        return v

    def validate_message_source(self):
        """Validate that either template_id or custom_message is provided."""
        if not self.message_template_id and not self.custom_message:
            raise ValueError(
                "Either message_template_id or custom_message must be provided"
            )
        if self.message_template_id and self.custom_message:
            raise ValueError(
                "Cannot specify both message_template_id and custom_message"
            )


class BulkMessageResponse(BaseModel):
    """Schema for bulk message response."""

    total_requested: int
    messages_queued: int
    messages_failed: int
    tenant_results: list[dict[str, Any]]
    errors: list[str]


class MessageSend(BaseModel):
    recipient_type: str
    selected_tenants: Optional[list[int]] = None
    send_time: str  # "now" or "scheduled"
    message: str
    test_mode: bool = True
    send_date: Optional[str] = None  # For scheduling
    send_hour: Optional[int] = None  # For scheduling


class MessageStats(BaseModel):
    """Schema for message statistics."""

    messages_today: int
    messages_yesterday: int
    total_messages: int
    successful_messages: int
    success_rate: float


# Message Reply Schemas
class MessageReplyBase(BaseModel):
    """Base message reply schema."""

    text_id: str
    from_number: str
    reply_text: str


class MessageReplyCreate(MessageReplyBase):
    """Schema for creating a new message reply."""

    original_message_id: Optional[int] = None


class MessageReplyInDB(MessageReplyBase):
    """Schema for message reply as stored in database."""

    id: int
    original_message_id: int
    received_at: datetime
    processed: bool = False

    class Config:
        from_attributes = True


class MessageReplyResponse(MessageReplyInDB):
    """Schema for message reply API responses."""

    @property
    def formatted_received_at(self) -> str:
        """Get formatted received time for display."""
        if self.received_at:
            return self.received_at.strftime("%B %d, %Y at %I:%M %p")
        return "Unknown"


# Webhook payload schema
class TextBeltWebhookPayload(BaseModel):
    """Schema for TextBelt webhook payload."""

    textId: str
    fromNumber: str
    text: str


# Schema aliases for API compatibility
MessageCreate = MessageLogCreate
MessageUpdate = MessageLogUpdate
MessageInDB = MessageLogInDB
MessageResponse = MessageLogResponse
