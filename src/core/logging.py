"""
Logging configuration for the Simple Applications Bot.

This module provides centralized logging configuration and utilities
for consistent logging across the application.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from .config import config


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    max_bytes: int = 1024 * 1024,  # 1MB
    backup_count: int = 5,
    format_string: Optional[str] = None,
) -> None:
    """
    Set up logging configuration for the application.

    Args:
        level: Logging level (default: INFO)
        log_file: Path to log file (default: storage/logs/bot.log)
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
        format_string: Custom format string for log messages
    """
    if log_file is None:
        log_file = f"{config.LOGS_DIR}/bot.log"

    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Ensure log directory exists
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Create formatter
    formatter = logging.Formatter(format_string)

    # Create handlers
    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    handlers.append(file_handler)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add new handlers
    for handler in handlers:
        root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_startup_info() -> None:
    """Log startup information."""
    logger = get_logger(__name__)

    logger.info("=" * 50)
    logger.info("Simple Applications Bot Starting Up")
    logger.info("=" * 50)

    # Log configuration info (without sensitive data)
    logger.info(f"Web Host: {config.WEB_HOST}")
    logger.info(f"Web Port: {config.WEB_PORT}")
    logger.info(f"Server ID: {config.SERVER_ID}")
    logger.info(f"Storage Directory: {config.STORAGE_DIR}")

    # Validate configuration
    missing_vars = config.validate()
    if missing_vars:
        logger.error("Missing required configuration variables:")
        for var in missing_vars:
            logger.error(f"  - {var}")
        logger.error("Please check your .env file or environment variables.")
    else:
        logger.info("Configuration validation passed")


def log_shutdown_info() -> None:
    """Log shutdown information."""
    logger = get_logger(__name__)
    logger.info("=" * 50)
    logger.info("Simple Applications Bot Shutting Down")
    logger.info("=" * 50)


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log messages."""

    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[32m',  # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',  # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m',  # Reset
    }

    def format(self, record):
        # Add color to the level name
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"

        return super().format(record)


def setup_colored_logging(level: int = logging.INFO) -> None:
    """
    Set up colored logging for console output.

    Args:
        level: Logging level
    """
    # Create colored formatter for console
    colored_formatter = ColoredFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Create standard formatter for file
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Ensure log directory exists
    log_file = f"{config.LOGS_DIR}/bot.log"
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(colored_formatter)

    file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5, encoding='utf-8')
    file_handler.setFormatter(file_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add new handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
