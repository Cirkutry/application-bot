"""
Core module for the Simple Applications Bot.

This module provides the foundational components for the application,
including configuration, logging, database access, and custom exceptions.
"""

from .config import Config, config
from .database import (
    ApplicationDatabase,
    ConfigDatabase,
    FileDatabase,
    application_db,
    config_db,
)
from .exceptions import (
    ApplicationBotError,
    ApplicationNotFoundError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    DatabaseError,
    DiscordError,
    InvalidStateError,
    PanelNotFoundError,
    PositionNotFoundError,
    TimeoutError,
    UserNotFoundError,
    ValidationError,
    WebServerError,
)
from .logging import (
    ColoredFormatter,
    get_logger,
    log_shutdown_info,
    log_startup_info,
    setup_colored_logging,
    setup_logging,
)

__all__ = [
    # Configuration
    'config',
    'Config',
    # Exceptions
    'ApplicationBotError',
    'ConfigurationError',
    'ValidationError',
    'DatabaseError',
    'DiscordError',
    'AuthenticationError',
    'AuthorizationError',
    'ApplicationNotFoundError',
    'PanelNotFoundError',
    'PositionNotFoundError',
    'UserNotFoundError',
    'InvalidStateError',
    'TimeoutError',
    'WebServerError',
    # Logging
    'setup_logging',
    'setup_colored_logging',
    'get_logger',
    'log_startup_info',
    'log_shutdown_info',
    'ColoredFormatter',
    # Database
    'FileDatabase',
    'ApplicationDatabase',
    'ConfigDatabase',
    'application_db',
    'config_db',
]
