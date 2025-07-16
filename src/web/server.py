import logging

from aiohttp import web

from src.web.config.settings import WEB_HOST, WEB_PORT
from src.web.middleware.auth import auth_middleware
from src.web.middleware.auth import set_bot_instance as set_bot_middleware
from src.web.middleware.error import error_middleware

# Import all route modules
from src.web.routes import api, auth, pages
from src.web.utils.logging import setup_logging
from src.web.utils.template_helpers import set_bot_instance as set_bot_utils
from src.web.utils.template_setup import setup_jinja2

logger = logging.getLogger(__name__)


async def start_web_server(bot_instance):
    """Start the web server with all components"""
    # Set bot instance in middleware and utilities
    set_bot_middleware(bot_instance)
    set_bot_utils(bot_instance)

    # Create web application
    app = web.Application(middlewares=[auth_middleware, error_middleware])

    # Setup Jinja2
    setup_jinja2(app)

    # Store bot instance and sessions in app context
    app["bot"] = bot_instance
    app["sessions"] = {}

    # Add routes from all modules
    app.add_routes(auth.routes)
    app.add_routes(pages.routes)
    app.add_routes(api.routes)

    # Add static routes
    app.router.add_static("/static", "static")

    # Setup logging
    setup_logging()

    # Start the server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
    await site.start()

    logger.info(f"Web server started on {WEB_HOST}:{WEB_PORT}")
    return runner, site
