"""
User service for the Simple Applications Bot.

This module provides business logic for user management,
including CRUD operations, validation, and user lifecycle.
"""

import logging
from typing import Any, Dict, List, Optional

from ..core.exceptions import UserNotFoundError, ValidationError
from ..core.user_db import user_db
from ..models import User, UserRole

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing users."""

    def create_user(self, user_id: str, username: str, role: UserRole = UserRole.USER) -> User:
        """
        Create a new user.

        Args:
            user_id: Discord user ID
            username: Discord username
            role: User role (default: USER)

        Returns:
            Created User instance

        Raises:
            ValidationError: If the user data is invalid
        """
        if not user_id or not user_id.strip():
            raise ValidationError("User ID is required")

        if not username or not username.strip():
            raise ValidationError("Username is required")

        # Check if user already exists
        existing_user = self.get_user(user_id)
        if existing_user:
            raise ValidationError(f"User {user_id} already exists")

        # Create user
        user = User(id=user_id.strip(), username=username.strip(), role=role)

        # Save to database
        user_db.save_user(user_id, user.to_dict())

        logger.info(f"Created user {user_id}: {username}")
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """
        Get a user by ID.

        Args:
            user_id: Discord user ID

        Returns:
            User instance or None if not found
        """
        try:
            data = user_db.load_user(user_id)
            if data:
                return User.from_dict(data)
            return None
        except Exception as e:
            logger.error(f"Error loading user {user_id}: {e}")
            return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Get a user by username.

        Args:
            username: Discord username

        Returns:
            User instance or None if not found
        """
        try:
            all_users = self.get_all_users()
            for user in all_users:
                if user.username.lower() == username.lower():
                    return user
            return None
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            return None

    def get_users_by_role(self, role: UserRole) -> List[User]:
        """
        Get all users with a specific role.

        Args:
            role: User role

        Returns:
            List of User instances
        """
        try:
            all_users = self.get_all_users()
            return [user for user in all_users if user.role == role]
        except Exception as e:
            logger.error(f"Error getting users with role {role}: {e}")
            return []

    def get_all_users(self) -> List[User]:
        """
        Get all users.

        Returns:
            List of all User instances
        """
        users = []
        try:
            user_ids = user_db.list_users()
            for user_id in user_ids:
                user = self.get_user(user_id)
                if user:
                    users.append(user)
        except Exception as e:
            logger.error(f"Error getting all users: {e}")

        return users

    def update_user(self, user_id: str, **kwargs) -> User:
        """
        Update a user.

        Args:
            user_id: Discord user ID
            **kwargs: Fields to update

        Returns:
            Updated User instance

        Raises:
            UserNotFoundError: If user not found
            ValidationError: If update data is invalid
        """
        user = self.get_user(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")

        # Update fields
        for key, value in kwargs.items():
            if hasattr(user, key):
                if key in ["user_id", "username"] and value:
                    setattr(user, key, value.strip())
                else:
                    setattr(user, key, value)

        # Validate and save
        user.validate()
        user_db.save_user(user_id, user.to_dict())

        logger.info(f"Updated user {user_id}")
        return user

    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user.

        Args:
            user_id: Discord user ID

        Returns:
            True if deleted, False if not found
        """
        try:
            success = user_db.delete_user(user_id)
            if success:
                logger.info(f"Deleted user {user_id}")
            return success
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False

    def promote_user(self, user_id: str, new_role: UserRole) -> User:
        """
        Promote a user to a higher role.

        Args:
            user_id: Discord user ID
            new_role: New role for the user

        Returns:
            Updated User instance

        Raises:
            UserNotFoundError: If user not found
            ValidationError: If new role is invalid
        """
        user = self.get_user(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")

        # Check if promotion is valid
        if new_role.value <= user.role.value:
            raise ValidationError(f"Cannot promote user from {user.role.value} to {new_role.value}")

        user.role = new_role
        user_db.save_user(user_id, user.to_dict())

        logger.info(f"Promoted user {user_id} to role {new_role.value}")
        return user

    def demote_user(self, user_id: str, new_role: UserRole) -> User:
        """
        Demote a user to a lower role.

        Args:
            user_id: Discord user ID
            new_role: New role for the user

        Returns:
            Updated User instance

        Raises:
            UserNotFoundError: If user not found
            ValidationError: If new role is invalid
        """
        user = self.get_user(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")

        # Check if demotion is valid
        if new_role.value >= user.role.value:
            raise ValidationError(f"Cannot demote user from {user.role.value} to {new_role.value}")

        user.role = new_role
        user_db.save_user(user_id, user.to_dict())

        logger.info(f"Demoted user {user_id} to role {new_role.value}")
        return user

    def set_user_role(self, user_id: str, role: UserRole) -> User:
        """
        Set a user's role directly.

        Args:
            user_id: Discord user ID
            role: New role for the user

        Returns:
            Updated User instance

        Raises:
            UserNotFoundError: If user not found
        """
        user = self.get_user(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")

        user.role = role
        user_db.save_user(user_id, user.to_dict())

        logger.info(f"Set user {user_id} role to {role.value}")
        return user

    def has_permission(self, user_id: str, required_role: UserRole) -> bool:
        """
        Check if a user has the required role or higher.

        Args:
            user_id: Discord user ID
            required_role: Minimum required role

        Returns:
            True if user has required role or higher, False otherwise
        """
        user = self.get_user(user_id)
        if not user:
            return False

        return user.role.value >= required_role.value

    def is_admin(self, user_id: str) -> bool:
        """
        Check if a user is an admin.

        Args:
            user_id: Discord user ID

        Returns:
            True if user is admin, False otherwise
        """
        return self.has_permission(user_id, UserRole.ADMIN)

    def is_moderator(self, user_id: str) -> bool:
        """
        Check if a user is a moderator or higher.

        Args:
            user_id: Discord user ID

        Returns:
            True if user is moderator or higher, False otherwise
        """
        return self.has_permission(user_id, UserRole.MODERATOR)

    def get_user_stats(self) -> Dict[str, Any]:
        """
        Get user statistics.

        Returns:
            Dictionary with user statistics
        """
        try:
            all_users = self.get_all_users()

            stats = {
                "total": len(all_users),
                "admins": len([user for user in all_users if user.role == UserRole.ADMIN]),
                "moderators": len([user for user in all_users if user.role == UserRole.MODERATOR]),
                "reviewers": len([user for user in all_users if user.role == UserRole.REVIEWER]),
                "users": len([user for user in all_users if user.role == UserRole.USER]),
            }

            return stats
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {"total": 0, "admins": 0, "moderators": 0, "reviewers": 0, "users": 0}

    def search_users(self, query: str) -> List[User]:
        """
        Search users by username.

        Args:
            query: Search query

        Returns:
            List of matching User instances
        """
        if not query or not query.strip():
            return []

        query_lower = query.lower().strip()
        matching_users = []

        try:
            all_users = self.get_all_users()
            for user in all_users:
                if query_lower in user.username.lower():
                    matching_users.append(user)
        except Exception as e:
            logger.error(f"Error searching users: {e}")

        return matching_users

    def get_or_create_user(self, user_id: str, username: str) -> User:
        """
        Get a user or create if they don't exist.

        Args:
            user_id: Discord user ID
            username: Discord username

        Returns:
            User instance
        """
        user = self.get_user(user_id)
        if user:
            # Update username if it changed
            if user.username != username:
                user.username = username
                user_db.save_user(user_id, user.to_dict())
                logger.info(f"Updated username for user {user_id}: {username}")
            return user

        # Create new user
        return self.create_user(user_id, username)

    def get_active_users(self, days: int = 30) -> List[User]:
        """
        Get users who have been active recently.
        Note: This is a placeholder implementation since we don't track activity yet.

        Args:
            days: Number of days to consider for activity

        Returns:
            List of active User instances
        """
        # For now, return all users since we don't track activity
        # In a real implementation, you would check last_activity timestamps
        return self.get_all_users()

    def get_user_activity_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get a summary of user activity.
        Note: This is a placeholder implementation since we don't track activity yet.

        Args:
            user_id: Discord user ID

        Returns:
            Dictionary with user activity summary
        """
        user = self.get_user(user_id)
        if not user:
            return {}

        # Placeholder activity summary
        # In a real implementation, you would track and return actual activity data
        return {
            "id": user.id,
            "username": user.username,
            "role": user.role.value,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_activity": None,  # Would be tracked in real implementation
            "total_applications": 0,  # Would be calculated from application service
            "total_reviews": 0,  # Would be calculated from panel service
        }


# Global service instance
user_service = UserService()
