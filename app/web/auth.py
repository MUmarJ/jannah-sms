"""
Web authentication routes for login/logout.
Provides elderly-friendly login interface.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.core.templates import templates
from app.models.user import UserDB

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display login page."""
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "company_name": settings.company_name,
            "app_version": "2.0.0",
            "error": request.query_params.get("error"),
        },
    )


@limiter.limit("5/minute")
@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember_me: bool = Form(False),
    db: Session = Depends(get_db),
):
    """Handle login form submission."""
    # Find user by username
    user = db.query(UserDB).filter(UserDB.username == username).first()

    # Verify credentials
    if not user or not verify_password(password, user.hashed_password):
        return RedirectResponse(
            url="/login?error=Invalid username or password", status_code=302
        )

    # Check if user is active
    if not user.is_active:
        # Check if pending approval
        if user.pending_approval:
            return RedirectResponse(
                url="/login?error=Your account is pending approval. Please contact an administrator.",
                status_code=302,
            )
        else:
            return RedirectResponse(
                url="/login?error=Your account has been disabled. Please contact an administrator.",
                status_code=302,
            )

    # Update login tracking
    user.last_login = datetime.utcnow()
    user.login_count = (user.login_count or 0) + 1
    db.commit()

    # Create token with appropriate expiration
    expires_delta = timedelta(days=30) if remember_me else timedelta(minutes=60)
    token = create_access_token(
        data={"sub": username, "user_id": user.id}, expires_delta=expires_delta
    )

    # Set cookie and redirect to dashboard
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=int(expires_delta.total_seconds()),
    )

    return response


@router.get("/logout")
async def logout():
    """Logout and redirect to login."""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key=settings.session_cookie_name)
    return response
