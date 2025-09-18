"""
Web interface routes for elderly-friendly UI.
"""

from fastapi import APIRouter
from app.web import dashboard, messages, tenants, schedules

# Create web router
web_router = APIRouter()

# Include all web interface routes
web_router.include_router(dashboard.router)
web_router.include_router(messages.router, prefix="/messages")
web_router.include_router(tenants.router, prefix="/tenants") 
web_router.include_router(schedules.router, prefix="/schedules")