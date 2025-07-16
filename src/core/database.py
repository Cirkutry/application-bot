"""
Database/persistence layer for the Simple Applications Bot.

This module provides a centralized interface for all data persistence operations,
including file-based storage with proper error handling and validation.
"""

# TODO: Implement a real database, or at least a mock database to replace the file-based database

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import config
from .exceptions import DatabaseError, ValidationError

logger = logging.getLogger(__name__)


class FileDatabase:
    """File-based database for storing application data."""

    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the file database.

        Args:
            base_dir: Base directory for data storage (default: config.STORAGE_DIR)
        """
        self.base_dir = Path(base_dir or config.STORAGE_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, filename: str) -> Path:
        """Get the full path for a file."""
        return self.base_dir / filename

    def read_json(self, filename: str, default: Any = None) -> Any:
        """
        Read JSON data from a file.

        Args:
            filename: Name of the file to read
            default: Default value if file doesn't exist or is invalid

        Returns:
            Parsed JSON data or default value

        Raises:
            DatabaseError: If there's an error reading the file
        """
        file_path = self._get_file_path(filename)

        if not file_path.exists():
            return default

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filename}: {e}")
            raise DatabaseError(f"Invalid JSON in {filename}: {e}")
        except Exception as e:
            logger.error(f"Error reading {filename}: {e}")
            raise DatabaseError(f"Error reading {filename}: {e}")

    def write_json(self, filename: str, data: Any, indent: int = 4) -> None:
        """
        Write JSON data to a file.

        Args:
            filename: Name of the file to write
            data: Data to write
            indent: JSON indentation (default: 4)

        Raises:
            DatabaseError: If there's an error writing the file
        """
        file_path = self._get_file_path(filename)

        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)

            logger.debug(f"Successfully wrote data to {filename}")
        except Exception as e:
            logger.error(f"Error writing {filename}: {e}")
            raise DatabaseError(f"Error writing {filename}: {e}")

    def delete_file(self, filename: str) -> bool:
        """
        Delete a file.

        Args:
            filename: Name of the file to delete

        Returns:
            True if file was deleted, False if it didn't exist

        Raises:
            DatabaseError: If there's an error deleting the file
        """
        file_path = self._get_file_path(filename)

        if not file_path.exists():
            return False

        try:
            file_path.unlink()
            logger.debug(f"Successfully deleted {filename}")
            return True
        except Exception as e:
            logger.error(f"Error deleting {filename}: {e}")
            raise DatabaseError(f"Error deleting {filename}: {e}")

    def file_exists(self, filename: str) -> bool:
        """
        Check if a file exists.

        Args:
            filename: Name of the file to check

        Returns:
            True if file exists, False otherwise
        """
        return self._get_file_path(filename).exists()

    def list_files(self, pattern: str = "*") -> List[str]:
        """
        List files in the database directory.

        Args:
            pattern: File pattern to match (default: all files)

        Returns:
            List of matching filenames
        """
        try:
            return [f.name for f in self.base_dir.glob(pattern)]
        except Exception as e:
            logger.error(f"Error listing files with pattern {pattern}: {e}")
            return []


class ApplicationDatabase(FileDatabase):
    """Database for application-specific data."""

    def __init__(self):
        """Initialize the application database."""
        super().__init__(config.APPLICATIONS_DIR)

    def save_application(self, application_id: str, data: Dict[str, Any]) -> None:
        """
        Save an application to the database.

        Args:
            application_id: Unique application ID
            data: Application data

        Raises:
            ValidationError: If application data is invalid
            DatabaseError: If there's an error saving the data
        """
        if not application_id:
            raise ValidationError("Application ID cannot be empty")

        if not isinstance(data, dict):
            raise ValidationError("Application data must be a dictionary")

        filename = f"{application_id}.json"
        self.write_json(filename, data)

    def load_application(self, application_id: str) -> Optional[Dict[str, Any]]:
        """
        Load an application from the database.

        Args:
            application_id: Unique application ID

        Returns:
            Application data or None if not found

        Raises:
            ValidationError: If application ID is invalid
        """
        if not application_id:
            raise ValidationError("Application ID cannot be empty")

        filename = f"{application_id}.json"
        return self.read_json(filename)

    def delete_application(self, application_id: str) -> bool:
        """
        Delete an application from the database.

        Args:
            application_id: Unique application ID

        Returns:
            True if application was deleted, False if it didn't exist

        Raises:
            ValidationError: If application ID is invalid
        """
        if not application_id:
            raise ValidationError("Application ID cannot be empty")

        filename = f"{application_id}.json"
        return self.delete_file(filename)

    def list_applications(self) -> List[str]:
        """
        List all application IDs in the database.

        Returns:
            List of application IDs
        """
        files = self.list_files("*.json")
        return [f.replace('.json', '') for f in files]


class ConfigDatabase(FileDatabase):
    """Database for configuration data."""

    def __init__(self):
        """Initialize the configuration database."""
        super().__init__(config.STORAGE_DIR)

    def load_questions(self) -> Dict[str, Any]:
        """Load questions configuration."""
        return self.read_json("questions.json", {})

    def save_questions(self, data: Dict[str, Any]) -> None:
        """Save questions configuration."""
        self.write_json("questions.json", data)

    def load_panels(self) -> Dict[str, Any]:
        """Load panels configuration."""
        return self.read_json("panels.json", {})

    def save_panels(self, data: Dict[str, Any]) -> None:
        """Save panels configuration."""
        self.write_json("panels.json", data)

    def load_active_applications(self) -> Dict[str, Any]:
        """Load active applications."""
        return self.read_json("active_applications.json", {})

    def save_active_applications(self, data: Dict[str, Any]) -> None:
        """Save active applications."""
        self.write_json("active_applications.json", data)

    def load_viewer_roles(self) -> List[str]:
        """Load viewer roles configuration."""
        return self.read_json("viewer_roles.json", [])

    def save_viewer_roles(self, data: List[str]) -> None:
        """Save viewer roles configuration."""
        self.write_json("viewer_roles.json", data)


# Global database instances
application_db = ApplicationDatabase()
config_db = ConfigDatabase()
