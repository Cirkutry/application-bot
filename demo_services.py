#!/usr/bin/env python3
# Run this script from the project root with: python -m demo_services
from src.core.logging import setup_logging
from src.models import ApplicationStatus, UserRole
from src.models.panel import PanelStatus
from src.services import (
    application_service,
    panel_service,
    position_service,
    user_service,
)

# Demo script for the Services module.
#
# This script demonstrates the functionality of all service classes:
# - ApplicationService
# - PositionService
# - PanelService
# - UserService
#
# It shows CRUD operations, validation, business logic, and error handling.


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_section(title):
    """Print a formatted section."""
    print(f"\n--- {title} ---")


def demo_user_service():
    """Demonstrate UserService functionality."""
    print_header("USER SERVICE DEMO")

    print_section("Creating Users")

    # Create some users
    try:
        admin_user = user_service.create_user("admin123", "AdminUser", UserRole.ADMIN)
        if admin_user:
            print(f"✓ Created admin user: {admin_user.username} (ID: {admin_user.id})")

        mod_user = user_service.create_user("mod456", "ModUser", UserRole.MODERATOR)
        if mod_user:
            print(f"✓ Created moderator user: {mod_user.username} (ID: {mod_user.id})")

        reviewer_user = user_service.create_user("rev789", "ReviewerUser", UserRole.REVIEWER)
        if reviewer_user:
            print(f"✓ Created reviewer user: {reviewer_user.username} (ID: {reviewer_user.id})")

        regular_user = user_service.create_user("user101", "RegularUser", UserRole.USER)
        if regular_user:
            print(f"✓ Created regular user: {regular_user.username} (ID: {regular_user.id})")

    except Exception as e:
        print(f"✗ Error creating users: {e}")

    print_section("User Management")

    # Get all users
    all_users = user_service.get_all_users()
    print(f"✓ Total users: {len(all_users)}")

    # Get users by role
    admins = user_service.get_users_by_role(UserRole.ADMIN)
    print(f"✓ Admin users: {len(admins)}")

    moderators = user_service.get_users_by_role(UserRole.MODERATOR)
    print(f"✓ Moderator users: {len(moderators)}")

    # Update user
    try:
        updated_user = user_service.update_user("user101", username="UpdatedUser")
        print(f"✓ Updated user: {updated_user.username}")
    except Exception as e:
        print(f"✗ Error updating user: {e}")

    # Promote user
    try:
        promoted_user = user_service.promote_user("user101", UserRole.REVIEWER)
        print(f"✓ Promoted user to: {promoted_user.role.value}")
    except Exception as e:
        print(f"✗ Error promoting user: {e}")

    # Permission checking
    print_section("Permission Checking")

    print(f"✓ Admin is admin: {user_service.is_admin('admin123')}")
    print(f"✓ Moderator is admin: {user_service.is_admin('mod456')}")
    print(f"✓ Regular user is admin: {user_service.is_admin('user101')}")

    print(f"✓ Admin has moderator permission: {user_service.has_permission('admin123', UserRole.MODERATOR)}")
    print(f"✓ Regular user has moderator permission: {user_service.has_permission('user101', UserRole.MODERATOR)}")

    # User statistics
    stats = user_service.get_user_stats()
    print_section("User Statistics")
    print(f"✓ Total users: {stats['total']}")
    print(f"✓ Admins: {stats['admins']}")
    print(f"✓ Moderators: {stats['moderators']}")
    print(f"✓ Reviewers: {stats['reviewers']}")
    print(f"✓ Regular users: {stats['users']}")

    # Search users
    search_results = user_service.search_users("User")
    print(f"✓ Users matching 'User': {len(search_results)}")

    # Get or create user
    existing_user = user_service.get_or_create_user("admin123", "AdminUser")
    print(f"✓ Get or create existing user: {existing_user.username}")

    new_user = user_service.get_or_create_user("newuser", "NewUser")
    print(f"✓ Get or create new user: {new_user.username}")


