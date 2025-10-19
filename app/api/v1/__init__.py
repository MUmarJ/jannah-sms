"""
API v1 routes - Main router configuration.
"""

from fastapi import APIRouter

from app.api.v1 import auth, messages, schedules, tenants, users, webhooks

# Create API router
api_router = APIRouter()

# Include auth routes (public endpoints)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Include all route modules
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(messages.router, prefix="/messages", tags=["messages"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
