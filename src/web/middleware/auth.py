import logging

from aiohttp import web

from src.web.config.settings import ADMIN_ROUTES, PUBLIC_ROUTES, SERVER_ID

logger = logging.getLogger(__name__)

# Global bot instance (will be set by the main web server)
bot = None


def set_bot_instance(bot_instance):
    """Set the global bot instance for middleware use"""
    global bot
    bot = bot_instance


@web.middleware
async def auth_middleware(request, handler):
    """Authentication middleware that checks user sessions and permissions"""
    # Allow public routes
    if request.path in PUBLIC_ROUTES:
        return await handler(request)

    # Check session
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in request.app["sessions"]:
        return web.HTTPFound("/auth/login")

    # Get user from session
    user = request.app["sessions"][session_id]
    request["user"] = user

    # Get server and member
    server = bot.get_guild(int(SERVER_ID))
    if not server:
        return web.Response(text="Server not found", status=404)

    member = server.get_member(int(user["user_id"]))
    if not member:
        return web.Response(text="User not found in server", status=404)

    # Check if user is administrator
    is_admin = member.guild_permissions.administrator

    # Set user permissions
    request["user_permissions"] = {
        "is_admin": is_admin,
        "viewer_roles": [],  # Will be populated in the index route
    }

    # Check admin-only routes
    if not is_admin and request.path in ADMIN_ROUTES:
        return web.Response(text="Admin access required", status=403)

    return await handler(request)
