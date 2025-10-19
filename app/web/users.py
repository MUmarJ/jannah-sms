"""
Users web interface routes.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.templates import templates
from app.models.user import UserDB

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def users_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Users list page (admin only)."""
    # Check if current user is admin
    user = db.query(UserDB).filter(UserDB.id == current_user["user_id"]).first()
    if not user or not user.is_admin:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "current_user": current_user,
                "error_code": 403,
                "error_message": "Access Denied",
                "error_details": "You must be an administrator to access this page.",
            },
            status_code=403,
        )

    try:
        # Get all users
        users = db.query(UserDB).order_by(UserDB.created_at.desc()).all()

        # Calculate stats
        total_users = len(users)
        active_users = sum(1 for u in users if u.is_active)
        pending_users = sum(1 for u in users if u.pending_approval and not u.is_active)

        stats = {
            "total_users": total_users,
            "active_users": active_users,
            "pending_users": pending_users,
        }

        return templates.TemplateResponse(
            "users.html",
            {
                "request": request,
                "current_user": current_user,
                "users": users,
                "stats": stats,
            },
        )

    except Exception as e:
        logger.error(f"Error loading users: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "current_user": current_user,
                "error_code": 500,
                "error_message": "Error Loading Users",
                "error_details": str(e),
            },
            status_code=500,
        )
