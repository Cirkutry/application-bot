"""
Unit tests for the core module.

This module tests the foundational components including configuration,
logging, database operations, and custom exceptions.
"""

import logging
import os
import sys
import tempfile
from pathlib import Path

import pytest

from src.core import (
    ApplicationBotError,
    ApplicationDatabase,
    ConfigDatabase,
    ConfigurationError,
    DatabaseError,
    FileDatabase,
    ValidationError,
    config,
    get_logger,
    setup_logging,
)

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestConfig:
    """Test configuration management."""

    def test_config_attributes(self):
        """Test that config has expected attributes."""
        assert hasattr(config, 'DISCORD_TOKEN')
        assert hasattr(config, 'SERVER_ID')
        assert hasattr(config, 'WEB_HOST')
        assert hasattr(config, 'WEB_PORT')
        assert hasattr(config, 'STORAGE_DIR')
        assert hasattr(config, 'APPLICATIONS_DIR')

    def test_validate_method(self):
        """Test configuration validation."""
        # This test assumes some environment variables are not set
        missing = config.validate()
        assert isinstance(missing, list)

    def test_get_web_url(self):
        """Test web URL generation."""
        url = config.get_web_url()
        assert isinstance(url, str)
        assert url.startswith('http://')

    def test_get_application_url(self):
        """Test application URL generation."""
        app_id = "test-123"
        url = config.get_application_url(app_id)
        assert isinstance(url, str)
        assert app_id in url
        assert url.endswith(f"/application/{app_id}")


class TestExceptions:
    """Test custom exceptions."""

    def test_exception_inheritance(self):
        """Test that all exceptions inherit from ApplicationBotError."""
        exceptions = [
            ConfigurationError,
            ValidationError,
            DatabaseError,
        ]

        for exc_class in exceptions:
            assert issubclass(exc_class, ApplicationBotError)

    def test_exception_instantiation(self):
        """Test that exceptions can be instantiated."""
        message = "Test error message"

        exc = ConfigurationError(message)
        assert str(exc) == message

        exc = ValidationError(message)
        assert str(exc) == message

        exc = DatabaseError(message)
        assert str(exc) == message


class TestFileDatabase:
    """Test file database operations."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db = FileDatabase(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_write_and_read_json(self):
        """Test writing and reading JSON data."""
        test_data = {"key": "value", "number": 42}
        filename = "test.json"

        # Write data
        self.db.write_json(filename, test_data)

        # Read data
        result = self.db.read_json(filename)
        assert result == test_data

    def test_read_nonexistent_file(self):
        """Test reading a file that doesn't exist."""
        result = self.db.read_json("nonexistent.json", default="default")
        assert result == "default"

    def test_file_exists(self):
        """Test file existence check."""
        filename = "test.json"
        assert not self.db.file_exists(filename)

        self.db.write_json(filename, {"test": "data"})
        assert self.db.file_exists(filename)

    def test_delete_file(self):
        """Test file deletion."""
        filename = "test.json"
        self.db.write_json(filename, {"test": "data"})
        assert self.db.file_exists(filename)

        result = self.db.delete_file(filename)
        assert result is True
        assert not self.db.file_exists(filename)

    def test_delete_nonexistent_file(self):
        """Test deleting a file that doesn't exist."""
        result = self.db.delete_file("nonexistent.json")
        assert result is False


class TestApplicationDatabase:
    """Test application database operations."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db = ApplicationDatabase()
        self.db.base_dir = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_load_application(self):
        """Test saving and loading an application."""
        app_id = "test-app-123"
        app_data = {"id": app_id, "user_id": "123456789", "position": "Moderator", "status": "pending"}

        # Save application
        self.db.save_application(app_id, app_data)

        # Load application
        result = self.db.load_application(app_id)
        assert result == app_data

    def test_save_application_invalid_id(self):
        """Test saving application with invalid ID."""
        with pytest.raises(ValidationError):
            self.db.save_application("", {"test": "data"})

    def test_save_application_invalid_data(self):
        """Test saving application with invalid data."""
        with pytest.raises(ValidationError):
            self.db.save_application("test", "not a dict")  # type: ignore

    def test_load_nonexistent_application(self):
        """Test loading an application that doesn't exist."""
        result = self.db.load_application("nonexistent")
        assert result is None

    def test_delete_application(self):
        """Test deleting an application."""
        app_id = "test-app-123"
        app_data = {"test": "data"}

        self.db.save_application(app_id, app_data)
        assert self.db.load_application(app_id) == app_data

        result = self.db.delete_application(app_id)
        assert result is True
        assert self.db.load_application(app_id) is None


class TestConfigDatabase:
    """Test configuration database operations."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db = ConfigDatabase()
        self.db.base_dir = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_questions_operations(self):
        """Test questions configuration operations."""
        questions_data = {
            "Moderator": {"enabled": True, "questions": ["What is your experience?", "Why do you want to join?"]}
        }

        # Save questions
        self.db.save_questions(questions_data)

        # Load questions
        result = self.db.load_questions()
        assert result == questions_data

    def test_panels_operations(self):
        """Test panels configuration operations."""
        panels_data = {"panel-1": {"id": "panel-1", "channel_id": "123456789", "positions": ["Moderator", "Helper"]}}

        # Save panels
        self.db.save_panels(panels_data)

        # Load panels
        result = self.db.load_panels()
        assert result == panels_data

    def test_active_applications_operations(self):
        """Test active applications operations."""
        active_apps = {"user-123": {"user_id": "user-123", "position": "Moderator", "current_question": 0}}

        # Save active applications
        self.db.save_active_applications(active_apps)

        # Load active applications
        result = self.db.load_active_applications()
        assert result == active_apps

    def test_viewer_roles_operations(self):
        """Test viewer roles operations."""
        viewer_roles = ["role-1", "role-2", "role-3"]

        # Save viewer roles
        self.db.save_viewer_roles(viewer_roles)

        # Load viewer roles
        result = self.db.load_viewer_roles()
        assert result == viewer_roles


class TestLogging:
    """Test logging functionality."""

    def test_get_logger(self):
        """Test getting a logger instance."""
        logger = get_logger("test_logger")
        assert isinstance(logger, type(logging.getLogger()))
        assert logger.name == "test_logger"

    def test_setup_logging(self):
        """Test logging setup."""
        # This test just ensures the function doesn't raise an exception
        setup_logging()
        assert True  # If we get here, no exception was raised
