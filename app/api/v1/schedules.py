"""
Schedules API endpoints for managing automated message schedules.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.schedule import (
    Schedule,
    ScheduleCreate,
    ScheduleResponse,
    ScheduleStats,
    ScheduleStatus,
    ScheduleUpdate,
)
from app.services.condition_service import condition_service
from app.services.scheduler_service import scheduler_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats", response_model=ScheduleStats)
async def get_schedule_stats(
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """Get schedule statistics for dashboard."""
    try:
        active_schedules = (
            db.query(Schedule).filter(Schedule.status == ScheduleStatus.ACTIVE).count()
        )

        paused_schedules = (
            db.query(Schedule).filter(Schedule.status == ScheduleStatus.PAUSED).count()
        )

        total_schedules = db.query(Schedule).count()

        # Calculate total executions from all schedules
        total_executions = sum(
            [schedule.run_count or 0 for schedule in db.query(Schedule).all()]
        )

        return ScheduleStats(
            active_schedules=active_schedules,
            paused_schedules=paused_schedules,
            total_schedules=total_schedules,
            total_executions=total_executions,
        )

    except Exception as e:
        logger.error(f"Failed to get schedule stats: {e!s}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve schedule statistics"
        )


@router.get("/", response_model=list[ScheduleResponse])
async def get_schedules(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    schedule_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get list of schedules with filtering and pagination."""
    try:
        query = db.query(Schedule)

        # Status filter
        if status:
            if status == "active":
                query = query.filter(Schedule.status == ScheduleStatus.ACTIVE)
            elif status == "paused":
                query = query.filter(Schedule.status == ScheduleStatus.PAUSED)
            elif status == "disabled":
                query = query.filter(Schedule.status == ScheduleStatus.DISABLED)

        # Type filter
        if schedule_type:
            query = query.filter(Schedule.schedule_type == schedule_type)

        schedules = (
            query.order_by(desc(Schedule.created_at)).offset(skip).limit(limit).all()
        )
        return schedules

    except Exception as e:
        logger.error(f"Failed to get schedules: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to retrieve schedules")


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get single schedule by ID."""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.post("/", response_model=ScheduleResponse)
async def create_schedule(
    schedule_data: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create new automated schedule."""
    try:
        # Create schedule
        schedule = Schedule(
            name=schedule_data.name,
            message_template=schedule_data.message_template,
            schedule_type=schedule_data.schedule_type,
            schedule_value=schedule_data.schedule_value,
            conditions=schedule_data.conditions,
            target_tenant_types=schedule_data.target_tenant_types,
            status=schedule_data.status,
            created_at=datetime.utcnow(),
        )

        db.add(schedule)
        db.commit()
        db.refresh(schedule)

        logger.info(f"Created schedule: {schedule.name} (ID: {schedule.id})")
        return schedule

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create schedule: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to create schedule")


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    schedule_data: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update schedule configuration."""
    try:
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

        # Update fields
        update_data = schedule_data.dict(exclude_unset=True)

        # Validate schedule config if provided
        if "schedule_config" in update_data:
            _validate_schedule_config(update_data["schedule_config"])

        for field, value in update_data.items():
            setattr(schedule, field, value)

        schedule.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(schedule)

        # If schedule is active, reschedule the job
        if schedule.status == ScheduleStatus.ACTIVE:
            await scheduler_service._schedule_job(schedule)

        logger.info(f"Updated schedule: {schedule.name} (ID: {schedule.id})")
        return schedule

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update schedule {schedule_id}: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to update schedule")


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete schedule."""
    try:
        success = await scheduler_service.delete_schedule(schedule_id, db)
        if not success:
            raise HTTPException(status_code=404, detail="Schedule not found")

        logger.info(f"Deleted schedule ID: {schedule_id}")
        return {"message": "Schedule deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete schedule {schedule_id}: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to delete schedule")


