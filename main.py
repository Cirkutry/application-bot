__version__ = "1.0.1"
import asyncio
import json
import logging
import os
import pathlib
import signal
import sys
from logging.handlers import RotatingFileHandler
import discord
from discord.ext import commands
from dotenv import load_dotenv
from webserver import start_web_server

COLOR = "\033[38;2;243;221;182m"
RESET = "\033[0m"
print(f"{COLOR}")
print("""
            ███████╗ █████╗ ██████╗ 
            ██╔════╝██╔══██╗██╔══██╗
            ███████╗███████║██████╔╝
            ╚════██║██╔══██║██╔══██╗
            ███████║██║  ██║██████╔╝
            ╚══════╝╚═╝  ╚═╝╚═════╝ 
""")
print(f"Simple Applications Bot v{__version__} by Kre0lidge - Starting up...\n{RESET}")
logger = logging.getLogger(__name__)


def ensure_directories():
    directories = ["storage", "storage/applications", "storage/logs"]
    for directory in directories:
        pathlib.Path(directory).mkdir(exist_ok=True)
    files = [("storage/questions.json", "{}")]
    for file_path, default_content in files:
        if not os.path.exists(file_path):
            with open(file_path, "w") as f:
                f.write(default_content)
            logger.info(f"Created default file: {file_path}")


ensure_directories()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(
            "storage/logs/bot.log", maxBytes=1024 * 1024, backupCount=5
        ),
        logging.StreamHandler(),
    ],
)
load_dotenv()
required_vars = {
    "TOKEN": "Discord Bot Token",
    "SERVER_ID": "Discord Server ID",
    "WEB_HOST": "Web Server Host",
    "WEB_PORT": "Web Server Port",
    "OAUTH_CLIENT_ID": "Discord OAuth Client ID",
    "OAUTH_CLIENT_SECRET": "Discord OAuth Client Secret",
    "OAUTH_REDIRECT_URI": "Discord OAuth Redirect URI",
}
missing_vars = [var for var, desc in required_vars.items() if not os.getenv(var)]
if missing_vars:
    error_msg = "Missing required environment variables:\n"
    for var in missing_vars:
        error_msg += f"- {var} ({required_vars[var]})\n"
    error_msg += "\nPlease create a .env file with these variables or set them in your environment."
    logging.error(error_msg)
    sys.exit(1)
TOKEN = os.getenv("TOKEN")
SERVER_ID = os.getenv("SERVER_ID")
WEB_HOST = os.getenv("WEB_HOST", "localhost")
WEB_PORT = os.getenv("WEB_PORT", "8080")
bot = None
web_runner = None
web_site = None
shutdown_event = asyncio.Event()
shutdown_lock = asyncio.Lock()


async def shutdown():
    async with shutdown_lock:
        if shutdown_event.is_set():
            return
        logging.info("Starting shutdown...")
        shutdown_event.set()
        if web_runner:
            logging.info("Closing web server...")
            await web_runner.cleanup()
        if bot:
            logging.info("Closing bot connection...")
            await bot.close()
        logging.info("Shutdown complete")
        os._exit(0)


def signal_handler(signum, frame):
    logging.info(f"Received signal {signum}, initiating shutdown...")
    asyncio.create_task(shutdown())


async def handle_exception(loop, context):
    exception = context.get("exception")
    if exception:
        logging.error(f"Caught exception: {exception}")
    else:
        logging.error(f"Caught exception: {context.get('message', 'Unknown error')}")
    if not shutdown_event.is_set():
        logging.info("Initiating shutdown due to exception...")
        await shutdown()


