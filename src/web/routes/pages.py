import aiohttp_jinja2
from aiohttp import web

from src.web.auth.decorators import auth_required
from src.web.config.settings import SERVER_ID
from src.web.utils.template_helpers import (
    get_application_stats,
    get_server_info,
    get_user_info,
    load_applications,
    load_viewer_roles,
)

routes = web.RouteTableDef()


@routes.get("/")
@auth_required
async def index(request):
    """Main dashboard page"""
    # Get user information from session
    user = await get_user_info(request["user"]["user_id"])

    # Get server information
    server = await get_server_info()

    # Get application statistics
    stats = await get_application_stats()

    # Load viewer roles for admin users
    viewer_roles = []
    if request["user_permissions"]["is_admin"]:
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

    return aiohttp_jinja2.render_template(
        "index.html",
        request,
        {
            "user": user,
            "is_admin": request["user_permissions"]["is_admin"],
            "server": server,
            "stats": stats,
            "viewer_roles": viewer_roles,
        },
    )


@routes.get("/applications")
@auth_required
async def applications(request):
    """Applications listing page"""
    # Get the user from the request
    user = await get_user_info(request["user"]["user_id"])

    # Get server information
    server = await get_server_info()

    # Load all applications
    applications = await load_applications()

    # Filter applications based on user permissions
    if not request["user_permissions"]["is_admin"]:
        # Non-admin users can only see applications they have permission to view
        viewer_roles = await load_viewer_roles()
        user_roles = [
            str(role.id)
            for role in request.app["bot"].get_guild(int(SERVER_ID)).get_member(int(request["user"]["user_id"])).roles
        ]

        # Check if user has any viewer roles
        has_viewer_role = any(role["id"] in user_roles for role in viewer_roles)

        if not has_viewer_role:
            # User has no viewer roles, show empty list
            applications = []
        else:
            # User has viewer roles, show all applications (viewer roles are for viewing all apps)
            pass

    # Sort applications by timestamp (newest first)
    applications.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return aiohttp_jinja2.render_template(
        "applications.html",
        request,
        {
            "user": user,
            "is_admin": request["user_permissions"]["is_admin"],
            "server": server,
            "applications": applications,
        },
    )


@routes.get("/positions")
@auth_required
async def questions(request):
    """Positions management page"""
    # Get user information from session
    user = await get_user_info(request["user"]["user_id"])

    # Get server information
    server = await get_server_info()

    # Load questions/positions
    from question_manager import load_questions

    questions_data = load_questions()

    # Get guild for channel and role information
    guild = request.app["bot"].get_guild(int(SERVER_ID))
    channels = []
    roles = []

    if guild:
        channels = [
            {"id": str(channel.id), "name": channel.name}
            for channel in guild.channels
            if hasattr(channel, 'type') and channel.type.value == 0  # Text channels
        ]
        roles = [
            {"id": str(role.id), "name": role.name, "color": f"#{role.color.value:06x}"}
            for role in guild.roles
            if role.name != "@everyone" and not role.managed
        ]

    return aiohttp_jinja2.render_template(
        "positions.html",
        request,
        {
            "user": user,
            "is_admin": request["user_permissions"]["is_admin"],
            "server": server,
            "questions": questions_data,
            "channels": channels,
            "roles": roles,
        },
    )


@routes.get("/application/{id}")
@auth_required
async def application(request):
    """Individual application view page"""
    # Get the user from the request
    user = await get_user_info(request["user"]["user_id"])

    # Get server information
    server = await get_server_info()

    # Get application ID from URL
    app_id = request.match_info["id"]

    # Load application data
    import json
    import os

    from src.web.config.settings import APPS_DIRECTORY

    app_path = os.path.join(APPS_DIRECTORY, f"{app_id}.json")
    try:
        with open(app_path, "r") as f:
            application = json.load(f)
    except FileNotFoundError:
        return web.Response(text="Application not found", status=404)
    except Exception as e:
        return web.Response(text=f"Error loading application: {str(e)}", status=500)

    # Check if user has permission to view this application
    if not request["user_permissions"]["is_admin"]:
        viewer_roles = await load_viewer_roles()
        user_roles = [
            str(role.id)
            for role in request.app["bot"].get_guild(int(SERVER_ID)).get_member(int(request["user"]["user_id"])).roles
        ]

        # Check if user has any viewer roles
        has_viewer_role = any(role["id"] in user_roles for role in viewer_roles)

        if not has_viewer_role:
            return web.Response(text="Access denied", status=403)

    # Get applicant information
    applicant = request.app["bot"].get_user(int(application["user_id"]))
    applicant_info = None
    if applicant:
        applicant_info = {
            "id": str(applicant.id),
            "name": applicant.name,
            "display_name": applicant.display_name,
            "avatar_url": str(applicant.avatar.url) if applicant.avatar else None,
        }

    return aiohttp_jinja2.render_template(
        "application.html",
        request,
        {
            "user": user,
            "is_admin": request["user_permissions"]["is_admin"],
            "server": server,
            "application": application,
            "applicant": applicant_info,
        },
    )


@routes.get("/panel-creator")
@auth_required
async def panel_creator(request):
    """Panel creator page"""
    # Get user information from session
    user = await get_user_info(request["user"]["user_id"])

    # Get server information
    server = await get_server_info()

    # Get guild for channel information
    guild = request.app["bot"].get_guild(int(SERVER_ID))
    channels = []
    if guild:
        channels = [
            {"id": str(channel.id), "name": channel.name}
            for channel in guild.channels
            if hasattr(channel, 'type') and channel.type.value == 0  # Text channels
        ]

    return aiohttp_jinja2.render_template(
        "panel_creator.html",
        request,
        {
            "user": user,
            "is_admin": request["user_permissions"]["is_admin"],
            "server": server,
            "channels": channels,
        },
    )


@routes.get("/positions/edit/{position}")
@auth_required
async def edit_position(request):
    """Edit position page"""
    position = request.match_info["position"]

    # Get position settings from questions file
    from question_manager import load_questions

    questions = load_questions()
    if position not in questions:
        return web.Response(text="Position not found", status=404)

    settings = questions[position]

    # Get channels and roles
    guild = request.app["bot"].get_guild(int(SERVER_ID))
    channels = []
    roles = []
    if guild:
        channels = [
            {"id": str(channel.id), "name": channel.name}
            for channel in guild.channels
            if hasattr(channel, 'type') and channel.type.value == 0  # Text channels
        ]
        roles = [
            {"id": str(role.id), "name": role.name, "color": f"#{role.color.value:06x}"}
            for role in guild.roles
            if role.name != "@everyone" and not role.managed
        ]

    # Get user info
    user = await get_user_info(request["user"]["user_id"])

    # Get server info
    server = await get_server_info()

    return aiohttp_jinja2.render_template(
        "edit_position.html",
        request,
        {
            "position": position,
            "settings": settings,
            "channels": channels,
            "roles": roles,
            "user": user,
            "is_admin": request["user_permissions"]["is_admin"],
            "server": server,
        },
    )
