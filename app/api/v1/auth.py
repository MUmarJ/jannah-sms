"""
Authentication API endpoints.
Provides login, logout, register, and user management endpoints.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    SessionManager,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.models.user import (
    UserCreate,
    UserDB,
    UserLogin,
    UserLoginResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/login", response_model=UserLoginResponse)
async def login(
    user_login: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Authenticate user and return access token.
    Sets session cookie for web interface.
    """
    try:
        # Find user by username
        user = db.query(UserDB).filter(UserDB.username == user_login.username).first()

        if not user or not verify_password(user_login.password, user.hashed_password):
            logger.warning(f"Failed login attempt for username: {user_login.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )

        # Update login tracking
        user.last_login = datetime.utcnow()
        user.login_count += 1
        db.commit()

        # Create access token
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
        if user_login.remember_me:
            expires_delta = timedelta(days=30)  # 30 days for "remember me"

        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.id}, expires_delta=expires_delta
        )

        # Set session cookie for web interface
        response.set_cookie(
            key=settings.session_cookie_name,
            value=access_token,
            httponly=True,  # Prevent XSS
            secure=settings.is_production,  # HTTPS only in production
            samesite="lax",  # CSRF protection
            max_age=int(expires_delta.total_seconds()),
        )

        logger.info(f"Successful login for user: {user.username}")

        return UserLoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=int(expires_delta.total_seconds()),
            user=UserResponse.from_orm(user),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to server error",
        )


@router.post("/logout")
async def logout(response: Response):
    """
    Logout user by clearing session cookie.
    """
    response.delete_cookie(key=settings.session_cookie_name)
    return {"message": "Logged out successfully"}


@router.post("/register", response_model=UserResponse)
async def register(
    user_create: UserCreate,
    db: Session = Depends(get_db),
):
    """
    Register a new user.
    Note: In production, you may want to restrict this or require admin approval.
    """
    try:
        # Check if username already exists
        existing_user = (
            db.query(UserDB).filter(UserDB.username == user_create.username).first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered",
            )

        # Check if email already exists
        if user_create.email:
            existing_email = (
                db.query(UserDB).filter(UserDB.email == user_create.email).first()
            )
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )

        # Check if this is the first user (make them admin)
        user_count = db.query(UserDB).count()
        is_first_user = user_count == 0

        # Create new user
        new_user = UserDB(
            username=user_create.username,
            email=user_create.email,
            full_name=user_create.full_name,
            hashed_password=get_password_hash(user_create.password),
            is_active=True,
            is_admin=is_first_user,  # First user is admin
            ui_large_text=user_create.ui_large_text,
            ui_high_contrast=user_create.ui_high_contrast,
            ui_simple_mode=user_create.ui_simple_mode,
            created_at=datetime.utcnow(),
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(
            f"New user registered: {new_user.username} "
            f"(admin={is_first_user}, first_user={is_first_user})"
        )

        return UserResponse.from_orm(new_user)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to server error",
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get current authenticated user's information.
    """
    username = current_user.get("username")
    user = db.query(UserDB).filter(UserDB.username == username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.from_orm(user)


@router.get("/check-setup")
async def check_auth_setup(db: Session = Depends(get_db)):
    """
    Check if authentication is set up (i.e., if any users exist).
    Used to determine if initial setup is needed.
    """
    user_count = db.query(UserDB).count()
    return {
        "setup_required": user_count == 0,
        "user_count": user_count,
        "message": (
            "No users found. Please create an admin account."
            if user_count == 0
            else "Authentication is configured."
        ),
    }
