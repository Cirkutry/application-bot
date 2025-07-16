import json
import logging
import os

from aiohttp import web

from panels_manager import load_panels, save_panels
from question_manager import load_questions, save_questions
from src.web.auth.decorators import auth_required
from src.web.config.settings import APPS_DIRECTORY, SERVER_ID

logger = logging.getLogger(__name__)


routes = web.RouteTableDef()


@routes.delete("/api/applications/{app_id}")
async def delete_application(request):
    """Delete an application"""
    app_id = request.match_info["app_id"]
    app_path = os.path.join(APPS_DIRECTORY, f"{app_id}.json")

    try:
        os.remove(app_path)
        return web.Response(text="Application deleted successfully")
    except FileNotFoundError:
        return web.Response(text="Application not found", status=404)
    except Exception as e:
        return web.Response(text=f"Error deleting application: {str(e)}", status=500)


@routes.post("/api/questions/position/add")
async def add_position(request):
    """Add a new position"""
    try:
        data = await request.json()
        position_name = data.get("name")

        if not position_name:
            return web.Response(text="Position name is required", status=400)

        # Load existing questions
        questions = load_questions()

        # Check if position already exists
        if position_name in questions:
            return web.Response(text="Position already exists", status=400)

        # Add new position with default settings
        questions[position_name] = {
            "enabled": True,
            "questions": [],
            "log_channel": None,
            "welcome_message": (
                f"Welcome to the {position_name} application process! "
                "Please answer the following questions to complete your application."
            ),
            "completion_message": (
                f"Thank you for completing your {position_name} application! "
                "Your responses have been submitted and will be reviewed soon."
            ),
            "accepted_message": (
                f"Congratulations! Your application for {position_name} " "has been accepted. Welcome to the team!"
            ),
            "denied_message": (
                f"Thank you for applying for {position_name}. "
                "After careful consideration, we have decided not to move forward "
                "with your application at this time."
            ),
            "ping_roles": [],
            "button_roles": [],
            "accept_roles": [],
            "reject_roles": [],
            "accept_reason_roles": [],
            "reject_reason_roles": [],
            "accepted_roles": [],
            "denied_roles": [],
            "restricted_roles": [],
            "required_roles": [],
            "accepted_removal_roles": [],
            "denied_removal_roles": [],
            "auto_thread": False,
            "time_limit": 60,
        }

        # Save changes
        save_questions(questions)
        return web.Response(text="Position added successfully")
    except Exception as e:
        return web.Response(text=str(e), status=500)


@routes.post("/api/questions/position/delete")
async def delete_position(request):
    """Delete a position"""
    try:
        data = await request.json()
        position_name = data.get("name")

        if not position_name:
            return web.Response(text="Position name is required", status=400)

        # Load existing questions
        questions = load_questions()

        # Check if position exists
        if position_name not in questions:
            return web.Response(text="Position not found", status=404)

        # Delete position
        del questions[position_name]

        # Save changes
        save_questions(questions)
        return web.Response(text="Position deleted successfully")
    except Exception as e:
        return web.Response(text=str(e), status=500)


@routes.post("/api/questions/add")
async def add_question(request):
    """Add a question to a position"""
    try:
        data = await request.json()
        position_name = data.get("position")
        question_text = data.get("question")

        if not position_name or not question_text:
            return web.Response(text="Position name and question text are required", status=400)

        # Load existing questions
        questions = load_questions()

        # Check if position exists
        if position_name not in questions:
            return web.Response(text="Position not found", status=404)

        # Add question
        questions[position_name]["questions"].append(question_text)

        # Save changes
        save_questions(questions)
        return web.Response(text="Question added successfully")
    except Exception as e:
        return web.Response(text=str(e), status=500)


@routes.post("/api/questions/remove")
async def remove_question(request):
    """Remove a question from a position"""
    try:
        data = await request.json()
        position_name = data.get("position")
        question_index = data.get("index")

        if position_name is None or question_index is None:
            return web.Response(text="Position name and question index are required", status=400)

        # Load existing questions
        questions = load_questions()

        # Check if position exists
        if position_name not in questions:
            return web.Response(text="Position not found", status=404)

        # Check if question index is valid
        if question_index < 0 or question_index >= len(questions[position_name]["questions"]):
            return web.Response(text="Invalid question index", status=400)

        # Remove question
        questions[position_name]["questions"].pop(question_index)

        # Save changes
        save_questions(questions)
        return web.Response(text="Question removed successfully")
    except Exception as e:
        return web.Response(text=str(e), status=500)


