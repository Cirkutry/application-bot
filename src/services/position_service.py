"""
Position service for the Simple Applications Bot.

This module provides business logic for position management,
including CRUD operations, validation, and position lifecycle.
"""

import logging
from typing import Any, Dict, List, Optional

from ..core.exceptions import PositionNotFoundError, ValidationError
from ..core.position_db import position_db
from ..models import Position

logger = logging.getLogger(__name__)


class PositionService:
    """Service for managing positions."""

    def create_position(self, name: str, description: str, questions: List[str], is_active: bool = True) -> Position:
        """
        Create a new position.

        Args:
            name: Position name
            description: Position description
            questions: List of questions for the position
            is_active: Whether the position is active

        Returns:
            Created Position instance

        Raises:
            ValidationError: If the position data is invalid
        """
        if not name or not name.strip():
            raise ValidationError("Position name is required")

        if not description or not description.strip():
            raise ValidationError("Position description is required")

        if not questions:
            raise ValidationError("Questions list cannot be empty")

        # Check if position already exists
        existing_positions = self.get_all_positions()
        for pos in existing_positions:
            if pos.name.lower() == name.lower():
                raise ValidationError(f"Position '{name}' already exists")

        # Create position
        position = Position(
            name=name.strip(), description=description.strip(), questions=questions, is_active=is_active
        )

        # Save to database
        position_db.save_position(position.id, position.to_dict())

        logger.info(f"Created position {position.id}: {name}")
        return position

    def get_position(self, position_id: str) -> Optional[Position]:
        """
        Get a position by ID.

        Args:
            position_id: Position ID

        Returns:
            Position instance or None if not found
        """
        try:
            data = position_db.load_position(position_id)
            if data:
                return Position.from_dict(data)
            return None
        except Exception as e:
            logger.error(f"Error loading position {position_id}: {e}")
            return None

    def get_position_by_name(self, name: str) -> Optional[Position]:
        """
        Get a position by name.

        Args:
            name: Position name

        Returns:
            Position instance or None if not found
        """
        try:
            positions = self.get_all_positions()
            for position in positions:
                if position.name.lower() == name.lower():
                    return position
            return None
        except Exception as e:
            logger.error(f"Error getting position by name {name}: {e}")
            return None

    def get_active_positions(self) -> List[Position]:
        """
        Get all active positions.

        Returns:
            List of active Position instances
        """
        try:
            all_positions = self.get_all_positions()
            return [pos for pos in all_positions if pos.is_active]
        except Exception as e:
            logger.error(f"Error getting active positions: {e}")
            return []

    def get_inactive_positions(self) -> List[Position]:
        """
        Get all inactive positions.

        Returns:
            List of inactive Position instances
        """
        try:
            all_positions = self.get_all_positions()
            return [pos for pos in all_positions if not pos.is_active]
        except Exception as e:
            logger.error(f"Error getting inactive positions: {e}")
            return []

    def get_all_positions(self) -> List[Position]:
        """
        Get all positions.

        Returns:
            List of all Position instances
        """
        positions = []
        try:
            position_ids = position_db.list_positions()
            for pos_id in position_ids:
                pos = self.get_position(pos_id)
                if pos:
                    positions.append(pos)
        except Exception as e:
            logger.error(f"Error getting all positions: {e}")

        return positions

    def update_position(self, position_id: str, **kwargs) -> Position:
        """
        Update a position.

        Args:
            position_id: Position ID
            **kwargs: Fields to update

        Returns:
            Updated Position instance

        Raises:
            PositionNotFoundError: If position not found
            ValidationError: If update data is invalid
        """
        position = self.get_position(position_id)
        if not position:
            raise PositionNotFoundError(f"Position {position_id} not found")

        # Check for name conflicts if name is being updated
        if "name" in kwargs:
            new_name = kwargs["name"].strip()
            existing_positions = self.get_all_positions()
            for pos in existing_positions:
                if pos.id != position_id and pos.name.lower() == new_name.lower():
                    raise ValidationError(f"Position '{new_name}' already exists")

        # Update fields
        for key, value in kwargs.items():
            if hasattr(position, key):
                if key in ["name", "description"] and value:
                    setattr(position, key, value.strip())
                else:
                    setattr(position, key, value)

        # Validate and save
        position.validate()
        position_db.save_position(position_id, position.to_dict())

        logger.info(f"Updated position {position_id}")
        return position

    def delete_position(self, position_id: str) -> bool:
        """
        Delete a position.

        Args:
            position_id: Position ID

        Returns:
            True if deleted, False if not found
        """
        try:
            success = position_db.delete_position(position_id)
            if success:
                logger.info(f"Deleted position {position_id}")
            return success
        except Exception as e:
            logger.error(f"Error deleting position {position_id}: {e}")
            return False

    def activate_position(self, position_id: str) -> Position:
        """
        Activate a position.

        Args:
            position_id: Position ID

        Returns:
            Activated Position instance

        Raises:
            PositionNotFoundError: If position not found
        """
        position = self.get_position(position_id)
        if not position:
            raise PositionNotFoundError(f"Position {position_id} not found")

        position.is_active = True
        position_db.save_position(position_id, position.to_dict())

        logger.info(f"Activated position {position_id}")
        return position

    def deactivate_position(self, position_id: str) -> Position:
        """
        Deactivate a position.

        Args:
            position_id: Position ID

        Returns:
            Deactivated Position instance

        Raises:
            PositionNotFoundError: If position not found
        """
        position = self.get_position(position_id)
        if not position:
            raise PositionNotFoundError(f"Position {position_id} not found")

        position.is_active = False
        position_db.save_position(position_id, position.to_dict())

        logger.info(f"Deactivated position {position_id}")
        return position

    def add_question(self, position_id: str, question: str) -> Position:
        """
        Add a question to a position.

        Args:
            position_id: Position ID
            question: Question text

        Returns:
            Updated Position instance

        Raises:
            PositionNotFoundError: If position not found
            ValidationError: If question is invalid
        """
        position = self.get_position(position_id)
        if not position:
            raise PositionNotFoundError(f"Position {position_id} not found")

        if not question or not question.strip():
            raise ValidationError("Question cannot be empty")

        position.settings.add_question(question.strip())
        position_db.save_position(position_id, position.to_dict())

        logger.info(f"Added question to position {position_id}")
        return position

    def remove_question(self, position_id: str, question_index: int) -> Position:
        """
        Remove a question from a position.

        Args:
            position_id: Position ID
            question_index: Index of the question to remove

        Returns:
            Updated Position instance

        Raises:
            PositionNotFoundError: If position not found
            ValidationError: If question index is invalid
        """
        position = self.get_position(position_id)
        if not position:
            raise PositionNotFoundError(f"Position {position_id} not found")

        if question_index < 0 or question_index >= len(position.questions):
            raise ValidationError("Invalid question index")

        position.settings.remove_question(question_index)
        position_db.save_position(position_id, position.to_dict())

        logger.info(f"Removed question {question_index} from position {position_id}")
        return position

    def update_question(self, position_id: str, question_index: int, new_question: str) -> Position:
        """
        Update a question in a position.

        Args:
            position_id: Position ID
            question_index: Index of the question to update
            new_question: New question text

        Returns:
            Updated Position instance

        Raises:
            PositionNotFoundError: If position not found
            ValidationError: If question index is invalid or new question is empty
        """
        position = self.get_position(position_id)
        if not position:
            raise PositionNotFoundError(f"Position {position_id} not found")

        if question_index < 0 or question_index >= len(position.questions):
            raise ValidationError("Invalid question index")

        if not new_question or not new_question.strip():
            raise ValidationError("Question cannot be empty")

        position.settings.update_question(question_index, new_question.strip())
        position_db.save_position(position_id, position.to_dict())

        logger.info(f"Updated question {question_index} in position {position_id}")
        return position

    def get_position_stats(self) -> Dict[str, Any]:
        """
        Get position statistics.

        Returns:
            Dictionary with position statistics
        """
        try:
            all_positions = self.get_all_positions()

            stats = {
                "total": len(all_positions),
                "active": len([pos for pos in all_positions if pos.is_active]),
                "inactive": len([pos for pos in all_positions if not pos.is_active]),
                "total_questions": sum(len(pos.questions) for pos in all_positions),
                "avg_questions": (
                    sum(len(pos.questions) for pos in all_positions) / len(all_positions) if all_positions else 0
                ),
            }

            return stats
        except Exception as e:
            logger.error(f"Error getting position stats: {e}")
            return {"total": 0, "active": 0, "inactive": 0, "total_questions": 0, "avg_questions": 0}

    def search_positions(self, query: str) -> List[Position]:
        """
        Search positions by name or description.

        Args:
            query: Search query

        Returns:
            List of matching Position instances
        """
        if not query or not query.strip():
            return []

        query_lower = query.lower().strip()
        matching_positions = []

        try:
            all_positions = self.get_all_positions()
            for position in all_positions:
                if query_lower in position.name.lower() or query_lower in position.description.lower():
                    matching_positions.append(position)
        except Exception as e:
            logger.error(f"Error searching positions: {e}")

        return matching_positions

    def duplicate_position(self, position_id: str, new_name: str) -> Position:
        """
        Duplicate a position with a new name.

        Args:
            position_id: Position ID to duplicate
            new_name: Name for the new position

        Returns:
            New Position instance

        Raises:
            PositionNotFoundError: If original position not found
            ValidationError: If new name is invalid or already exists
        """
        original_position = self.get_position(position_id)
        if not original_position:
            raise PositionNotFoundError(f"Position {position_id} not found")

        if not new_name or not new_name.strip():
            raise ValidationError("New position name is required")

        # Check if new name already exists
        existing_positions = self.get_all_positions()
        for pos in existing_positions:
            if pos.name.lower() == new_name.lower():
                raise ValidationError(f"Position '{new_name}' already exists")

        # Create new position
        new_position = Position(
            name=new_name.strip(),
            description=original_position.description,
            questions=original_position.questions.copy(),
            is_active=False,  # Start as inactive
        )

        # Save to database
        position_db.save_position(new_position.id, new_position.to_dict())

        logger.info(f"Duplicated position {position_id} as {new_position.id}: {new_name}")
        return new_position


# Global service instance
position_service = PositionService()
