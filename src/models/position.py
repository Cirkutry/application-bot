"""
Position model for the Simple Applications Bot.

This module defines the Position data model with validation,
serialization, and business logic for position management.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..core.exceptions import ValidationError


class PositionStatus(Enum):
    """Position status enumeration."""

    ENABLED = "enabled"
    DISABLED = "disabled"


@dataclass
class PositionSettings:
    """Position settings configuration."""

    # Basic settings
    enabled: bool = True
    questions: List[str] = field(default_factory=list)
    time_limit: int = 60  # minutes

    # Messages
    welcome_message: str = ""
    completion_message: str = ""
    accepted_message: str = ""
    denied_message: str = ""

    # Discord integration
    log_channel: Optional[str] = None
    restricted_roles: List[str] = field(default_factory=list)
    required_roles: List[str] = field(default_factory=list)
    accepted_roles: List[str] = field(default_factory=list)
    denied_roles: List[str] = field(default_factory=list)
    ping_roles: List[str] = field(default_factory=list)
    accepted_removal_roles: List[str] = field(default_factory=list)
    denied_removal_roles: List[str] = field(default_factory=list)

    # Additional settings
    auto_thread: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate the position settings after initialization."""
        self.validate()

    def validate(self) -> None:
        """
        Validate the position settings.

        Raises:
            ValidationError: If the settings are invalid
        """
        if not isinstance(self.enabled, bool):
            raise ValidationError("Enabled must be a boolean")

        if not isinstance(self.questions, list):
            raise ValidationError("Questions must be a list")

        if not isinstance(self.time_limit, int) or self.time_limit <= 0:
            raise ValidationError("Time limit must be a positive integer")

        if not isinstance(self.restricted_roles, list):
            raise ValidationError("Restricted roles must be a list")

        if not isinstance(self.required_roles, list):
            raise ValidationError("Required roles must be a list")

        if not isinstance(self.accepted_roles, list):
            raise ValidationError("Accepted roles must be a list")

        if not isinstance(self.denied_roles, list):
            raise ValidationError("Denied roles must be a list")

        if not isinstance(self.ping_roles, list):
            raise ValidationError("Ping roles must be a list")

        if not isinstance(self.accepted_removal_roles, list):
            raise ValidationError("Accepted removal roles must be a list")

        if not isinstance(self.denied_removal_roles, list):
            raise ValidationError("Denied removal roles must be a list")

        if not isinstance(self.auto_thread, bool):
            raise ValidationError("Auto thread must be a boolean")

    def add_question(self, question: str) -> None:
        """
        Add a question to the position.

        Args:
            question: The question to add

        Raises:
            ValidationError: If the question is invalid
        """
        if not question or not question.strip():
            raise ValidationError("Question cannot be empty")

        self.questions.append(question.strip())

    def remove_question(self, index: int) -> None:
        """
        Remove a question from the position.

        Args:
            index: Index of the question to remove

        Raises:
            ValidationError: If the index is invalid
        """
        if not isinstance(index, int) or index < 0 or index >= len(self.questions):
            raise ValidationError(f"Invalid question index: {index}")

        self.questions.pop(index)

    def update_question(self, index: int, question: str) -> None:
        """
        Update a question in the position.

        Args:
            index: Index of the question to update
            question: New question text

        Raises:
            ValidationError: If the index or question is invalid
        """
        if not isinstance(index, int) or index < 0 or index >= len(self.questions):
            raise ValidationError(f"Invalid question index: {index}")

        if not question or not question.strip():
            raise ValidationError("Question cannot be empty")

        self.questions[index] = question.strip()

    def reorder_questions(self, new_order: List[int]) -> None:
        """
        Reorder questions in the position.

        Args:
            new_order: List of indices representing the new order

        Raises:
            ValidationError: If the new order is invalid
        """
        if not isinstance(new_order, list):
            raise ValidationError("New order must be a list")

        if len(new_order) != len(self.questions):
            raise ValidationError("New order length must match number of questions")

        # Validate indices
        for i, index in enumerate(new_order):
            if not isinstance(index, int) or index < 0 or index >= len(self.questions):
                raise ValidationError(f"Invalid index in new order: {index}")

        # Check for duplicates
        if len(set(new_order)) != len(new_order):
            raise ValidationError("New order contains duplicate indices")

        # Reorder questions
        self.questions = [self.questions[i] for i in new_order]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the position settings to a dictionary.

        Returns:
            Dictionary representation of the position settings
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PositionSettings':
        """
        Create position settings from a dictionary.

        Args:
            data: Dictionary containing position settings data

        Returns:
            PositionSettings instance

        Raises:
            ValidationError: If the data is invalid
        """
        return cls(**data)

    def get_default_messages(self, position_name: str) -> None:
        """
        Set default messages for the position.

        Args:
            position_name: Name of the position
        """
        if not self.welcome_message:
            self.welcome_message = (
                f"Welcome to the {position_name} application process! "
                f"Please answer the following questions to complete your application."
            )

        if not self.completion_message:
            self.completion_message = (
                f"Thank you for completing your {position_name} application! "
                f"Your responses have been submitted and will be reviewed soon."
            )

        if not self.accepted_message:
            self.accepted_message = (
                f"Congratulations! Your application for {position_name} has been accepted. " f"Welcome to the team!"
            )

        if not self.denied_message:
            self.denied_message = (
                f"Thank you for applying for {position_name}. "
                f"After careful consideration, we have decided not to move forward "
                f"with your application at this time."
            )


@dataclass
class Position:
    """Position data model."""

    id: str = ""
    name: str = ""
    description: str = ""
    is_active: bool = False
    questions: List[str] = field(default_factory=list)
    settings: PositionSettings = field(default_factory=PositionSettings)

    def __post_init__(self):
        """Validate the position after initialization."""
        self.validate()

    def validate(self) -> None:
        """
        Validate the position data.

        Raises:
            ValidationError: If the position data is invalid
        """
        if not self.name or not self.name.strip():
            raise ValidationError("Position name cannot be empty")

        if not isinstance(self.settings, PositionSettings):
            raise ValidationError("Settings must be a PositionSettings instance")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the position to a dictionary.

        Returns:
            Dictionary representation of the position
        """
        return {'name': self.name, 'settings': self.settings.to_dict()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """
        Create a position from a dictionary.

        Args:
            data: Dictionary containing position data

        Returns:
            Position instance

        Raises:
            ValidationError: If the data is invalid
        """
        settings_data = data.get('settings', {})
        settings = PositionSettings.from_dict(settings_data)

        return cls(name=data.get('name', ''), settings=settings)

    def is_enabled(self) -> bool:
        """
        Check if the position is enabled.

        Returns:
            True if the position is enabled
        """
        return self.settings.enabled

    def get_question_count(self) -> int:
        """
        Get the number of questions for this position.

        Returns:
            Number of questions
        """
        return len(self.settings.questions)

    def has_questions(self) -> bool:
        """
        Check if the position has any questions.

        Returns:
            True if the position has questions
        """
        return len(self.settings.questions) > 0