@routes.post("/api/questions/update")
async def update_question(request):
    """Update a question in a position"""
    try:
        data = await request.json()
        position_name = data.get("position")
        question_index = data.get("index")
        question_text = data.get("question")

        if position_name is None or question_index is None or not question_text:
            return web.Response(text="Position name, question index, and question text are required", status=400)

        # Load existing questions
        questions = load_questions()

        # Check if position exists
        if position_name not in questions:
            return web.Response(text="Position not found", status=404)

        # Check if question index is valid
        if question_index < 0 or question_index >= len(questions[position_name]["questions"]):
            return web.Response(text="Invalid question index", status=400)

        # Update question
        questions[position_name]["questions"][question_index] = question_text

        # Save changes
        save_questions(questions)
        return web.Response(text="Question updated successfully")
    except Exception as e:
        return web.Response(text=str(e), status=500)


@routes.post("/api/panels/create")
async def create_panel(request):
    """Create a new application panel"""
    try:
        data = await request.json()
        position = data.get("position")
        channel_id = data.get("channel_id")
        message = data.get("message", "")

        if not position or not channel_id:
            return web.Response(text="Position and channel ID are required", status=400)

        # Load questions to validate position
        questions = load_questions()
        if position not in questions:
            return web.Response(text="Position not found", status=404)

        # Get the channel
        channel = request.app["bot"].get_channel(int(channel_id))
        if not channel:
            return web.Response(text="Channel not found", status=404)

        # Create the panel embed
        import discord

        embed = discord.Embed(
            title=f"{position} Applications",
            description=message or f"Click the button below to apply for {position}",
            color=discord.Color.blue(),
        )

        # Create the view with the application button
        from src.discord.views.application_view import ApplicationStartView

        # Create application data
        application_data = {
            "position": position,
            "questions": questions[position]["questions"],
            "welcome_message": questions[position].get("welcome_message", ""),
            "completion_message": questions[position].get("completion_message", ""),
            "time_limit": questions[position].get("time_limit", 60),
        }

        view = ApplicationStartView(application_data)
        view.bot = request.app["bot"]

        # Send the panel
        panel_message = await channel.send(embed=embed, view=view)

        # Save panel information
        panels = load_panels()
        panel_id = str(panel_message.id)
        panels[panel_id] = {
            "position": position,
            "channel_id": str(channel_id),
            "message_id": panel_id,
            "created_by": str(request["user"]["user_id"]),
            "created_at": str(discord.utils.utcnow()),
        }
        save_panels(panels)

        return web.Response(text="Panel created successfully")
    except Exception as e:
        logger.error(f"Error creating panel: {e}")
        return web.Response(text=str(e), status=500)


@routes.post("/api/applications/{app_id}/status")
@auth_required
async def update_application_status(request):
    """Update application status"""
    # Check if user is admin
    if not request["user_permissions"]["is_admin"]:
        return web.Response(text="Admin access required", status=403)

    app_id = request.match_info["app_id"]

    try:
        data = await request.json()
        status = data.get("status")
        reason = data.get("reason", "")

        if not status:
            return web.Response(text="Status is required", status=400)

        # Load application
        app_path = os.path.join(APPS_DIRECTORY, f"{app_id}.json")
        try:
            with open(app_path, "r") as f:
                application = json.load(f)
        except FileNotFoundError:
            return web.Response(text="Application not found", status=404)

        # Update status
        application["status"] = status
        application["processed_by"] = {
            "id": str(request["user"]["user_id"]),
            "name": request["user"]["username"],
            "with_reason": bool(reason),
            "reason": reason,
        }

        # Save application
        with open(app_path, "w") as f:
            json.dump(application, f)

        return web.Response(text="Application status updated successfully")
    except Exception as e:
        return web.Response(text=str(e), status=500)