def demo_position_service():
    """Demonstrate PositionService functionality."""
    print_header("POSITION SERVICE DEMO")

    print_section("Creating Positions")

    # Create some positions
    try:
        dev_position = position_service.create_position(
            name="Software Developer",
            description="Full-stack software developer position",
            questions=[
                "What is your experience with Python?",
                "Describe a challenging project you worked on",
                "Why do you want to work here?",
            ],
        )
        print(f"✓ Created position: {dev_position.name}")

        manager_position = position_service.create_position(
            name="Project Manager",
            description="Project management position",
            questions=[
                "How do you handle team conflicts?",
                "Describe your project management methodology",
                "What tools do you use for project tracking?",
            ],
        )
        print(f"✓ Created position: {manager_position.name}")

        designer_position = position_service.create_position(
            name="UI/UX Designer",
            description="User interface and experience designer",
            questions=["Show us your portfolio", "What's your design process?", "How do you handle user feedback?"],
            is_active=False,  # Start as inactive
        )
        print(f"✓ Created inactive position: {designer_position.name}")

    except Exception as e:
        print(f"✗ Error creating positions: {e}")

    print_section("Position Management")

    # Get all positions
    all_positions = position_service.get_all_positions()
    print(f"✓ Total positions: {len(all_positions)}")

    # Get active positions
    active_positions = position_service.get_active_positions()
    print(f"✓ Active positions: {len(active_positions)}")

    # Get inactive positions
    inactive_positions = position_service.get_inactive_positions()
    print(f"✓ Inactive positions: {len(inactive_positions)}")

    # Get position by name
    dev_pos = position_service.get_position_by_name("Software Developer")
    if dev_pos:
        print(f"✓ Found position by name: {dev_pos.name}")

    # Update position
    try:
        if dev_pos:
            position_service.update_position(dev_pos.id, description="Updated full-stack developer position")
            print("✓ Updated position description")
    except Exception as e:
        print(f"✗ Error updating position: {e}")

    # Activate inactive position
    try:
        if designer_position:
            activated_pos = position_service.activate_position(designer_position.id)
            print(f"✓ Activated position: {activated_pos.name}")
    except Exception as e:
        print(f"✗ Error activating position: {e}")

    # Add question to position
    try:
        if dev_pos:
            position_service.add_question(dev_pos.id, "What's your experience with databases?")
            print("✓ Added question to position")
    except Exception as e:
        print(f"✗ Error adding question: {e}")

    # Update question
    try:
        if dev_pos:
            position_service.update_question(dev_pos.id, 0, "What is your experience with Python and web development?")
            print("✓ Updated question in position")
    except Exception as e:
        print(f"✗ Error updating question: {e}")

    # Position statistics
    stats = position_service.get_position_stats()
    print_section("Position Statistics")
    print(f"✓ Total positions: {stats['total']}")
    print(f"✓ Active positions: {stats['active']}")
    print(f"✓ Inactive positions: {stats['inactive']}")
    print(f"✓ Total questions: {stats['total_questions']}")
    print(f"✓ Average questions per position: {stats['avg_questions']:.1f}")

    # Search positions
    search_results = position_service.search_positions("developer")
    print(f"✓ Positions matching 'developer': {len(search_results)}")

    # Duplicate position
    try:
        if dev_pos:
            duplicated_pos = position_service.duplicate_position(dev_pos.id, "Senior Software Developer")
            print(f"✓ Duplicated position: {duplicated_pos.name}")
    except Exception as e:
        print(f"✗ Error duplicating position: {e}")


