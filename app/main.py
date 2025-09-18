"""
Main FastAPI application entry point.
Jannah SMS Admin - Modern SMS scheduling system for property management.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

from app.core.config import settings
from app.core.database import init_db
from app.core.templates import templates
from app.services.scheduler_service import scheduler_service
from app.services.sms_service import sms_service


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

    # Root route - redirect to dashboard
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def root(request: Request):
        """Root endpoint - redirect to dashboard."""
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/dashboard", status_code=302)

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
