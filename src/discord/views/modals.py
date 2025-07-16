import json
import logging
import os

import discord
from discord.ui import Modal, TextInput
from question_manager import load_questions
from src.core.discord_helpers import APPS_DIRECTORY

logger = logging.getLogger(__name__)


class ReasonModal(Modal):
    def __init__(self, action: str, application_id: str):
        super().__init__(title=f"{action.capitalize()} Application")
        self.action = action
        self.application_id = application_id
        self.reason = TextInput(
            label="Reason",
            placeholder="Enter your reason here",
            style=discord.TextStyle.paragraph,
            required=True,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        app_path = os.path.join(APPS_DIRECTORY, f"{self.application_id}.json")
        with open(app_path, "r") as f:
            application = json.load(f)
        if application.get("status") in ["accept", "reject"]:
            await interaction.followup.send("This application has already been processed.", ephemeral=True)
            return
        applicant = interaction.client.get_user(int(application["user_id"]))
        if not applicant:
            await interaction.followup.send("Could not find the applicant.", ephemeral=True)
            return
        questions = load_questions()
        position_settings = questions.get(application["position"], {})
        dm_sent = False
        dm_error = None
        try:
            dm_channel = None
            for channel in interaction.client.private_channels:
                if isinstance(channel, discord.DMChannel) and channel.recipient.id == applicant.id:
                    dm_channel = channel
                    break
            if not dm_channel:
                dm_channel = await applicant.create_dm()
            if self.action == "accept":
                message = position_settings.get("accepted_message", "Your application has been accepted!")
                embed = discord.Embed(
                    title="Application Accepted!",
                    description=self.reason.value,
                    color=discord.Color.green(),
                )
                await dm_channel.send(embed=embed)
            else:
                message = position_settings.get("denied_message", "Your application has been denied.")
                embed = discord.Embed(
                    title="Application Denied",
                    description=self.reason.value,
                    color=discord.Color.red(),
                )
                await dm_channel.send(embed=embed)
            dm_sent = True
            if dm_sent:
                guild_member = interaction.guild.get_member(int(application["user_id"]))
                if guild_member:
                    if self.action == "accept":
                        bot_member = interaction.guild.get_member(interaction.client.user.id)
                        if not bot_member.guild_permissions.manage_roles:
                            logger.error("Bot does not have permission to manage roles!")
                            await interaction.followup.send(
                                "Bot does not have permission to manage roles. Please check bot permissions.",
                                ephemeral=True,
                            )
                            return
                        roles_to_add = []
                        for role_id in position_settings.get("accepted_roles", []):
                            role = interaction.guild.get_role(int(role_id))
                            if role:
                                if role.position >= bot_member.top_role.position:
                                    logger.error(f"Bot cannot manage role {role.name} (position too high)")
                                    await interaction.followup.send(
                                        f"Bot cannot manage role {role.name} (position too high). Please adjust role hierarchy.",
                                        ephemeral=True,
                                    )
                                    return
                                roles_to_add.append(role)
                                logger.info(f"Found role to add: {role.name} (ID: {role.id})")
                        roles_to_remove = []
                        for role_id in position_settings.get("denied_roles", []):
                            role = interaction.guild.get_role(int(role_id))
                            if role:
                                if role.position >= bot_member.top_role.position:
                                    logger.error(f"Bot cannot manage role {role.name} (position too high)")
                                    await interaction.followup.send(
                                        f"Bot cannot manage role {role.name} (position too high). Please adjust role hierarchy.",
                                        ephemeral=True,
                                    )
                                    return
                                roles_to_remove.append(role)
                                logger.info(f"Found role to remove: {role.name} (ID: {role.id})")
                        try:
                            if roles_to_add:
                                await guild_member.add_roles(*roles_to_add)
                                logger.info(f"Added roles: {[r.name for r in roles_to_add]}")
                            if roles_to_remove:
                                await guild_member.remove_roles(*roles_to_remove)
                                logger.info(f"Removed roles: {[r.name for r in roles_to_remove]}")
                        except discord.Forbidden as e:
                            logger.error(f"Permission error while managing roles: {e}")
                            await interaction.followup.send(
                                f"Permission error while managing roles: {e}",
                                ephemeral=True,
                            )
                            return
                        except Exception as e:
                            logger.error(f"Error while managing roles: {e}")
                            await interaction.followup.send(f"Error while managing roles: {e}", ephemeral=True)
                            return
                    else:
                        roles_to_add = []
                        for role_id in position_settings.get("denied_roles", []):
                            role = interaction.guild.get_role(int(role_id))
                            if role:
                                roles_to_add.append(role)
                                logger.info(f"Found role to add: {role.name} (ID: {role.id})")
                        roles_to_remove = []
                        for role_id in position_settings.get("accepted_roles", []):
                            role = interaction.guild.get_role(int(role_id))
                            if role:
                                roles_to_remove.append(role)
                                logger.info(f"Found role to remove: {role.name} (ID: {role.id})")
                        if roles_to_add:
                            await guild_member.add_roles(*roles_to_add)
                            logger.info(f"Added roles: {[r.name for r in roles_to_add]}")
                        if roles_to_remove:
                            await guild_member.remove_roles(*roles_to_remove)
                            logger.info(f"Removed roles: {[r.name for r in roles_to_remove]}")
                else:
                    logger.warning(f"Could not find guild member for user ID: {application['user_id']}")
        except discord.Forbidden:
            dm_error = "The bot does not have permission to send DMs to this user."
            logger.error(f"Permission error when sending DM to user ID {application['user_id']}: {dm_error}")
        except discord.HTTPException as e:
            dm_error = f"Failed to send DM: {str(e)}"
            logger.error(f"HTTP error when sending DM to user ID {application['user_id']}: {dm_error}")
        except Exception as e:
            dm_error = f"Unexpected error while sending DM: {str(e)}"
            logger.error(f"Unexpected error when sending DM to user ID {application['user_id']}: {dm_error}")
        application["status"] = "approved" if self.action == "accept" else "rejected"
        application["processed_by"] = {
            "id": str(interaction.user.id),
            "name": interaction.user.name,
            "with_reason": True,
            "reason": self.reason.value,
        }
        with open(app_path, "w") as f:
            json.dump(application, f)
        try:
            message = await interaction.channel.fetch_message(interaction.message.id)
            embed = message.embeds[0]
            embed.color = discord.Color.green() if self.action == "accept" else discord.Color.red()
            current_title = embed.title
            status_prefix = "**[ACCEPTED]** - " if self.action == "accept" else "**[DENIED]** - "
            if not current_title.startswith("**[ACCEPTED]** - ") and not current_title.startswith("**[DENIED]** - "):
                embed.title = status_prefix + current_title
            embed.add_field(
                name="Processed by",
                value=f"{interaction.user.mention} (With reason)",
                inline=False,
            )
            embed.add_field(name="Reason", value=self.reason.value, inline=False)
            await message.edit(embed=embed, view=None)
        except Exception as e:
            logger.error(f"Error updating embed: {e}")
        if dm_sent:
            await interaction.followup.send(f"Application {self.action}ed with reason.", ephemeral=True)
        else:
            await interaction.followup.send(
                f"Application {self.action}ed with reason, but could not send DM to the applicant: {dm_error}",
                ephemeral=True,
            )
