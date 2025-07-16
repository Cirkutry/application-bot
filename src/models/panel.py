"""
Panel model for the Simple Applications Bot.

This module defines the Panel data model with validation,
serialization, and business logic for panel management.
"""

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from ..core.exceptions import ValidationError


@dataclass
class PanelEmbed:
    """Panel embed configuration."""

    title: str = "Staff Applications"
    description: str = "Select a position below to apply!"
    color: str = "0x3498db"
    author_name: Optional[str] = None
    author_url: Optional[str] = None
    author_icon_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    image_url: Optional[str] = None
    footer_text: Optional[str] = None
    footer_icon_url: Optional[str] = None

    def validate(self) -> None:
        """
        Validate the panel embed configuration.

        Raises:
            ValidationError: If the embed configuration is invalid
        """
        if not self.title or not self.title.strip():
            raise ValidationError("Embed title cannot be empty")

        if not self.description or not self.description.strip():
            raise ValidationError("Embed description cannot be empty")

        # Validate color format
        if not self.color.startswith("0x"):
            raise ValidationError("Color must start with '0x'")

        try:
            int(self.color, 16)
        except ValueError:
            raise ValidationError("Invalid color format")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the panel embed to a dictionary.

        Returns:
            Dictionary representation of the panel embed
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PanelEmbed':
        """
        Create a panel embed from a dictionary.

        Args:
            data: Dictionary containing panel embed data

        Returns:
            PanelEmbed instance

        Raises:
            ValidationError: If the data is invalid
        """
        embed = cls(**data)
        embed.validate()
        return embed


class PanelStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DENIED = "denied"
    CLOSED = "closed"


@dataclass
class Panel:
    """Panel data model."""

    # Core fields
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    position: str = ""
    status: PanelStatus = PanelStatus.PENDING
    channel_id: str = ""
    message_id: Optional[str] = None
    positions: List[str] = field(default_factory=list)

    # Embed configuration
    embed: PanelEmbed = field(default_factory=PanelEmbed)

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate the panel after initialization."""
        self.validate()

    def validate(self) -> None:
        """
        Validate the panel data.

        Raises:
            ValidationError: If the panel data is invalid
        """
        if not self.channel_id:
            raise ValidationError("Channel ID cannot be empty")

        if not isinstance(self.positions, list):
            raise ValidationError("Positions must be a list")

        if not self.positions:
            raise ValidationError("Panel must have at least one position")

        # Validate positions
        for position in self.positions:
            if not position or not position.strip():
                raise ValidationError("Position names cannot be empty")

        # Validate embed
        if not isinstance(self.embed, PanelEmbed):
            raise ValidationError("Embed must be a PanelEmbed instance")

        self.embed.validate()

    def add_position(self, position: str) -> None:
        """
        Add a position to the panel.

        Args:
            position: The position to add

        Raises:
            ValidationError: If the position is invalid
        """
        if not position or not position.strip():
            raise ValidationError("Position cannot be empty")

        position = position.strip()
        if position in self.positions:
            raise ValidationError(f"Position '{position}' already exists in panel")

        self.positions.append(position)
        self.updated_at = datetime.now(timezone.utc)

    def remove_position(self, position: str) -> None:
        """
        Remove a position from the panel.

        Args:
            position: The position to remove

        Raises:
            ValidationError: If the position doesn't exist
        """
        if position not in self.positions:
            raise ValidationError(f"Position '{position}' not found in panel")

        self.positions.remove(position)
        self.updated_at = datetime.now(timezone.utc)

        # Ensure panel still has at least one position
        if not self.positions:
            raise ValidationError("Panel must have at least one position")

    def update_embed(self, embed: PanelEmbed) -> None:
        """
        Update the panel embed.

        Args:
            embed: New embed configuration

        Raises:
            ValidationError: If the embed is invalid
        """
        if not isinstance(embed, PanelEmbed):
            raise ValidationError("Embed must be a PanelEmbed instance")

        embed.validate()
        self.embed = embed
        self.updated_at = datetime.now(timezone.utc)

    def set_message_id(self, message_id: str) -> None:
        """
        Set the Discord message ID for this panel.

        Args:
            message_id: Discord message ID
        """
        self.message_id = message_id
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the panel to a dictionary.

        Returns:
            Dictionary representation of the panel
        """
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Panel':
        """
        Create a panel from a dictionary.

        Args:
            data: Dictionary containing panel data

        Returns:
            Panel instance

        Raises:
            ValidationError: If the data is invalid
        """
        # Handle datetime fields
        datetime_fields = ['created_at', 'updated_at']
        for field_name in datetime_fields:
            if field_name in data and data[field_name]:
                if isinstance(data[field_name], str):
                    data[field_name] = datetime.fromisoformat(data[field_name].replace('Z', '+00:00'))
                elif isinstance(data[field_name], datetime):
                    # Ensure timezone awareness
                    if data[field_name].tzinfo is None:
                        data[field_name] = data[field_name].replace(tzinfo=timezone.utc)

        # Handle embed field
        if 'embed' in data and isinstance(data['embed'], dict):
            data['embed'] = PanelEmbed.from_dict(data['embed'])

        return cls(**data)

    def get_position_count(self) -> int:
        """
        Get the number of positions in this panel.

        Returns:
            Number of positions
        """
        return len(self.positions)

    def has_position(self, position: str) -> bool:
        """
        Check if the panel has a specific position.

        Args:
            position: Position name to check

        Returns:
            True if the position exists in the panel
        """
        return position in self.positions

    @property
    def is_active(self) -> bool:
        """
        Check if the panel is active (has a message ID).

        Returns:
            True if the panel has a message ID
        """
        return self.message_id is not None
