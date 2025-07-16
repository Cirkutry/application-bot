"""
Application service for the Simple Applications Bot.

This module provides business logic for application management,
including CRUD operations, validation, and application lifecycle.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..core.application_db import application_db
from ..core.database import config_db
from ..core.exceptions import ApplicationNotFoundError, ValidationError
from ..models import Application, ApplicationStatus

logger = logging.getLogger(__name__)


# TODO: Change Position from a string to a Position object or similar,
# .... See create_application(), get_applications_by_position(), etc.
# def get_applications_by_position(self, position: str) -> List[Application]:
# Change `position` from `str` to a reliable lookup property


class ApplicationService:
    """Service for managing applications."""

    def __init__(self):
        """Initialize the application service."""
        self.active_applications = self._load_active_applications()

    def _load_active_applications(self) -> Dict[str, Any]:
        """Load active applications from the database."""
        try:
            return config_db.load_active_applications()
        except Exception as e:
            logger.error(f"Error loading active applications: {e}")
            return {}

    def _save_active_applications(self) -> None:
        """Save active applications to the database."""
        try:
            config_db.save_active_applications(self.active_applications)
        except Exception as e:
            logger.error(f"Error saving active applications: {e}")
            raise

    def create_application(self, user_id: str, user_name: str, position: str, questions: List[str]) -> Application:
        """
        Create a new application.

        Args:
            user_id: Discord user ID
            user_name: Discord username
            position: Position being applied for
            questions: List of questions for the position

        Returns:
            Created Application instance

        Raises:
            ValidationError: If the application data is invalid
        """
        if not user_id or not user_name or not position:
            raise ValidationError("User ID, user name, and position are required")

        if not questions:
            raise ValidationError("Questions list cannot be empty")

        # Create application
        application = Application(user_id=user_id, user_name=user_name, position=position, questions=questions)

        # Save to database
        application_db.save_application(application.id, application.to_dict())

        logger.info(f"Created application {application.id} for user {user_name} ({user_id})")
        return application

    def get_application(self, application_id: str) -> Optional[Application]:
        """
        Get an application by ID.

        Args:
            application_id: Application ID

        Returns:
            Application instance or None if not found
        """
        try:
            data = application_db.load_application(application_id)
            if data:
                return Application.from_dict(data)
            return None
        except Exception as e:
            logger.error(f"Error loading application {application_id}: {e}")
            return None

    def get_applications_by_user(self, user_id: str) -> List[Application]:
        """
        Get all applications for a user.

        Args:
            user_id: Discord user ID

        Returns:
            List of Application instances
        """
        applications = []
        try:
            app_ids = application_db.list_applications()
            for app_id in app_ids:
                app = self.get_application(app_id)
                if app and app.user_id == user_id:
                    applications.append(app)
        except Exception as e:
            logger.error(f"Error getting applications for user {user_id}: {e}")

        return applications

    def get_applications_by_position(self, position: str) -> List[Application]:
        """
        Get all applications for a position.

        Args:
            position: Position name

        Returns:
            List of Application instances
        """
        applications = []
        try:
            app_ids = application_db.list_applications()
            for app_id in app_ids:
                app = self.get_application(app_id)
                if app and app.position == position:
                    applications.append(app)
        except Exception as e:
            logger.error(f"Error getting applications for position {position}: {e}")

        return applications

    def get_applications_by_status(self, status: ApplicationStatus) -> List[Application]:
        """
        Get all applications with a specific status.

        Args:
            status: Application status

        Returns:
            List of Application instances
        """
        applications = []
        try:
            app_ids = application_db.list_applications()
            for app_id in app_ids:
                app = self.get_application(app_id)
                if app and app.status == status:
                    applications.append(app)
        except Exception as e:
            logger.error(f"Error getting applications with status {status}: {e}")

        return applications

    def get_all_applications(self) -> List[Application]:
        """
        Get all applications.

        Returns:
            List of all Application instances
        """
        applications = []
        try:
            app_ids = application_db.list_applications()
            for app_id in app_ids:
                app = self.get_application(app_id)
                if app:
                    applications.append(app)
        except Exception as e:
            logger.error(f"Error getting all applications: {e}")

        return applications

    def update_application(self, application_id: str, **kwargs) -> Application:
        """
        Update an application.

        Args:
            application_id: Application ID
            **kwargs: Fields to update

        Returns:
            Updated Application instance

        Raises:
            ApplicationNotFoundError: If application not found
            ValidationError: If update data is invalid
        """
        application = self.get_application(application_id)
        if not application:
            raise ApplicationNotFoundError(f"Application {application_id} not found")

        # Update fields
        for key, value in kwargs.items():
            if hasattr(application, key):
                setattr(application, key, value)

        # Validate and save
        application.validate()
        application_db.save_application(application_id, application.to_dict())

        logger.info(f"Updated application {application_id}")
        return application

    def delete_application(self, application_id: str) -> bool:
        """
        Delete an application.

        Args:
            application_id: Application ID

        Returns:
            True if deleted, False if not found
        """
        try:
            success = application_db.delete_application(application_id)
            if success:
                logger.info(f"Deleted application {application_id}")
            return success
        except Exception as e:
            logger.error(f"Error deleting application {application_id}: {e}")
            return False

    def add_answer(self, application_id: str, answer: str) -> Application:
        """
        Add an answer to an application.

        Args:
            application_id: Application ID
            answer: Answer text

        Returns:
            Updated Application instance

        Raises:
            ApplicationNotFoundError: If application not found
            ValidationError: If answer is invalid
        """
        application = self.get_application(application_id)
        if not application:
            raise ApplicationNotFoundError(f"Application {application_id} not found")

        application.add_answer(answer)
        application_db.save_application(application_id, application.to_dict())

        logger.info(f"Added answer to application {application_id}")
        return application

    def submit_application(self, application_id: str) -> Application:
        """
        Submit an application.

        Args:
            application_id: Application ID

        Returns:
            Submitted Application instance

        Raises:
            ApplicationNotFoundError: If application not found
            ValidationError: If application cannot be submitted
        """
        application = self.get_application(application_id)
        if not application:
            raise ApplicationNotFoundError(f"Application {application_id} not found")

        application.submit()
        application_db.save_application(application_id, application.to_dict())

        logger.info(f"Submitted application {application_id}")
        return application

    def review_application(
        self, application_id: str, status: ApplicationStatus, reviewer_id: str, reason: Optional[str] = None
    ) -> Application:
        """
        Review an application.

        Args:
            application_id: Application ID
            status: New status
            reviewer_id: ID of the reviewer
            reason: Optional reason for the decision

        Returns:
            Reviewed Application instance

        Raises:
            ApplicationNotFoundError: If application not found
            ValidationError: If review data is invalid
        """
        application = self.get_application(application_id)
        if not application:
            raise ApplicationNotFoundError(f"Application {application_id} not found")

        application.review(status, reviewer_id, reason)
        application_db.save_application(application_id, application.to_dict())

        logger.info(f"Reviewed application {application_id} with status {status.value}")
        return application

    def start_active_application(self, user_id: str, position: str, questions: List[str]) -> Dict[str, Any]:
        """
        Start an active application (in-progress).

        Args:
            user_id: Discord user ID
            position: Position being applied for
            questions: List of questions

        Returns:
            Active application data

        Raises:
            ValidationError: If data is invalid
        """
        if not user_id or not position or not questions:
            raise ValidationError("User ID, position, and questions are required")

        # Check if user already has an active application
        if user_id in self.active_applications:
            raise ValidationError("User already has an active application")

        # Create active application data
        active_app = {
            "user_id": user_id,
            "position": position,
            "questions": questions,
            "answers": [],
            "current_question": 0,
            "start_time": datetime.now(timezone.utc).isoformat(),
        }

        self.active_applications[user_id] = active_app
        self._save_active_applications()

        logger.info(f"Started active application for user {user_id}")
        return active_app

    def get_active_application(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get active application for a user.

        Args:
            user_id: Discord user ID

        Returns:
            Active application data or None
        """
        return self.active_applications.get(user_id)

    def add_active_answer(self, user_id: str, answer: str) -> Dict[str, Any]:
        """
        Add an answer to an active application.

        Args:
            user_id: Discord user ID
            answer: Answer text

        Returns:
            Updated active application data

        Raises:
            ValidationError: If no active application or answer is invalid
        """
        if user_id not in self.active_applications:
            raise ValidationError("No active application found for user")

        active_app = self.active_applications[user_id]

        if not answer or not answer.strip():
            raise ValidationError("Answer cannot be empty")

        active_app["answers"].append(answer.strip())
        active_app["current_question"] = len(active_app["answers"])

        self._save_active_applications()

        logger.info(f"Added answer to active application for user {user_id}")
        return active_app

    def complete_active_application(self, user_id: str) -> Application:
        """
        Complete an active application and create a submitted application.

        Args:
            user_id: Discord user ID

        Returns:
            Created Application instance

        Raises:
            ValidationError: If no active application or application is incomplete
        """
        if user_id not in self.active_applications:
            raise ValidationError("No active application found for user")

        active_app = self.active_applications[user_id]

        if len(active_app["answers"]) != len(active_app["questions"]):
            raise ValidationError("Application is not complete")

        # Create and submit application
        application = Application(
            user_id=active_app["user_id"],
            user_name=active_app.get("user_name", "Unknown"),
            position=active_app["position"],
            questions=active_app["questions"],
            answers=active_app["answers"],
        )

        application.submit()

        # Save application
        application_db.save_application(application.id, application.to_dict())

        # Remove from active applications
        del self.active_applications[user_id]
        self._save_active_applications()

        logger.info(f"Completed active application for user {user_id}, created application {application.id}")
        return application

    def cancel_active_application(self, user_id: str) -> bool:
        """
        Cancel an active application.

        Args:
            user_id: Discord user ID

        Returns:
            True if cancelled, False if no active application
        """
        if user_id in self.active_applications:
            del self.active_applications[user_id]
            self._save_active_applications()
            logger.info(f"Cancelled active application for user {user_id}")
            return True
        return False

    def get_application_stats(self) -> Dict[str, Any]:
        """
        Get application statistics.

        Returns:
            Dictionary with application statistics
        """
        try:
            all_applications = self.get_all_applications()

            stats = {
                "total": len(all_applications),
                "pending": len([app for app in all_applications if app.status == ApplicationStatus.PENDING]),
                "accepted": len([app for app in all_applications if app.status == ApplicationStatus.ACCEPTED]),
                "denied": len([app for app in all_applications if app.status == ApplicationStatus.DENIED]),
                "withdrawn": len([app for app in all_applications if app.status == ApplicationStatus.WITHDRAWN]),
                "active": len(self.active_applications),
            }

            return stats
        except Exception as e:
            logger.error(f"Error getting application stats: {e}")
            return {"total": 0, "pending": 0, "accepted": 0, "denied": 0, "withdrawn": 0, "active": 0}


# Global service instance
application_service = ApplicationService()
