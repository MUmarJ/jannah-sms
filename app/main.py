"""
Main FastAPI application entry point.
Jannah SMS Admin - Modern SMS scheduling system for property management.
"""

from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.database import init_db
from app.core.templates import templates
from app.services.scheduler_service import scheduler_service


# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle application startup and shutdown.
    Manages database initialization and scheduler lifecycle.
    """
    # Startup
    print(f"🚀 Starting {settings.app_name}...")
    print(f"📊 Debug mode: {settings.debug}")

    # Initialize database
    init_db()

    # Check for admin user and create if needed
    from app.core.database import SessionLocal
    from app.models.user import UserDB

    db = SessionLocal()
    try:
        user_count = db.query(UserDB).count()

        if user_count == 0:
            print("⚠️  NO USERS FOUND!")
            if settings.admin_password != "changeme":
                from app.utils.init_admin import create_admin_user

                create_admin_user(
                    db,
                    settings.admin_username,
                    settings.admin_password,
                    settings.admin_email,
                )
                print("✅ Admin user created from environment variables")
            else:
                print("🔧 Set ADMIN_PASSWORD in environment to auto-create admin")
        else:
            print(f"👤 Found {user_count} user(s) in database")
    except Exception as e:
        print(f"⚠️  Warning: Error checking/creating admin user: {e}")
    finally:
        db.close()

    # Start scheduler service
    try:
        await scheduler_service.start()
        print("⏰ Scheduler service started successfully")
    except Exception as e:
        print(f"⚠️  Warning: Failed to start scheduler service: {e}")

    print("✅ Application startup complete")

    yield

    # Shutdown
    print("🛑 Shutting down application...")

    # Stop scheduler service
    try:
        await scheduler_service.stop()
        print("⏰ Scheduler service stopped")
    except Exception as e:
        print(f"⚠️  Warning: Error stopping scheduler service: {e}")

    print("✅ Application shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    Returns configured FastAPI instance.
    """

    # Create FastAPI application
    app = FastAPI(
        title=settings.app_name,
        description="Modern SMS scheduling system for property management with elderly-friendly interface",
        version="2.0.0",
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Rate limiting setup
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Security middleware
    if not settings.debug:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["localhost", "127.0.0.1", "*.jannah-sms.com"],
        )

    # CORS middleware for development
    if settings.debug:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        """Add security headers to all responses."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    # Mount static files
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    # Add custom template functions for elderly-friendly UI
    def format_datetime(dt, format_str="%B %d, %Y at %I:%M %p"):
        """Format datetime for elderly-friendly display."""
        if dt:
            return dt.strftime(format_str)
        return "Not available"

    def format_phone(phone):
        """Format phone number for display."""
        if phone:
            cleaned = "".join(filter(str.isdigit, phone))
            if len(cleaned) == 10:
                return f"({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"
            elif len(cleaned) == 11 and cleaned[0] == "1":
                return f"+1 ({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:]}"
        return phone

    def format_12hour(hour):
        """Format hour in 12-hour format for display."""
        if hour == 0:
            return "12:00 AM"
        elif hour < 12:
            return f"{hour}:00 AM"
        elif hour == 12:
            return "12:00 PM"
        else:
            return f"{hour-12}:00 PM"

    # Add functions to Jinja2 environment
    templates.env.filters["format_datetime"] = format_datetime
    templates.env.filters["format_phone"] = format_phone
    templates.env.filters["format_12hour"] = format_12hour
    templates.env.globals.update(
        {
            "settings": settings,
            "app_name": settings.app_name,
            "company_name": settings.company_name,
            "today": datetime.utcnow().date().isoformat(),
        }
    )

    # Root route - check auth and redirect
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def root(request: Request):
        """Root endpoint - check auth and redirect."""
        from fastapi.responses import RedirectResponse

        from app.core.security import verify_token

        # Check if user is authenticated
        session_token = request.cookies.get(settings.session_cookie_name)
        if session_token:
            user = verify_token(session_token)
            if user:
                return RedirectResponse(url="/dashboard", status_code=302)

        # Not authenticated, redirect to login
        return RedirectResponse(url="/login", status_code=302)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Simple health check endpoint."""
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": "2.0.0",
            "database": "connected",
        }

    # Include API routers
    from app.api.v1 import api_router

    app.include_router(api_router, prefix="/api/v1")

    # Include web interface routers
    from app.web import web_router

    app.include_router(web_router)

    return app


# Create application instance
app = create_app()


# Development server
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
