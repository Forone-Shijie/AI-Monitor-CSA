"""
Main API Router - Combines all route modules.

Provides the main FastAPI router with all API endpoints.
"""

from fastapi import APIRouter

from .routes import (
    config_router,
    evaluation_router,
    playback_router,
    sessions_router,
    websocket_router,
)

# Create main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(sessions_router)
api_router.include_router(evaluation_router)
api_router.include_router(playback_router)
api_router.include_router(config_router)
api_router.include_router(websocket_router)


def get_api_router() -> APIRouter:
    """Get the main API router."""
    return api_router