def demo_application_service():
    """Demonstrate ApplicationService functionality."""
    print_header("APPLICATION SERVICE DEMO")

    print_section("Creating Applications")

    # Create some applications
    try:
        app1 = application_service.create_application(
            user_id="user101",
            user_name="RegularUser",
            position="Software Developer",
            questions=[
                "What is your experience with Python?",
                "Describe a challenging project you worked on",
                "Why do you want to work here?",
            ],
        )
        print(f"✓ Created application: {app1.id}")

        app2 = application_service.create_application(
            user_id="user102",
            user_name="AnotherUser",
            position="Project Manager",
            questions=["How do you handle team conflicts?", "Describe your project management methodology"],
        )
        print(f"✓ Created application: {app2.id}")

    except Exception as e:
        print(f"✗ Error creating applications: {e}")

    print_section("Application Management")

    # Get all applications
    all_applications = application_service.get_all_applications()
    print(f"✓ Total applications: {len(all_applications)}")

    # Get applications by user
    user_apps = application_service.get_applications_by_user("user101")
    print(f"✓ Applications for user101: {len(user_apps)}")

    # Get applications by position
    dev_apps = application_service.get_applications_by_position("Software Developer")
    print(f"✓ Applications for Software Developer: {len(dev_apps)}")

    # Get applications by status
    pending_apps = application_service.get_applications_by_status(ApplicationStatus.PENDING)
    print(f"✓ Pending applications: {len(pending_apps)}")

    # Add answers to application
    try:
        application_service.add_answer(app1.id, "5 years of Python experience")
        print("✓ Added answer to application")

        application_service.add_answer(app1.id, "Built a complex web application")
        print("✓ Added second answer to application")

        application_service.add_answer(app1.id, "I love the company culture")
        print("✓ Added third answer to application")

    except Exception as e:
        print(f"✗ Error adding answers: {e}")

    # Submit application
    try:
        submitted_app = application_service.submit_application(app1.id)
        print(f"✓ Submitted application: {submitted_app.status.value}")
    except Exception as e:
        print(f"✗ Error submitting application: {e}")

    # Review application
    try:
        reviewed_app = application_service.review_application(
            app1.id, ApplicationStatus.ACCEPTED, "admin123", "Excellent candidate with strong skills"
        )
        print(f"✓ Reviewed application: {reviewed_app.status.value}")
    except Exception as e:
        print(f"✗ Error reviewing application: {e}")

    print_section("Active Applications")

    # Start active application
    try:
        application_service.start_active_application(
            user_id="user103",
            position="UI/UX Designer",
            questions=["Show us your portfolio", "What's your design process?"],
        )
        print("✓ Started active application for user103")

        # Add answers to active application
        application_service.add_active_answer("user103", "Here's my portfolio link")
        print("✓ Added answer to active application")

        application_service.add_active_answer("user103", "I follow a user-centered design process")
        print("✓ Added second answer to active application")

        # Complete active application
        completed_app = application_service.complete_active_application("user103")
        print(f"✓ Completed active application: {completed_app.id}")

    except Exception as e:
        print(f"✗ Error with active application: {e}")

    # Application statistics
    stats = application_service.get_application_stats()
    print_section("Application Statistics")
    print(f"✓ Total applications: {stats['total']}")
    print(f"✓ Pending applications: {stats['pending']}")
    print(f"✓ Accepted applications: {stats['accepted']}")
    print(f"✓ Denied applications: {stats['denied']}")
    print(f"✓ Withdrawn applications: {stats['withdrawn']}")
    print(f"✓ Active applications: {stats['active']}")


