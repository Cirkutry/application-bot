#!/usr/bin/env python3
"""
Standalone web server entry point for testing the refactored web server.
This can be used to test the web server independently of the Discord bot.
"""

import asyncio
import logging

from src.web.server import start_web_server


# Create a mock bot instance for testing
class MockBot:
    def __init__(self):
        self.guilds = []
        self.private_channels = []

    def get_guild(self, guild_id):
        return None

    def get_user(self, user_id):
        return None

    def get_channel(self, channel_id):
        return None


async def main():
    """Main entry point for standalone web server"""
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Create mock bot instance
    mock_bot = MockBot()

    try:
        # Start the web server
        runner, site = await start_web_server(mock_bot)

        logger.info("Web server started successfully!")
        logger.info("Press Ctrl+C to stop the server")

        # Keep the server running
        try:
            await asyncio.Event().wait()  # Wait indefinitely
        except KeyboardInterrupt:
            logger.info("Shutting down web server...")
        finally:
            await runner.cleanup()

    except Exception as e:
        logger.error(f"Failed to start web server: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
