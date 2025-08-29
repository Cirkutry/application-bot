import datetime
import json
import logging
import math
import os
import pathlib
import secrets
import urllib.parse
import uuid
from datetime import UTC
import aiohttp
import aiohttp_jinja2
import discord
import jinja2
from aiohttp import web
from dotenv import load_dotenv
from application_components import StaffApplicationView
from panels_manager import load_panels, save_panels
from question_manager import load_questions, save_questions

load_dotenv()
WEB_HOST = os.getenv("WEB_HOST", "localhost")
WEB_PORT = int(os.getenv("WEB_PORT") or 8080)
APPS_DIRECTORY = "storage/applications"
CLIENT_ID = os.getenv("OAUTH_CLIENT_ID")
CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET")
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8080/auth/callback")
SERVER_ID = os.getenv("SERVER_ID")
API_ENDPOINT = "https://discord.com/api/v10"
TOKEN_URL = f"{API_ENDPOINT}/oauth2/token"
USER_URL = f"{API_ENDPOINT}/users/@me"
bot = None
pathlib.Path(APPS_DIRECTORY).mkdir(exist_ok=True)
oauth_states = {}
sessions = {}
PANELS_DIRECTORY = "storage"
pathlib.Path(PANELS_DIRECTORY).mkdir(exist_ok=True)


def setup_jinja2(app):
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader("static/templates"),
        context_processors=[aiohttp_jinja2.request_processor],
        filters={"json": json.dumps},
    )


class SimpleAccessFormatter(logging.Formatter):
    def format(self, record):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
        parts = record.getMessage().split('"')
        if len(parts) >= 3:
            ip = parts[0].split()[0]
            request = parts[1]
            status_size = parts[2].strip()
            return f"{timestamp} - {ip} {request} {status_size}"
        return f"{timestamp} - {record.getMessage()}"


access_log_format = SimpleAccessFormatter()


def auth_required(handler):
    async def wrapper(request):
        session_id = request.cookies.get("session_id")
        if not session_id or session_id not in sessions:
            return web.HTTPFound("/auth/login")
        user = sessions[session_id]
        request["user"] = user
        server = bot.get_guild(int(SERVER_ID))
        if not server:
            return web.Response(text="Server not found", status=404)
        member = server.get_member(int(user["user_id"]))
        if not member:
            return web.Response(text="User not found in server", status=404)
        is_admin = member.guild_permissions.administrator
        request["user_permissions"] = {
            "is_admin": is_admin,
        }
        return await handler(request)

    return wrapper


@web.middleware
async def auth_middleware(request, handler):
    if request.path in [
        "/auth/login",
        "/auth/callback",
        "/auth/logout",
    ] or request.path.startswith("/static/"):
        return await handler(request)
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        return web.HTTPFound("/auth/login")
    user = sessions[session_id]
    request["user"] = user
    server = bot.get_guild(int(SERVER_ID))
    if not server:
        return web.Response(text="Server not found", status=404)
    member = server.get_member(int(user["user_id"]))
    if not member:
        return web.Response(text="User not found in server", status=404)
    is_admin = member.guild_permissions.administrator
    request["user_permissions"] = {
        "is_admin": is_admin,
    }
    admin_routes = [
        "/positions",
        "/panel-creator",
        "/api/panels/create",
        "/api/questions/position/add",
        "/api/questions/position/delete",
        "/api/questions/add",
        "/api/questions/remove",
        "/api/questions/update",
    ]
    if not is_admin and request.path in admin_routes:
        return await handle_403(request, "admin_required")
    return await handler(request)


@web.middleware
async def error_middleware(request, handler):
    try:
        return await handler(request)
    except web.HTTPNotFound:
        return await handle_404(request)
    except Exception:
        return await handler(request)


