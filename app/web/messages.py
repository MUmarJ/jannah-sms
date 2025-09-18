"""
Messages web interface routes.
"""

import logging
from datetime import datetime, timedelta, date
from typing import Optional
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.message import Message, MessageStatus, MessageReply
from app.models.schedule import Schedule, ScheduleStatus
from app.services.sms_service import sms_service
from app.core.templates import templates, get_template_context


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
@router.get("/history", response_class=HTMLResponse)
async def messages_history(
    request: Request,
    page: int = 1,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Messages history page with filtering."""
    try:
        per_page = 20
        offset = (page - 1) * per_page
        
        # Build query - use left join to include messages with deleted tenants
        query = db.query(Message).outerjoin(Tenant, Message.tenant_id == Tenant.id)
        
        # Apply filters
        if status:
            if status == "sent":
                query = query.filter(Message.status == MessageStatus.SENT)
            elif status == "failed":
                query = query.filter(Message.status == MessageStatus.FAILED)
            elif status == "scheduled":
                query = query.filter(Message.status == MessageStatus.SCHEDULED)
        
        if from_date:
            try:
                from_dt = datetime.fromisoformat(from_date)
                query = query.filter(Message.sent_at >= from_dt)
            except ValueError:
                pass
        
        if to_date:
            try:
                to_dt = datetime.fromisoformat(to_date)
                query = query.filter(Message.sent_at <= to_dt)
            except ValueError:
                pass
        
        # Get total count for pagination
        total_count = query.count()
        
        # Get messages for current page
        messages = query.order_by(Message.created_at.desc()).offset(offset).limit(per_page).all()
        
        # Format messages for display
        formatted_messages = []
        for message in messages:
            tenant = db.query(Tenant).filter(Tenant.id == message.tenant_id).first()
            
            # Get reply count for this message
            reply_count = 0
            if message.message_id:  # Only check if we have a TextBelt message ID
                reply_count = db.query(MessageReply).filter(
                    MessageReply.text_id == message.message_id
                ).count()
            
            if tenant:
                formatted_messages.append({
                    "id": message.id,
                    "tenant_name": tenant.name,
                    "tenant_phone": tenant.contact,
                    "content": message.content,
                    "status": message.status.value if hasattr(message.status, 'value') else message.status,
                    "status_display": _get_status_display(message.status),
                    "sent_at": message.sent_at,
                    "scheduled_for": message.scheduled_for,
                    "reply_count": reply_count
                })
            else:
                # Handle messages with deleted tenants
                formatted_messages.append({
                    "id": message.id,
                    "tenant_name": "Deleted Tenant",
                    "tenant_phone": "N/A",
                    "content": message.content,
                    "status": message.status.value if hasattr(message.status, 'value') else message.status,
                    "status_display": _get_status_display(message.status),
                    "sent_at": message.sent_at,
                    "scheduled_for": message.scheduled_for,
                    "reply_count": reply_count
                })
        
        # Pagination info
        total_pages = (total_count + per_page - 1) // per_page
        pagination = {
            "page": page,
            "pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_num": page - 1 if page > 1 else None,
            "next_num": page + 1 if page < total_pages else None
        } if total_pages > 1 else None
        
        return templates.TemplateResponse(
            "messages.html",
            {
                "request": request,
                "message_history": formatted_messages,
                "pagination": pagination,
                "today": date.today().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Messages history error: {str(e)}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "Failed to load messages"
            }
        )


@router.get("/send", response_class=HTMLResponse)
async def send_message_form(
    request: Request,
    tenant: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Send message form page."""
    try:
        # Get all active tenants
        tenants = db.query(Tenant).filter(Tenant.active == True).order_by(Tenant.name).all()
        
        return templates.TemplateResponse(
            "messages.html",
            {
                "request": request,
                "tenants": tenants,
                "today": date.today().isoformat(),
                "selected_tenant": tenant
            }
        )
        
    except Exception as e:
        logger.error(f"Send message form error: {str(e)}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "Failed to load send message form"
            }
        )


