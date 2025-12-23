"""
API Routes - FastAPI router modules.

Provides routers for:
- Sessions: Training session management
- WebSocket: Real-time monitoring
- Evaluation: Scoring and reports
- Playback: Session playback
- Config: System configuration
"""

from .config import router as config_router
from .evaluation import router as evaluation_router
from .playback import router as playback_router
from .sessions import router as sessions_router
from .websocket import router as websocket_router

__all__ = [
    "sessions_router",
    "websocket_router",
    "evaluation_router",
    "playback_router",
    "config_router",
]
