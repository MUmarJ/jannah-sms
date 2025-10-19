"""
Schedules web interface routes.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.templates import templates
from app.models.schedule import Schedule, ScheduleStatus
from app.services.condition_service import condition_service
from app.services.scheduler_service import scheduler_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def schedules_list(
    request: Request,
    page: int = 1,
    status: Optional[str] = None,
    schedule_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Schedules list page with filtering and pagination."""
    try:
        per_page = 20
        offset = (page - 1) * per_page

        # Build query
        query = db.query(Schedule)

        # Apply filters
        if status:
            if status == "active":
                query = query.filter(Schedule.status == ScheduleStatus.ACTIVE)
            elif status == "paused":
                query = query.filter(Schedule.status == ScheduleStatus.PAUSED)
            elif status == "completed":
                query = query.filter(Schedule.status == ScheduleStatus.COMPLETED)

        if schedule_type:
            query = query.filter(Schedule.schedule_type == schedule_type)

        # Get total count for pagination
        total_count = query.count()

        # Get schedules for current page
        schedules = (
            query.order_by(Schedule.created_at.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )

        # Format schedules for display
        formatted_schedules = []
        for schedule in schedules:
            # Handle status field - it might be string or enum
            status_value = (
                schedule.status.value
                if hasattr(schedule.status, "value")
                else schedule.status
            )
            formatted_schedules.append(
                {
                    "id": schedule.id,
                    "name": schedule.name,
                    "schedule_type": schedule.schedule_type,
                    "status": status_value,
                    "status_display": _get_schedule_status_display(schedule.status),
                    "schedule_display": _format_schedule_display(
                        _build_schedule_config_from_db(schedule)
                    ),
                    "next_run": schedule.next_run,
                    "created_at": schedule.created_at,
                }
            )

        # Get statistics
        stats = await _get_schedule_stats(db)

        # Get recent executions
        recent_executions = []
        recent_schedules = (
            db.query(Schedule)
            .filter(Schedule.last_run.isnot(None))
            .order_by(Schedule.last_run.desc())
            .limit(5)
            .all()
        )

        for schedule in recent_schedules:
            if schedule.last_run:
                # Use basic stats from schedule model fields
                stats_data = {
                    "successful_sends": schedule.success_count,
                    "failed_sends": schedule.failure_count,
                    "total_recipients": schedule.success_count + schedule.failure_count,
                }
                recent_executions.append(
                    {
                        "id": f"exec_{schedule.id}_{schedule.execution_count}",
                        "schedule_name": schedule.name,
                        "executed_at": schedule.last_run,
                        "total_recipients": stats_data.get("total_recipients", 0),
                        "successful_sends": stats_data.get("successful_sends", 0),
                        "success_rate": stats_data.get("success_rate", 0),
                    }
                )

        # Pagination info
        total_pages = (total_count + per_page - 1) // per_page
        pagination = (
            {
                "page": page,
                "pages": total_pages,
                "has_prev": page > 1,
                "has_next": page < total_pages,
                "prev_num": page - 1 if page > 1 else None,
                "next_num": page + 1 if page < total_pages else None,
            }
            if total_pages > 1
            else None
        )

        return templates.TemplateResponse(
            "schedules.html",
            {
                "request": request,
                "schedules": formatted_schedules,
                "stats": stats,
                "recent_executions": recent_executions,
                "pagination": pagination,
                "status": status,
                "schedule_type": schedule_type,
                "current_user": current_user,
            },
        )

    except Exception as e:
        logger.error(f"Schedules list error: {e!s}")
        return templates.TemplateResponse(
            "error.html", {"request": request, "error": "Failed to load schedules", "current_user": current_user}
        )


@router.get("/new", response_class=HTMLResponse)
async def new_schedule_form(request: Request, current_user: dict = Depends(get_current_user)):
    """New schedule form page."""
    try:
        # Get predefined conditions
        predefined_conditions = condition_service.get_predefined_conditions()

        return templates.TemplateResponse(
            "schedule_form.html",
            {
                "request": request,
                "action": "new",
                "schedule": None,
                "predefined_conditions": predefined_conditions,
                "current_user": current_user,
            },
        )

    except Exception as e:
        logger.error(f"New schedule form error: {e!s}")
        return templates.TemplateResponse(
            "error.html", {"request": request, "error": "Failed to load schedule form", "current_user": current_user}
        )


@router.post("/new")
async def new_schedule_submit(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    schedule_type: str = Form(...),
    message_template: str = Form(...),
    schedule_frequency: str = Form(...),
    schedule_hour: int = Form(9),
    schedule_minute: int = Form(0),
    conditions_type: str = Form("all_tenants"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Handle new schedule form submission."""
    try:
        # Build schedule configuration
        schedule_config = _build_schedule_config(
            schedule_frequency, schedule_hour, schedule_minute
        )

        # Build conditions
        conditions = _build_conditions(conditions_type)

        # Create schedule data
        schedule_data = {
            "name": name.strip(),
            "description": description.strip() if description else None,
            "schedule_type": schedule_type,
            "message_template": message_template,
            "conditions": conditions,
            "schedule_config": schedule_config,
        }

        # Create schedule
        schedule = await scheduler_service.create_schedule(schedule_data, db)

        logger.info(f"Created schedule: {schedule.name} (ID: {schedule.id})")

        return RedirectResponse(
            url="/schedules?success=schedule_created", status_code=302
        )

    except Exception as e:
        logger.error(f"Create schedule error: {e!s}")
        return RedirectResponse(
            url="/schedules/new?error=create_failed", status_code=302
        )


@router.get("/{schedule_id}/edit", response_class=HTMLResponse)
async def edit_schedule_form(
    schedule_id: int, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """Edit schedule form page."""
    try:
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            return RedirectResponse(
                url="/schedules?error=schedule_not_found", status_code=302
            )

        # Get predefined conditions
        predefined_conditions = condition_service.get_predefined_conditions()

        return templates.TemplateResponse(
            "schedule_form.html",
            {
                "request": request,
                "action": "edit",
                "schedule": schedule,
                "predefined_conditions": predefined_conditions,
                "current_user": current_user,
            },
        )

    except Exception as e:
        logger.error(f"Edit schedule form error: {e!s}")
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Failed to load schedule edit form", "current_user": current_user},
        )


@router.post("/{schedule_id}/edit")
async def edit_schedule_submit(
    schedule_id: int,
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    schedule_type: str = Form(...),
    message_template: str = Form(...),
    schedule_frequency: str = Form(...),
    schedule_hour: int = Form(9),
    schedule_minute: int = Form(0),
    conditions_type: str = Form("all_tenants"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Handle edit schedule form submission."""
    try:
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            return RedirectResponse(
                url="/schedules?error=schedule_not_found", status_code=302
            )

        # Build schedule configuration
        schedule_config = _build_schedule_config(
            schedule_frequency, schedule_hour, schedule_minute
        )

        # Build conditions
        conditions = _build_conditions(conditions_type)

        # Update schedule
        schedule.name = name.strip()
        schedule.description = description.strip() if description else None
        schedule.schedule_type = schedule_type
        schedule.message_template = message_template
        schedule.conditions = conditions
        schedule.schedule_config = schedule_config
        schedule.updated_at = datetime.utcnow()

        db.commit()

        # If schedule is active, reschedule the job
        if schedule.status == ScheduleStatus.ACTIVE:
            await scheduler_service._schedule_job(schedule)

        logger.info(f"Updated schedule: {schedule.name} (ID: {schedule.id})")

        return RedirectResponse(
            url="/schedules?success=schedule_updated", status_code=302
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Update schedule error: {e!s}")
        return RedirectResponse(
            url=f"/schedules/{schedule_id}/edit?error=update_failed", status_code=302
        )


@router.get("/{schedule_id}", response_class=HTMLResponse)
async def schedule_details(
    schedule_id: int, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """Schedule details page."""
    try:
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            return RedirectResponse(
                url="/schedules?error=schedule_not_found", status_code=302
            )

        # Format schedule for display
        status_value = (
            schedule.status.value
            if hasattr(schedule.status, "value")
            else schedule.status
        )
        formatted_schedule = {
            "id": schedule.id,
            "name": schedule.name,
            "description": getattr(schedule, "description", None),
            "schedule_type": schedule.schedule_type,
            "message_template": schedule.message_template,
            "status": status_value,
            "status_display": _get_schedule_status_display(schedule.status),
            "schedule_display": _format_schedule_display(
                _build_schedule_config_from_db(schedule)
            ),
            "conditions": schedule.conditions,
            "conditions_summary": condition_service._summarize_conditions(
                schedule.conditions or {}
            ),
            "next_run": schedule.next_run,
            "last_run": schedule.last_run,
            "execution_count": getattr(schedule, "execution_count", schedule.run_count)
            or 0,
            "success_count": schedule.success_count or 0,
            "failure_count": schedule.failure_count or 0,
            "created_at": schedule.created_at,
        }

        return templates.TemplateResponse(
            "schedule_details.html",
            {"request": request, "schedule": formatted_schedule, "current_user": current_user},
        )

    except Exception as e:
        logger.error(f"Schedule details error: {e!s}")
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Failed to load schedule details", "current_user": current_user},
        )


def _build_schedule_config(frequency: str, hour: int, minute: int) -> dict:
    """Build schedule configuration from form inputs."""
    if frequency == "daily":
        return {"type": "cron", "hour": hour, "minute": minute, "timezone": "UTC"}
    elif frequency == "weekly":
        return {
            "type": "cron",
            "day_of_week": 0,  # Monday
            "hour": hour,
            "minute": minute,
            "timezone": "UTC",
        }
    elif frequency == "monthly":
        return {
            "type": "cron",
            "day": 1,  # 1st of month
            "hour": hour,
            "minute": minute,
            "timezone": "UTC",
        }
    elif frequency == "hourly":
        return {"type": "interval", "hours": 1, "timezone": "UTC"}
    else:
        # Default to daily
        return {"type": "cron", "hour": hour, "minute": minute, "timezone": "UTC"}


def _build_conditions(conditions_type: str) -> dict:
    """Build conditions from form input."""
    predefined = condition_service.get_predefined_conditions()

    if conditions_type in predefined:
        return predefined[conditions_type]
    else:
        # Default to all tenants
        return predefined["all_tenants"]


async def _get_schedule_stats(db: Session) -> dict:
    """Get schedule statistics."""
    try:
        active_schedules = (
            db.query(Schedule).filter(Schedule.status == ScheduleStatus.ACTIVE).count()
        )

        paused_schedules = (
            db.query(Schedule).filter(Schedule.status == ScheduleStatus.PAUSED).count()
        )

        total_schedules = db.query(Schedule).count()

        # Calculate total executions using run_count field
        total_executions = sum(
            [
                getattr(schedule, "execution_count", schedule.run_count) or 0
                for schedule in db.query(Schedule).all()
            ]
        )

        return {
            "active_schedules": active_schedules,
            "paused_schedules": paused_schedules,
            "total_schedules": total_schedules,
            "total_executions": total_executions,
        }

    except Exception as e:
        logger.error(f"Error getting schedule stats: {e!s}")
        return {
            "active_schedules": 0,
            "paused_schedules": 0,
            "total_schedules": 0,
            "total_executions": 0,
        }


def _get_schedule_status_display(status) -> str:
    """Get display text for schedule status."""
    # Handle both enum and string values
    if hasattr(status, "value"):
        status_value = status.value
    else:
        status_value = status

    status_map = {
        "active": "Active",
        "paused": "Paused",
        "completed": "Completed",
        "disabled": "Disabled",
    }
    return status_map.get(status_value, "Unknown")


def _build_schedule_config_from_db(schedule) -> dict:
    """Build schedule config dictionary from database fields."""
    try:
        # Parse schedule_value from database (e.g., "09:00", "monday 10:00", "5 14:00")
        schedule_value = schedule.schedule_value or ""
        schedule_type = schedule.schedule_type or "daily"

        # Default config
        config = {"type": "cron", "hour": 9, "minute": 0, "timezone": "UTC"}

        # Parse based on schedule_type and schedule_value
        if schedule_type == "daily" and ":" in schedule_value:
            # Format: "09:00"
            parts = schedule_value.split(":")
            if len(parts) >= 2:
                config.update({"hour": int(parts[0]), "minute": int(parts[1])})
        elif schedule_type == "weekly" and " " in schedule_value:
            # Format: "monday 10:00"
            day_time = schedule_value.split(" ")
            if len(day_time) >= 2:
                day_name = day_time[0].lower()
                time_part = day_time[1]
                day_map = {
                    "monday": 0,
                    "tuesday": 1,
                    "wednesday": 2,
                    "thursday": 3,
                    "friday": 4,
                    "saturday": 5,
                    "sunday": 6,
                }
                if ":" in time_part:
                    hour, minute = time_part.split(":")
                    config.update(
                        {
                            "day_of_week": day_map.get(day_name, 0),
                            "hour": int(hour),
                            "minute": int(minute),
                        }
                    )
        elif schedule_type == "monthly" and " " in schedule_value:
            # Format: "5 14:00" (5th day at 2 PM)
            parts = schedule_value.split(" ")
            if len(parts) >= 2:
                day = int(parts[0])
                time_part = parts[1]
                if ":" in time_part:
                    hour, minute = time_part.split(":")
                    config.update(
                        {"day": day, "hour": int(hour), "minute": int(minute)}
                    )

        return config
    except Exception:
        # Fallback config
        return {"type": "cron", "hour": 9, "minute": 0, "timezone": "UTC"}


def _format_schedule_display(schedule_config: dict) -> str:
    """Format schedule configuration for display."""
    try:
        schedule_type = schedule_config.get("type", "")

        if schedule_type == "cron":
            hour = schedule_config.get("hour", 9)
            minute = schedule_config.get("minute", 0)
            day = schedule_config.get("day")
            month = schedule_config.get("month")
            day_of_week = schedule_config.get("day_of_week")

            time_str = f"{hour:02d}:{minute:02d}"

            if month and day:
                return f"Monthly on {day}th at {time_str}"
            elif day:
                return f"Monthly on {day}th at {time_str}"
            elif day_of_week is not None:
                days = [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                    "Sunday",
                ]
                day_name = days[day_of_week] if 0 <= day_of_week < 7 else "Monday"
                return f"Weekly on {day_name} at {time_str}"
            else:
                return f"Daily at {time_str}"

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
