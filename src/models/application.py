"""
Application model for the Simple Applications Bot.

This module defines the Application data model with validation,
serialization, and business logic for application management.
"""

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from ..core.exceptions import ValidationError


class ApplicationStatus(Enum):
    """Application status enumeration."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"


@dataclass
class Application:
    """Application data model."""

    # Core fields
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    user_name: str = ""
    position: str = ""
    status: ApplicationStatus = ApplicationStatus.PENDING

    # Application content
    questions: List[str] = field(default_factory=list)
    answers: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    review_reason: Optional[str] = None

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate the application after initialization."""
        self.validate()

    def validate(self) -> None:
        """
        Validate the application data.

        Raises:
            ValidationError: If the application data is invalid
        """
        if not self.user_id:
            raise ValidationError("User ID cannot be empty")

        if not self.user_name:
            raise ValidationError("User name cannot be empty")

        if not self.position:
            raise ValidationError("Position cannot be empty")

        if not isinstance(self.questions, list):
            raise ValidationError("Questions must be a list")

        if not isinstance(self.answers, list):
            raise ValidationError("Answers must be a list")

        if len(self.answers) > len(self.questions):
            raise ValidationError("Cannot have more answers than questions")

        # Validate status
        if not isinstance(self.status, ApplicationStatus):
            try:
                self.status = ApplicationStatus(self.status)
            except ValueError:
                raise ValidationError(f"Invalid status: {self.status}")

    def add_answer(self, answer: str) -> None:
        """
        Add an answer to the application.

        Args:
            answer: The answer to add

        Raises:
            ValidationError: If the answer is invalid or all questions are answered
        """
        if not answer or not answer.strip():
            raise ValidationError("Answer cannot be empty")

        if len(self.answers) >= len(self.questions):
            raise ValidationError("All questions have already been answered")

        self.answers.append(answer.strip())
        self.updated_at = datetime.now(timezone.utc)

    def is_complete(self) -> bool:
        """
        Check if the application is complete (all questions answered).

        Returns:
            True if all questions have been answered
        """
        return len(self.answers) == len(self.questions)

    def submit(self) -> None:
        """
        Submit the application.

        Raises:
            ValidationError: If the application is not complete
        """
        if not self.is_complete():
            raise ValidationError("Cannot submit incomplete application")

        self.submitted_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def review(self, status: ApplicationStatus, reviewer_id: str, reason: Optional[str] = None) -> None:
        """
        Review the application.

        Args:
            status: The new status
            reviewer_id: ID of the reviewer
            reason: Optional reason for the decision

        Raises:
            ValidationError: If the review data is invalid
        """
        if not reviewer_id:
            raise ValidationError("Reviewer ID cannot be empty")

        if not isinstance(status, ApplicationStatus):
            try:
                status = ApplicationStatus(status)
            except ValueError:
                raise ValidationError(f"Invalid status: {status}")

        self.status = status
        self.reviewed_at = datetime.now(timezone.utc)
        self.reviewed_by = reviewer_id
        self.review_reason = reason
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the application to a dictionary.

        Returns:
            Dictionary representation of the application
        """
        data = asdict(self)
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()

        if self.submitted_at:
            data['submitted_at'] = self.submitted_at.isoformat()

        if self.reviewed_at:
            data['reviewed_at'] = self.reviewed_at.isoformat()

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Application':
        """
        Create an application from a dictionary.

        Args:
            data: Dictionary containing application data

        Returns:
            Application instance

        Raises:
            ValidationError: If the data is invalid
        """
        # Handle datetime fields
        datetime_fields = ['created_at', 'updated_at', 'submitted_at', 'reviewed_at']
        for field_name in datetime_fields:
            if field_name in data and data[field_name]:
                if isinstance(data[field_name], str):
                    data[field_name] = datetime.fromisoformat(data[field_name].replace('Z', '+00:00'))
                elif isinstance(data[field_name], datetime):
                    # Ensure timezone awareness
                    if data[field_name].tzinfo is None:
                        data[field_name] = data[field_name].replace(tzinfo=timezone.utc)

        # Handle status field
        if 'status' in data and isinstance(data['status'], str):
            try:
                data['status'] = ApplicationStatus(data['status'])
            except ValueError:
                raise ValidationError(f"Invalid status: {data['status']}")

        return cls(**data)

    def get_question_answer_pairs(self) -> List[Dict[str, str]]:
        """
        Get question-answer pairs.

        Returns:
            List of dictionaries with 'question' and 'answer' keys
        """
        pairs = []
        for i, question in enumerate(self.questions):
            answer = self.answers[i] if i < len(self.answers) else ""
            pairs.append({'question': question, 'answer': answer})
        return pairs

    def get_progress(self) -> float:
        """
        Get the completion progress as a percentage.

        Returns:
            Progress percentage (0.0 to 1.0)
        """
        if not self.questions:
            return 1.0

        return len(self.answers) / len(self.questions)

    def get_current_question_index(self) -> int:
        """
        Get the index of the current question.

        Returns:
            Index of the current question, or -1 if complete
        """
        return len(self.answers) if not self.is_complete() else -1

    def get_current_question(self) -> Optional[str]:
        """
        Get the current question text.

        Returns:
            Current question text, or None if complete
        """
        current_index = self.get_current_question_index()
        if current_index >= 0 and current_index < len(self.questions):
            return self.questions[current_index]
        return None
