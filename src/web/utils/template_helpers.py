import json
import logging
import os

from src.web.config.settings import APPS_DIRECTORY, SERVER_ID

logger = logging.getLogger(__name__)

# Global bot instance (will be set by the main web server)
bot = None


def set_bot_instance(bot_instance):
    """Set the global bot instance for utility functions"""
    global bot
    bot = bot_instance


async def get_session(request):
    """Get the current user session"""
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in request.app["sessions"]:
        return None
    return request.app["sessions"][session_id]


async def get_user_info(user_id):
    """Get user information from Discord"""
    try:
        user = bot.get_user(int(user_id))
        if user:
            return {
                "id": str(user.id),
                "name": user.name,
                "display_name": user.display_name,
                "avatar_url": str(user.avatar.url) if user.avatar else None,
            }
    except Exception as e:
        logger.error(f"Error getting user info for {user_id}: {e}")
    return None


async def load_viewer_roles():
    """Load viewer roles from storage"""
    try:
        with open("storage/viewer_roles.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error(f"Error loading viewer roles: {e}")
        return []


async def get_application_stats():
    """Get application statistics"""
    try:
        # Count total applications
        total_apps = 0
        pending_apps = 0
        approved_apps = 0
        rejected_apps = 0

        for filename in os.listdir(APPS_DIRECTORY):
            if filename.endswith(".json"):
                total_apps += 1
                try:
                    with open(os.path.join(APPS_DIRECTORY, filename), "r") as f:
                        app_data = json.load(f)
                        status = app_data.get("status", "pending")
                        if status == "pending":
                            pending_apps += 1
                        elif status == "approved":
                            approved_apps += 1
                        elif status == "rejected":
                            rejected_apps += 1
                except Exception as e:
                    logger.error(f"Error reading application {filename}: {e}")

        return {
            "total": total_apps,
            "pending": pending_apps,
            "approved": approved_apps,
            "rejected": rejected_apps,
        }
    except Exception as e:
        logger.error(f"Error getting application stats: {e}")
        return {"total": 0, "pending": 0, "approved": 0, "rejected": 0}


async def load_applications():
    """Load all applications from storage"""
    applications = []
    try:
        for filename in os.listdir(APPS_DIRECTORY):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(APPS_DIRECTORY, filename), "r") as f:
                        app_data = json.load(f)
                        app_data["id"] = filename.replace(".json", "")
                        applications.append(app_data)
                except Exception as e:
                    logger.error(f"Error reading application {filename}: {e}")
    except Exception as e:
        logger.error(f"Error loading applications: {e}")

    return applications


async def get_server_info():
    """Get server information from Discord"""
    try:
        guild = bot.get_guild(int(SERVER_ID))
        if guild:
            return {
                "id": str(guild.id),
                "name": guild.name,
                "member_count": guild.member_count,
                "icon_url": str(guild.icon.url) if guild.icon else None,
            }
    except Exception as e:
        logger.error(f"Error getting server info: {e}")
    return None
