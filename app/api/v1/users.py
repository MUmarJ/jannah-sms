"""
User management API endpoints.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import UserDB

logger = logging.getLogger(__name__)
router = APIRouter()


def check_admin_access(current_user: dict, db: Session) -> UserDB:
    """Check if current user is admin."""
    user = db.query(UserDB).filter(UserDB.id == current_user["user_id"]).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.post("/{user_id}/approve")
async def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Approve a pending user (admin only)."""
    check_admin_access(current_user, db)

    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    user.pending_approval = False
    db.commit()

    logger.info(f"User {user.username} approved by {current_user['username']}")
    return {"message": "User approved successfully"}


@router.post("/{user_id}/disable")
async def disable_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Disable a user (admin only)."""
    check_admin_access(current_user, db)

    if user_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot disable yourself")

    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    db.commit()

    logger.info(f"User {user.username} disabled by {current_user['username']}")
    return {"message": "User disabled successfully"}


@router.post("/{user_id}/enable")
async def enable_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Enable a user (admin only)."""
    check_admin_access(current_user, db)

    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    user.pending_approval = False
    db.commit()

    logger.info(f"User {user.username} enabled by {current_user['username']}")
    return {"message": "User enabled successfully"}


@router.post("/{user_id}/make-admin")
async def make_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Grant admin privileges to a user (admin only)."""
    check_admin_access(current_user, db)

    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_admin = True
    db.commit()

    logger.info(f"User {user.username} promoted to admin by {current_user['username']}")
    return {"message": "User promoted to admin successfully"}


@router.post("/{user_id}/revoke-admin")
async def revoke_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Revoke admin privileges from a user (admin only)."""
    check_admin_access(current_user, db)

    if user_id == current_user["user_id"]:
        raise HTTPException(
            status_code=400, detail="Cannot revoke your own admin privileges"
        )

    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_admin = False
    db.commit()

    logger.info(
        f"Admin privileges revoked from {user.username} by {current_user['username']}"
    )
    return {"message": "Admin privileges revoked successfully"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a user (admin only)."""
    check_admin_access(current_user, db)

    if user_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    username = user.username
    db.delete(user)
    db.commit()

    logger.info(f"User {username} deleted by {current_user['username']}")
    return {"message": "User deleted successfully"}
