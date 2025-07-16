import discord


class BaseView(discord.ui.View):
    """Base class for all Discord views with shared logic."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add shared logic here (logging, error handling, etc.)
