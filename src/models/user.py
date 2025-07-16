"""
User model for the Simple Applications Bot.

This module defines the User data model with validation,
serialization, and business logic for user management.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from ..core.exceptions import ValidationError


class UserRole(Enum):
    """User role enumeration."""

    ADMIN = "admin"
    MODERATOR = "moderator"
    REVIEWER = "reviewer"
    MEMBER = "member"
    VIEWER = "viewer"
    USER = "limited_user"  # No access role?


@dataclass
class UserPermissions:
    """User permissions configuration."""

    can_view_applications: bool = False
    can_review_applications: bool = False
    can_manage_positions: bool = False
    can_manage_panels: bool = False
    can_manage_users: bool = False
    can_access_dashboard: bool = False

    def validate(self) -> None:
        """
        Validate the user permissions.

        Raises:
            ValidationError: If the permissions are invalid
        """
        if not isinstance(self.can_view_applications, bool):
            raise ValidationError("can_view_applications must be a boolean")

        if not isinstance(self.can_review_applications, bool):
            raise ValidationError("can_review_applications must be a boolean")

        if not isinstance(self.can_manage_positions, bool):
            raise ValidationError("can_manage_positions must be a boolean")

        if not isinstance(self.can_manage_panels, bool):
            raise ValidationError("can_manage_panels must be a boolean")

        if not isinstance(self.can_manage_users, bool):
            raise ValidationError("can_manage_users must be a boolean")

        if not isinstance(self.can_access_dashboard, bool):
            raise ValidationError("can_access_dashboard must be a boolean")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the user permissions to a dictionary.

        Returns:
            Dictionary representation of the user permissions
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPermissions':
        """
        Create user permissions from a dictionary.

        Args:
            data: Dictionary containing user permissions data

        Returns:
            UserPermissions instance

        Raises:
            ValidationError: If the data is invalid
        """
        permissions = cls(**data)
        permissions.validate()
        return permissions

    @classmethod
    def get_admin_permissions(cls) -> 'UserPermissions':
        """
        Get admin permissions.

        Returns:
            UserPermissions instance with admin privileges
        """
        return cls(
            can_view_applications=True,
            can_review_applications=True,
            can_manage_positions=True,
            can_manage_panels=True,
            can_manage_users=True,
            can_access_dashboard=True,
        )

    @classmethod
    def get_moderator_permissions(cls) -> 'UserPermissions':
        """
        Get moderator permissions.

        Returns:
            UserPermissions instance with moderator privileges
        """
        return cls(
            can_view_applications=True,
            can_review_applications=True,
            can_manage_positions=False,
            can_manage_panels=False,
            can_manage_users=False,
            can_access_dashboard=True,
        )

    @classmethod
    def get_viewer_permissions(cls) -> 'UserPermissions':
        """
        Get viewer permissions.

        Returns:
            UserPermissions instance with viewer privileges
        """
        return cls(
            can_view_applications=True,
            can_review_applications=False,
            can_manage_positions=False,
            can_manage_panels=False,
            can_manage_users=False,
            can_access_dashboard=True,
        )


@dataclass
class User:
    """User data model."""

    # Core fields
    id: str = ""
    username: str = ""
    discriminator: Optional[str] = None
    avatar: Optional[str] = None

    # Role and permissions
    role: UserRole = UserRole.MEMBER
    permissions: UserPermissions = field(default_factory=UserPermissions)

    # Discord integration
    discord_id: str = ""
    discord_roles: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: Optional[datetime] = None

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate the user after initialization."""
        self.validate()

    def validate(self) -> None:
        """
        Validate the user data.

        Raises:
            ValidationError: If the user data is invalid
        """
        if not self.id:
            raise ValidationError("User ID cannot be empty")

        if not self.username or not self.username.strip():
            raise ValidationError("Username cannot be empty")

        if not isinstance(self.discord_roles, list):
            raise ValidationError("Discord roles must be a list")

        # Validate role
        if not isinstance(self.role, UserRole):
            try:
                self.role = UserRole(self.role)
            except ValueError:
                raise ValidationError(f"Invalid role: {self.role}")

        # Validate permissions
        if not isinstance(self.permissions, UserPermissions):
            raise ValidationError("Permissions must be a UserPermissions instance")

        self.permissions.validate()

    def update_discord_info(
        self, username: str, discriminator: Optional[str] = None, avatar: Optional[str] = None
    ) -> None:
        """
        Update Discord information.

        Args:
            username: New username
            discriminator: New discriminator
            avatar: New avatar URL
        """
        if username and username.strip():
            self.username = username.strip()

        self.discriminator = discriminator
        self.avatar = avatar
        self.updated_at = datetime.now(timezone.utc)

    def add_discord_role(self, role_id: str) -> None:
        """
        Add a Discord role to the user.

        Args:
            role_id: Discord role ID to add
        """
        if role_id and role_id not in self.discord_roles:
            self.discord_roles.append(role_id)
            self.updated_at = datetime.now(timezone.utc)

    def remove_discord_role(self, role_id: str) -> None:
        """
        Remove a Discord role from the user.

        Args:
            role_id: Discord role ID to remove
        """
        if role_id in self.discord_roles:
            self.discord_roles.remove(role_id)
            self.updated_at = datetime.now(timezone.utc)

    def has_discord_role(self, role_id: str) -> bool:
        """
        Check if the user has a specific Discord role.

        Args:
            role_id: Discord role ID to check

        Returns:
            True if the user has the role
        """
        return role_id in self.discord_roles

    def set_role(self, role: UserRole) -> None:
        """
        Set the user's role and update permissions accordingly.

        Args:
            role: New role for the user
        """
        if not isinstance(role, UserRole):
            try:
                role = UserRole(role)
            except ValueError:
                raise ValidationError(f"Invalid role: {role}")

        self.role = role

        # Update permissions based on role
        if role == UserRole.ADMIN:
            self.permissions = UserPermissions.get_admin_permissions()
        elif role == UserRole.MODERATOR:
            self.permissions = UserPermissions.get_moderator_permissions()
        elif role == UserRole.VIEWER:
            self.permissions = UserPermissions.get_viewer_permissions()
        else:  # MEMBER
            self.permissions = UserPermissions()

        self.updated_at = datetime.now(timezone.utc)

    def update_last_seen(self) -> None:
        """Update the last seen timestamp."""
        self.last_seen = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the user to a dictionary.

        Returns:
            Dictionary representation of the user
        """
        data = asdict(self)
        data['role'] = self.role.value
        data['permissions'] = self.permissions.to_dict()
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()

        if self.last_seen:
            data['last_seen'] = self.last_seen.isoformat()

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """
        Create a user from a dictionary.

        Args:
            data: Dictionary containing user data

        Returns:
            User instance

        Raises:
            ValidationError: If the data is invalid
        """
        # Handle datetime fields
        datetime_fields = ['created_at', 'updated_at', 'last_seen']
        for field_name in datetime_fields:
            if field_name in data and data[field_name]:
                if isinstance(data[field_name], str):
                    data[field_name] = datetime.fromisoformat(data[field_name].replace('Z', '+00:00'))
                elif isinstance(data[field_name], datetime):
                    # Ensure timezone awareness
                    if data[field_name].tzinfo is None:
                        data[field_name] = data[field_name].replace(tzinfo=timezone.utc)

        # Handle role field
        if 'role' in data and isinstance(data['role'], str):
            try:
                data['role'] = UserRole(data['role'])
            except ValueError:
                raise ValidationError(f"Invalid role: {data['role']}")

        # Handle permissions field
        if 'permissions' in data and isinstance(data['permissions'], dict):
            data['permissions'] = UserPermissions.from_dict(data['permissions'])

        return cls(**data)

    def is_admin(self) -> bool:
        """
        Check if the user is an admin.

        Returns:
            True if the user is an admin
        """
        return self.role == UserRole.ADMIN

    def is_moderator(self) -> bool:
        """
        Check if the user is a moderator.

        Returns:
            True if the user is a moderator
        """
        return self.role == UserRole.MODERATOR

    def can_review_applications(self) -> bool:
        """
        Check if the user can review applications.

        Returns:
            True if the user can review applications
        """
        return self.permissions.can_review_applications

    def can_manage_positions(self) -> bool:
        """
        Check if the user can manage positions.

        Returns:
            True if the user can manage positions
        """
        return self.permissions.can_manage_positions

    def can_access_dashboard(self) -> bool:
        """
        Check if the user can access the dashboard.

        Returns:
            True if the user can access the dashboard
        """
        return self.permissions.can_access_dashboard
