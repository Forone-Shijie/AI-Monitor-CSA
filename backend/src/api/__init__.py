"""
API Module - FastAPI backend for CC-SOP Monitor.

This module provides:

Application:
    - create_app: FastAPI application factory
    - app: Application instance

Routers:
    - api_router: Main API router
    - sessions_router: Session management
    - evaluation_router: Evaluation and reports
    - playback_router: Session playback
    - config_router: System configuration
    - websocket_router: Real-time WebSocket

Session Management:
    - SessionManager: Session lifecycle management
    - session_manager: Global session manager instance

Usage:
    # Run with uvicorn
    uvicorn src.api:app --reload

    # Or programmatically
    from src.api import create_app
    app = create_app()
"""

from .app import app, create_app
from .router import api_router, get_api_router
from .session_manager import SessionData, SessionManager, session_manager

__all__ = [
    # Application
    "app",
    "create_app",
    # Router
    "api_router",
    "get_api_router",
    # Session Management
    "SessionManager",
    "SessionData",
    "session_manager",
]
