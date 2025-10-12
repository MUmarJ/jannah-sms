"""
Dashboard web interface routes.
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import get_template_context, templates
from app.models.message import Message, MessageStatus
from app.models.schedule import Schedule, ScheduleStatus
from app.models.tenant import Tenant
from app.services.sms_service import sms_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: Session = Depends(get_db)):
    """Main dashboard page with overview statistics."""
    try:
        # Get dashboard statistics
        stats = await _get_dashboard_stats(db)

        # Get recent messages (last 10) - FIXED JOIN
        recent_messages = (
            db.query(Message)
            .select_from(Message)
            .join(Tenant, Message.tenant_id == Tenant.id)
            .filter(Message.sent_at.isnot(None))
            .order_by(Message.sent_at.desc())
            .limit(10)
            .all()
        )

        # Format recent messages for display
        formatted_messages = []
        for message in recent_messages:
            tenant = db.query(Tenant).filter(Tenant.id == message.tenant_id).first()
            if tenant:
                formatted_messages.append(
                    {
                        "id": message.id,
                        "tenant_name": tenant.name,
                        "status": (
                            message.status.value
                            if hasattr(message.status, "value")
                            else message.status
                        ),
                        "status_display": _get_status_display(message.status),
                        "sent_at": message.sent_at,
                    }
                )

        # Get upcoming schedules (next 5)
        upcoming_schedules = (
            db.query(Schedule)
            .filter(
                Schedule.status == ScheduleStatus.ACTIVE, Schedule.next_run.isnot(None)
            )
            .order_by(Schedule.next_run)
            .limit(5)
            .all()
        )

        # Format upcoming schedules for display
        formatted_schedules = []
        for schedule in upcoming_schedules:
            formatted_schedules.append(
                {
                    "id": schedule.id,
                    "name": schedule.name,
                    "status": (
                        schedule.status.value
                        if hasattr(schedule.status, "value")
                        else schedule.status
                    ),
                    "status_display": _get_schedule_status_display(schedule.status),
                    "schedule_display": _format_schedule_display(
                        schedule.schedule_config
                    ),
                    "next_run": schedule.next_run,
                }
            )

        # Get SMS quota information
        sms_quota = await sms_service.get_quota_remaining(test_mode=True)

        # System status (optional)
        system_status = {
            "sms_api": True,  # TODO: Check SMS API status
            "scheduler": True,  # TODO: Check scheduler status
            "database": True,  # TODO: Check database status
        }

        return templates.TemplateResponse(
            "dashboard.html",
            get_template_context(
                request,
                stats=stats,
                recent_messages=formatted_messages,
                upcoming_schedules=formatted_schedules,
                system_status=system_status,
                sms_quota=sms_quota,
            ),
        )

    except Exception as e:
        logger.error(f"Dashboard page error: {e!s}")
        return templates.TemplateResponse(
            "error.html",
            get_template_context(request, error="Failed to load dashboard"),
        )


async def _get_dashboard_stats(db: Session) -> dict:
    """Get dashboard statistics."""
    try:
        # Tenant stats
        total_tenants = db.query(Tenant).filter(Tenant.active == True).count()

        # Schedule stats
        active_schedules = (
            db.query(Schedule).filter(Schedule.status == ScheduleStatus.ACTIVE).count()
        )

        # Message stats (today)
        today = datetime.utcnow().date()
        messages_today = db.query(Message).filter(Message.sent_at >= today).count()

        # Success rate (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        total_recent_messages = (
            db.query(Message).filter(Message.sent_at >= thirty_days_ago).count()
        )

        successful_recent_messages = (
            db.query(Message)
            .filter(
                Message.sent_at >= thirty_days_ago, Message.status == MessageStatus.SENT
            )
            .count()
        )

        success_rate = 0
        if total_recent_messages > 0:
            success_rate = round(
                (successful_recent_messages / total_recent_messages) * 100, 1
            )

        return {
            "total_tenants": total_tenants,
            "active_schedules": active_schedules,
            "messages_today": messages_today,
            "success_rate": success_rate,
        }

    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e!s}")
        return {
            "total_tenants": 0,
            "active_schedules": 0,
            "messages_today": 0,
            "success_rate": 0,
        }


def _get_status_display(status) -> str:
    """Get display text for message status."""
    # Handle both enum and string status values
    if hasattr(status, "value"):
        status_value = status.value
    else:
        status_value = status

    status_map = {
        "sent": "Sent",
        "failed": "Failed",
        "scheduled": "Scheduled",
        "cancelled": "Cancelled",
    }
    return status_map.get(status_value, "Unknown")


def _get_schedule_status_display(status) -> str:
    """Get display text for schedule status."""
    # Handle both enum and string status values
    if hasattr(status, "value"):
        status_value = status.value
    else:
        status_value = status

    status_map = {
        "active": "Active",
        "paused": "Paused",
        "completed": "Completed",
    }
    return status_map.get(status_value, "Unknown")


def _format_schedule_display(schedule_config: dict) -> str:
    """Format schedule configuration for display."""
    try:
        schedule_type = schedule_config.get("type", "")

        if schedule_type == "cron":
            hour = schedule_config.get("hour", 9)
            minute = schedule_config.get("minute", 0)
            day = schedule_config.get("day")
            month = schedule_config.get("month")

            time_str = f"{hour:02d}:{minute:02d}"

            if month and day:
                return f"Monthly on {day}th at {time_str}"
            elif day:
                return f"Daily at {time_str}"
            else:
                return f"At {time_str}"

        elif schedule_type == "interval":
            if schedule_config.get("days"):
                return f"Every {schedule_config['days']} day(s)"
            elif schedule_config.get("hours"):
                return f"Every {schedule_config['hours']} hour(s)"
            elif schedule_config.get("minutes"):
                return f"Every {schedule_config['minutes']} minute(s)"

        elif schedule_type == "date":
            run_date = schedule_config.get("run_date")
            if run_date:
                return f"One-time on {run_date}"

        return "Custom schedule"

    except Exception:
        return "Custom schedule"