@routes.get("/api/viewer-roles")
@auth_required
async def get_viewer_roles(request):
    """Get viewer roles"""
    # Check if user is admin
    if not request["user_permissions"]["is_admin"]:
        return web.Response(text="Admin access required", status=403)

    try:
        from src.web.utils.template_helpers import load_viewer_roles

        viewer_roles = await load_viewer_roles()

        # Get guild for role information
        guild = request.app["bot"].get_guild(int(SERVER_ID))
        if guild:
            # Update viewer roles with current role information
            for role_data in viewer_roles:
                role = guild.get_role(int(role_data["id"]))
                if role:
                    role_data["name"] = role.name
                    role_data["color"] = f"#{role.color.value:06x}"
                else:
                    role_data["name"] = "Unknown Role"
                    role_data["color"] = "#000000"

        return web.json_response(viewer_roles)
    except Exception as e:
        return web.Response(text=str(e), status=500)


@routes.post("/api/viewer-roles/update")
@auth_required
async def update_viewer_roles(request):
    """Update viewer roles"""
    # Check if user is admin
    if not request["user_permissions"]["is_admin"]:
        return web.Response(text="Admin access required", status=403)

    try:
        data = await request.json()
        viewer_roles = data.get("viewer_roles", [])

        # Save viewer roles
        with open("storage/viewer_roles.json", "w") as f:
            json.dump(viewer_roles, f)

        return web.Response(text="Viewer roles updated successfully")
    except Exception as e:
        return web.Response(text=str(e), status=500)


@routes.post("/api/questions/position/update")
@auth_required
async def update_position(request):
    """Update position settings"""
    try:
        data = await request.json()
        position_name = data.get("name")
        settings = data.get("settings")
        original_position = data.get("original_position", position_name)

        if not position_name or not settings:
            return web.Response(text="Position name and settings are required", status=400)

        # Load existing questions
        questions = load_questions()

        # Check if original position exists
        if original_position not in questions:
            return web.Response(text="Position not found", status=404)

        # Check if we're renaming the position
        if position_name != original_position:
            # Check if the new position name already exists
            if position_name in questions:
                return web.Response(text="A position with this name already exists", status=400)

            # Create new position with the new name
            questions[position_name] = questions[original_position].copy()

            # Delete the old position
            del questions[original_position]

        # Update settings
        questions[position_name].update(
            {
                "enabled": settings.get("enabled", True),
                "questions": settings.get("questions", []),
                "log_channel": settings.get("log_channel"),
                "welcome_message": settings.get(
                    "welcome_message",
                    f"Welcome to the {position_name} application process! "
                    "Please answer the following questions to complete your application.",
                ),
                "completion_message": settings.get(
                    "completion_message",
                    f"Thank you for completing your {position_name} application! "
                    "Your responses have been submitted and will be reviewed soon.",
                ),
                "accepted_message": settings.get(
                    "accepted_message",
                    f"Congratulations! Your application for {position_name} " "has been accepted. Welcome to the team!",
                ),
                "denied_message": settings.get(
                    "denied_message",
                    f"Thank you for applying for {position_name}. "
                    "After careful consideration, we have decided not to move forward "
                    "with your application at this time.",
                ),
                "ping_roles": settings.get("ping_roles", []),
                "button_roles": settings.get("button_roles", []),
                "accept_roles": settings.get("accept_roles", []),
                "reject_roles": settings.get("reject_roles", []),
                "accept_reason_roles": settings.get("accept_reason_roles", []),
                "reject_reason_roles": settings.get("reject_reason_roles", []),
                "accepted_roles": settings.get("accepted_roles", []),
                "denied_roles": settings.get("denied_roles", []),
                "restricted_roles": settings.get("restricted_roles", []),
                "required_roles": settings.get("required_roles", []),
                "accepted_removal_roles": settings.get("accepted_removal_roles", []),
                "denied_removal_roles": settings.get("denied_removal_roles", []),
                "auto_thread": settings.get("auto_thread", False),
                "time_limit": settings.get("time_limit", 60),
            }
        )

        # Save changes
        save_questions(questions)
        return web.Response(text="Position updated successfully")
    except Exception as e:
        return web.Response(text=str(e), status=500)


@routes.get("/api/validate_channel/{channel_id}")
@auth_required
async def validate_channel(request):
    """Validate that a channel exists"""
    channel_id = request.match_info["channel_id"]

    try:
        # Try to fetch the channel from Discord
        channel = request.app["bot"].get_channel(int(channel_id))
        if channel is None:
            return web.Response(status=404, text="Channel not found")

        return web.Response(status=200, text="Channel exists")
    except ValueError:
        # Invalid channel ID format
        return web.Response(status=400, text="Invalid channel ID format")
    except Exception as e:
        # Any other error
        return web.Response(status=500, text=f"Error: {str(e)}")
