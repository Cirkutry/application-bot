"""
Panel service for the Simple Applications Bot.

This module provides business logic for panel management,
including CRUD operations, validation, and panel lifecycle.
"""

import logging
from typing import Any, Dict, List, Optional

from ..core.exceptions import PanelNotFoundError, ValidationError
from ..core.panel_db import panel_db
from ..models.panel import Panel, PanelStatus

logger = logging.getLogger(__name__)


class PanelService:
    """Service for managing panels."""

    def create_panel(
        self, name: str, description: str, channel_id: str, message_id: str, position: str, is_active: bool = True
    ) -> Panel:
        """
        Create a new panel.

        Args:
            name: Panel name
            description: Panel description
            channel_id: Discord channel ID
            message_id: Discord message ID
            position: Position this panel is for
            is_active: Whether the panel is active

        Returns:
            Created Panel instance

        Raises:
            ValidationError: If the panel data is invalid
        """
        if not name or not name.strip():
            raise ValidationError("Panel name is required")

        if not description or not description.strip():
            raise ValidationError("Panel description is required")

        if not channel_id or not channel_id.strip():
            raise ValidationError("Channel ID is required")

        if not message_id or not message_id.strip():
            raise ValidationError("Message ID is required")

        if not position or not position.strip():
            raise ValidationError("Position is required")

        # Create panel
        panel = Panel(
            name=name.strip(),
            description=description.strip(),
            channel_id=channel_id.strip(),
            message_id=message_id.strip(),
            position=position.strip(),
            is_active=is_active,
        )

        # Save to database
        panel_db.save_panel(panel.id, panel.to_dict())

        logger.info(f"Created panel {panel.id}: {name}")
        return panel

    def get_panel(self, panel_id: str) -> Optional[Panel]:
        """
        Get a panel by ID.

        Args:
            panel_id: Panel ID

        Returns:
            Panel instance or None if not found
        """
        try:
            data = panel_db.load_panel(panel_id)
            if data:
                return Panel.from_dict(data)
            return None
        except Exception as e:
            logger.error(f"Error loading panel {panel_id}: {e}")
            return None

    def get_panel_by_message(self, message_id: str) -> Optional[Panel]:
        """
        Get a panel by Discord message ID.

        Args:
            message_id: Discord message ID

        Returns:
            Panel instance or None if not found
        """
        try:
            panels = self.get_all_panels()
            for panel in panels:
                if panel.message_id == message_id:
                    return panel
            return None
        except Exception as e:
            logger.error(f"Error getting panel by message {message_id}: {e}")
            return None

    def get_panels_by_position(self, position: str) -> List[Panel]:
        """
        Get all panels for a position.

        Args:
            position: Position name

        Returns:
            List of Panel instances
        """
        try:
            all_panels = self.get_all_panels()
            return [panel for panel in all_panels if panel.position.lower() == position.lower()]
        except Exception as e:
            logger.error(f"Error getting panels for position {position}: {e}")
            return []

    def get_active_panels(self) -> List[Panel]:
        """
        Get all active panels.

        Returns:
            List of active Panel instances
        """
        try:
            all_panels = self.get_all_panels()
            return [panel for panel in all_panels if panel.is_active]
        except Exception as e:
            logger.error(f"Error getting active panels: {e}")
            return []

    def get_inactive_panels(self) -> List[Panel]:
        """
        Get all inactive panels.

        Returns:
            List of inactive Panel instances
        """
        try:
            all_panels = self.get_all_panels()
            return [panel for panel in all_panels if not panel.is_active]
        except Exception as e:
            logger.error(f"Error getting inactive panels: {e}")
            return []

    def get_all_panels(self) -> List[Panel]:
        """
        Get all panels.

        Returns:
            List of all Panel instances
        """
        panels = []
        try:
            panel_ids = panel_db.list_panels()
            for panel_id in panel_ids:
                panel = self.get_panel(panel_id)
                if panel:
                    panels.append(panel)
        except Exception as e:
            logger.error(f"Error getting all panels: {e}")

        return panels

    def update_panel(self, panel_id: str, **kwargs) -> Panel:
        """
        Update a panel.

        Args:
            panel_id: Panel ID
            **kwargs: Fields to update

        Returns:
            Updated Panel instance

        Raises:
            PanelNotFoundError: If panel not found
            ValidationError: If update data is invalid
        """
        panel = self.get_panel(panel_id)
        if not panel:
            raise PanelNotFoundError(f"Panel {panel_id} not found")

        # Update fields
        for key, value in kwargs.items():
            if hasattr(panel, key):
                if key in ["name", "description", "channel_id", "message_id", "position"] and value:
                    setattr(panel, key, value.strip())
                else:
                    setattr(panel, key, value)

        # Validate and save
        panel.validate()
        panel_db.save_panel(panel_id, panel.to_dict())

        logger.info(f"Updated panel {panel_id}")
        return panel

    def delete_panel(self, panel_id: str) -> bool:
        """
        Delete a panel.

        Args:
            panel_id: Panel ID

        Returns:
            True if deleted, False if not found
        """
        try:
            success = panel_db.delete_panel(panel_id)
            if success:
                logger.info(f"Deleted panel {panel_id}")
            return success
        except Exception as e:
            logger.error(f"Error deleting panel {panel_id}: {e}")
            return False

    def activate_panel(self, panel_id: str) -> Panel:
        """
        Activate a panel.

        Args:
            panel_id: Panel ID

        Returns:
            Activated Panel instance

        Raises:
            PanelNotFoundError: If panel not found
        """
        panel = self.get_panel(panel_id)
        if not panel:
            raise PanelNotFoundError(f"Panel {panel_id} not found")

        panel.is_active = True
        panel_db.save_panel(panel_id, panel.to_dict())

        logger.info(f"Activated panel {panel_id}")
        return panel

    def deactivate_panel(self, panel_id: str) -> Panel:
        """
        Deactivate a panel.

        Args:
            panel_id: Panel ID

        Returns:
            Deactivated Panel instance

        Raises:
            PanelNotFoundError: If panel not found
        """
        panel = self.get_panel(panel_id)
        if not panel:
            raise PanelNotFoundError(f"Panel {panel_id} not found")

        panel.is_active = False
        panel_db.save_panel(panel_id, panel.to_dict())

        logger.info(f"Deactivated panel {panel_id}")
        return panel

    def add_reviewer(self, panel_id: str, reviewer_id: str, reviewer_name: str) -> Panel:
        """
        Add a reviewer to a panel.

        Args:
            panel_id: Panel ID
            reviewer_id: Discord user ID of the reviewer
            reviewer_name: Discord username of the reviewer

        Returns:
            Updated Panel instance

        Raises:
            PanelNotFoundError: If panel not found
            ValidationError: If reviewer data is invalid
        """
        panel = self.get_panel(panel_id)
        if not panel:
            raise PanelNotFoundError(f"Panel {panel_id} not found")

        if not reviewer_id or not reviewer_name:
            raise ValidationError("Reviewer ID and name are required")

        panel.add_reviewer(reviewer_id, reviewer_name)
        panel_db.save_panel(panel_id, panel.to_dict())

        logger.info(f"Added reviewer {reviewer_name} ({reviewer_id}) to panel {panel_id}")
        return panel

    def remove_reviewer(self, panel_id: str, reviewer_id: str) -> Panel:
        """
        Remove a reviewer from a panel.

        Args:
            panel_id: Panel ID
            reviewer_id: Discord user ID of the reviewer

        Returns:
            Updated Panel instance

        Raises:
            PanelNotFoundError: If panel not found
            ValidationError: If reviewer not found
        """
        panel = self.get_panel(panel_id)
        if not panel:
            raise PanelNotFoundError(f"Panel {panel_id} not found")

        panel.remove_reviewer(reviewer_id)
        panel_db.save_panel(panel_id, panel.to_dict())

        logger.info(f"Removed reviewer {reviewer_id} from panel {panel_id}")
        return panel

    def add_application_to_panel(self, panel_id: str, application_id: str) -> Panel:
        """
        Add an application to a panel for review.

        Args:
            panel_id: Panel ID
            application_id: Application ID

        Returns:
            Updated Panel instance

        Raises:
            PanelNotFoundError: If panel not found
            ValidationError: If application is already in panel
        """
        panel = self.get_panel(panel_id)
        if not panel:
            raise PanelNotFoundError(f"Panel {panel_id} not found")

        if application_id in panel.applications:
            raise ValidationError(f"Application {application_id} is already in panel {panel_id}")

        panel.add_application(application_id)
        panel_db.save_panel(panel_id, panel.to_dict())

        logger.info(f"Added application {application_id} to panel {panel_id}")
        return panel

    def remove_application_from_panel(self, panel_id: str, application_id: str) -> Panel:
        """
        Remove an application from a panel.

        Args:
            panel_id: Panel ID
            application_id: Application ID

        Returns:
            Updated Panel instance

        Raises:
            PanelNotFoundError: If panel not found
            ValidationError: If application not in panel
        """
        panel = self.get_panel(panel_id)
        if not panel:
            raise PanelNotFoundError(f"Panel {panel_id} not found")

        if application_id not in panel.applications:
            raise ValidationError(f"Application {application_id} is not in panel {panel_id}")

        panel.remove_application(application_id)
        panel_db.save_panel(panel_id, panel.to_dict())

        logger.info(f"Removed application {application_id} from panel {panel_id}")
        return panel

    def review_application_in_panel(
        self, panel_id: str, application_id: str, reviewer_id: str, status: PanelStatus, reason: Optional[str] = None
    ) -> Panel:
        """
        Review an application in a panel.

        Args:
            panel_id: Panel ID
            application_id: Application ID
            reviewer_id: Discord user ID of the reviewer
            status: Review status
            reason: Optional reason for the decision

        Returns:
            Updated Panel instance

        Raises:
            PanelNotFoundError: If panel not found
            ValidationError: If application not in panel or review data is invalid
        """
        panel = self.get_panel(panel_id)
        if not panel:
            raise PanelNotFoundError(f"Panel {panel_id} not found")

        if application_id not in panel.applications:
            raise ValidationError(f"Application {application_id} is not in panel {panel_id}")

        panel.review_application(application_id, reviewer_id, status, reason)
        panel_db.save_panel(panel_id, panel.to_dict())

        logger.info(f"Reviewed application {application_id} in panel {panel_id} with status {status.value}")
        return panel

    def get_panel_stats(self) -> Dict[str, Any]:
        """
        Get panel statistics.

        Returns:
            Dictionary with panel statistics
        """
        try:
            all_panels = self.get_all_panels()

            total_applications = sum(len(panel.applications) for panel in all_panels)
            total_reviewers = sum(len(panel.reviewers) for panel in all_panels)

            stats = {
                "total": len(all_panels),
                "active": len([panel for panel in all_panels if panel.is_active]),
                "inactive": len([panel for panel in all_panels if not panel.is_active]),
                "total_applications": total_applications,
                "total_reviewers": total_reviewers,
                "avg_applications_per_panel": total_applications / len(all_panels) if all_panels else 0,
                "avg_reviewers_per_panel": total_reviewers / len(all_panels) if all_panels else 0,
            }

            return stats
        except Exception as e:
            logger.error(f"Error getting panel stats: {e}")
            return {
                "total": 0,
                "active": 0,
                "inactive": 0,
                "total_applications": 0,
                "total_reviewers": 0,
                "avg_applications_per_panel": 0,
                "avg_reviewers_per_panel": 0,
            }

    def search_panels(self, query: str) -> List[Panel]:
        """
        Search panels by name, description, or position.

        Args:
            query: Search query

        Returns:
            List of matching Panel instances
        """
        if not query or not query.strip():
            return []

        query_lower = query.lower().strip()
        matching_panels = []

        try:
            all_panels = self.get_all_panels()
            for panel in all_panels:
                if (
                    query_lower in panel.name.lower()
                    or query_lower in panel.description.lower()
                    or query_lower in panel.position.lower()
                ):
                    matching_panels.append(panel)
        except Exception as e:
            logger.error(f"Error searching panels: {e}")

        return matching_panels

    def get_panels_by_reviewer(self, reviewer_id: str) -> List[Panel]:
        """
        Get all panels that a reviewer is part of.

        Args:
            reviewer_id: Discord user ID of the reviewer

        Returns:
            List of Panel instances
        """
        try:
            all_panels = self.get_all_panels()
            return [panel for panel in all_panels if reviewer_id in panel.reviewers]
        except Exception as e:
            logger.error(f"Error getting panels for reviewer {reviewer_id}: {e}")
            return []

    def get_panels_with_pending_applications(self) -> List[Panel]:
        """
        Get all panels that have pending applications.

        Returns:
            List of Panel instances with pending applications
        """
        try:
            all_panels = self.get_all_panels()
            return [panel for panel in all_panels if panel.applications]
        except Exception as e:
            logger.error(f"Error getting panels with pending applications: {e}")
            return []


# Global service instance
panel_service = PanelService()
