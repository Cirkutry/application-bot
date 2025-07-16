import logging

import discord
from question_manager import load_questions
from src.core.discord_helpers import save_active_applications

from .buttons import ApplicationResponseButton, ApplicationStartButton

logger = logging.getLogger(__name__)


class ApplicationResponseView(discord.ui.View):
    def __init__(self, application_id: str, position: str):
        super().__init__(timeout=None)  # Make the view persistent
        self.application_id = application_id
        self.position = position

        # Add all buttons
        self.add_item(ApplicationResponseButton("accept", application_id))
        self.add_item(ApplicationResponseButton("reject", application_id))
        self.add_item(ApplicationResponseButton("accept", application_id, with_reason=True))
        self.add_item(ApplicationResponseButton("reject", application_id, with_reason=True))

        # Register the view with the bot
        self.bot = None  # Will be set when the view is used

    def set_bot(self, bot):
        # Set the bot instance and register view with bot's persistence system
        self.bot = bot
        bot.add_view(self)
        return self

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Get position settings
        questions = load_questions()
        position_settings = questions.get(self.position, {})

        # Get user's roles
        user_roles = [str(role.id) for role in interaction.user.roles]

        # Administrator always has permissions
        if interaction.user.guild_permissions.administrator:
            return True

        # Determine which button was clicked based on the custom_id
        custom_id = interaction.data.get("custom_id", "")
        button_type = ""

        if custom_id.startswith("app_accept_simple"):
            button_type = "accept"
            required_roles = position_settings.get("accept_roles", [])
        elif custom_id.startswith("app_reject_simple"):
            button_type = "reject"
            required_roles = position_settings.get("reject_roles", [])
        elif custom_id.startswith("app_accept_reason"):
            button_type = "accept_reason"
            required_roles = position_settings.get("accept_reason_roles", [])
        elif custom_id.startswith("app_reject_reason"):
            button_type = "reject_reason"
            required_roles = position_settings.get("reject_reason_roles", [])
        else:
            # If we can't determine button type, fall back to the general button_roles
            button_type = "unknown"
            required_roles = position_settings.get("button_roles", [])

        # Check if user has any of the required roles for this button type
        has_required_role = any(role_id in user_roles for role_id in required_roles)

        # Check the general button_roles
        has_button_role = any(role_id in user_roles for role_id in position_settings.get("button_roles", []))

        # Allow interaction if user has either specific role for this button or a general button role
        if has_required_role or has_button_role:
            return True

        # Send ephemeral error message if user doesn't have permissions
        await interaction.response.send_message(
            f"You don't have permission to use the {button_type.replace('_', ' ').title()} button. Only administrators and users with the specified roles can use this button.",
            ephemeral=True,
        )
        return False

    async def on_error(self, error: Exception, item: discord.ui.Item, interaction: discord.Interaction) -> None:
        logger.error(f"Error processing interaction: {error}")
        await interaction.response.send_message(
            "An error occurred while processing your request. Please try again later.",
            ephemeral=True,
        )


class ApplicationStartView(discord.ui.View):
    def __init__(self, bot, application_data):
        super().__init__(timeout=None)
        self.bot = bot
        self.application_data = application_data

        # Add a custom_id to the view for persistence
        self.custom_id = f"app_welcome_view_{application_data['user_id']}_{application_data['position']}"

        # Add start and cancel buttons with custom_ids
        self.add_item(ApplicationStartButton("start", application_data["user_id"], application_data["position"]))
        self.add_item(ApplicationStartButton("cancel", application_data["user_id"], application_data["position"]))

        bot.add_view(self)

    async def on_timeout(self):
        # Get the DM channel to send expiration message
        user_id = int(self.application_data["user_id"])
        user = self.bot.get_user(user_id)

        try:
            if user:
                # Create DM channel if needed
                dm_channel = await user.create_dm()
                await dm_channel.send("Your application has expired. Please start a new one.")

                # Remove from active applications
                if hasattr(self.bot, "active_applications") and str(user_id) in self.bot.active_applications:
                    del self.bot.active_applications[str(user_id)]
                    save_active_applications(self.bot.active_applications)
        except Exception as e:
            logger.error(f"Error sending expiration message: {e}")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Verify that the interaction is coming from the user who owns this application
        user_id = str(interaction.user.id)
        app_user_id = self.application_data.get("user_id", "")

        if user_id != app_user_id:
            logger.warning(f"User {user_id} tried to interact with an application belonging to {app_user_id}")
            await interaction.response.send_message("This application doesn't belong to you.", ephemeral=True)
            return False

        return True

    @classmethod
    async def restore_view(cls, bot, application_data):
        # Create the view
        view = cls(bot, application_data)

        bot.add_view(view)

        if "message_id" in application_data:
            try:
                message_id = int(application_data["message_id"])
                bot.add_view(view, message_id=message_id)
                logger.info(f"Registered view with specific message ID: {message_id}")
            except Exception as e:
                logger.error(f"Error registering view with message ID: {e}")

        return view
