"""
Logging configuration for CC-SOP Monitor.

Configures logging to output to both console and file with rotation.
"""

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(
    log_dir: Path = None,
    log_level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> Path:
    """
    Configure logging for the application.

    Args:
        log_dir: Directory to store log files
        log_level: Logging level
        max_bytes: Max size per log file before rotation
        backup_count: Number of backup files to keep

    Returns:
        Path to the current log file
    """
    if log_dir is None:
        log_dir = Path(__file__).parent.parent.parent / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)

    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"backend_{timestamp}.log"

    # Also maintain a 'latest.log' symlink/copy for easy access
    latest_log = log_dir / "latest.log"

    # Log format
    log_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler (colored output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_format)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(log_format)

    # Latest log file handler (always writes to latest.log)
    latest_handler = logging.FileHandler(
        latest_log,
        mode="w",  # Overwrite each run
        encoding="utf-8",
    )
    latest_handler.setLevel(log_level)
    latest_handler.setFormatter(log_format)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(latest_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)

    # Log startup message
    root_logger.info("=" * 60)
    root_logger.info("CC-SOP Monitor Backend Logging Initialized")
    root_logger.info(f"Log file: {log_file}")
    root_logger.info(f"Latest log: {latest_log}")
    root_logger.info("=" * 60)

    return log_file


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)