async def main():
    global bot, web_runner, web_site
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal_handler)
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.listen("on_interaction")
    async def handle_global_app_buttons(interaction):
        try:
            if not interaction.type == discord.InteractionType.component:
                return
            custom_id = interaction.data.get("custom_id", "")
            if custom_id.startswith("app_welcome_") and isinstance(
                interaction.channel, discord.DMChannel
            ):
                parts = custom_id.split("_")
                if len(parts) >= 4:
                    action = parts[2]
                    user_id = parts[3]
                    "_".join(parts[4:])
                    if not hasattr(bot, "active_applications"):
                        from application_components import load_active_applications

                        bot.active_applications = load_active_applications()
                    if user_id in bot.active_applications:
                        from application_components import (
                            ApplicationStartButton,
                            ApplicationStartView,
                        )

                        view = ApplicationStartView(
                            bot, bot.active_applications[user_id]
                        )
                        if action == "start" and len(view.children) > 0:
                            start_button = view.children[0]
                            if (
                                isinstance(start_button, ApplicationStartButton)
                                and start_button.action == "start"
                            ):
                                await start_button.callback(interaction)
                            else:
                                await interaction.response.send_message(
                                    "Error processing your request. Please try starting a new application.",
                                    ephemeral=True,
                                )
                        elif action == "cancel" and len(view.children) > 1:
                            cancel_button = view.children[1]
                            if (
                                isinstance(cancel_button, ApplicationStartButton)
                                and cancel_button.action == "cancel"
                            ):
                                await cancel_button.callback(interaction)
                            else:
                                await interaction.response.send_message(
                                    "Error processing your request. Please try starting a new application.",
                                    ephemeral=True,
                                )
                        else:
                            await interaction.response.send_message(
                                "Error processing your request. Please try starting a new application.",
                                ephemeral=True,
                            )
                    else:
                        await interaction.response.send_message(
                            "Your application session has expired or was not found. Please start a new application.",
                            ephemeral=True,
                        )
        except discord.errors.NotFound:
            pass
        except Exception:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "An error occurred while processing your request. Please try again or start a new application.",
                        ephemeral=True,
                    )
            except Exception:
                pass

    @bot.event
    async def on_message(message):
        await bot.process_commands(message)
        if message.guild is None:
            from application_components import handle_dm_message

            await handle_dm_message(bot, message)

    @bot.event
    async def on_ready():
        server = bot.get_guild(int(SERVER_ID))
        server_name = server.name if server else "Unknown Server"
        from application_components import load_active_applications

        bot.active_applications = load_active_applications()
        logging.info(f"Loaded {len(bot.active_applications)} active applications")
        from panels_manager import register_panels

        panel_count = await register_panels(bot)
        logging.info(f"Registered {panel_count} application panels")
        try:
            from application_components import ApplicationResponseView

            count = 0
            apps_directory = "storage/applications"
            if os.path.exists(apps_directory):
                for filename in os.listdir(apps_directory):
                    if filename.endswith(".json"):
                        app_id = filename.split(".")[0]
                        app_path = os.path.join(apps_directory, filename)
                        with open(app_path, "r") as f:
                            app_data = json.load(f)
                            if app_data.get("status") not in ["accept", "reject"]:
                                position = app_data.get("position", "")
                                ApplicationResponseView(app_id, position).set_bot(bot)
                                count += 1
            logging.info(f"Registered {count} persistent application response views")
        except Exception as e:
            logging.error(f"Error registering application response views: {e}")
        logging.info(f"Bot is ready! Connected to server: {server_name}")
        dashboard_url = f"http://{WEB_HOST}:{WEB_PORT}"
        web_external = os.getenv("WEB_EXTERNAL")
        if web_external:
            dashboard_url = web_external
        logging.info(f"Dashboard is available at: {dashboard_url}")
        logging.info("Bot is now running!")

    loop = asyncio.get_running_loop()
    loop.set_exception_handler(handle_exception)
    web_runner, web_site = await start_web_server(bot)
    try:
        try:
            await bot.start(TOKEN)
        except discord.PrivilegedIntentsRequired:
            logging.error(
                "Required Privileged Gateway Intents are disabled for this bot."
            )
            logging.error(
                "Make sure Server Members and Message Content intents are enabled in the Discord Developer Portal."
            )
            await shutdown()
        except Exception as e:
            logging.error(f"Failed to start bot: {str(e)}")
            await shutdown()
        while not shutdown_event.is_set():
            await asyncio.sleep(0.1)
        await shutdown()
    except Exception as e:
        logging.error(f"Error starting bot: {e}")
        await shutdown()
    finally:
        if not shutdown_event.is_set():
            await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logging.error(f"Unhandled exception: {e}")
    finally:
        logging.info("Successfully shutdown the service.")
