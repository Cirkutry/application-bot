#!/usr/bin/env python3
# Run this script from the project root with: python -m demo_models
"""
Demonstration script for the models module.

This script shows how to use the data models including Application,
Position, Panel, and User with their validation and business logic.
"""

from src.core.exceptions import ValidationError
from src.models import (
    Application,
    ApplicationStatus,
    Panel,
    PanelEmbed,
    Position,
    PositionSettings,
    User,
    UserPermissions,
    UserRole,
)


def demo_application():
    """Demonstrate Application model functionality."""
    print("📝 Application Model Demo:")
    print("-" * 30)

    try:
        # Create a new application
        app = Application(
            user_id="123456789",
            user_name="John Doe",
            position="Moderator",
            questions=["What is your experience?", "Why do you want to join?"],
        )
        print(f"  ✅ Created application: {app.id}")
        print(f"  📊 Progress: {app.get_progress():.1%}")

        # Add answers
        app.add_answer("I have 2 years of moderation experience")
        print("  ✅ Added answer 1")
        print(f"  📊 Progress: {app.get_progress():.1%}")

        app.add_answer("I want to help maintain a positive community")
        print("  ✅ Added answer 2")
        print(f"  📊 Progress: {app.get_progress():.1%}")

        # Submit application
        app.submit()
        print("  ✅ Application submitted")

        # Review application
        app.review(ApplicationStatus.ACCEPTED, "admin-123", "Great experience and motivation")
        print(f"  ✅ Application reviewed: {app.status.value}")

        # Convert to dict and back
        app_dict = app.to_dict()
        Application.from_dict(app_dict)
        print("  ✅ Serialization/deserialization successful")

        print(f"  📋 Question-Answer pairs: {len(app.get_question_answer_pairs())}")

    except ValidationError as e:
        print(f"  ❌ Validation error: {e}")


def demo_position():
    """Demonstrate Position model functionality."""
    print("\n🎯 Position Model Demo:")
    print("-" * 30)

    try:
        # Create position settings
        settings = PositionSettings(
            enabled=True, time_limit=30, questions=["What is your experience?", "Why do you want to join?"]
        )
        settings.get_default_messages("Helper")
        print("  ✅ Created position settings")
        print(f"  📝 Questions: {len(settings.questions)}")
        print(f"  ⏱️  Time limit: {settings.time_limit} minutes")

        # Create position
        position = Position(name="Helper", settings=settings)
        print(f"  ✅ Created position: {position.name}")

        # Add question
        position.settings.add_question("What are your strengths?")
        print("  ✅ Added question")
        print(f"  📝 Total questions: {position.get_question_count()}")

        # Update question
        position.settings.update_question(0, "What is your moderation experience?")
        print("  ✅ Updated question")

        # Reorder questions
        position.settings.reorder_questions([2, 0, 1])
        print("  ✅ Reordered questions")

        # Convert to dict and back
        pos_dict = position.to_dict()
        Position.from_dict(pos_dict)
        print("  ✅ Serialization/deserialization successful")

    except ValidationError as e:
        print(f"  ❌ Validation error: {e}")


def demo_panel():
    """Demonstrate Panel model functionality."""
    print("\n📋 Panel Model Demo:")
    print("-" * 30)

    try:
        # Create panel embed
        embed = PanelEmbed(
            title="Staff Applications",
            description="Apply for staff positions!",
            color="0x00ff00",
            footer_text="Applications are reviewed within 48 hours",
        )
        print("  ✅ Created panel embed")

        # Create panel
        panel = Panel(channel_id="123456789", positions=["Moderator", "Helper"], embed=embed)
        print(f"  ✅ Created panel: {panel.id}")
        print(f"  📍 Channel: {panel.channel_id}")
        print(f"  🎯 Positions: {len(panel.positions)}")

        # Add position
        panel.add_position("Event Manager")
        print("  ✅ Added position")
        print(f"  🎯 Total positions: {panel.get_position_count()}")

        # Set message ID
        panel.set_message_id("987654321")
        print("  ✅ Set message ID")
        print(f"  🔗 Active: {panel.is_active()}")

        # Check position
        print(f"  ✅ Has Moderator: {panel.has_position('Moderator')}")
        print(f"  ❌ Has Admin: {panel.has_position('Admin')}")

        # Convert to dict and back
        panel_dict = panel.to_dict()
        Panel.from_dict(panel_dict)
        print("  ✅ Serialization/deserialization successful")

    except ValidationError as e:
        print(f"  ❌ Validation error: {e}")


def demo_user():
    """Demonstrate User model functionality."""
    print("\n👤 User Model Demo:")
    print("-" * 30)

    try:
        # Create user permissions
        permissions = UserPermissions.get_moderator_permissions()
        print("  ✅ Created moderator permissions")

        # Create user
        user = User(
            id="user-123",
            username="moderator_user",
            discord_id="123456789",
            role=UserRole.MODERATOR,
            permissions=permissions,
        )
        print(f"  ✅ Created user: {user.username}")
        print(f"  🎭 Role: {user.role.value}")

        # Add Discord role
        user.add_discord_role("role-456")
        print("  ✅ Added Discord role")
        print(f"  🏷️  Has role: {user.has_discord_role('role-456')}")

        # Update Discord info
        user.update_discord_info("new_username", "1234", "avatar_url")
        print("  ✅ Updated Discord info")
        print(f"  📝 Username: {user.username}")

        # Change role
        user.set_role(UserRole.ADMIN)
        print("  ✅ Changed role to admin")
        print(f"  🎭 New role: {user.role.value}")
        print(f"  🔐 Can manage positions: {user.can_manage_positions()}")

        # Update last seen
        user.update_last_seen()
        print("  ✅ Updated last seen")

        # Convert to dict and back
        user_dict = user.to_dict()
        User.from_dict(user_dict)
        print("  ✅ Serialization/deserialization successful")

    except ValidationError as e:
        print(f"  ❌ Validation error: {e}")


def demo_validation_errors():
    """Demonstrate validation error handling."""
    print("\n⚠️  Validation Error Demo:")
    print("-" * 30)

    # Test invalid application
    try:
        Application(user_id="", user_name="", position="")
    except ValidationError as e:
        print(f"  ✅ Caught validation error: {e}")

    # Test invalid position
    try:
        Position(name="", settings="not a settings object")  # type: ignore
    except ValidationError as e:
        print(f"  ✅ Caught validation error: {e}")

    # Test invalid panel
    try:
        Panel(channel_id="", positions=[])
    except ValidationError as e:
        print(f"  ✅ Caught validation error: {e}")

    # Test invalid user
    try:
        User(id="", username="", role="invalid_role")  # type: ignore
    except ValidationError as e:
        print(f"  ✅ Caught validation error: {e}")


def main():
    """Run all model demonstrations."""
    print("🚀 Simple Applications Bot - Models Module Demo")
    print("=" * 60)

    demo_application()
    demo_position()
    demo_panel()
    demo_user()
    demo_validation_errors()

    print("\n🎉 Models module demonstration completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