async def handle_404(request):
    server_info = await get_server_info()
    user_info = {}
    if "user" in request and "user_id" in request["user"]:
        user_info = await get_user_info(request["user"]["user_id"])
    return aiohttp_jinja2.render_template(
        "404.html",
        request,
        {
            "user": user_info,
            "is_admin": request.get("user_permissions", {}).get("is_admin", False),
            "server": server_info,
        },
    )


async def handle_403(request, context="general"):
    server_info = await get_server_info()
    user_info = {"name": "Guest", "avatar": None, "id": None}
    is_admin = False
    if "user" in request and "user_id" in request["user"]:
        user_info = await get_user_info(request["user"]["user_id"])
        is_admin = request.get("user_permissions", {}).get("is_admin", False)
    elif hasattr(request, "_user_data"):
        user_data = request._user_data
        server = bot.get_guild(int(SERVER_ID))
        if server:
            member = server.get_member(int(user_data["id"]))
            if member:
                user_info = {
                    "name": member.name,
                    "avatar": member.display_avatar.url
                    if member.display_avatar
                    else None,
                    "id": str(member.id),
                }
    return aiohttp_jinja2.render_template(
        "403.html",
        request,
        {
            "user": user_info,
            "is_admin": is_admin,
            "server": server_info,
            "is_403": True,
            "context": context,
        },
    )


async def get_session(request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        raise web.HTTPUnauthorized(text="Invalid session")
    return sessions[session_id]


async def get_user_info(user_id):
    server = bot.get_guild(int(SERVER_ID))
    if not server:
        return None
    member = server.get_member(int(user_id))
    if not member:
        return None
    return {
        "id": str(member.id),
        "name": member.name,
        "avatar": member.display_avatar.url if member.display_avatar else None,
        "roles": [str(role.id) for role in member.roles],
        "is_admin": member.guild_permissions.administrator,
    }


def has_position_viewer_access(member, position_data):
    if not member:
        return False
    if member.guild_permissions.administrator:
        return True
    viewer_roles = position_data.get("viewer_roles", [])
    member_role_ids = [str(role.id) for role in member.roles]
    return any(role_id in member_role_ids for role_id in viewer_roles)


def get_accessible_positions(member, all_positions):
    if not member:
        return {}
    if member.guild_permissions.administrator:
        return all_positions
    accessible_positions = {}
    for position, data in all_positions.items():
        if has_position_viewer_access(member, data):
            accessible_positions[position] = data
    return accessible_positions


async def get_application_stats():
    try:
        applications = []
        for filename in os.listdir(APPS_DIRECTORY):
            if filename.endswith(".json"):
                with open(os.path.join(APPS_DIRECTORY, filename), "r") as f:
                    applications.append(json.load(f))
        total = len(applications)
        pending = sum(
            1
            for app in applications
            if app.get("status", "pending").lower() == "pending"
        )
        approved = sum(
            1 for app in applications if app.get("status", "").lower() == "approved"
        )
        rejected = sum(
            1 for app in applications if app.get("status", "").lower() == "rejected"
        )
        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
        }
    except Exception:
        return {"total": 0, "pending": 0, "approved": 0, "rejected": 0}


async def load_applications():
    applications = []
    for filename in os.listdir(APPS_DIRECTORY):
        if filename.endswith(".json"):
            with open(os.path.join(APPS_DIRECTORY, filename), "r") as f:
                app = json.load(f)
                app["id"] = filename[:-5]
                if "status" not in app:
                    app["status"] = "pending"
                applications.append(app)
    return applications


routes = web.RouteTableDef()


@routes.get("/auth/login")
async def auth_login(request):
    state = secrets.token_urlsafe(16)
    oauth_states[state] = {"created_at": datetime.datetime.now().timestamp()}
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
        "state": state,
        "prompt": "none",
    }
    oauth_url = f"{API_ENDPOINT}/oauth2/authorize?{urllib.parse.urlencode(params)}"
    return web.HTTPFound(oauth_url)


