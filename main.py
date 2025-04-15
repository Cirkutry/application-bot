import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import signal
import sys
from webserver import start_web_server
import logging
from logging.handlers import RotatingFileHandler
import json
import pathlib

# Get logger
logger = logging.getLogger(__name__)

def ensure_directories():
    directories = [
        'storage',
        'storage/applications',
        'storage/logs'
    ]
    
    for directory in directories:
        pathlib.Path(directory).mkdir(exist_ok=True)
    
    # Create empty files if they don't exist
    files = [
        ('storage/viewer_roles.json', '[]'),
        ('storage/questions.json', '{}')
    ]
    
    for file_path, default_content in files:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                f.write(default_content)
            logger.info(f"Created default file: {file_path}")

# Ensure directories exist before configuring logging
ensure_directories()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('storage/logs/bot.log', maxBytes=1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

# Check required environment variables
required_vars = {
    'TOKEN': 'Discord Bot Token',
    'SERVER_ID': 'Discord Server ID',
    'WEB_HOST': 'Web Server Host',
    'WEB_PORT': 'Web Server Port',
    'OAUTH_CLIENT_ID': 'Discord OAuth Client ID',
    'OAUTH_CLIENT_SECRET': 'Discord OAuth Client Secret',
    'OAUTH_REDIRECT_URI': 'Discord OAuth Redirect URI'
}

missing_vars = [var for var, desc in required_vars.items() if not os.getenv(var)]
if missing_vars:
    error_msg = "Missing required environment variables:\n"
    for var in missing_vars:
        error_msg += f"- {var} ({required_vars[var]})\n"
    error_msg += "\nPlease create a .env file with these variables or set them in your environment."
    logging.error(error_msg)
    sys.exit(1)

# Get environment variables
TOKEN = os.getenv('TOKEN')
SERVER_ID = os.getenv('SERVER_ID')
WEB_HOST = os.getenv('WEB_HOST', 'localhost')
WEB_PORT = os.getenv('WEB_PORT', '8080')

# Global variables for cleanup
bot = None
web_runner = None
web_site = None
shutdown_event = asyncio.Event()

async def shutdown():
    logging.info("Starting shutdown...")
    
    # Set shutdown event
    shutdown_event.set()
    
    # Close web server
    if web_runner:
        logging.info("Closing web server...")
        await web_runner.cleanup()
    
    # Close bot
    if bot:
        logging.info("Closing bot connection...")
        await bot.close()
    
    logging.info("Shutdown complete")

def signal_handler(signum, frame):
    logging.info(f"Received signal {signum}, initiating shutdown...")
    # Don't create a new task, just set the shutdown event
    shutdown_event.set()

async def handle_exception(loop, context):
    exception = context.get('exception')
    if exception:
        logging.error(f"Caught exception: {exception}")
    else:
        logging.error(f"Caught exception: {context.get('message', 'Unknown error')}")
    
    # Only initiate shutdown if we're not already shutting down
    if not shutdown_event.is_set():
        logging.info("Initiating shutdown due to exception...")
        await shutdown()

async def main():
    global bot, web_runner, web_site
    
    # Set up signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal_handler)
    
    # Create bot instance
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    @bot.event
    async def on_message(message):
        # Process commands first
        await bot.process_commands(message)
        
        # Handle DM messages
        if message.guild is None:  # This is a DM
            from application_components import handle_dm_message
            await handle_dm_message(bot, message)

    @bot.event
    async def on_ready():
        # Get server name
        server = bot.get_guild(int(SERVER_ID))
        server_name = server.name if server else "Unknown Server"
        
        # Load active applications
        from application_components import load_active_applications
        bot.active_applications = load_active_applications()
        logging.info(f"Loaded {len(bot.active_applications)} active applications")
        
        # Register panels
        from panels_manager import register_panels
        panel_count = await register_panels(bot)
        logging.info(f"Registered {panel_count} application panels")
        
        # Register persistent application response views for existing log embeds
        try:
            from application_components import ApplicationResponseView
            count = 0
            # Get all applications from the APPS_DIRECTORY
            apps_directory = 'storage/applications'
            if os.path.exists(apps_directory):
                for filename in os.listdir(apps_directory):
                    if filename.endswith('.json'):
                        app_id = filename.split('.')[0]
                        app_path = os.path.join(apps_directory, filename)
                        with open(app_path, 'r') as f:
                            app_data = json.load(f)
                            # Only register views for unprocessed applications
                            if app_data.get('status') not in ['accept', 'reject']:
                                position = app_data.get('position', '')
                                # Create and register view with the bot
                                ApplicationResponseView(app_id, position).set_bot(bot)
                                count += 1
            logging.info(f"Registered {count} persistent application response views")
        except Exception as e:
            logging.error(f"Error registering application response views: {e}")
        
        # Log startup information
        logging.info(f"Bot is ready! Connected to server: {server_name}")
        logging.info(f"Dashboard is available at: http://{WEB_HOST}:{WEB_PORT}")
        logging.info("Bot is now running!")
    
    # Set up exception handler
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(handle_exception)
    
    # Start web server
    web_runner, web_site = await start_web_server(bot)
    
    # Run bot
    try:
        # Start the bot
        bot_task = asyncio.create_task(bot.start(TOKEN))
        
        # Wait for either the bot to complete or the shutdown event to be set
        while not shutdown_event.is_set():
            await asyncio.sleep(0.1)
            
        # If we get here, shutdown was requested
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