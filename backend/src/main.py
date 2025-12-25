"""
CC-SOP Monitor Backend Entry Point

Cabin Crew Standard Operating Procedure Monitor - AI Training Evaluation System
For China Southern Airlines
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

import uvicorn

# Import the configured FastAPI application from api module
from src.api.app import app


# === Run Application ===
def main() -> None:
    """Run the FastAPI application with uvicorn."""
    print("=" * 60)
    print("CC-SOP Monitor Backend Starting...")
    print("=" * 60)
    print("API Documentation: http://localhost:8000/docs")
    print("ReDoc: http://localhost:8000/redoc")
    print("=" * 60)

    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()


# Export app for direct uvicorn usage: uvicorn src.main:app
__all__ = ["app", "main"]
