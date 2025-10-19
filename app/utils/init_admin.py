"""
Admin user initialization utility.
Creates default admin user on first startup.
"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.user import UserDB

logger = logging.getLogger(__name__)


def create_admin_user(
    db: Session,
    username: str,
    password: str,
    email: str,
    full_name: str = "Administrator",
) -> UserDB:
    """
    Create admin user if not exists.

    Args:
        db: Database session
        username: Admin username
        password: Admin password (will be hashed, auto-truncated to 72 bytes for bcrypt)
        email: Admin email
        full_name: Full name for admin user

    Returns:
        UserDB: Created or existing admin user
    """
    # Check if user already exists
    existing = db.query(UserDB).filter(UserDB.username == username).first()
    if existing:
        logger.info(f"Admin user '{username}' already exists")
        return existing

    # Truncate password to 72 bytes (bcrypt limit)
    password = password[:72]

    # Create new admin user
    admin = UserDB(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=get_password_hash(password),
        is_active=True,
        is_admin=True,
        created_at=datetime.utcnow(),
        login_count=0,
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    logger.info(f"✅ Created admin user: {username}")
    return admin
