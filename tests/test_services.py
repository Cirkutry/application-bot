"""
Unit tests for the services module.

This module tests all service classes to ensure they work correctly
with proper error handling and validation.
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.core import (
    ApplicationNotFoundError,
    PanelNotFoundError,
    PositionNotFoundError,
    UserNotFoundError,
    ValidationError,
)
from src.models import (
    Application,
    ApplicationStatus,
    Panel,
    PanelStatus,
    Position,
    User,
    UserRole,
)
from src.services import (
    ApplicationService,
    PanelService,
    PositionService,
    UserService,
    application_service,
    panel_service,
    position_service,
    user_service,
)


class TestApplicationService(unittest.TestCase):
    """Test cases for ApplicationService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = ApplicationService()
        self.service.active_applications = {}

        # Mock application data
        self.app_data = {
            "user_id": "123456789",
            "user_name": "TestUser",
            "position": "Developer",
            "questions": ["What is your experience?", "Why do you want this job?"],
            "answers": ["5 years", "I love coding"],
            "status": ApplicationStatus.PENDING.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "submitted_at": None,
            "reviewed_at": None,
            "reviewer_id": None,
            "review_reason": None,
        }

    @patch('src.services.application_service.application_db')
    def test_create_application(self, mock_db):
        """Test creating a new application."""
        # Test successful creation
        app = self.service.create_application(
            user_id="123456789",
            user_name="TestUser",
            position="Developer",
            questions=["What is your experience?", "Why do you want this job?"],
        )

        self.assertIsInstance(app, Application)
        self.assertEqual(app.user_id, "123456789")
        self.assertEqual(app.user_name, "TestUser")
        self.assertEqual(app.position, "Developer")
        self.assertEqual(len(app.questions), 2)
        mock_db.save_application.assert_called_once()

    def test_create_application_validation(self):
        """Test application creation validation."""
        # Test missing user_id
        with self.assertRaises(ValidationError):
            self.service.create_application("", "TestUser", "Developer", ["Question"])

        # Test missing user_name
        with self.assertRaises(ValidationError):
            self.service.create_application("123456789", "", "Developer", ["Question"])

        # Test missing position
        with self.assertRaises(ValidationError):
            self.service.create_application("123456789", "TestUser", "", ["Question"])

        # Test empty questions
        with self.assertRaises(ValidationError):
            self.service.create_application("123456789", "TestUser", "Developer", [])

    @patch('src.services.application_service.application_db')
    def test_get_application(self, mock_db):
        """Test getting an application by ID."""
        # Test successful retrieval
        mock_db.load_application.return_value = self.app_data
        app = self.service.get_application("test-id")

        self.assertIsInstance(app, Application)
        self.assertEqual(app.user_id, "123456789")
        mock_db.load_application.assert_called_once_with("test-id")

        # Test not found
        mock_db.load_application.return_value = None
        app = self.service.get_application("nonexistent")
        self.assertIsNone(app)

    @patch('src.services.application_service.application_db')
    def test_get_applications_by_user(self, mock_db):
        """Test getting applications by user."""
        mock_db.list_applications.return_value = ["app1", "app2"]

        with patch.object(self.service, 'get_application') as mock_get:
            mock_get.side_effect = [Application.from_dict(self.app_data), Application.from_dict(self.app_data)]

            apps = self.service.get_applications_by_user("123456789")
            self.assertEqual(len(apps), 2)

    @patch('src.services.application_service.application_db')
    def test_update_application(self, mock_db):
        """Test updating an application."""
        with patch.object(self.service, 'get_application') as mock_get:
            app = Application.from_dict(self.app_data)
            mock_get.return_value = app

            updated_app = self.service.update_application("test-id", user_name="NewName")

            self.assertEqual(updated_app.user_name, "NewName")
            mock_db.save_application.assert_called_once()

    def test_update_application_not_found(self):
        """Test updating a non-existent application."""
        with patch.object(self.service, 'get_application', return_value=None):
            with self.assertRaises(ApplicationNotFoundError):
                self.service.update_application("nonexistent", user_name="NewName")

    def test_start_active_application(self):
        """Test starting an active application."""
        active_app = self.service.start_active_application(
            user_id="123456789", position="Developer", questions=["Question 1", "Question 2"]
        )

        self.assertIn("123456789", self.service.active_applications)
        self.assertEqual(active_app["position"], "Developer")
        self.assertEqual(len(active_app["questions"]), 2)

    def test_start_active_application_duplicate(self):
        """Test starting an active application when user already has one."""
        self.service.active_applications["123456789"] = {"existing": "app"}

        with self.assertRaises(ValidationError):
            self.service.start_active_application(user_id="123456789", position="Developer", questions=["Question"])

    def test_add_active_answer(self):
        """Test adding an answer to an active application."""
        self.service.active_applications["123456789"] = {
            "user_id": "123456789",
            "position": "Developer",
            "questions": ["Question 1", "Question 2"],
            "answers": [],
            "current_question": 0,
        }

        result = self.service.add_active_answer("123456789", "My answer")

        self.assertEqual(len(result["answers"]), 1)
        self.assertEqual(result["answers"][0], "My answer")
        self.assertEqual(result["current_question"], 1)

    def test_add_active_answer_no_application(self):
        """Test adding an answer when no active application exists."""
        with self.assertRaises(ValidationError):
            self.service.add_active_answer("123456789", "My answer")

    def test_get_application_stats(self):
        """Test getting application statistics."""
        with patch.object(self.service, 'get_all_applications') as mock_get:
            app1 = Application.from_dict(self.app_data)
            app2 = Application.from_dict(self.app_data)
            app2.status = ApplicationStatus.ACCEPTED
            mock_get.return_value = [app1, app2]

            stats = self.service.get_application_stats()

            self.assertEqual(stats["total"], 2)
            self.assertEqual(stats["pending"], 1)
            self.assertEqual(stats["accepted"], 1)


