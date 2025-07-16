import logging

import aiohttp_jinja2
from aiohttp import web

from src.web.utils.template_helpers import get_server_info, get_user_info

logger = logging.getLogger(__name__)


@web.middleware
async def error_middleware(request, handler):
    """Error handling middleware that catches exceptions and handles 404s"""
    try:
        return await handler(request)
    except web.HTTPNotFound:
        return await handle_404(request)
    except Exception:
        return await handler(request)


async def handle_404(request):
    """Handle 404 errors with a custom template"""
    # Get server info for the template
    server_info = await get_server_info()

    # Get user info if available
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
