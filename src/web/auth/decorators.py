import logging

from aiohttp import web

from src.web.config.settings import SERVER_ID

logger = logging.getLogger(__name__)


def auth_required(handler):
    """Decorator that requires authentication for protected routes"""

    async def wrapper(request):
        # Check session
        session_id = request.cookies.get("session_id")
        if not session_id or session_id not in request.app["sessions"]:
            return web.HTTPFound("/auth/login")

        # Get user from session
        user = request.app["sessions"][session_id]
        request["user"] = user

        # Get server and member
        server = request.app["bot"].get_guild(int(SERVER_ID))
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

        return await handler(request)

    return wrapper
