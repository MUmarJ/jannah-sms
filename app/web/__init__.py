"""
Web interface routes for elderly-friendly UI.
"""

from fastapi import APIRouter

from app.web import auth, dashboard, messages, schedules, tenants, users

# Create web router
web_router = APIRouter()

# Include authentication routes (no prefix)
web_router.include_router(auth.router, tags=["auth-web"])

# Include all web interface routes
web_router.include_router(dashboard.router)
web_router.include_router(messages.router, prefix="/messages")
web_router.include_router(tenants.router, prefix="/tenants")
web_router.include_router(schedules.router, prefix="/schedules")
web_router.include_router(users.router, prefix="/users")
