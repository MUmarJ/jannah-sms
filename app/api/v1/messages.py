"""
Messages API endpoints for sending SMS and managing message history.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.message import (
    Message,
    MessageReply,
    MessageResponse,
    MessageSend,
    MessageStats,
    MessageStatus,
)
from app.models.tenant import Tenant
from app.services.sms_service import sms_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats", response_model=MessageStats)
async def get_message_stats(
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """Get message statistics for dashboard."""
    try:
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)

        messages_today = db.query(Message).filter(Message.sent_at >= today).count()

        messages_yesterday = (
            db.query(Message)
            .filter(Message.sent_at >= yesterday, Message.sent_at < today)
            .count()
        )

        total_messages = db.query(Message).count()
        successful_messages = (
            db.query(Message).filter(Message.status == MessageStatus.SENT).count()
        )

        success_rate = (
            (successful_messages / total_messages * 100) if total_messages > 0 else 0
        )

        return MessageStats(
            messages_today=messages_today,
            messages_yesterday=messages_yesterday,
            total_messages=total_messages,
            successful_messages=successful_messages,
            success_rate=round(success_rate, 1),
        )

    except Exception as e:
        logger.error(f"Failed to get message stats: {e!s}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve message statistics"
        )


@router.get("/", response_model=list[MessageResponse])
async def get_messages(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    tenant_id: Optional[int] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get list of messages with filtering and pagination."""
    try:
        query = db.query(Message)

        # Status filter
        if status:
            if status == "sent":
                query = query.filter(Message.status == MessageStatus.SENT)
            elif status == "failed":
                query = query.filter(Message.status == MessageStatus.FAILED)
            elif status == "scheduled":
                query = query.filter(Message.status == MessageStatus.SCHEDULED)

        # Tenant filter
        if tenant_id:
            query = query.filter(Message.tenant_id == tenant_id)

        # Date range filters
        if from_date:
            try:
                from_dt = datetime.fromisoformat(from_date)
                query = query.filter(Message.sent_at >= from_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid from_date format")

        if to_date:
            try:
                to_dt = datetime.fromisoformat(to_date)
                query = query.filter(Message.sent_at <= to_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid to_date format")

        messages = (
            query.order_by(desc(Message.created_at)).offset(skip).limit(limit).all()
        )
        return messages

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get messages: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to retrieve messages")


@router.get("/{message_id}")
async def get_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get single message by ID."""
    try:
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        # Get tenant information
        tenant = db.query(Tenant).filter(Tenant.id == message.tenant_id).first()

        # Get replies for this message
        replies = []
        if message.message_id:  # Only look for replies if we have a TextBelt message ID
            message_replies = (
                db.query(MessageReply)
                .filter(MessageReply.text_id == message.message_id)
                .order_by(MessageReply.received_at.asc())
                .all()
            )

            replies = [
                {
                    "id": reply.id,
                    "from_number": reply.from_number,
                    "reply_text": reply.reply_text,
                    "received_at": (
                        reply.received_at.isoformat() if reply.received_at else None
                    ),
                    "formatted_received_at": (
                        reply.received_at.strftime("%B %d, %Y at %I:%M %p")
                        if reply.received_at
                        else "Unknown"
                    ),
                }
                for reply in message_replies
            ]

        # Format response according to MessageLogResponse schema
        formatted_response = {
            "id": message.id,
            "tenant_id": message.tenant_id,
            "tenant_name": tenant.name if tenant else "Deleted Tenant",
            "tenant_contact": tenant.contact if tenant else "N/A",
            "message_content": message.content,
            "message_template": None,  # Not stored in current schema
            "message_type": "manual",  # Default value
            "status": (
                message.status
                if isinstance(message.status, str)
                else message.status.value
            ),
            "scheduled_message_id": None,  # Not used in current schema
            "is_test_mode": message.test_mode or False,
            "job_id": None,  # Not used in current schema
            "api_response": None,  # Not used in current schema
            "error_message": message.error_message,
            "conditions_met": None,  # Not used in current schema
            "condition_evaluation": None,  # Not used in current schema
            "sent_at": message.sent_at or message.created_at,
            "delivered_at": None,  # Not tracked in current schema
            "created_by": None,  # Not tracked in current schema
            "retry_count": 0,  # Not tracked in current schema
            "replies": replies,  # Add replies to response
        }

        return formatted_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get message {message_id}: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to retrieve message")


@router.post("/send")
async def send_message(
    message_data: MessageSend,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Send SMS message to tenants."""
    try:
        # Get eligible tenants based on recipient type
        tenants = await _get_eligible_tenants(
            message_data.recipient_type, message_data.selected_tenants, db
        )

        if not tenants:
            raise HTTPException(status_code=400, detail="No eligible tenants found")

        # Determine if this is immediate or scheduled
        if message_data.send_time == "now":
            # Send immediately in background
            background_tasks.add_task(
                _send_immediate_messages,
                tenants,
                message_data.message,
                message_data.test_mode,
                db,
            )
            return {
                "message": f"Sending messages to {len(tenants)} tenants",
                "recipient_count": len(tenants),
                "send_type": "immediate",
            }
        else:
            # Schedule for later
            scheduled_time = _parse_schedule_time(
                message_data.send_date, message_data.send_hour
            )

            # Create scheduled message records
            created_messages = []
            for tenant in tenants:
                message = Message(
                    tenant_id=tenant.id,
                    content=message_data.message,
                    status=MessageStatus.SCHEDULED,
                    scheduled_for=scheduled_time,
                    test_mode=message_data.test_mode,
                    created_at=datetime.utcnow(),
                )
                db.add(message)
                created_messages.append(message)

            db.commit()

            logger.info(
                f"Scheduled {len(created_messages)} messages for {scheduled_time}"
            )

            return {
                "message": f"Scheduled messages for {len(tenants)} tenants",
                "recipient_count": len(tenants),
                "send_type": "scheduled",
                "scheduled_for": scheduled_time.isoformat(),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send messages: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to send messages")


@router.post("/send-rent-reminders")
async def send_rent_reminders(
    background_tasks: BackgroundTasks,
    test_mode: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Send rent reminder messages to unpaid tenants."""
    try:
        # Get unpaid tenants
        unpaid_tenants = (
            db.query(Tenant)
            .filter(Tenant.active == True, Tenant.is_current_month_rent_paid == False)
            .all()
        )

        if not unpaid_tenants:
            return {"message": "No unpaid tenants found", "count": 0}

        # Send rent reminders in background
        background_tasks.add_task(
            _send_rent_reminders_task, unpaid_tenants, test_mode, db
        )

        return {
            "message": f"Sending rent reminders to {len(unpaid_tenants)} tenants",
            "count": len(unpaid_tenants),
        }

    except Exception as e:
        logger.error(f"Failed to send rent reminders: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to send rent reminders")


@router.post("/send-late-notices")
async def send_late_fee_notices(
    background_tasks: BackgroundTasks,
    test_mode: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Send late fee notices to tenants with overdue rent."""
    try:
        # Get tenants with late fees
        late_tenants = (
            db.query(Tenant)
            .filter(Tenant.active == True, Tenant.late_fee_applicable == True)
            .all()
        )

        if not late_tenants:
            return {"message": "No tenants with late fees found", "count": 0}

        # Send late notices in background
        background_tasks.add_task(_send_late_notices_task, late_tenants, test_mode, db)

        return {
            "message": f"Sending late fee notices to {len(late_tenants)} tenants",
            "count": len(late_tenants),
        }

    except Exception as e:
        logger.error(f"Failed to send late fee notices: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to send late fee notices")


@router.post("/{message_id}/cancel")
async def cancel_scheduled_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Cancel a scheduled message."""
    try:
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        if message.status != MessageStatus.SCHEDULED:
            raise HTTPException(status_code=400, detail="Message is not scheduled")

        message.status = MessageStatus.CANCELLED
        message.updated_at = datetime.utcnow()

        db.commit()

        logger.info(f"Cancelled scheduled message {message_id}")
        return {"message": "Message cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to cancel message {message_id}: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to cancel message")


@router.get("/templates/list")
async def get_message_templates(current_user: dict = Depends(get_current_user)):
    """Get available message templates."""
    try:
        templates = sms_service.get_available_templates()
        return {"templates": templates}

    except Exception as e:
        logger.error(f"Failed to get message templates: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to get message templates")


@router.post("/test-sms")
async def test_sms_api(
    test_mode: bool = Query(True), current_user: dict = Depends(get_current_user)
):
    """Test SMS API key and connection."""
    try:
        result = await sms_service.test_api_key(test_mode)
        return result

    except Exception as e:
        logger.error(f"Failed to test SMS API: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to test SMS API")


@router.get("/quota/remaining")
async def get_sms_quota(
    test_mode: bool = Query(False), current_user: dict = Depends(get_current_user)
):
    """Get remaining SMS quota."""
    try:
        quota = await sms_service.get_quota_remaining(test_mode)
        return {"quota_remaining": quota}

    except Exception as e:
        logger.error(f"Failed to get SMS quota: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to get SMS quota")


# Helper functions
async def _get_eligible_tenants(
    recipient_type: str, selected_tenants: Optional[list[int]], db: Session
) -> list[Tenant]:
    """Get eligible tenants based on recipient type."""
    if recipient_type == "all":
        return db.query(Tenant).filter(Tenant.active == True).all()
    elif recipient_type == "paid":
        return (
            db.query(Tenant)
            .filter(Tenant.active == True, Tenant.is_current_month_rent_paid == True)
            .all()
        )
    elif recipient_type == "unpaid":
        return (
            db.query(Tenant)
            .filter(Tenant.active == True, Tenant.is_current_month_rent_paid == False)
            .all()
        )
    elif recipient_type == "late_fee":
        return (
            db.query(Tenant)
            .filter(Tenant.active == True, Tenant.late_fee_applicable == True)
            .all()
        )
    elif recipient_type == "custom" and selected_tenants:
        return (
            db.query(Tenant)
            .filter(Tenant.active == True, Tenant.id.in_(selected_tenants))
            .all()
        )
    else:
        return []


def _parse_schedule_time(send_date: str, send_hour: int) -> datetime:
    """Parse scheduled send time from date and hour."""
    try:
        date_part = datetime.strptime(send_date, "%Y-%m-%d").date()
        scheduled_time = datetime.combine(date_part, datetime.min.time())
        scheduled_time = scheduled_time.replace(hour=send_hour)
        return scheduled_time
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid schedule time: {e!s}")


async def _send_immediate_messages(
    tenants: list[Tenant], message: str, test_mode: bool, db: Session
):
    """Background task to send immediate messages."""
    try:
        result = await sms_service.send_bulk_sms(
            tenants=tenants, message=message, test_mode=test_mode
        )

        # Create message records
        for sms_result in result["results"]:
            message_record = Message(
                tenant_id=sms_result["tenant_id"],
                content=sms_result.get("content", message),
                status=(
                    MessageStatus.SENT
                    if sms_result["success"]
                    else MessageStatus.FAILED
                ),
                sent_at=datetime.utcnow() if sms_result["success"] else None,
                message_id=sms_result.get("message_id"),
                error_message=sms_result.get("error"),
                test_mode=test_mode,
                created_at=datetime.utcnow(),
            )
            db.add(message_record)

        db.commit()

        logger.info(
            f"Completed immediate message send: {result['successful_sends']}/{len(tenants)} successful"
        )

    except Exception as e:
        logger.error(f"Failed to send immediate messages: {e!s}")
        db.rollback()


async def _send_rent_reminders_task(
    tenants: list[Tenant], test_mode: bool, db: Session
):
    """Background task to send rent reminders."""
    try:
        # Calculate due date (typically 1st of current month)
        current_date = datetime.utcnow()
        due_date = f"{current_date.strftime('%B')} 1st"

        result = await sms_service.send_rent_reminders(
            unpaid_tenants=tenants, due_date=due_date, test_mode=test_mode
        )

        # Create message records
        for sms_result in result["results"]:
            message_record = Message(
                tenant_id=sms_result["tenant_id"],
                content=sms_result.get("content", ""),
                status=(
                    MessageStatus.SENT
                    if sms_result["success"]
                    else MessageStatus.FAILED
                ),
                sent_at=datetime.utcnow() if sms_result["success"] else None,
                message_id=sms_result.get("message_id"),
                error_message=sms_result.get("error"),
                test_mode=test_mode,
                created_at=datetime.utcnow(),
            )
            db.add(message_record)

        db.commit()

        logger.info(
            f"Completed rent reminders: {result['successful_sends']}/{len(tenants)} successful"
        )

    except Exception as e:
        logger.error(f"Failed to send rent reminders: {e!s}")
        db.rollback()


async def _send_late_notices_task(tenants: list[Tenant], test_mode: bool, db: Session):
    """Background task to send late fee notices."""
    try:
        result = await sms_service.send_late_fee_notices(
            late_tenants=tenants, test_mode=test_mode
        )

        # Create message records
        for sms_result in result["results"]:
            message_record = Message(
                tenant_id=sms_result["tenant_id"],
                content=sms_result.get("content", ""),
                status=(
                    MessageStatus.SENT
                    if sms_result["success"]
                    else MessageStatus.FAILED
                ),
                sent_at=datetime.utcnow() if sms_result["success"] else None,
                message_id=sms_result.get("message_id"),
                error_message=sms_result.get("error"),
                test_mode=test_mode,
                created_at=datetime.utcnow(),
            )
            db.add(message_record)

        db.commit()

        logger.info(
            f"Completed late fee notices: {result['successful_sends']}/{len(tenants)} successful"
        )

    except Exception as e:
        logger.error(f"Failed to send late fee notices: {e!s}")
        db.rollback()