@routes.get("/auth/callback")
async def auth_callback(request):
    code = request.query.get("code")
    if not code:
        return web.Response(text="No code provided", status=400)
    async with aiohttp.ClientSession() as session:
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }
        async with session.post(TOKEN_URL, data=data) as response:
            if response.status != 200:
                return web.Response(text="Failed to get access token", status=400)
            token_data = await response.json()
            access_token = token_data["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}
            async with session.get(USER_URL, headers=headers) as user_response:
                if user_response.status != 200:
                    return web.Response(text="Failed to get user info", status=400)
                user_data = await user_response.json()
                server = bot.get_guild(int(SERVER_ID))
                if not server:
                    return web.Response(text="Server not found", status=404)
                member = server.get_member(int(user_data["id"]))
                if not member:
                    return web.Response(text="User not found in server", status=404)
                is_admin = member.guild_permissions.administrator
                all_positions = load_questions()
                has_any_viewer_access = False
                for position_data in all_positions.values():
                    if has_position_viewer_access(member, position_data):
                        has_any_viewer_access = True
                        break
                if not is_admin and not has_any_viewer_access:
                    request._user_data = user_data
                    return await handle_403(request)
                session_id = secrets.token_urlsafe(32)
                sessions[session_id] = {
                    "user_id": user_data["id"],
                    "username": user_data["username"],
                    "avatar": user_data.get("avatar"),
                    "created_at": datetime.datetime.now().timestamp(),
                }
                response = web.HTTPFound("/")
                response.set_cookie(
                    "session_id", session_id, httponly=True, max_age=86400
                )
                return response


@routes.get("/auth/logout")
async def auth_logout(request):
    session_id = request.cookies.get("session_id")
    if session_id and session_id in sessions:
        del sessions[session_id]
    response = web.HTTPFound("/auth/login")
    response.del_cookie("session_id")
    return response


async def get_server_info():
    server = bot.get_guild(int(SERVER_ID))
    if server:
        return {
            "name": server.name,
            "icon": server.icon.url if server.icon else None,
            "member_count": server.member_count,
        }
    return None


@routes.get("/")
@auth_required
async def index(request):
    session = await get_session(request)
    user_id = session["user_id"]
    server = await get_server_info()
    user = await get_user_info(user_id)
    stats = await get_application_stats()
    positions = load_questions()
    panels = load_panels()
    guild = bot.get_guild(int(SERVER_ID))
    roles = [
        {"id": str(role.id), "name": role.name}
        for role in guild.roles
        if role.name != "@everyone" and not role.managed
    ]
    return aiohttp_jinja2.render_template(
        "index.html",
        request,
        {
            "server": server,
            "user": user,
            "stats": stats,
            "positions": positions,
            "panels": panels,
            "roles": roles,
            "is_admin": request["user_permissions"]["is_admin"],
        },
    )


@routes.get("/applications")
@auth_required
async def applications(request):
    user = request["user"]
    user_permissions = request["user_permissions"]
    is_admin = user_permissions.get("is_admin", False)
    server = bot.get_guild(int(SERVER_ID))
    if not server:
        return web.Response(text="Server not found", status=404)
    member = server.get_member(int(user["user_id"]))
    if not member:
        return web.Response(text="User not found in server", status=404)
    all_positions = load_questions()
    accessible_positions = get_accessible_positions(member, all_positions)
    if not accessible_positions and not is_admin:
        return await handle_403(request, "no_positions")
    status = request.query.get("status")
    position = request.query.get("position")
    sort = request.query.get("sort")
    page = int(request.query.get("page", 1))
    per_page = 10
    all_applications = await load_applications()
    if not is_admin:
        all_applications = [
            app
            for app in all_applications
            if app.get("position") in accessible_positions
        ]
    if status:
        all_applications = [
            app
            for app in all_applications
            if app.get("status", "pending").lower() == status.lower()
        ]
    if position:
        all_applications = [
            app for app in all_applications if app.get("position") == position
        ]
    if sort == "newest":
        all_applications.sort(key=lambda app: app.get("id", ""), reverse=True)
    elif sort == "oldest":
        all_applications.sort(key=lambda app: app.get("id", ""))
    else:
        all_applications.sort(key=lambda app: app.get("id", ""), reverse=True)
    total_applications = len(all_applications)
    total_pages = math.ceil(total_applications / per_page)
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    applications = all_applications[start_index:end_index]
    for app in applications:
        status = app.get("status", "pending").lower()
        if status == "approved":
            app["status_color"] = "success"
        elif status == "rejected":
            app["status_color"] = "danger"
        else:
            app["status_color"] = "warning"
        if server:
            member = server.get_member(int(app.get("user_id", "0")))
            if member:
                app["user_avatar"] = (
                    str(member.display_avatar.url) if member.display_avatar else None
                )
                app["user_name"] = member.name
                app["user_left_server"] = False
            else:
                app["user_avatar"] = None
                app["user_name"] = app.get("user_name", "Unknown User")
                app["user_left_server"] = True
        else:
            app["user_avatar"] = None
            app["user_name"] = app.get("user_name", "Unknown User")
            app["user_left_server"] = True
    questions = load_questions()
    positions = list(questions.keys())
    server_info = await get_server_info()
    user_info = await get_user_info(user["user_id"])
    context = {
        "applications": applications,
        "total_pages": total_pages,
        "page": page,
        "positions": positions,
        "is_admin": is_admin,
        "accessible_positions": (
            list(accessible_positions.keys()) if not is_admin else positions
        ),
        "server": server_info,
        "user": user_info,
    }
    if status:
        context["status"] = status
    if position:
        context["position"] = position
    if sort:
        context["sort"] = sort
    return aiohttp_jinja2.render_template("applications.html", request, context)


@routes.get("/positions")
@auth_required
async def questions(request):
    user = request["user"]
    positions = load_questions()
    server = await get_server_info()
    user_info = await get_user_info(user["user_id"])
    guild = bot.get_guild(int(SERVER_ID))
    channels = [
        {"id": str(channel.id), "name": channel.name}
        for channel in guild.channels
        if isinstance(channel, discord.TextChannel)
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
            "user": user_info,
            "positions": positions,
            "channels": channels,
            "roles": roles,
            "is_admin": request["user_permissions"]["is_admin"],
            "server": server,
        },
    )