@router.post("/{schedule_id}/pause")
async def pause_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Pause a schedule."""
    try:
        success = await scheduler_service.pause_schedule(schedule_id, db)
        if not success:
            raise HTTPException(status_code=404, detail="Schedule not found")

        logger.info(f"Paused schedule ID: {schedule_id}")
        return {"message": "Schedule paused successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause schedule {schedule_id}: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to pause schedule")


@router.post("/{schedule_id}/resume")
async def resume_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Resume a paused schedule."""
    try:
        success = await scheduler_service.resume_schedule(schedule_id, db)
        if not success:
            raise HTTPException(status_code=404, detail="Schedule not found")

        logger.info(f"Resumed schedule ID: {schedule_id}")
        return {"message": "Schedule resumed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume schedule {schedule_id}: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to resume schedule")


@router.post("/{schedule_id}/run")
async def run_schedule_now(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Run a schedule immediately."""
    try:
        result = await scheduler_service.run_schedule_now(schedule_id, db)

        if not result["success"]:
            raise HTTPException(
                status_code=400, detail=result.get("error", "Failed to run schedule")
            )

        # Get execution stats from schedule
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        execution_stats = schedule.last_execution_stats or {}

        return {
            "message": "Schedule executed successfully",
            "messages_sent": execution_stats.get("successful_sends", 0),
            "total_recipients": execution_stats.get("total_recipients", 0),
            "success_rate": execution_stats.get("success_rate", 0),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to run schedule {schedule_id}: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to run schedule")


@router.post("/pause-all")
async def pause_all_schedules(
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """Pause all active schedules."""
    try:
        active_schedules = (
            db.query(Schedule).filter(Schedule.status == ScheduleStatus.ACTIVE).all()
        )

        paused_count = 0
        for schedule in active_schedules:
            success = await scheduler_service.pause_schedule(schedule.id, db)
            if success:
                paused_count += 1

        logger.info(f"Paused {paused_count} schedules")
        return {"message": f"Paused {paused_count} schedules"}

    except Exception as e:
        logger.error(f"Failed to pause all schedules: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to pause all schedules")


@router.post("/resume-all")
async def resume_all_schedules(
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """Resume all paused schedules."""
    try:
        paused_schedules = (
            db.query(Schedule).filter(Schedule.status == ScheduleStatus.PAUSED).all()
        )

        resumed_count = 0
        for schedule in paused_schedules:
            success = await scheduler_service.resume_schedule(schedule.id, db)
            if success:
                resumed_count += 1

        logger.info(f"Resumed {resumed_count} schedules")
        return {"message": f"Resumed {resumed_count} schedules"}

    except Exception as e:
        logger.error(f"Failed to resume all schedules: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to resume all schedules")


@router.get("/{schedule_id}/job-status")
async def get_job_status(
    schedule_id: int, current_user: dict = Depends(get_current_user)
):
    """Get status of schedule's background job."""
    try:
        status = scheduler_service.get_job_status(schedule_id)
        if not status:
            raise HTTPException(
                status_code=404, detail="Job not found or schedule not active"
            )

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status for schedule {schedule_id}: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to get job status")


@router.get("/jobs/all")
async def get_all_jobs(current_user: dict = Depends(get_current_user)):
    """Get status of all scheduled jobs."""
    try:
        jobs = scheduler_service.get_all_jobs()
        return {"jobs": jobs}

    except Exception as e:
        logger.error(f"Failed to get all jobs: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to get all jobs")


@router.post("/test-conditions")
async def test_schedule_conditions(
    conditions: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Test schedule conditions and see which tenants would match."""
    try:
        result = await condition_service.test_conditions(conditions, db)
        return result

    except Exception as e:
        logger.error(f"Failed to test conditions: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to test conditions")


@router.get("/conditions/predefined")
async def get_predefined_conditions(current_user: dict = Depends(get_current_user)):
    """Get list of predefined condition sets."""
    try:
        conditions = condition_service.get_predefined_conditions()
        return {"predefined_conditions": conditions}

    except Exception as e:
        logger.error(f"Failed to get predefined conditions: {e!s}")
        raise HTTPException(
            status_code=500, detail="Failed to get predefined conditions"
        )


@router.get("/types/available")
async def get_available_schedule_types(current_user: dict = Depends(get_current_user)):
    """Get available schedule types and their descriptions."""
    return {
        "schedule_types": {
            "rent_reminder": {
                "name": "Rent Reminder",
                "description": "Automatic reminders for rent payments",
                "icon": "💰",
                "default_template": "rent_reminder",
            },
            "late_fee_notice": {
                "name": "Late Fee Notice",
                "description": "Notices for overdue rent and late fees",
                "icon": "⚠️",
                "default_template": "late_fee_notice",
            },
            "payment_confirmation": {
                "name": "Payment Confirmation",
                "description": "Confirmations for received payments",
                "icon": "✅",
                "default_template": "payment_received",
            },
            "maintenance_notice": {
                "name": "Maintenance Notice",
                "description": "Notifications for scheduled maintenance",
                "icon": "🔧",
                "default_template": "maintenance_notice",
            },
            "custom": {
                "name": "Custom Message",
                "description": "Custom message with your own content",
                "icon": "📝",
                "default_template": "custom",
            },
        }
    }


@router.get("/executions/recent")
async def get_recent_executions(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get recent schedule executions."""
    try:
        # Get schedules with recent executions
        schedules = (
            db.query(Schedule)
            .filter(Schedule.last_execution_stats.isnot(None))
            .order_by(desc(Schedule.last_run))
            .limit(limit)
            .all()
        )

        executions = []
        for schedule in schedules:
            stats = schedule.last_execution_stats or {}
            if schedule.last_run:
                executions.append(
                    {
                        "id": f"exec_{schedule.id}_{schedule.execution_count}",
                        "schedule_id": schedule.id,
                        "schedule_name": schedule.name,
                        "executed_at": schedule.last_run.isoformat(),
                        "total_recipients": stats.get("total_recipients", 0),
                        "successful_sends": stats.get("successful_sends", 0),
                        "failed_sends": stats.get("failed_sends", 0),
                        "success_rate": stats.get("success_rate", 0),
                        "conditions": schedule.conditions,
                    }
                )

        return {"executions": executions}

    except Exception as e:
        logger.error(f"Failed to get recent executions: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to get recent executions")


@router.get("/executions/{execution_id}")
async def get_execution_details(
    execution_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get detailed execution information."""
    try:
        # Parse execution ID (format: exec_{schedule_id}_{execution_count})
        parts = execution_id.split("_")
        if len(parts) != 3 or parts[0] != "exec":
            raise HTTPException(status_code=400, detail="Invalid execution ID format")

        schedule_id = int(parts[1])
        # execution_count = int(parts[2])  # Unused for now

        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

        # Use basic stats from schedule model
        stats = {
            "total_recipients": 0,
            "successful_sends": schedule.success_count,
            "failed_sends": schedule.failure_count,
            "success_rate": 0,
        }

        return {
            "data": {
                "id": execution_id,
                "schedule_id": schedule_id,
                "schedule_name": schedule.name,
                "executed_at": (
                    schedule.last_run.isoformat() if schedule.last_run else None
                ),
                "total_recipients": stats.get("total_recipients", 0),
                "successful_sends": stats.get("successful_sends", 0),
                "failed_sends": stats.get("failed_sends", 0),
                "success_rate": stats.get("success_rate", 0),
                "conditions": schedule.conditions,
                "message_template": schedule.message_template,
                "schedule_type": schedule.schedule_type,
                "schedule_value": schedule.schedule_value,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution details: {e!s}")
        raise HTTPException(status_code=500, detail="Failed to get execution details")


# Helper functions are simplified for now
