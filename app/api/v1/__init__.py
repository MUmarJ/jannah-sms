"""
API v1 routes - Main router configuration.
"""

from fastapi import APIRouter

from app.api.v1 import messages, schedules, tenants, webhooks

# Create API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(messages.router, prefix="/messages", tags=["messages"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
