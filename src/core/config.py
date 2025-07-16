"""
Configuration management for the Simple Applications Bot.

This module centralizes all configuration settings and environment variables,
providing a single source of truth for application configuration.
"""

import os
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Centralized configuration management."""

    # Discord Bot Configuration
    DISCORD_TOKEN: str = os.getenv("TOKEN", "")
    SERVER_ID: str = os.getenv("SERVER_ID", "")

    # Web Server Configuration
    WEB_HOST: str = os.getenv("WEB_HOST", "localhost")
    WEB_PORT: int = int(os.getenv("WEB_PORT", "8080"))
    WEB_EXTERNAL: Optional[str] = os.getenv("WEB_EXTERNAL")

    # Discord OAuth Configuration
    OAUTH_CLIENT_ID: str = os.getenv("OAUTH_CLIENT_ID", "")
    OAUTH_CLIENT_SECRET: str = os.getenv("OAUTH_CLIENT_SECRET", "")
    OAUTH_REDIRECT_URI: str = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8080/auth/callback")

    # Storage Configuration
    STORAGE_DIR: str = "storage"
    APPLICATIONS_DIR: str = "storage/applications"
    LOGS_DIR: str = "storage/logs"

    # File Paths
    ACTIVE_APPLICATIONS_FILE: str = "storage/active_applications.json"
    QUESTIONS_FILE: str = "storage/questions.json"
    PANELS_FILE: str = "storage/panels.json"
    VIEWER_ROLES_FILE: str = "storage/viewer_roles.json"

    # Discord API Configuration
    DISCORD_API_ENDPOINT: str = "https://discord.com/api/v10"

    @classmethod
    def validate(cls) -> list[str]:
        """
        Validate that all required configuration values are present.

        Returns:
            List of missing required configuration keys.
        """
        missing = []

        required_vars = {
            "DISCORD_TOKEN": "Discord Bot Token",
            "SERVER_ID": "Discord Server ID",
            "OAUTH_CLIENT_ID": "Discord OAuth Client ID",
            "OAUTH_CLIENT_SECRET": "Discord OAuth Client Secret",
        }

        for var_name, description in required_vars.items():
            if not getattr(cls, var_name):
                missing.append(f"{var_name} ({description})")

        return missing

    @classmethod
    def get_web_url(cls) -> str:
        """
        Get the web dashboard URL.

        Returns:
            The web dashboard URL, using WEB_EXTERNAL if set, otherwise WEB_HOST:WEB_PORT.
        """
        if cls.WEB_EXTERNAL:
            return cls.WEB_EXTERNAL.rstrip('/')
        return f"http://{cls.WEB_HOST}:{cls.WEB_PORT}"

    @classmethod
    def get_application_url(cls, application_id: str) -> str:
        """
        Get the URL for a specific application.

        Args:
            application_id: The application ID.

        Returns:
            The URL for the application.
        """
        base_url = cls.get_web_url()
        return f"{base_url}/application/{application_id}"

    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure all required directories exist."""
        import pathlib

        directories = [
            cls.STORAGE_DIR,
            cls.APPLICATIONS_DIR,
            cls.LOGS_DIR,
        ]

        for directory in directories:
            pathlib.Path(directory).mkdir(exist_ok=True)

    @classmethod
    def ensure_files(cls) -> None:
        """Ensure all required files exist with default content."""
        files_with_defaults = [
            (cls.VIEWER_ROLES_FILE, "[]"),
            (cls.QUESTIONS_FILE, "{}"),
            (cls.PANELS_FILE, "{}"),
            (cls.ACTIVE_APPLICATIONS_FILE, "{}"),
        ]

        for file_path, default_content in files_with_defaults:
            if not os.path.exists(file_path):
                # Ensure directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                # Write default content
                with open(file_path, "w") as f:
                    f.write(default_content)


# Global configuration instance
config = Config()
