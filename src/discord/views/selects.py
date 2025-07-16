import logging
import traceback

import discord
from discord.ui import Select
from panels_manager import load_panels
from question_manager import load_questions
from src.core.discord_helpers import save_active_applications

logger = logging.getLogger(__name__)


class StaffPositionSelect(Select):
    def __init__(self, bot, options, panel_id=None):
        self.bot = bot
        # Ensure panel_id is always a string
        self.panel_id = str(panel_id) if panel_id is not None else "default"
        # Set the custom_id to include the panel_id and make it consistent, using the class name dynamically
        custom_id = f"{self.__class__.__name__.lower()}_{self.panel_id}"
        super().__init__(
            placeholder="Select a position to apply for.",
            options=options,
            custom_id=custom_id,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            # Get the selected position
            position = self.values[0]

            # Check if position is disabled
            questions_data = load_questions()
            position_settings = questions_data.get(position, {})
            if not position_settings.get("enabled", True):
                await interaction.response.send_message(
                    "This position is currently not taking applicants. Please try again later.",
                    ephemeral=True,
                )
                # Refresh the select menu for other users
                await self.refresh_select_menu(interaction)
                return

            # Check if user already has an active application
            if hasattr(self.view.bot, "active_applications"):
                active_app = self.view.bot.active_applications.get(str(interaction.user.id))
                if active_app:
                    # If the position and panel match, resume the application process
                    if active_app["position"] == position and active_app["panel_id"] == self.panel_id:
                        # Check if application has been started
                        if "start_time" not in active_app:
                            # Defer the interaction response first to prevent timeout
                            await interaction.response.defer(ephemeral=True)

                            # Delete the old application
                            del self.view.bot.active_applications[str(interaction.user.id)]
                            save_active_applications(self.view.bot.active_applications)

                            # Try to delete the old welcome message if it exists
                            if "message_id" in active_app:
                                try:
                                    dm_channel = await interaction.user.create_dm()
                                    try:
                                        old_message = await dm_channel.fetch_message(int(active_app["message_id"]))
                                        await old_message.delete()
                                    except Exception:
                                        pass  # Ignore if message doesn't exist or can't be deleted
                                except Exception:
                                    pass  # Ignore if DM channel can't be created

            # ... (rest of the callback logic, including sending welcome message, etc.)

        except Exception as e:
            logger.error(f"Error in StaffApplicationSelect callback: {e}")
            logger.error(f"Error traceback: {traceback.format_exc()}")
            try:
                await interaction.response.send_message(
                    "An error occurred while processing your selection. Please try again later.",
                    ephemeral=True,
                )
                # Try to refresh the select menu even on error
                await self.refresh_select_menu(interaction)
            except Exception:
                try:
                    await interaction.followup.send(
                        "An error occurred while processing your selection. Please try again later.",
                        ephemeral=True,
                    )
                    # Try to refresh the select menu even on error
                    await self.refresh_select_menu(interaction)
                except Exception:
                    pass

    async def refresh_select_menu(self, interaction: discord.Interaction):
        try:
            # Create a new view with the same options
            panels = load_panels()
            panel_data = panels.get(self.panel_id)

            if panel_data:
                from .selects import StaffPositionSelectView

                new_view = StaffPositionSelectView(self.view.bot, panel_id=self.panel_id)
                # Update the original message with the new view
                await interaction.message.edit(view=new_view)
        except Exception as e:
            logger.error(f"Error refreshing select menu: {e}")
            logger.error(f"Error traceback: {traceback.format_exc()}")


class StaffPositionSelectView(discord.ui.View):
    def __init__(self, bot, options=None, panel_id=None):
        super().__init__(timeout=None)  # Set timeout to None for persistent views
        self.bot = bot

        # Ensure panel_id is always a string
        self.panel_id = str(panel_id) if panel_id is not None else "default"

        # Create the select menu
        if options:
            select = StaffPositionSelect(bot, options, self.panel_id)
            self.add_item(select)
        else:
            # If no options provided, try to get them from the panel data
            panels = load_panels()
            panel_data = panels.get(self.panel_id)
            if panel_data:
                select_options = [
                    discord.SelectOption(
                        label=position if isinstance(position, str) else position["name"],
                        description=f"Apply for {position if isinstance(position, str) else position['name']} position",
                        value=position if isinstance(position, str) else position["name"],
                    )
                    for position in panel_data["positions"]
                ]
                select = StaffPositionSelect(bot, select_options, self.panel_id)
                self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        try:
            return True
        except Exception as e:
            logger.error(f"Error in interaction check: {e}")
            return False

    async def on_error(self, error: Exception, item: discord.ui.Item, interaction: discord.Interaction) -> None:
        logger.error(f"Error processing interaction: {error}")
        await interaction.response.send_message(
            "An error occurred while processing your request. Please try again later.",
            ephemeral=True,
        )