@router.post("/send")
async def send_message_submit(
    request: Request,
    recipient_type: str = Form(...),
    message: str = Form(...),
    send_time: str = Form(...),
    selected_tenants: Optional[list] = Form(None),
    send_date: Optional[str] = Form(None),
    send_hour_final: Optional[int] = Form(None),
    send_minute_final: Optional[int] = Form(None),
    # Keep backwards compatibility with old field names
    send_hour: Optional[int] = Form(None),
    send_minute: Optional[int] = Form(None),
    custom_minute: Optional[int] = Form(None),
    create_schedule: Optional[bool] = Form(False),
    rent_day: Optional[int] = Form(5),
    db: Session = Depends(get_db)
):
    """Handle message send form submission."""
    try:
        # Get eligible tenants
        tenants = await _get_eligible_tenants(recipient_type, selected_tenants, db)
        
        if not tenants:
            # Flash error message and redirect
            return RedirectResponse(
                url="/messages/send?error=no_recipients",
                status_code=302
            )
        
        if send_time == "now":
            # Send immediately with rent day for dynamic replacement
            result = await sms_service.send_bulk_sms(
                tenants=tenants,
                message=message,
                test_mode=False,  # TODO: Add test mode option to form
                rent_day=rent_day if create_schedule else None
            )
            
            # Create message records
            for sms_result in result["results"]:
                message_record = Message(
                    tenant_id=sms_result["tenant_id"],
                    content=sms_result.get("content", message),
                    status=MessageStatus.SENT if sms_result["success"] else MessageStatus.FAILED,
                    sent_at=datetime.utcnow() if sms_result["success"] else None,
                    message_id=sms_result.get("message_id"),
                    error_message=sms_result.get("error"),
                    test_mode=False,
                    created_at=datetime.utcnow()
                )
                db.add(message_record)
            
            db.commit()
            
            # Create monthly schedule if requested
            if create_schedule:
                try:
                    schedule_name = f"Monthly Rent Reminder - Day {rent_day}"
                    schedule = Schedule(
                        name=schedule_name,
                        message_template=message,
                        schedule_type="monthly",
                        schedule_value=str(rent_day),  # Store rent day
                        target_tenant_types=recipient_type,
                        status=ScheduleStatus.ACTIVE,
                        created_at=datetime.utcnow()
                    )
                    db.add(schedule)
                    db.commit()
                    
                    return RedirectResponse(
                        url=f"/messages?success=sent_{result['successful_sends']}_of_{len(tenants)}_and_schedule_created",
                        status_code=302
                    )
                except Exception as e:
                    logger.error(f"Failed to create schedule: {str(e)}")
                    # Still redirect with success for sent messages
                    return RedirectResponse(
                        url=f"/messages?success=sent_{result['successful_sends']}_of_{len(tenants)}_schedule_failed",
                        status_code=302
                    )
            
            # Redirect with success message
            return RedirectResponse(
                url=f"/messages?success=sent_{result['successful_sends']}_of_{len(tenants)}",
                status_code=302
            )
            
        else:
            # Schedule for later - prioritize new field names
            hour_final = send_hour_final if send_hour_final is not None else send_hour
            minute_final = send_minute_final if send_minute_final is not None else (custom_minute if custom_minute is not None else (send_minute if send_minute is not None else 0))
            
            if not send_date or hour_final is None:
                return RedirectResponse(
                    url="/messages/send?error=missing_schedule_info",
                    status_code=302
                )
            
            scheduled_time = _parse_schedule_time(send_date, hour_final, minute_final)
            
            # Create scheduled message records
            for tenant in tenants:
                message_record = Message(
                    tenant_id=tenant.id,
                    content=message,
                    status=MessageStatus.SCHEDULED,
                    scheduled_for=scheduled_time,
                    test_mode=False,
                    created_at=datetime.utcnow()
                )
                db.add(message_record)
            
            db.commit()
            
            # Redirect with success message
            return RedirectResponse(
                url=f"/messages?success=scheduled_{len(tenants)}_messages",
                status_code=302
            )
        
    except Exception as e:
        logger.error(f"Send message submit error: {str(e)}")
        return RedirectResponse(
            url="/messages/send?error=send_failed",
            status_code=302
        )


async def _get_eligible_tenants(
    recipient_type: str,
    selected_tenants: Optional[list],
    db: Session
) -> list[Tenant]:
    """Get eligible tenants based on recipient type."""
    if recipient_type == "all":
        return db.query(Tenant).filter(Tenant.active == True).all()
    elif recipient_type == "paid":
        return db.query(Tenant).filter(
            Tenant.active == True,
            Tenant.is_current_month_rent_paid == True
        ).all()
    elif recipient_type == "unpaid":
        return db.query(Tenant).filter(
            Tenant.active == True,
            Tenant.is_current_month_rent_paid == False
        ).all()
    elif recipient_type == "late_fee":
        return db.query(Tenant).filter(
            Tenant.active == True,
            Tenant.late_fee_applicable == True
        ).all()
    elif recipient_type == "custom" and selected_tenants:
        return db.query(Tenant).filter(
            Tenant.active == True,
            Tenant.id.in_(selected_tenants)
        ).all()
    else:
        return []


def _parse_schedule_time(send_date: str, send_hour: int, send_minute: int = 0) -> datetime:
    """Parse scheduled send time from date, hour, and minute."""
    try:
        date_part = datetime.strptime(send_date, "%Y-%m-%d").date()
        scheduled_time = datetime.combine(date_part, datetime.min.time())
        scheduled_time = scheduled_time.replace(hour=send_hour, minute=send_minute)
        
        # Validate that the scheduled time is in the future (with 2 minute buffer for processing)
        current_time = datetime.utcnow()
        buffer_time = current_time + timedelta(minutes=2)
        if scheduled_time <= buffer_time:
            # Add more detailed error message
            raise HTTPException(
                status_code=400, 
                detail=f"Scheduled time must be at least 2 minutes in the future. Scheduled: {scheduled_time.strftime('%Y-%m-%d %H:%M')}, Current: {current_time.strftime('%Y-%m-%d %H:%M')} UTC"
            )
            
        return scheduled_time
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid schedule time: {str(e)}")


def _get_status_display(status) -> str:
    """Get display text for message status."""
    # Handle both enum and string values
    if hasattr(status, 'value'):
        status_value = status.value
    else:
        status_value = status
        
    status_map = {
        "sent": "Sent",
        "failed": "Failed", 
        "scheduled": "Scheduled",
        "cancelled": "Cancelled",
        "pending": "Pending",
        "delivered": "Delivered"
    }
    return status_map.get(status_value, "Unknown")