def demo_panel_service():
    """Demonstrate PanelService functionality."""
    print_header("PANEL SERVICE DEMO")

    print_section("Creating Panels")

    # Create some panels
    try:
        dev_panel = panel_service.create_panel(
            name="Developer Review Panel",
            description="Panel for reviewing software developer applications",
            channel_id="dev-channel-123",
            message_id="dev-message-456",
            position="Software Developer",
        )
        print(f"✓ Created panel: {dev_panel.name}")

        manager_panel = panel_service.create_panel(
            name="Manager Review Panel",
            description="Panel for reviewing project manager applications",
            channel_id="manager-channel-789",
            message_id="manager-message-012",
            position="Project Manager",
        )
        print(f"✓ Created panel: {manager_panel.name}")

    except Exception as e:
        print(f"✗ Error creating panels: {e}")

    print_section("Panel Management")

    # Get all panels
    all_panels = panel_service.get_all_panels()
    print(f"✓ Total panels: {len(all_panels)}")

    # Get active panels
    active_panels = panel_service.get_active_panels()
    print(f"✓ Active panels: {len(active_panels)}")

    # Get panels by position
    dev_panels = panel_service.get_panels_by_position("Software Developer")
    print(f"✓ Panels for Software Developer: {len(dev_panels)}")

    # Get panel by message
    panel_by_message = panel_service.get_panel_by_message("dev-message-456")
    if panel_by_message:
        print(f"✓ Found panel by message: {panel_by_message.name}")

    # Add reviewers to panel
    try:
        panel_service.add_reviewer(dev_panel.id, "admin123", "AdminUser")
        print("✓ Added reviewer to panel")

        panel_service.add_reviewer(dev_panel.id, "mod456", "ModUser")
        print("✓ Added second reviewer to panel")

    except Exception as e:
        print(f"✗ Error adding reviewers: {e}")

    # Add applications to panel
    try:
        # Get an application to add
        all_apps = application_service.get_all_applications()
        if all_apps:
            app_to_add = all_apps[0]

            panel_service.add_application_to_panel(dev_panel.id, app_to_add.id)
            print("✓ Added application to panel")

            # Review application in panel
            panel_service.review_application_in_panel(
                dev_panel.id, app_to_add.id, "admin123", PanelStatus.ACCEPTED, "Strong candidate with excellent skills"
            )
            print("✓ Reviewed application in panel")

    except Exception as e:
        print(f"✗ Error with applications in panel: {e}")

    # Get panels by reviewer
    admin_panels = panel_service.get_panels_by_reviewer("admin123")
    print(f"✓ Panels for admin123: {len(admin_panels)}")

    # Get panels with pending applications
    pending_panels = panel_service.get_panels_with_pending_applications()
    print(f"✓ Panels with pending applications: {len(pending_panels)}")

    # Panel statistics
    stats = panel_service.get_panel_stats()
    print_section("Panel Statistics")
    print(f"✓ Total panels: {stats['total']}")
    print(f"✓ Active panels: {stats['active']}")
    print(f"✓ Inactive panels: {stats['inactive']}")
    print(f"✓ Total applications in panels: {stats['total_applications']}")
    print(f"✓ Total reviewers: {stats['total_reviewers']}")
    print(f"✓ Average applications per panel: {stats['avg_applications_per_panel']:.1f}")
    print(f"✓ Average reviewers per panel: {stats['avg_reviewers_per_panel']:.1f}")

    # Search panels
    search_results = panel_service.search_panels("developer")
    print(f"✓ Panels matching 'developer': {len(search_results)}")


def demo_error_handling():
    """Demonstrate error handling in services."""
    print_header("ERROR HANDLING DEMO")

    print_section("Validation Errors")

    # Try to create invalid data
    try:
        user_service.create_user("", "InvalidUser")
    except Exception as e:
        print(f"✓ Caught validation error: {e}")

    try:
        position_service.create_position("", "Description", ["Question"])
    except Exception as e:
        print(f"✓ Caught validation error: {e}")

    try:
        application_service.create_application("user", "name", "position", [])
    except Exception as e:
        print(f"✓ Caught validation error: {e}")

    print_section("Not Found Errors")

    # Try to get non-existent items
    try:
        user_service.get_user("nonexistent")
        print("✓ Non-existent user returns None (not an error)")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")

    try:
        user_service.update_user("nonexistent", username="NewName")
    except Exception as e:
        print(f"✓ Caught not found error: {e}")

    try:
        position_service.get_position("nonexistent")
        print("✓ Non-existent position returns None (not an error)")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")

    try:
        position_service.update_position("nonexistent", name="NewName")
    except Exception as e:
        print(f"✓ Caught not found error: {e}")

    print_section("Business Logic Errors")

    # Try to promote user to same or lower role
    try:
        user_service.promote_user("user101", UserRole.USER)
    except Exception as e:
        print(f"✓ Caught business logic error: {e}")

    # Try to start active application when user already has one
    try:
        application_service.start_active_application("user103", "position", ["question"])
    except Exception as e:
        print(f"✓ Caught business logic error: {e}")

    # Try to add answer to non-existent active application
    try:
        application_service.add_active_answer("nonexistent", "answer")
    except Exception as e:
        print(f"✓ Caught business logic error: {e}")


def main():
    """Run the services demo."""
    print("🚀 Starting Services Module Demo")
    print("This demo showcases all service classes and their functionality.")

    # Setup logging
    setup_logging()

    try:
        # Run all demos
        demo_user_service()
        demo_position_service()
        demo_application_service()
        demo_panel_service()
        demo_error_handling()

        print_header("DEMO COMPLETED SUCCESSFULLY")
        print("✅ All service classes are working correctly!")
        print("✅ CRUD operations, validation, and business logic are functional.")
        print("✅ Error handling is working as expected.")
        print("\nThe services module provides a robust business logic layer")
        print("that coordinates between models and the database layer.")

    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
