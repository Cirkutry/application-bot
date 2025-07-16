import datetime
import json
import logging
import os
from datetime import UTC

import discord
from discord.ui import Button
from question_manager import load_questions
from src.core.discord_helpers import APPS_DIRECTORY, save_active_applications

from .modals import ReasonModal

logger = logging.getLogger(__name__)


class ApplicationResponseButton(Button):
    def __init__(self, action: str, application_id: str, with_reason: bool = False):
        super().__init__(
            label=f"{action.capitalize()}{' with Reason' if with_reason else ''}",
            style=discord.ButtonStyle.success if action == "accept" else discord.ButtonStyle.danger,
            custom_id=f"app_{action}_{'reason' if with_reason else 'simple'}_{application_id}",
        )
        self.action = action
        self.application_id = application_id
        self.with_reason = with_reason

    async def callback(self, interaction: discord.Interaction):
        if self.with_reason:
            # Show modal for reason input
            modal = ReasonModal(self.action, self.application_id)
            await interaction.response.send_modal(modal)
        else:
            # Defer the interaction response
            await interaction.response.defer(ephemeral=True)

            # Get the application data
            app_path = os.path.join(APPS_DIRECTORY, f"{self.application_id}.json")
            with open(app_path, "r") as f:
                application = json.load(f)

            # Check if application is already processed
            if application.get("status") in ["accept", "reject"]:
                await interaction.followup.send("This application has already been processed.", ephemeral=True)
                return

            # Get the applicant - use bot.get_user instead of guild.get_member
            applicant = interaction.client.get_user(int(application["user_id"]))
            if not applicant:
                await interaction.followup.send("Could not find the applicant.", ephemeral=True)
                return

            # Get position settings
            questions = load_questions()
            position_settings = questions.get(application["position"], {})

            # Send DM to applicant first
            dm_sent = False
            dm_error = None
            try:
                # Try to get the existing DM channel first
                dm_channel = None
                for channel in interaction.client.private_channels:
                    if isinstance(channel, discord.DMChannel) and channel.recipient.id == applicant.id:
                        dm_channel = channel
                        break

                # If no existing channel, create a new one
                if not dm_channel:
                    dm_channel = await applicant.create_dm()

                # Send DM first, before any role changes
                if self.action == "accept":
                    message = position_settings.get("accepted_message", "Your application has been accepted!")
                    embed = discord.Embed(
                        title="Application Accepted!",
                        description=message.format(position=application["position"]),
                        color=discord.Color.green(),
                    )
                    await dm_channel.send(embed=embed)
                else:
                    message = position_settings.get("denied_message", "Your application has been denied.")
                    embed = discord.Embed(
                        title="Application Denied",
                        description=message.format(position=application["position"]),
                        color=discord.Color.red(),
                    )
                    await dm_channel.send(embed=embed)
                dm_sent = True

                # Only proceed with role changes if DM was sent successfully
                if dm_sent:
                    # Get the guild member for role management
                    guild_member = interaction.guild.get_member(int(application["user_id"]))
                    if guild_member:
                        if self.action == "accept":
                            # Assign accepted roles
                            roles_to_add = []
                            for role_id in position_settings.get("accepted_roles", []):
                                role = interaction.guild.get_role(int(role_id))
                                if role:
                                    roles_to_add.append(role)
                                    logger.info(f"Found role to add: {role.name} (ID: {role.id})")

                            # Remove denied roles
                            roles_to_remove = []
                            for role_id in position_settings.get("denied_roles", []):
                                role = interaction.guild.get_role(int(role_id))
                                if role:
                                    roles_to_remove.append(role)
                                    logger.info(f"Found role to remove: {role.name} (ID: {role.id})")

                            # Apply role changes
                            if roles_to_add:
                                await guild_member.add_roles(*roles_to_add)
                                logger.info(f"Added roles: {[r.name for r in roles_to_add]}")
                            if roles_to_remove:
                                await guild_member.remove_roles(*roles_to_remove)
                                logger.info(f"Removed roles: {[r.name for r in roles_to_remove]}")
                        else:
                            # Assign denied roles
                            roles_to_add = []
                            for role_id in position_settings.get("denied_roles", []):
                                role = interaction.guild.get_role(int(role_id))
                                if role:
                                    roles_to_add.append(role)
                                    logger.info(f"Found role to add: {role.name} (ID: {role_id})")

                            # Remove accepted roles
                            roles_to_remove = []
                            for role_id in position_settings.get("accepted_roles", []):
                                role = interaction.guild.get_role(int(role_id))
                                if role:
                                    roles_to_remove.append(role)
                                    logger.info(f"Found role to remove: {role.name} (ID: {role_id})")

                            # Apply role changes
                            if roles_to_add:
                                await guild_member.add_roles(*roles_to_add)
                                logger.info(f"Added roles: {[r.name for r in roles_to_add]}")
                            if roles_to_remove:
                                await guild_member.remove_roles(*roles_to_remove)
                                logger.info(f"Removed roles: {[r.name for r in roles_to_remove]}")
                    else:
                        logger.error(f"Could not find guild member for user ID: {application['user_id']}")
            except discord.Forbidden:
                dm_error = "The bot does not have permission to send DMs to this user."
            except discord.HTTPException as e:
                dm_error = f"Failed to send DM: {str(e)}"
            except Exception as e:
                dm_error = f"Unexpected error while sending DM: {str(e)}"

            # Update application status and add processed by info
            application["status"] = "approved" if self.action == "accept" else "rejected"
            application["processed_by"] = {
                "id": str(interaction.user.id),
                "name": interaction.user.name,
                "with_reason": False,
            }
            with open(app_path, "w") as f:
                json.dump(application, f)

            # Update the embed
            try:
                # Get the original message
                message = await interaction.channel.fetch_message(interaction.message.id)

                # Create a new embed with updated color and information
                embed = message.embeds[0]
                embed.color = discord.Color.green() if self.action == "accept" else discord.Color.red()

                # Update title to indicate status for colorblind users
                current_title = embed.title
                status_prefix = "**[ACCEPTED]** - " if self.action == "accept" else "**[DENIED]** - "
                if not current_title.startswith("**[ACCEPTED]** - ") and not current_title.startswith(
                    "**[DENIED]** - "
                ):
                    embed.title = status_prefix + current_title

                # Add processed by information
                embed.add_field(
                    name="Processed by",
                    value=f"{interaction.user.mention} (Default message)",
                    inline=False,
                )

                # Update the message with new embed and remove buttons
                await message.edit(embed=embed, view=None)
            except Exception as e:
                logger.error(f"Error updating embed: {e}")

            # Send followup message
            if dm_sent:
                await interaction.followup.send(f"Application {self.action}ed.", ephemeral=True)
            else:
                await interaction.followup.send(
                    f"Application {self.action}ed, but could not send DM to the applicant: {dm_error}",
                    ephemeral=True,
                )


