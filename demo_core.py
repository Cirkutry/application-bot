#!/usr/bin/env python3
# Run this script from the project root with: python -m demo_core
"""
Demonstration script for the core module.

This script shows how to use the core components including configuration,
logging, database operations, and custom exceptions.
"""

from src.core import (
    DatabaseError,
    ValidationError,
    application_db,
    config,
    config_db,
    log_startup_info,
    setup_colored_logging,
)


def main():
    """Demonstrate core module functionality."""
    print("🚀 Simple Applications Bot - Core Module Demo")
    print("=" * 50)

    # Set up logging
    setup_colored_logging()

    # Log startup info
    log_startup_info()

    print("\n📋 Configuration Demo:")
    print(f"  Web Host: {config.WEB_HOST}")
    print(f"  Web Port: {config.WEB_PORT}")
    print(f"  Storage Directory: {config.STORAGE_DIR}")
    print(f"  Applications Directory: {config.APPLICATIONS_DIR}")

    # Validate configuration
    missing_vars = config.validate()
    if missing_vars:
        print(f"\n⚠️  Missing configuration variables: {len(missing_vars)}")
        for var in missing_vars:
            print(f"    - {var}")
    else:
        print("\n✅ Configuration validation passed")

    # Ensure directories and files exist
    print("\n📁 Setting up directories and files...")
    config.ensure_directories()
    config.ensure_files()
    print("✅ Directories and files created")

    # Database operations demo
    print("\n💾 Database Operations Demo:")

    # Test application database
    try:
        test_app_id = "demo-app-123"
        test_app_data = {
            "id": test_app_id,
            "user_id": "123456789",
            "user_name": "Demo User",
            "position": "Moderator",
            "status": "pending",
            "questions": ["What is your experience?", "Why do you want to join?"],
            "answers": ["I have 2 years of experience", "I want to help the community"],
        }

        # Save application
        application_db.save_application(test_app_id, test_app_data)
        print(f"  ✅ Saved application: {test_app_id}")

        # Load application
        loaded_app = application_db.load_application(test_app_id)
        if loaded_app:
            print(f"  ✅ Loaded application: {loaded_app['user_name']} - {loaded_app['position']}")

        # List applications
        apps = application_db.list_applications()
        print(f"  📋 Total applications: {len(apps)}")

        # Clean up
        application_db.delete_application(test_app_id)
        print(f"  🗑️  Deleted application: {test_app_id}")

    except (ValidationError, DatabaseError) as e:
        print(f"  ❌ Database error: {e}")

    # Test configuration database
    try:
        # Test questions
        questions_data = {
            "Moderator": {
                "enabled": True,
                "questions": ["What is your experience?", "Why do you want to join?"],
                "time_limit": 60,
            }
        }
        config_db.save_questions(questions_data)
        loaded_questions = config_db.load_questions()
        print(f"  ✅ Questions saved and loaded: {len(loaded_questions)} positions")

        # Test panels
        panels_data = {
            "demo-panel": {"id": "demo-panel", "channel_id": "123456789", "positions": ["Moderator", "Helper"]}
        }
        config_db.save_panels(panels_data)
        loaded_panels = config_db.load_panels()
        print(f"  ✅ Panels saved and loaded: {len(loaded_panels)} panels")

        # Test active applications
        active_apps = {"demo-user": {"user_id": "demo-user", "position": "Moderator", "current_question": 0}}
        config_db.save_active_applications(active_apps)
        loaded_active = config_db.load_active_applications()
        print(f"  ✅ Active applications saved and loaded: {len(loaded_active)} active")

        # Test viewer roles
        viewer_roles = ["role-1", "role-2"]
        config_db.save_viewer_roles(viewer_roles)
        loaded_roles = config_db.load_viewer_roles()
        print(f"  ✅ Viewer roles saved and loaded: {len(loaded_roles)} roles")

    except (ValidationError, DatabaseError) as e:
        print(f"  ❌ Configuration database error: {e}")

    # Exception handling demo
    print("\n⚠️  Exception Handling Demo:")

    try:
        # This should raise a ValidationError
        application_db.save_application("", {"test": "data"})
    except ValidationError as e:
        print(f"  ✅ Caught ValidationError: {e}")

    try:
        # This should raise a ValidationError
        application_db.save_application("test", "not a dict")  # type: ignore
    except ValidationError as e:
        print(f"  ✅ Caught ValidationError: {e}")

    print("\n🎉 Core module demonstration completed successfully!")
    print("=" * 50)


if __name__ == "__main__":
    main()
