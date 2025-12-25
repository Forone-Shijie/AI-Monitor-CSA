"""
FastAPI Application - Main application factory.

Creates and configures the FastAPI application with:
- CORS middleware
- API routes
- WebSocket endpoints
- Documentation
"""

from pathlib import Path

from dotenv import load_dotenv

# Load .env before any other imports that might need env vars
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Initialize logging
from src.utils.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router import api_router
from .session_manager import session_manager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan handler."""
    # Startup
    logger.info("CC-SOP Monitor API starting...")
    yield
    # Shutdown
    logger.info("CC-SOP Monitor API shutting down...")
    session_manager.clear_all()


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="CC-SOP Monitor API",
        description="""
        客舱乘务员姿态与操作规范监测系统 API

        ## 功能模块

        * **Sessions** - 训练会话管理
        * **Evaluation** - 评估与报告
        * **Playback** - 会话回放
        * **Config** - 系统配置
        * **WebSocket** - 实时监控

        ## 认证

        当前版本不需要认证。生产环境请添加适当的认证机制。
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify actual origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(api_router, prefix="/api")

    # Add root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """API root endpoint."""
        return {
            "name": "CC-SOP Monitor API",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
        }

    # Add health check
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "sessions": session_manager.session_count,
            "active_session": session_manager.active_session_id,
        }

    return app


# Create application instance
app = create_app()