class TestPositionService(unittest.TestCase):
    """Test cases for PositionService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = PositionService()

        # Mock position data
        self.pos_data = {
            "name": "Developer",
            "description": "Software developer position",
            "questions": ["What is your experience?", "Why do you want this job?"],
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    @patch('src.services.position_service.position_db')
    def test_create_position(self, mock_db):
        """Test creating a new position."""
        with patch.object(self.service, 'get_all_positions', return_value=[]):
            pos = self.service.create_position(
                name="Developer",
                description="Software developer position",
                questions=["What is your experience?", "Why do you want this job?"],
            )

            self.assertIsInstance(pos, Position)
            self.assertEqual(pos.name, "Developer")
            self.assertEqual(pos.description, "Software developer position")
            self.assertEqual(len(pos.questions), 2)
            mock_db.save_position.assert_called_once()

    def test_create_position_validation(self):
        """Test position creation validation."""
        # Test missing name
        with self.assertRaises(ValidationError):
            self.service.create_position("", "Description", ["Question"])

        # Test missing description
        with self.assertRaises(ValidationError):
            self.service.create_position("Name", "", "Question")

        # Test empty questions
        with self.assertRaises(ValidationError):
            self.service.create_position("Name", "Description", [])

    def test_create_position_duplicate(self):
        """Test creating a duplicate position."""
        existing_pos = Position.from_dict(self.pos_data)

        with patch.object(self.service, 'get_all_positions', return_value=[existing_pos]):
            with self.assertRaises(ValidationError):
                self.service.create_position(
                    name="Developer", description="Different description", questions=["Question"]
                )

    @patch('src.services.position_service.position_db')
    def test_get_position(self, mock_db):
        """Test getting a position by ID."""
        # Test successful retrieval
        mock_db.load_position.return_value = self.pos_data
        pos = self.service.get_position("test-id")

        self.assertIsInstance(pos, Position)
        self.assertEqual(pos.name, "Developer")
        mock_db.load_position.assert_called_once_with("test-id")

        # Test not found
        mock_db.load_position.return_value = None
        pos = self.service.get_position("nonexistent")
        self.assertIsNone(pos)

    def test_get_position_by_name(self):
        """Test getting a position by name."""
        pos1 = Position.from_dict(self.pos_data)
        pos2 = Position.from_dict(self.pos_data)
        pos2.name = "Manager"

        with patch.object(self.service, 'get_all_positions', return_value=[pos1, pos2]):
            found_pos = self.service.get_position_by_name("Developer")
            self.assertEqual(found_pos.name, "Developer")

            not_found = self.service.get_position_by_name("Designer")
            self.assertIsNone(not_found)

    def test_get_active_positions(self):
        """Test getting active positions."""
        pos1 = Position.from_dict(self.pos_data)
        pos2 = Position.from_dict(self.pos_data)
        pos2.name = "Manager"
        pos2.is_active = False

        with patch.object(self.service, 'get_all_positions', return_value=[pos1, pos2]):
            active_positions = self.service.get_active_positions()
            self.assertEqual(len(active_positions), 1)
            self.assertEqual(active_positions[0].name, "Developer")

    @patch('src.services.position_service.position_db')
    def test_update_position(self, mock_db):
        """Test updating a position."""
        with patch.object(self.service, 'get_position') as mock_get:
            pos = Position.from_dict(self.pos_data)
            mock_get.return_value = pos

            updated_pos = self.service.update_position("test-id", name="Senior Developer")

            self.assertEqual(updated_pos.name, "Senior Developer")
            mock_db.save_position.assert_called_once()

    def test_update_position_not_found(self):
        """Test updating a non-existent position."""
        with patch.object(self.service, 'get_position', return_value=None):
            with self.assertRaises(PositionNotFoundError):
                self.service.update_position("nonexistent", name="New Name")

    @patch('src.services.position_service.position_db')
    def test_activate_position(self, mock_db):
        """Test activating a position."""
        with patch.object(self.service, 'get_position') as mock_get:
            pos = Position.from_dict(self.pos_data)
            pos.is_active = False
            mock_get.return_value = pos

            activated_pos = self.service.activate_position("test-id")

            self.assertTrue(activated_pos.is_active)
            mock_db.save_position.assert_called_once()

    @patch('src.services.position_service.position_db')
    def test_add_question(self, mock_db):
        """Test adding a question to a position."""
        with patch.object(self.service, 'get_position') as mock_get:
            pos = Position.from_dict(self.pos_data)
            mock_get.return_value = pos

            updated_pos = self.service.add_question("test-id", "New question?")

            self.assertEqual(len(updated_pos.questions), 3)
            self.assertIn("New question?", updated_pos.questions)
            mock_db.save_position.assert_called_once()

    def test_add_question_validation(self):
        """Test adding an invalid question."""
        with patch.object(self.service, 'get_position') as mock_get:
            pos = Position.from_dict(self.pos_data)
            mock_get.return_value = pos

            with self.assertRaises(ValidationError):
                self.service.add_question("test-id", "")

    def test_get_position_stats(self):
        """Test getting position statistics."""
        pos1 = Position.from_dict(self.pos_data)
        pos2 = Position.from_dict(self.pos_data)
        pos2.name = "Manager"
        pos2.is_active = False

        with patch.object(self.service, 'get_all_positions', return_value=[pos1, pos2]):
            stats = self.service.get_position_stats()

            self.assertEqual(stats["total"], 2)
            self.assertEqual(stats["active"], 1)
            self.assertEqual(stats["inactive"], 1)
            self.assertEqual(stats["total_questions"], 4)  # 2 questions each


class TestPanelService(unittest.TestCase):
    """Test cases for PanelService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = PanelService()

        # Mock panel data
        self.panel_data = {
            "name": "Developer Panel",
            "description": "Panel for reviewing developer applications",
            "channel_id": "123456789",
            "message_id": "987654321",
            "position": "Developer",
            "is_active": True,
            "reviewers": {"reviewer1": "Reviewer One"},
            "applications": ["app1", "app2"],
            "reviews": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    @patch('src.services.panel_service.panel_db')
    def test_create_panel(self, mock_db):
        """Test creating a new panel."""
        panel = self.service.create_panel(
            name="Developer Panel",
            description="Panel for reviewing developer applications",
            channel_id="123456789",
            message_id="987654321",
            position="Developer",
        )

        self.assertIsInstance(panel, Panel)
        self.assertEqual(panel.name, "Developer Panel")
        self.assertEqual(panel.channel_id, "123456789")
        self.assertEqual(panel.message_id, "987654321")
        self.assertEqual(panel.position, "Developer")
        mock_db.save_panel.assert_called_once()

    def test_create_panel_validation(self):
        """Test panel creation validation."""
        # Test missing name
        with self.assertRaises(ValidationError):
            self.service.create_panel("", "Description", "channel", "message", "position")

        # Test missing description
        with self.assertRaises(ValidationError):
            self.service.create_panel("Name", "", "channel", "message", "position")

        # Test missing channel_id
        with self.assertRaises(ValidationError):
            self.service.create_panel("Name", "Description", "", "message", "position")

        # Test missing message_id
        with self.assertRaises(ValidationError):
            self.service.create_panel("Name", "Description", "channel", "", "position")

        # Test missing position
        with self.assertRaises(ValidationError):
            self.service.create_panel("Name", "Description", "channel", "message", "")

    @patch('src.services.panel_service.panel_db')
    def test_get_panel(self, mock_db):
        """Test getting a panel by ID."""
        # Test successful retrieval
        mock_db.load_panel.return_value = self.panel_data
        panel = self.service.get_panel("test-id")

        self.assertIsInstance(panel, Panel)
        self.assertEqual(panel.name, "Developer Panel")
        mock_db.load_panel.assert_called_once_with("test-id")

        # Test not found
        mock_db.load_panel.return_value = None
        panel = self.service.get_panel("nonexistent")
        self.assertIsNone(panel)

    def test_get_panel_by_message(self):
        """Test getting a panel by message ID."""
        panel1 = Panel.from_dict(self.panel_data)
        panel2 = Panel.from_dict(self.panel_data)
        panel2.message_id = "111111111"

        with patch.object(self.service, 'get_all_panels', return_value=[panel1, panel2]):
            found_panel = self.service.get_panel_by_message("987654321")
            self.assertEqual(found_panel.message_id, "987654321")

            not_found = self.service.get_panel_by_message("999999999")
            self.assertIsNone(not_found)

    def test_get_panels_by_position(self):
        """Test getting panels by position."""
        panel1 = Panel.from_dict(self.panel_data)
        panel2 = Panel.from_dict(self.panel_data)
        panel2.position = "Manager"

        with patch.object(self.service, 'get_all_panels', return_value=[panel1, panel2]):
            dev_panels = self.service.get_panels_by_position("Developer")
            self.assertEqual(len(dev_panels), 1)
            self.assertEqual(dev_panels[0].position, "Developer")

    @patch('src.services.panel_service.panel_db')
    def test_add_reviewer(self, mock_db):
        """Test adding a reviewer to a panel."""
        with patch.object(self.service, 'get_panel') as mock_get:
            panel = Panel.from_dict(self.panel_data)
            mock_get.return_value = panel

            updated_panel = self.service.add_reviewer("test-id", "reviewer2", "Reviewer Two")

            self.assertIn("reviewer2", updated_panel.reviewers)
            self.assertEqual(updated_panel.reviewers["reviewer2"], "Reviewer Two")
            mock_db.save_panel.assert_called_once()

    def test_add_reviewer_validation(self):
        """Test adding an invalid reviewer."""
        with patch.object(self.service, 'get_panel') as mock_get:
            panel = Panel.from_dict(self.panel_data)
            mock_get.return_value = panel

            with self.assertRaises(ValidationError):
                self.service.add_reviewer("test-id", "", "Reviewer")

            with self.assertRaises(ValidationError):
                self.service.add_reviewer("test-id", "reviewer", "")

    @patch('src.services.panel_service.panel_db')
    def test_add_application_to_panel(self, mock_db):
        """Test adding an application to a panel."""
        with patch.object(self.service, 'get_panel') as mock_get:
            panel = Panel.from_dict(self.panel_data)
            mock_get.return_value = panel

            updated_panel = self.service.add_application_to_panel("test-id", "app3")

            self.assertIn("app3", updated_panel.applications)
            mock_db.save_panel.assert_called_once()

    def test_add_application_to_panel_duplicate(self):
        """Test adding a duplicate application to a panel."""
        with patch.object(self.service, 'get_panel') as mock_get:
            panel = Panel.from_dict(self.panel_data)
            mock_get.return_value = panel

            with self.assertRaises(ValidationError):
                self.service.add_application_to_panel("test-id", "app1")

    @patch('src.services.panel_service.panel_db')
    def test_review_application_in_panel(self, mock_db):
        """Test reviewing an application in a panel."""
        with patch.object(self.service, 'get_panel') as mock_get:
            panel = Panel.from_dict(self.panel_data)
            mock_get.return_value = panel

            updated_panel = self.service.review_application_in_panel(
                "test-id", "app1", "reviewer1", PanelStatus.ACCEPTED, "Great candidate"
            )

            self.assertIn("app1", updated_panel.reviews)
            review = updated_panel.reviews["app1"]
            self.assertEqual(review["reviewer_id"], "reviewer1")
            self.assertEqual(review["status"], PanelStatus.ACCEPTED)
            self.assertEqual(review["reason"], "Great candidate")
            mock_db.save_panel.assert_called_once()

    def test_review_application_not_in_panel(self):
        """Test reviewing an application not in the panel."""
        with patch.object(self.service, 'get_panel') as mock_get:
            panel = Panel.from_dict(self.panel_data)
            mock_get.return_value = panel

            with self.assertRaises(ValidationError):
                self.service.review_application_in_panel("test-id", "nonexistent", "reviewer1", PanelStatus.ACCEPTED)

    def test_get_panel_stats(self):
        """Test getting panel statistics."""
        panel1 = Panel.from_dict(self.panel_data)
        panel2 = Panel.from_dict(self.panel_data)
        panel2.name = "Manager Panel"
        panel2.is_active = False

        with patch.object(self.service, 'get_all_panels', return_value=[panel1, panel2]):
            stats = self.service.get_panel_stats()

            self.assertEqual(stats["total"], 2)
            self.assertEqual(stats["active"], 1)
            self.assertEqual(stats["inactive"], 1)
            self.assertEqual(stats["total_applications"], 4)  # 2 applications each
            self.assertEqual(stats["total_reviewers"], 2)  # 1 reviewer each


class TestUserService(unittest.TestCase):
    """Test cases for UserService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = UserService()

        # Mock user data
        self.user_data = {
            "user_id": "123456789",
            "username": "TestUser",
            "role": UserRole.USER.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    @patch('src.services.user_service.user_db')
    def test_create_user(self, mock_db):
        """Test creating a new user."""
        with patch.object(self.service, 'get_user', return_value=None):
            user = self.service.create_user(user_id="123456789", username="TestUser")

            self.assertIsInstance(user, User)
            self.assertEqual(user.user_id, "123456789")
            self.assertEqual(user.username, "TestUser")
            self.assertEqual(user.role, UserRole.USER)
            mock_db.save_user.assert_called_once()

    def test_create_user_validation(self):
        """Test user creation validation."""
        # Test missing user_id
        with self.assertRaises(ValidationError):
            self.service.create_user("", "TestUser")

        # Test missing username
        with self.assertRaises(ValidationError):
            self.service.create_user("123456789", "")

    def test_create_user_duplicate(self):
        """Test creating a duplicate user."""
        existing_user = User.from_dict(self.user_data)

        with patch.object(self.service, 'get_user', return_value=existing_user):
            with self.assertRaises(ValidationError):
                self.service.create_user("123456789", "TestUser")

    @patch('src.services.user_service.user_db')
    def test_get_user(self, mock_db):
        """Test getting a user by ID."""
        # Test successful retrieval
        mock_db.load_user.return_value = self.user_data
        user = self.service.get_user("123456789")

        self.assertIsInstance(user, User)
        self.assertEqual(user.user_id, "123456789")
        mock_db.load_user.assert_called_once_with("123456789")

        # Test not found
        mock_db.load_user.return_value = None
        user = self.service.get_user("nonexistent")
        self.assertIsNone(user)

    def test_get_user_by_username(self):
        """Test getting a user by username."""
        user1 = User.from_dict(self.user_data)
        user2 = User.from_dict(self.user_data)
        user2.username = "AnotherUser"

        with patch.object(self.service, 'get_all_users', return_value=[user1, user2]):
            found_user = self.service.get_user_by_username("TestUser")
            self.assertEqual(found_user.username, "TestUser")

            not_found = self.service.get_user_by_username("NonexistentUser")
            self.assertIsNone(not_found)

    def test_get_users_by_role(self):
        """Test getting users by role."""
        user1 = User.from_dict(self.user_data)
        user2 = User.from_dict(self.user_data)
        user2.role = UserRole.ADMIN

        with patch.object(self.service, 'get_all_users', return_value=[user1, user2]):
            admin_users = self.service.get_users_by_role(UserRole.ADMIN)
            self.assertEqual(len(admin_users), 1)
            self.assertEqual(admin_users[0].role, UserRole.ADMIN)

    @patch('src.services.user_service.user_db')
    def test_update_user(self, mock_db):
        """Test updating a user."""
        with patch.object(self.service, 'get_user') as mock_get:
            user = User.from_dict(self.user_data)
            mock_get.return_value = user

            updated_user = self.service.update_user("123456789", username="NewUsername")

            self.assertEqual(updated_user.username, "NewUsername")
            mock_db.save_user.assert_called_once()

    def test_update_user_not_found(self):
        """Test updating a non-existent user."""
        with patch.object(self.service, 'get_user', return_value=None):
            with self.assertRaises(UserNotFoundError):
                self.service.update_user("nonexistent", username="NewUsername")

    @patch('src.services.user_service.user_db')
    def test_promote_user(self, mock_db):
        """Test promoting a user."""
        with patch.object(self.service, 'get_user') as mock_get:
            user = User.from_dict(self.user_data)
            mock_get.return_value = user

            promoted_user = self.service.promote_user("123456789", UserRole.MODERATOR)

            self.assertEqual(promoted_user.role, UserRole.MODERATOR)
            mock_db.save_user.assert_called_once()

    def test_promote_user_invalid(self):
        """Test promoting a user to an invalid role."""
        with patch.object(self.service, 'get_user') as mock_get:
            user = User.from_dict(self.user_data)
            user.role = UserRole.MODERATOR
            mock_get.return_value = user

            with self.assertRaises(ValidationError):
                self.service.promote_user("123456789", UserRole.USER)

    def test_has_permission(self):
        """Test permission checking."""
        with patch.object(self.service, 'get_user') as mock_get:
            user = User.from_dict(self.user_data)
            user.role = UserRole.MODERATOR
            mock_get.return_value = user

            # Test moderator has moderator permission
            self.assertTrue(self.service.has_permission("123456789", UserRole.MODERATOR))

            # Test moderator has user permission
            self.assertTrue(self.service.has_permission("123456789", UserRole.USER))

            # Test moderator doesn't have admin permission
            self.assertFalse(self.service.has_permission("123456789", UserRole.ADMIN))

    def test_is_admin(self):
        """Test admin role checking."""
        with patch.object(self.service, 'get_user') as mock_get:
            user = User.from_dict(self.user_data)
            user.role = UserRole.ADMIN
            mock_get.return_value = user

            self.assertTrue(self.service.is_admin("123456789"))

            user.role = UserRole.USER
            self.assertFalse(self.service.is_admin("123456789"))

    def test_get_user_stats(self):
        """Test getting user statistics."""
        user1 = User.from_dict(self.user_data)
        user2 = User.from_dict(self.user_data)
        user2.role = UserRole.ADMIN

        with patch.object(self.service, 'get_all_users', return_value=[user1, user2]):
            stats = self.service.get_user_stats()

            self.assertEqual(stats["total"], 2)
            self.assertEqual(stats["admins"], 1)
            self.assertEqual(stats["users"], 1)

    def test_search_users(self):
        """Test searching users."""
        user1 = User.from_dict(self.user_data)
        user2 = User.from_dict(self.user_data)
        user2.username = "AnotherUser"

        with patch.object(self.service, 'get_all_users', return_value=[user1, user2]):
            results = self.service.search_users("Test")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].username, "TestUser")

    @patch('src.services.user_service.user_db')
    def test_get_or_create_user(self, mock_db):
        """Test getting or creating a user."""
        # Test getting existing user
        with patch.object(self.service, 'get_user') as mock_get:
            user = User.from_dict(self.user_data)
            mock_get.return_value = user

            result = self.service.get_or_create_user("123456789", "TestUser")
            self.assertEqual(result, user)

        # Test creating new user
        with patch.object(self.service, 'get_user', return_value=None):
            with patch.object(self.service, 'create_user') as mock_create:
                new_user = User.from_dict(self.user_data)
                mock_create.return_value = new_user

                result = self.service.get_or_create_user("123456789", "TestUser")
                self.assertEqual(result, new_user)
                mock_create.assert_called_once_with("123456789", "TestUser")


if __name__ == '__main__':
    unittest.main()
