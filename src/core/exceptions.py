"""
Custom exceptions for the Simple Applications Bot.

This module defines application-specific exceptions that provide
better error handling and more meaningful error messages.
"""


class ApplicationBotError(Exception):
    """Base exception for all application bot errors."""

    pass


class ConfigurationError(ApplicationBotError):
    """Raised when there's a configuration-related error."""

    pass


class ValidationError(ApplicationBotError):
    """Raised when data validation fails."""

    pass


class DatabaseError(ApplicationBotError):
    """Raised when there's a database/persistence error."""

    pass


class DiscordError(ApplicationBotError):
    """Raised when there's a Discord API or interaction error."""

    pass


class AuthenticationError(ApplicationBotError):
    """Raised when authentication fails."""

    pass


class AuthorizationError(ApplicationBotError):
    """Raised when a user doesn't have permission to perform an action."""

    pass


class ApplicationNotFoundError(ApplicationBotError):
    """Raised when an application cannot be found."""

    pass


class PanelNotFoundError(ApplicationBotError):
    """Raised when a panel cannot be found."""

    pass


class PositionNotFoundError(ApplicationBotError):
    """Raised when a position cannot be found."""

    pass


class UserNotFoundError(ApplicationBotError):
    """Raised when a user cannot be found."""

    pass


class InvalidStateError(ApplicationBotError):
    """Raised when an operation is performed on an object in an invalid state."""

    pass


class TimeoutError(ApplicationBotError):
    """Raised when an operation times out."""

    pass


class WebServerError(ApplicationBotError):
    """Raised when there's a web server error."""

    pass
