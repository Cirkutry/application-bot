import os
import pathlib

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Web server settings
WEB_HOST = os.getenv("WEB_HOST", "localhost")
WEB_PORT = int(os.getenv("WEB_PORT") or 8080)

# Discord OAuth settings
CLIENT_ID = os.getenv("OAUTH_CLIENT_ID")
CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET")
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8080/auth/callback")
SERVER_ID = os.getenv("SERVER_ID")

# Discord API endpoints
API_ENDPOINT = "https://discord.com/api/v10"
TOKEN_URL = f"{API_ENDPOINT}/oauth2/token"
USER_URL = f"{API_ENDPOINT}/users/@me"

# Storage directories
APPS_DIRECTORY = "storage/applications"
PANELS_DIRECTORY = "storage"

# Ensure directories exist
pathlib.Path(APPS_DIRECTORY).mkdir(exist_ok=True)
pathlib.Path(PANELS_DIRECTORY).mkdir(exist_ok=True)

# Admin-only routes that require administrator permissions
ADMIN_ROUTES = [
    "/positions",
    "/panel-creator",
    "/api/panels/create",
    "/api/questions/position/add",
    "/api/questions/position/delete",
    "/api/questions/add",
    "/api/questions/remove",
    "/api/questions/update",
]

# Public routes that don't require authentication
PUBLIC_ROUTES = ["/auth/login", "/auth/callback", "/auth/logout"]