@routes.get("/application/{id}")
@auth_required
async def application(request):
    user = request["user"]
    user_permissions = request["user_permissions"]
    application_id = request.match_info["id"]
    app_path = os.path.join(APPS_DIRECTORY, f"{application_id}.json")
    if not os.path.exists(app_path):
        return web.Response(text="Application not found", status=404)
    try:
        with open(app_path, "r") as f:
            application = json.load(f)
    except Exception:
        return web.Response(text="Failed to load application", status=500)
    is_admin = user_permissions.get("is_admin", False)
    server = bot.get_guild(int(SERVER_ID))
    if not server:
        return web.Response(text="Server not found", status=404)
    member = server.get_member(int(user["user_id"]))
    if not member:
        return web.Response(text="User not found in server", status=404)
    all_positions = load_questions()
    app_position = application.get("position")
    if not app_position or app_position not in all_positions:
        return web.Response(text="Application position not found", status=404)
    if not is_admin and not has_position_viewer_access(
        member, all_positions[app_position]
    ):
        return await handle_403(request, "specific_application")
    status = application.get("status", "pending").lower()
    if status == "approved":
        application["status_color"] = "success"
    elif status == "rejected":
        application["status_color"] = "danger"
    else:
        application["status_color"] = "warning"
    server_info = await get_server_info()
    if server:
        member = server.get_member(int(application.get("user_id", "0")))
        if member:
            application["user_avatar"] = (
                str(member.display_avatar.url) if member.display_avatar else None
            )
            application["user_name"] = member.name
            application["user_left_server"] = False
        else:
            application["user_avatar"] = None
            application["user_name"] = application.get("user_name", "Unknown User")
            application["user_left_server"] = True
    else:
        application["user_avatar"] = None
        application["user_name"] = application.get("user_name", "Unknown User")
        application["user_left_server"] = True
    questions_text = application.get("questions", [])
    answers = application.get("answers", [])
    application["questions"] = [
        {
            "question": questions_text[i],
            "answer": answers[i] if i < len(answers) else "",
        }
        for i in range(len(questions_text))
    ]
    application["id"] = application_id
    user_info = await get_user_info(user["user_id"])
    return aiohttp_jinja2.render_template(
        "application.html",
        request,
        {
            "application": application,
            "user": user_info,
            "server": server_info,
            "is_admin": is_admin,
        },
    )


