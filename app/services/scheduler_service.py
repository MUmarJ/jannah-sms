"""
Scheduler Service for managing automated message schedules.
Uses APScheduler for background job scheduling with conditional execution.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.message import Message, MessageStatus
from app.models.schedule import Schedule, ScheduleStatus
from app.models.tenant import Tenant
from app.services.condition_service import condition_service
from app.services.sms_service import sms_service

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Service for managing scheduled SMS messages with conditional logic.
    Integrates APScheduler with database and SMS service.
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.jobs: dict[str, Job] = {}

    async def start(self) -> None:
        """Start the scheduler service."""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("Scheduler service started")

            # Load and schedule existing active schedules
            await self._load_existing_schedules()

    async def stop(self) -> None:
        """Stop the scheduler service."""
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            self.jobs.clear()
            logger.info("Scheduler service stopped")

    async def _load_existing_schedules(self) -> None:
        """Load and schedule all active schedules from database."""
        try:
            with SessionLocal() as db:
                active_schedules = (
                    db.query(Schedule)
                    .filter(Schedule.status == ScheduleStatus.ACTIVE)
                    .all()
                )

                for schedule in active_schedules:
                    await self._schedule_job(schedule)

                logger.info(f"Loaded {len(active_schedules)} active schedules")

        except Exception as e:
            logger.error(f"Failed to load existing schedules: {e!s}")

    async def create_schedule(
        self, schedule_data: dict[str, Any], db: Session
    ) -> Schedule:
        """
        Create a new schedule and add it to the scheduler.

        Args:
            schedule_data: Schedule configuration
            db: Database session

        Returns:
            Created Schedule object
        """
        try:
            # Create schedule in database
            schedule = Schedule(
                name=schedule_data["name"],
                description=schedule_data.get("description"),
                schedule_type=schedule_data["schedule_type"],
                message_template=schedule_data["message_template"],
                conditions=schedule_data.get("conditions", {}),
                schedule_config=schedule_data["schedule_config"],
                status=ScheduleStatus.ACTIVE,
                created_at=datetime.utcnow(),
            )

            db.add(schedule)
            db.commit()
            db.refresh(schedule)

            # Schedule the job
            await self._schedule_job(schedule)

            logger.info(f"Created and scheduled: {schedule.name} (ID: {schedule.id})")
            return schedule

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create schedule: {e!s}")
            raise

    async def _schedule_job(self, schedule: Schedule) -> None:
        """
        Add a schedule to APScheduler.

        Args:
            schedule: Schedule to add
        """
        try:
            job_id = f"schedule_{schedule.id}"

            # Parse schedule configuration
            config = schedule.schedule_config
            trigger = self._create_trigger(config)

            # Schedule the job
            job = self.scheduler.add_job(
                func=self._execute_schedule,
                trigger=trigger,
                args=[schedule.id],
                id=job_id,
                name=schedule.name,
                replace_existing=True,
                misfire_grace_time=300,  # 5 minutes grace period
            )

            self.jobs[job_id] = job

            # Update next run time in database
            if job.next_run_time:
                with SessionLocal() as db:
                    db_schedule = (
                        db.query(Schedule).filter(Schedule.id == schedule.id).first()
                    )
                    if db_schedule:
                        db_schedule.next_run = job.next_run_time
                        db.commit()

            logger.info(
                f"Scheduled job: {schedule.name} - Next run: {job.next_run_time}"
            )

        except Exception as e:
            logger.error(f"Failed to schedule job for {schedule.name}: {e!s}")
            raise

    def _create_trigger(self, config: dict[str, Any]):
        """
        Create APScheduler trigger from configuration.

        Args:
            config: Schedule configuration

        Returns:
            APScheduler trigger object
        """
        schedule_type = config.get("type")

        if schedule_type == "cron":
            return CronTrigger(
                year=config.get("year"),
                month=config.get("month"),
                day=config.get("day"),
                week=config.get("week"),
                day_of_week=config.get("day_of_week"),
                hour=config.get("hour", 9),
                minute=config.get("minute", 0),
                second=config.get("second", 0),
                timezone=config.get("timezone", "UTC"),
            )
        elif schedule_type == "interval":
            return IntervalTrigger(
                weeks=config.get("weeks"),
                days=config.get("days"),
                hours=config.get("hours"),
                minutes=config.get("minutes"),
                seconds=config.get("seconds"),
                start_date=config.get("start_date"),
                end_date=config.get("end_date"),
                timezone=config.get("timezone", "UTC"),
            )
        elif schedule_type == "date":
            return DateTrigger(
                run_date=config.get("run_date"), timezone=config.get("timezone", "UTC")
            )
        else:
            raise ValueError(f"Unsupported schedule type: {schedule_type}")

    async def _execute_schedule(self, schedule_id: int) -> None:
        """
        Execute a scheduled job.

        Args:
            schedule_id: ID of schedule to execute
        """
        execution_start = datetime.utcnow()

        try:
            with SessionLocal() as db:
                # Get schedule
                schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
                if not schedule or schedule.status != ScheduleStatus.ACTIVE:
                    logger.warning(f"Schedule {schedule_id} not found or not active")
                    return

                logger.info(f"Executing schedule: {schedule.name}")

                # Get eligible tenants based on conditions
                eligible_tenants = await condition_service.get_eligible_tenants(
                    schedule.conditions, db
                )

                if not eligible_tenants:
                    logger.info(f"No eligible tenants for schedule: {schedule.name}")
                    # Still create execution record
                    self._create_execution_record(
                        schedule, 0, 0, 0, execution_start, db
                    )
                    return

                logger.info(f"Found {len(eligible_tenants)} eligible tenants")

                # Send messages with dynamic rent day
                rent_day = (
                    int(schedule.schedule_value) if schedule.schedule_value else 5
                )
                result = await sms_service.send_bulk_sms(
                    tenants=eligible_tenants,
                    message=schedule.message_template,  # Use actual message template
                    template_name=None,  # Don't use predefined template
                    test_mode=schedule.schedule_config.get("test_mode", False),
                    rent_day=rent_day,  # Pass rent day for dynamic replacement
                )

                # Create message records
                await self._create_message_records(
                    schedule, eligible_tenants, result, db
                )

                # Create execution record
                self._create_execution_record(
                    schedule,
                    len(eligible_tenants),
                    result["successful_sends"],
                    result["failed_sends"],
                    execution_start,
                    db,
                )

                # Update schedule last run time
                schedule.last_run = execution_start
                db.commit()

                logger.info(
                    f"Schedule execution completed: {schedule.name} - "
                    f"{result['successful_sends']}/{len(eligible_tenants)} successful"
                )

        except Exception as e:
            logger.error(f"Failed to execute schedule {schedule_id}: {e!s}")
            # TODO: Create error execution record

    async def _create_message_records(
        self,
        schedule: Schedule,
        tenants: list[Tenant],
        sms_result: dict[str, Any],
        db: Session,
    ) -> None:
        """Create message records for scheduled execution."""
        try:
            for result in sms_result["results"]:
                message = Message(
                    tenant_id=result["tenant_id"],
                    content=result.get("content", ""),
                    status=(
                        MessageStatus.SENT
                        if result["success"]
                        else MessageStatus.FAILED
                    ),
                    scheduled_for=schedule.last_run,
                    sent_at=datetime.utcnow() if result["success"] else None,
                    schedule_id=schedule.id,
                    message_id=result.get("message_id"),
                    error_message=result.get("error"),
                    conditions_met=schedule.conditions,
                    test_mode=sms_result.get("test_mode", False),
                )
                db.add(message)

            db.commit()

        except Exception as e:
            logger.error(f"Failed to create message records: {e!s}")
            db.rollback()

    def _create_execution_record(
        self,
        schedule: Schedule,
        total_recipients: int,
        successful_sends: int,
        failed_sends: int,
        execution_time: datetime,
        db: Session,
    ) -> None:
        """Create execution record for schedule run."""
        # For now, we'll update the schedule record
        # In a more complex system, you might have a separate executions table
        schedule.execution_count = (schedule.execution_count or 0) + 1
        schedule.last_execution_stats = {
            "total_recipients": total_recipients,
            "successful_sends": successful_sends,
            "failed_sends": failed_sends,
            "success_rate": (
                (successful_sends / total_recipients * 100)
                if total_recipients > 0
                else 0
            ),
            "executed_at": execution_time.isoformat(),
        }
        db.commit()

    async def pause_schedule(self, schedule_id: int, db: Session) -> bool:
        """
        Pause a schedule.

        Args:
            schedule_id: Schedule ID to pause
            db: Database session

        Returns:
            Success status
        """
        try:
            # Update database
            schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
            if not schedule:
                return False

            schedule.status = ScheduleStatus.PAUSED
            db.commit()

            # Remove from scheduler
            job_id = f"schedule_{schedule_id}"
            if job_id in self.jobs:
                self.jobs[job_id].remove()
                del self.jobs[job_id]
                logger.info(f"Paused schedule: {schedule.name}")

            return True

        except Exception as e:
            logger.error(f"Failed to pause schedule {schedule_id}: {e!s}")
            return False

    async def resume_schedule(self, schedule_id: int, db: Session) -> bool:
        """
        Resume a paused schedule.

        Args:
            schedule_id: Schedule ID to resume
            db: Database session

        Returns:
            Success status
        """
        try:
            # Update database
            schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
            if not schedule:
                return False

            schedule.status = ScheduleStatus.ACTIVE
            db.commit()

            # Re-schedule job
            await self._schedule_job(schedule)
            logger.info(f"Resumed schedule: {schedule.name}")

            return True

        except Exception as e:
            logger.error(f"Failed to resume schedule {schedule_id}: {e!s}")
            return False

    async def delete_schedule(self, schedule_id: int, db: Session) -> bool:
        """
        Delete a schedule.

        Args:
            schedule_id: Schedule ID to delete
            db: Database session

        Returns:
            Success status
        """
        try:
            # Remove from scheduler
            job_id = f"schedule_{schedule_id}"
            if job_id in self.jobs:
                self.jobs[job_id].remove()
                del self.jobs[job_id]

            # Delete from database
            schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
            if schedule:
                db.delete(schedule)
                db.commit()
                logger.info(f"Deleted schedule: {schedule.name}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete schedule {schedule_id}: {e!s}")
            return False

    async def run_schedule_now(self, schedule_id: int, db: Session) -> dict[str, Any]:
        """
        Run a schedule immediately.

        Args:
            schedule_id: Schedule ID to run
            db: Database session

        Returns:
            Execution result
        """
        try:
            schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
            if not schedule:
                return {"success": False, "error": "Schedule not found"}

            # Execute the schedule
            await self._execute_schedule(schedule_id)

            return {
                "success": True,
                "message": f"Schedule '{schedule.name}' executed successfully",
            }

        except Exception as e:
            error_msg = f"Failed to run schedule {schedule_id}: {e!s}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def get_job_status(self, schedule_id: int) -> Optional[dict[str, Any]]:
        """
        Get status of a scheduled job.

        Args:
            schedule_id: Schedule ID

        Returns:
            Job status info or None if not found
        """
        job_id = f"schedule_{schedule_id}"
        if job_id in self.jobs:
            job = self.jobs[job_id]
            return {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time,
                "trigger": str(job.trigger),
                "pending": job.pending,
            }
        return None

    def get_all_jobs(self) -> list[dict[str, Any]]:
        """
        Get status of all scheduled jobs.

        Returns:
            List of job status info
        """
        jobs_info = []
        for job in self.scheduler.get_jobs():
            jobs_info.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time,
                    "trigger": str(job.trigger),
                    "pending": job.pending,
                }
            )
        return jobs_info


# Global scheduler service instance
scheduler_service = SchedulerService()