class ApplicationStartButton(Button):
    def __init__(self, action: str, user_id: str, position: str):
        custom_id = f"app_welcome_{action}_{user_id}_{position}"

        style = discord.ButtonStyle.success if action == "start" else discord.ButtonStyle.danger
        super().__init__(
            label="Start Application" if action == "start" else "Cancel Application",
            style=style,
            custom_id=custom_id,
        )
        self.action = action
        self.user_id = user_id
        self.position = position

    async def callback(self, interaction: discord.Interaction):
        # Get the application data from the view
        app_data = self.view.application_data

        # Handle button press
        if self.action == "start":
            # Acknowledge the interaction
            await interaction.response.defer()

            # Get position settings for time limit
            questions = load_questions()
            position = app_data.get("position", "")
            position_settings = questions.get(position, {})
            time_limit = position_settings.get("time_limit", 60)  # Default to 60 minutes if not set

            # Add a start_time to the application data to track the time limit
            if (
                hasattr(self.view.bot, "active_applications")
                and str(interaction.user.id) in self.view.bot.active_applications
            ):
                self.view.bot.active_applications[str(interaction.user.id)]["start_time"] = datetime.datetime.now(
                    UTC
                ).isoformat()
                self.view.bot.active_applications[str(interaction.user.id)]["message_id"] = str(interaction.message.id)
                save_active_applications(self.view.bot.active_applications)

            # Send the first question to the DM channel
            dm_channel = interaction.channel
            total_questions = len(app_data["questions"])
            await dm_channel.send(
                f"⏰ **Note:** You have {time_limit} minutes to complete all questions in this application."
            )
            await dm_channel.send(f"**Question 1 of {total_questions}:** {app_data['questions'][0]}")

            # Update the original embed with green color and "Application Started" footer
            original_embed = interaction.message.embeds[0]
            original_embed.color = discord.Color.green()
            original_embed.set_footer(text="Application has been started.")

            # Remove the buttons and update the embed in the original message
            await interaction.message.edit(embed=original_embed, view=None)
        else:
            # Cancel the application
            # Remove the application from active applications
            if (
                hasattr(self.view.bot, "active_applications")
                and str(interaction.user.id) in self.view.bot.active_applications
            ):
                del self.view.bot.active_applications[str(interaction.user.id)]
                save_active_applications(self.view.bot.active_applications)

            # Acknowledge the interaction and inform the user
            await interaction.response.defer()

            # Update the original embed with red color and "Application Cancelled" footer
            original_embed = interaction.message.embeds[0]
            original_embed.color = discord.Color.red()
            original_embed.set_footer(text="Application has been cancelled.")

            # Remove the buttons and update the embed in the original message
            await interaction.message.edit(embed=original_embed, view=None)

        # Stop listening for button presses
        self.view.stop()