@routes.delete("/api/applications/{app_id}")
async def delete_application(request):
    app_id = request.match_info["app_id"]
    json_path = os.path.join(APPS_DIRECTORY, f"{app_id}.json")
    if not os.path.exists(json_path):
        return web.json_response({"error": "Application not found"}, status=404)
    try:
        os.remove(json_path)
        return web.json_response({"message": "Application deleted successfully"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@routes.post("/api/questions/position/add")
async def add_position(request):
    try:
        data = await request.json()
        position_name = data.get("name")
        copy_from = data.get("copy_from")
        if not position_name:
            return web.Response(text="Position name is required", status=400)
        questions = load_questions()
        if position_name in questions:
            return web.Response(text="Position already exists", status=400)
        if copy_from and copy_from in questions:
            questions[position_name] = questions[copy_from].copy()
        else:
            questions[position_name] = {
                "enabled": True,
                "questions": [],
                "log_channel": None,
                "welcome_message": f"Welcome to the {position_name} application process! Please answer the following questions to complete your application.",
                "completion_message": f"Thank you for completing your {position_name} application! Your responses have been submitted and will be reviewed soon.",
                "accepted_message": f"Congratulations! Your application for {position_name} has been accepted. Welcome to the team!",
                "denied_message": f"Thank you for applying for {position_name}. After careful consideration, we have decided not to move forward with your application at this time.",
                "ping_roles": [],
                "button_roles": [],
                "denied_removal_roles": [],
            }
        save_questions(questions)
        return web.Response(text="Position added successfully")
    except Exception as e:
        return web.Response(text=str(e), status=500)


@routes.post("/api/questions/position/delete")
async def delete_position(request):
    try:
        data = await request.json()
        position = data.get("position")
        if not position:
            return web.Response(text="Position name is required", status=400)
        questions = load_questions()
        if position in questions:
            del questions[position]
            save_questions(questions)
            return web.Response(text="Position deleted successfully")
        else:
            return web.Response(text="Position not found", status=404)
    except Exception as e:
        return web.Response(text=str(e), status=500)


@routes.post("/api/questions/add")
async def add_question(request):
    try:
        data = await request.json()
        position = data.get("position")
        question = data.get("question")
        if not position or not question:
            return web.Response(text="Position and question are required", status=400)
        questions = load_questions()
        if position in questions:
            questions[position].append(question)
            save_questions(questions)
            return web.Response(text="Question added successfully")
        else:
            return web.Response(text="Position not found", status=404)
    except Exception as e:
        return web.Response(text=str(e), status=500)


@routes.post("/api/questions/remove")
async def remove_question(request):
    try:
        data = await request.json()
        position = data.get("position")
        index = data.get("index")
        if position is None or index is None:
            return web.Response(text="Position and index are required", status=400)
        questions = load_questions()
        if position in questions and 0 <= index < len(questions[position]):
            questions[position].pop(index)
            save_questions(questions)
            return web.Response(text="Question removed successfully")
        else:
            return web.Response(text="Position or index not found", status=404)
    except Exception as e:
        return web.Response(text=str(e), status=500)


@routes.post("/api/questions/update")
async def update_question(request):
    try:
        data = await request.json()
        position = data.get("position")
        index = data.get("index")
        question = data.get("question")
        if position is None or index is None or not question:
            return web.Response(
                text="Position, index, and question are required", status=400
            )
        questions = load_questions()
        if position in questions and 0 <= index < len(questions[position]):
            questions[position][index] = question
            save_questions(questions)
            return web.Response(text="Question updated successfully")
        else:
            return web.Response(text="Position or index not found", status=404)
    except Exception as e:
        return web.Response(text=str(e), status=500)


@routes.get("/panel-creator")
@auth_required
async def panel_creator(request):
    session = await get_session(request)
    user_id = session["user_id"]
    user = await get_user_info(user_id)
    server = await get_server_info()
    positions = load_questions().keys()
    return aiohttp_jinja2.render_template(
        "panel_creator.html",
        request,
        {
            "user": user,
            "positions": positions,
            "is_admin": request["user_permissions"]["is_admin"],
            "server": server,
        },
    )


@routes.post("/api/panels/create")
async def create_panel(request):
    try:
        data = await request.json()
        try:
            channel_id = int(data["channel_id"])
        except ValueError:
            return web.Response(
                text="Invalid channel ID. Channel ID must be a number.", status=400
            )
        channel = bot.get_channel(channel_id)
        if not channel:
            return web.Response(text="Channel not found", status=404)
        panel_id = str(uuid.uuid4())
        embed = discord.Embed(
            title=data["title"],
            url=data["url"] if data["url"] else None,
            description=data["description"],
            color=int(data["color"].replace("#", ""), 16),
        )
        if data["author"]["name"]:
            embed.set_author(
                name=data["author"]["name"],
                url=data["author"]["url"] if data["author"]["url"] else None,
                icon_url=(
                    data["author"]["icon_url"] if data["author"]["icon_url"] else None
                ),
            )
        if data["thumbnail"]["url"]:
            embed.set_thumbnail(url=data["thumbnail"]["url"])
        if data["image"]["url"]:
            embed.set_image(url=data["image"]["url"])
        if data["footer"]["text"]:
            embed.set_footer(
                text=data["footer"]["text"],
                icon_url=(
                    data["footer"]["icon_url"] if data["footer"]["icon_url"] else None
                ),
            )
        select_options = [
            discord.SelectOption(
                label=position,
                value=position,
                description=f"Apply for {position} position",
            )
            for position in data["positions"]
        ]
        view = StaffApplicationView(bot, select_options, panel_id)
        message = await channel.send(embed=embed, view=view)
        bot.add_view(view, message_id=message.id)
        panel_data = {
            "id": panel_id,
            "channel_id": str(channel.id),
            "message_id": str(message.id),
            "positions": data["positions"],
        }
        panels = load_panels()
        panels[panel_id] = panel_data
        if not save_panels(panels):
            return web.Response(text="Failed to save panel data", status=500)
        return web.Response(text="Panel created successfully")
    except Exception as e:
        return web.Response(text=str(e), status=500)


@routes.post("/api/applications/{app_id}/status")
@auth_required
async def update_application_status(request):
    if not request["user_permissions"]["is_admin"]:
        return web.json_response(
            {"success": False, "error": "Admin privileges required"}, status=403
        )
    app_id = request.match_info["app_id"]
    app_path = os.path.join(APPS_DIRECTORY, f"{app_id}.json")
    if not os.path.exists(app_path):
        return web.json_response(
            {"success": False, "error": "Application not found"}, status=404
        )
    try:
        data = await request.json()
        status = data.get("status")
        if status not in ["approve", "reject"]:
            return web.json_response(
                {"success": False, "error": "Invalid status"}, status=400
            )
        with open(app_path, "r") as f:
            application = json.load(f)
        application["status"] = "approved" if status == "approve" else "rejected"
        application["processed_by"] = {
            "id": request["user"]["user_id"],
            "name": request["user"]["name"],
            "timestamp": datetime.datetime.now(UTC).isoformat(),
        }
        with open(app_path, "w") as f:
            json.dump(application, f)
        return web.json_response({"success": True})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500)


@routes.post("/api/questions/position/update")
@auth_required
async def update_position(request):
    try:
        data = await request.json()
        position_name = data.get("name")
        settings = data.get("settings")
        original_position = data.get("original_position", position_name)
        if not position_name or not settings:
            return web.Response(
                text="Position name and settings are required", status=400
            )
        questions = load_questions()
        if original_position not in questions:
            return web.Response(text="Position not found", status=404)
        if position_name != original_position:
            if position_name in questions:
                return web.Response(
                    text="A position with this name already exists", status=400
                )
            questions[position_name] = questions[original_position].copy()
            del questions[original_position]
        questions[position_name].update(
            {
                "enabled": settings.get("enabled", True),
                "questions": settings.get("questions", []),
                "log_channel": settings.get("log_channel"),
                "welcome_message": settings.get(
                    "welcome_message",
                    f"Welcome to the {position_name} application process! Please answer the following questions to complete your application.",
                ),
                "completion_message": settings.get(
                    "completion_message",
                    f"Thank you for completing your {position_name} application! Your responses have been submitted and will be reviewed soon.",
                ),
                "accepted_message": settings.get(
                    "accepted_message",
                    f"Congratulations! Your application for {position_name} has been accepted. Welcome to the team!",
                ),
                "denied_message": settings.get(
                    "denied_message",
                    f"Thank you for applying for {position_name}. After careful consideration, we have decided not to move forward with your application at this time.",
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
                "viewer_roles": settings.get("viewer_roles", []),
                "auto_thread": settings.get("auto_thread", False),
                "time_limit": settings.get("time_limit", 60),
            }
        )
        save_questions(questions)
        return web.Response(text="Position updated successfully")
    except Exception as e:
        return web.Response(text=str(e), status=500)


@routes.get("/positions/edit/{position}")
@auth_required
async def edit_position(request):
    position = request.match_info["position"]
    questions = load_questions()
    if position not in questions:
        return web.Response(text="Position not found", status=404)
    settings = questions[position]
    guild = bot.get_guild(int(SERVER_ID))
    channels = [
        {"id": str(channel.id), "name": channel.name}
        for channel in guild.channels
        if isinstance(channel, discord.TextChannel)
    ]
    roles = [
        {"id": str(role.id), "name": role.name, "color": f"#{role.color.value:06x}"}
        for role in guild.roles
        if role.name != "@everyone" and not role.managed
    ]
    user = await get_user_info(request["user"]["user_id"])
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


@routes.get("/api/validate_channel/{channel_id}")
@auth_required
async def validate_channel(request):
    channel_id = request.match_info["channel_id"]
    try:
        channel = bot.get_channel(int(channel_id))
        if channel is None:
            return web.Response(status=404, text="Channel not found")
        return web.Response(status=200, text="Channel exists")
    except ValueError:
        return web.Response(status=400, text="Invalid channel ID format")
    except Exception as e:
        return web.Response(status=500, text=f"Error: {str(e)}")


async def start_web_server(bot_instance):
    global bot
    bot = bot_instance
    app = web.Application(middlewares=[auth_middleware, error_middleware])
    setup_jinja2(app)
    app.add_routes(routes)
    app.router.add_static("/static", "static")
    logging.basicConfig(level=logging.INFO)
    aiohttp_logger = logging.getLogger("aiohttp.access")
    aiohttp_logger.setLevel(logging.INFO)
    access_logger = logging.getLogger("aiohttp.access")
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False
    handler = logging.StreamHandler()
    handler.setFormatter(access_log_format)
    access_logger.addHandler(handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
    await site.start()
    return runner, site


if __name__ == "__main__":
    import asyncio

    loop = asyncio.get_event_loop()
    runner, site = loop.run_until_complete(start_web_server(bot))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(runner.cleanup())
