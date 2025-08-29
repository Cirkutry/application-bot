import datetime
import json
import logging
import os
import pathlib
import traceback
import uuid
from datetime import UTC
import discord
from discord.ui import Button, Item, Modal, Select, TextInput, View
from dotenv import load_dotenv
from panels_manager import load_panels
from question_manager import get_questions, load_questions
logger = logging.getLogger(__name__)
load_dotenv()
pathlib.Path("storage").mkdir(exist_ok=True)
APPS_DIRECTORY = "storage/applications"
pathlib.Path(APPS_DIRECTORY).mkdir(exist_ok=True)
ACTIVE_APPS_FILE = os.path.join("storage", "active_applications.json")
async def get_dm_link(bot, user):
    try:
        dm_channel = await user.create_dm()
        if dm_channel:
            return f"https://discord.com/channels/@me/{dm_channel.id}"
    except Exception as e:
        logger.error(f"Error creating DM link: {e}")
    return "https://discord.com/app"
def load_active_applications():
    if not os.path.exists(ACTIVE_APPS_FILE):
        return {}
    try:
        with open(ACTIVE_APPS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading active applications: {str(e)}")
        return {}
def save_active_applications(applications):
    try:
        if not os.path.exists(APPS_DIRECTORY):
            os.makedirs(APPS_DIRECTORY)
        with open(ACTIVE_APPS_FILE, "w") as f:
            json.dump(applications, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving active applications: {str(e)}")
        return False
async def handle_dm_message(bot, message):
    if not isinstance(message.channel, discord.DMChannel):
        return
    if message.author.bot:
        return
    if not hasattr(bot, "active_applications"):
        bot.active_applications = load_active_applications()
    application = bot.active_applications.get(str(message.author.id))
    if not application:
        return
    if "start_time" not in application:
        return
    if "start_time" in application:
        start_time = datetime.datetime.fromisoformat(application["start_time"])
        current_time = datetime.datetime.now(UTC)
        time_elapsed = (
            current_time - start_time
        ).total_seconds() / 60
        questions = load_questions()
        position_settings = questions.get(application["position"], {})
        time_limit = position_settings.get(
            "time_limit", 60
        )
        if time_elapsed > time_limit:
            await message.channel.send(
                f"⌛ Your application has expired. You had {time_limit} minutes to complete it. Please start a new application if you wish to apply."
            )
            del bot.active_applications[str(message.author.id)]
            save_active_applications(bot.active_applications)
            return
    current_question = application["current_question"]
    questions = application["questions"]
    application["answers"].append(message.content)
    if current_question + 1 < len(questions):
        application["current_question"] += 1
        await message.channel.send(
            f"**Question {current_question + 2} of {len(questions)}:** {questions[current_question + 1]}"
        )
        save_active_applications(bot.active_applications)
    else:
        application_id = str(uuid.uuid4())
        application_data = {
            "id": application_id,
            "user_id": application["user_id"],
            "user_name": application["user_name"],
            "position": application["position"],
            "questions": application["questions"],
            "answers": application["answers"],
            "status": "pending",
        }
        app_path = os.path.join(APPS_DIRECTORY, f"{application_id}.json")
        with open(app_path, "w") as f:
            json.dump(application_data, f)
        del bot.active_applications[str(message.author.id)]
        save_active_applications(bot.active_applications)
        questions = load_questions()
        position_settings = questions.get(application["position"], {})
        completion_message = position_settings.get(
            "completion_message",
            f"Thank you for completing your application for {application['position']}! Your responses have been submitted and will be reviewed soon.",
        )
        embed = discord.Embed(
            title=f"{application['position']} Application Submitted",
            description=completion_message.format(position=application["position"]),
            color=discord.Color.green(),
        )
        await message.channel.send(embed=embed)
        questions = load_questions()
        position_settings = questions.get(application["position"], {})
        log_channel_id = position_settings.get("log_channel")
        if log_channel_id:
            try:
                log_channel = bot.get_channel(int(log_channel_id))
                if log_channel:
                    web_host = os.getenv("WEB_HOST", "localhost")
                    web_port = os.getenv("WEB_PORT", "8080")
                    application_url = (
                        f"http://{web_host}:{web_port}/application/{application_id}"
                    )
                    web_external = os.getenv("WEB_EXTERNAL")
                    if web_external:
                        application_url = f"{web_external}/application/{application_id}"
                    embed = discord.Embed(
                        title=f"{message.author.name}'s {application['position']} application",
                        description=f"Applicant: {message.author.mention} ({message.author.id})",
                        color=0x808080,
                    )
                    embed.description += (
                        f"\n\n[Click here to view the application]({application_url})"
                    )
                    guild = log_channel.guild
                    member = guild.get_member(message.author.id)
                    if member and member.joined_at:
                        embed.description += f"\n\nJoined server: <t:{int(member.joined_at.timestamp())}:R>"
                    embed.set_thumbnail(url=message.author.display_avatar.url)
                    embed.set_footer(text=f"{application_id}")
                    view = ApplicationResponseView(
                        application_id, application["position"]
                    )
                    view.bot = bot
                    ping_mentions = ""
                    ping_roles = position_settings.get("ping_roles", [])
                    if ping_roles:
                        ping_mentions = " ".join(
                            [f"<@&{role_id}>" for role_id in ping_roles]
                        )
                    log_message = await log_channel.send(
                        content=ping_mentions if ping_mentions else None,
                        embed=embed,
                        view=view,
                    )
                    if position_settings.get("auto_thread", False):
                        try:
                            thread_name = (
                                f"{application['position']} - {message.author.name}"
                            )
                            await log_message.create_thread(
                                name=thread_name, auto_archive_duration=1440
                            )
                        except Exception as e:
                            logger.error(f"Error creating thread: {e}")
            except Exception as e:
                logger.error(f"Error logging application: {e}")
class StaffApplicationSelect(Select):
    def __init__(self, bot, options, panel_id=None):
        self.bot = bot
        self.panel_id = str(panel_id) if panel_id is not None else "default"
        custom_id = f"staff_application_select_{self.panel_id}"
        super().__init__(
            placeholder="Select a position to apply for.",
            options=options,
            custom_id=custom_id,
            min_values=1,
            max_values=1,
        )
    async def callback(self, interaction: discord.Interaction):
        try:
            position = self.values[0]
            questions_data = load_questions()
            position_settings = questions_data.get(position, {})
            if not position_settings.get("enabled", True):
                await interaction.response.send_message(
                    "This position is currently not taking applicants. Please try again later.",
                    ephemeral=True,
                )
                await self.refresh_select_menu(interaction)
                return
            user_roles = [str(role.id) for role in interaction.user.roles]
            restricted_roles = position_settings.get("restricted_roles", [])
            if restricted_roles and any(
                role_id in user_roles for role_id in restricted_roles
            ):
                await interaction.response.send_message(
                    "You do not have permission to apply for this position.",
                    ephemeral=True,
                )
                await self.refresh_select_menu(interaction)
                return
            required_roles = position_settings.get("required_roles", [])
            if required_roles and not any(
                role_id in user_roles for role_id in required_roles
            ):
                await interaction.response.send_message(
                    "You do not have the required roles to apply for this position.",
                    ephemeral=True,
                )
                await self.refresh_select_menu(interaction)
                return
            if hasattr(self.view.bot, "active_applications"):
                active_app = self.view.bot.active_applications.get(
                    str(interaction.user.id)
                )
                if active_app:
                    if (
                        active_app["position"] == position
                        and active_app["panel_id"] == self.panel_id
                    ):
                        if "start_time" not in active_app:
                            await interaction.response.defer(ephemeral=True)
                            del self.view.bot.active_applications[
                                str(interaction.user.id)
                            ]
                            save_active_applications(self.view.bot.active_applications)
                            if "message_id" in active_app:
                                try:
                                    dm_channel = await interaction.user.create_dm()
                                    try:
                                        old_message = await dm_channel.fetch_message(
                                            int(active_app["message_id"])
                                        )
                                        await old_message.delete()
                                    except Exception:
                                        pass
                                except Exception:
                                    pass
                            user_roles = [
                                str(role.id) for role in interaction.user.roles
                            ]
                            restricted_roles = position_settings.get(
                                "restricted_roles", []
                            )
                            if restricted_roles and any(
                                role_id in user_roles for role_id in restricted_roles
                            ):
                                await interaction.followup.send(
                                    "You do not have permission to apply for this position.",
                                    ephemeral=True,
                                )
                                await self.refresh_select_menu(interaction)
                                return
                            required_roles = position_settings.get("required_roles", [])
                            if required_roles and not any(
                                role_id in user_roles for role_id in required_roles
                            ):
                                await interaction.followup.send(
                                    "You do not have the required roles to apply for this position.",
                                    ephemeral=True,
                                )
                                await self.refresh_select_menu(interaction)
                                return
                            questions = get_questions(position)
                            if not questions or len(questions) == 0:
                                logger.error(
                                    f"No questions loaded for position {position}"
                                )
                                await interaction.followup.send(
                                    "This position has no questions set up. Please contact an administrator.",
                                    ephemeral=True,
                                )
                                await self.refresh_select_menu(interaction)
                                return
                            application_data = {
                                "user_id": str(interaction.user.id),
                                "user_name": interaction.user.name,
                                "position": position,
                                "questions": questions,
                                "answers": [],
                                "current_question": 0,
                                "panel_id": self.panel_id,
                            }
                            self.view.bot.active_applications[
                                str(interaction.user.id)
                            ] = application_data
                            save_active_applications(self.view.bot.active_applications)
                            try:
                                dm = await interaction.user.create_dm()
                                questions_data = load_questions()
                                position_settings = questions_data.get(position, {})
                                welcome_message = position_settings.get(
                                    "welcome_message",
                                    f"Thank you for applying for the {position} position!",
                                )
                                welcome_view = ApplicationStartView(
                                    self.view.bot, application_data
                                )
                                embed = discord.Embed(
                                    title=f"{position} Application",
                                    description=welcome_message.format(
                                        position=position
                                    ),
                                    color=discord.Color.blue(),
                                )
                                welcome_message = await dm.send(
                                    embed=embed, view=welcome_view
                                )
                                self.view.bot.active_applications[
                                    str(interaction.user.id)
                                ]["message_id"] = str(welcome_message.id)
                                save_active_applications(
                                    self.view.bot.active_applications
                                )
                                dm_link = await get_dm_link(
                                    self.view.bot, interaction.user
                                )
                                await interaction.followup.send(
                                    f"Please check your DMs to start or cancel the application.\n[Click here to open your DMs]({dm_link})",
                                    ephemeral=True,
                                )
                            except Exception as e:
                                logger.error(f"Error sending new welcome message: {e}")
                                await interaction.followup.send(
                                    "Failed to send you a DM. Please check your Privacy settings for this server and make sure Direct Messages are enabled.",
                                    ephemeral=True,
                                )
                            await self.refresh_select_menu(interaction)
                            return
                    elif active_app["position"] == position:
                        dm_link = await get_dm_link(self.view.bot, interaction.user)
                        await interaction.response.send_message(
                            f"You have an active application but haven't started it yet. Please check your DMs to start or cancel the application.\n[Click here to open your DMs]({dm_link})",
                            ephemeral=True,
                        )
                        await self.refresh_select_menu(interaction)
                        return
                    else:
                        if "start_time" not in active_app:
                            dm_link = await get_dm_link(self.view.bot, interaction.user)
                            await interaction.response.send_message(
                                f"You have an active application for a different position but haven't started it yet. Please check your DMs to start or cancel the application.\n[Click here to open your DMs]({dm_link})",
                                ephemeral=True,
                            )
                        else:
                            dm_link = await get_dm_link(self.view.bot, interaction.user)
                            await interaction.response.send_message(
                                f"You already have an active application for a different position. Please complete it or wait for it to be reviewed.\n[Click here to open your DMs]({dm_link})",
                                ephemeral=True,
                            )
                        await self.refresh_select_menu(interaction)
                        return
            questions = get_questions(position)
            if not questions or len(questions) == 0:
                logger.error(f"No questions loaded for position {position}")
                await interaction.response.send_message(
                    "This position has no questions set up. Please contact an administrator.",
                    ephemeral=True,
                )
                await self.refresh_select_menu(interaction)
                return
            questions_data = load_questions()
            position_settings = questions_data.get(position, {})
            log_channel_id = position_settings.get("log_channel")
            if not log_channel_id:
                logger.error(f"No log channel set for position {position}")
                await interaction.response.send_message(
                    "This position has no log channel set up. Please contact an administrator.",
                    ephemeral=True,
                )
                await self.refresh_select_menu(interaction)
                return
            application_data = {
                "user_id": str(interaction.user.id),
                "user_name": interaction.user.name,
                "position": position,
                "questions": questions,
                "answers": [],
                "current_question": 0,
                "panel_id": self.panel_id,
            }
            if not hasattr(self.view.bot, "active_applications"):
                self.view.bot.active_applications = load_active_applications()
            self.view.bot.active_applications[str(interaction.user.id)] = (
                application_data
            )
            save_active_applications(self.view.bot.active_applications)
            await interaction.response.defer(ephemeral=True)
            dm_success = False
            try:
                dm = await interaction.user.create_dm()
                questions_data = load_questions()
                position_settings = questions_data.get(position, {})
                welcome_message = position_settings.get(
                    "welcome_message",
                    f"Thank you for applying for the {position} position!",
                )
                welcome_view = ApplicationStartView(self.view.bot, application_data)
                embed = discord.Embed(
                    title=f"{position} Application",
                    description=welcome_message.format(position=position),
                    color=discord.Color.blue(),
                )
                welcome_message = await dm.send(embed=embed, view=welcome_view)
                if str(interaction.user.id) in self.view.bot.active_applications:
                    self.view.bot.active_applications[str(interaction.user.id)][
                        "message_id"
                    ] = str(welcome_message.id)
                    save_active_applications(self.view.bot.active_applications)
                if (
                    not application_data["questions"]
                    or len(application_data["questions"]) == 0
                ):
                    logger.error(f"No questions found for position {position}")
                    await dm.send(
                        "ERROR: No questions were found for this position. Please contact an administrator."
                    )
                    await interaction.followup.send(
                        "Error: No questions found for this position. Please contact an administrator.",
                        ephemeral=True,
                    )
                    del self.view.bot.active_applications[str(interaction.user.id)]
                    save_active_applications(self.view.bot.active_applications)
                    await self.refresh_select_menu(interaction)
                    return
                dm_success = True
                dm_link = await get_dm_link(self.view.bot, interaction.user)
                await interaction.followup.send(
                    f"Application initiated! Please check your DMs to start the application process.\n[Click here to open your DMs]({dm_link})",
                    ephemeral=True,
                )
                await self.refresh_select_menu(interaction)
            except Exception as e:
                logger.error(f"Error sending DM questions: {e}")
                logger.error(f"Application data: {application_data}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                try:
                    if "dm" in locals():
                        await dm.send(
                            "An error occurred while sending your questions. Please contact an administrator."
                        )
                except Exception:
                    pass
                if not dm_success:
                    await interaction.followup.send(
                        "Failed to send you a DM to start the application! Please check your Privacy settings for this server and make sure Direct Messages are enabled and try again.",
                        ephemeral=True,
                    )
                if str(interaction.user.id) in self.view.bot.active_applications:
                    del self.view.bot.active_applications[str(interaction.user.id)]
                    save_active_applications(self.view.bot.active_applications)
                await self.refresh_select_menu(interaction)
                return
        except Exception as e:
            logger.error(f"Error in StaffApplicationSelect callback: {e}")
            logger.error(f"Error traceback: {traceback.format_exc()}")
            try:
                await interaction.response.send_message(
                    "An error occurred while processing your selection. Please try again later.",
                    ephemeral=True,
                )
                await self.refresh_select_menu(interaction)
            except Exception:
                try:
                    await interaction.followup.send(
                        "An error occurred while processing your selection. Please try again later.",
                        ephemeral=True,
                    )
                    await self.refresh_select_menu(interaction)
                except Exception:
                    pass
    async def refresh_select_menu(self, interaction: discord.Interaction):
        try:
            panels = load_panels()
            panel_data = panels.get(self.panel_id)
            if panel_data:
                new_view = StaffApplicationView(self.view.bot, panel_id=self.panel_id)
                await interaction.message.edit(view=new_view)
        except Exception as e:
            logger.error(f"Error refreshing select menu: {e}")
            logger.error(f"Error traceback: {traceback.format_exc()}")
class StaffApplicationView(View):
    def __init__(self, bot, options=None, panel_id=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.panel_id = str(panel_id) if panel_id is not None else "default"
        if options:
            select = StaffApplicationSelect(bot, options, self.panel_id)
            self.add_item(select)
        else:
            panels = load_panels()
            panel_data = panels.get(self.panel_id)
            if panel_data:
                select_options = [
                    discord.SelectOption(
                        label=position
                        if isinstance(position, str)
                        else position["name"],
                        description=f"Apply for {position if isinstance(position, str) else position['name']} position",
                        value=position
                        if isinstance(position, str)
                        else position["name"],
                    )
                    for position in panel_data["positions"]
                ]
                select = StaffApplicationSelect(bot, select_options, self.panel_id)
                self.add_item(select)
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        try:
            return True
        except Exception as e:
            logger.error(f"Error in interaction check: {e}")
            return False
    async def on_error(
        self, error: Exception, item: Item, interaction: discord.Interaction
    ) -> None:
        logger.error(f"Error processing interaction: {error}")
        await interaction.response.send_message(
            "An error occurred while processing your request. Please try again later.",
            ephemeral=True,
        )
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
            await interaction.followup.send(
                "This application has already been processed.", ephemeral=True
            )
            return
        applicant = interaction.client.get_user(int(application["user_id"]))
        if not applicant:
            await interaction.followup.send(
                "Could not find the applicant.", ephemeral=True
            )
            return
        questions = load_questions()
        position_settings = questions.get(application["position"], {})
        dm_sent = False
        dm_error = None
        try:
            dm_channel = None
            for channel in interaction.client.private_channels:
                if (
                    isinstance(channel, discord.DMChannel)
                    and channel.recipient.id == applicant.id
                ):
                    dm_channel = channel
                    break
            if not dm_channel:
                dm_channel = await applicant.create_dm()
            if self.action == "accept":
                message = position_settings.get(
                    "accepted_message", "Your application has been accepted!"
                )
                embed = discord.Embed(
                    title="Application Accepted!",
                    description=self.reason.value,
                    color=discord.Color.green(),
                )
                await dm_channel.send(embed=embed)
            else:
                message = position_settings.get(
                    "denied_message", "Your application has been denied."
                )
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
                        bot_member = interaction.guild.get_member(
                            interaction.client.user.id
                        )
                        if not bot_member.guild_permissions.manage_roles:
                            logger.error(
                                "Bot does not have permission to manage roles!"
                            )
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
                                    logger.error(
                                        f"Bot cannot manage role {role.name} (position too high)"
                                    )
                                    await interaction.followup.send(
                                        f"Bot cannot manage role {role.name} (position too high). Please adjust role hierarchy.",
                                        ephemeral=True,
                                    )
                                    return
                                roles_to_add.append(role)
                                logger.info(
                                    f"Found role to add: {role.name} (ID: {role.id})"
                                )
                        roles_to_remove = []
                        for role_id in position_settings.get("denied_roles", []):
                            role = interaction.guild.get_role(int(role_id))
                            if role:
                                if role.position >= bot_member.top_role.position:
                                    logger.error(
                                        f"Bot cannot manage role {role.name} (position too high)"
                                    )
                                    await interaction.followup.send(
                                        f"Bot cannot manage role {role.name} (position too high). Please adjust role hierarchy.",
                                        ephemeral=True,
                                    )
                                    return
                                roles_to_remove.append(role)
                                logger.info(
                                    f"Found role to remove: {role.name} (ID: {role.id})"
                                )
                        try:
                            if roles_to_add:
                                await guild_member.add_roles(*roles_to_add)
                                logger.info(
                                    f"Added roles: {[r.name for r in roles_to_add]}"
                                )
                            if roles_to_remove:
                                await guild_member.remove_roles(*roles_to_remove)
                                logger.info(
                                    f"Removed roles: {[r.name for r in roles_to_remove]}"
                                )
                        except discord.Forbidden as e:
                            logger.error(f"Permission error while managing roles: {e}")
                            await interaction.followup.send(
                                f"Permission error while managing roles: {e}",
                                ephemeral=True,
                            )
                            return
                        except Exception as e:
                            logger.error(f"Error while managing roles: {e}")
                            await interaction.followup.send(
                                f"Error while managing roles: {e}", ephemeral=True
                            )
                            return
                    else:
                        roles_to_add = []
                        for role_id in position_settings.get("denied_roles", []):
                            role = interaction.guild.get_role(int(role_id))
                            if role:
                                roles_to_add.append(role)
                                logger.info(
                                    f"Found role to add: {role.name} (ID: {role.id})"
                                )
                        roles_to_remove = []
                        for role_id in position_settings.get("accepted_roles", []):
                            role = interaction.guild.get_role(int(role_id))
                            if role:
                                roles_to_remove.append(role)
                                logger.info(
                                    f"Found role to remove: {role.name} (ID: {role.id})"
                                )
                        if roles_to_add:
                            await guild_member.add_roles(*roles_to_add)
                            logger.info(
                                f"Added roles: {[r.name for r in roles_to_add]}"
                            )
                        if roles_to_remove:
                            await guild_member.remove_roles(*roles_to_remove)
                            logger.info(
                                f"Removed roles: {[r.name for r in roles_to_remove]}"
                            )
                else:
                    logger.warning(
                        f"Could not find guild member for user ID: {application['user_id']}"
                    )
        except discord.Forbidden:
            dm_error = "The bot does not have permission to send DMs to this user."
            logger.error(
                f"Permission error when sending DM to user ID {application['user_id']}: {dm_error}"
            )
        except discord.HTTPException as e:
            dm_error = f"Failed to send DM: {str(e)}"
            logger.error(
                f"HTTP error when sending DM to user ID {application['user_id']}: {dm_error}"
            )
        except Exception as e:
            dm_error = f"Unexpected error while sending DM: {str(e)}"
            logger.error(
                f"Unexpected error when sending DM to user ID {application['user_id']}: {dm_error}"
            )
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
            embed.color = (
                discord.Color.green()
                if self.action == "accept"
                else discord.Color.red()
            )
            current_title = embed.title
            status_prefix = (
                "**[ACCEPTED]** - " if self.action == "accept" else "**[DENIED]** - "
            )
            if not current_title.startswith(
                "**[ACCEPTED]** - "
            ) and not current_title.startswith("**[DENIED]** - "):
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
            await interaction.followup.send(
                f"Application {self.action}ed with reason.", ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"Application {self.action}ed with reason, but could not send DM to the applicant: {dm_error}",
                ephemeral=True,
            )
class ApplicationResponseButton(Button):
    def __init__(self, action: str, application_id: str, with_reason: bool = False):
        super().__init__(
            label=f"{action.capitalize()}{' with Reason' if with_reason else ''}",
            style=discord.ButtonStyle.success
            if action == "accept"
            else discord.ButtonStyle.danger,
            custom_id=f"app_{action}_{'reason' if with_reason else 'simple'}_{application_id}",
        )
        self.action = action
        self.application_id = application_id
        self.with_reason = with_reason
    async def callback(self, interaction: discord.Interaction):
        if self.with_reason:
            modal = ReasonModal(self.action, self.application_id)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.defer(ephemeral=True)
            app_path = os.path.join(APPS_DIRECTORY, f"{self.application_id}.json")
            with open(app_path, "r") as f:
                application = json.load(f)
            if application.get("status") in ["accept", "reject"]:
                await interaction.followup.send(
                    "This application has already been processed.", ephemeral=True
                )
                return
            applicant = interaction.client.get_user(int(application["user_id"]))
            if not applicant:
                await interaction.followup.send(
                    "Could not find the applicant.", ephemeral=True
                )
                return
            questions = load_questions()
            position_settings = questions.get(application["position"], {})
            dm_sent = False
            dm_error = None
            try:
                dm_channel = None
                for channel in interaction.client.private_channels:
                    if (
                        isinstance(channel, discord.DMChannel)
                        and channel.recipient.id == applicant.id
                    ):
                        dm_channel = channel
                        break
                if not dm_channel:
                    dm_channel = await applicant.create_dm()
                if self.action == "accept":
                    message = position_settings.get(
                        "accepted_message", "Your application has been accepted!"
                    )
                    embed = discord.Embed(
                        title="Application Accepted!",
                        description=message.format(position=application["position"]),
                        color=discord.Color.green(),
                    )
                    await dm_channel.send(embed=embed)
                else:
                    message = position_settings.get(
                        "denied_message", "Your application has been denied."
                    )
                    embed = discord.Embed(
                        title="Application Denied",
                        description=message.format(position=application["position"]),
                        color=discord.Color.red(),
                    )
                    await dm_channel.send(embed=embed)
                dm_sent = True
                if dm_sent:
                    guild_member = interaction.guild.get_member(
                        int(application["user_id"])
                    )
                    if guild_member:
                        if self.action == "accept":
                            roles_to_add = []
                            for role_id in position_settings.get("accepted_roles", []):
                                role = interaction.guild.get_role(int(role_id))
                                if role:
                                    roles_to_add.append(role)
                                    logger.info(
                                        f"Found role to add: {role.name} (ID: {role.id})"
                                    )
                            roles_to_remove = []
                            for role_id in position_settings.get("denied_roles", []):
                                role = interaction.guild.get_role(int(role_id))
                                if role:
                                    roles_to_remove.append(role)
                                    logger.info(
                                        f"Found role to remove: {role.name} (ID: {role.id})"
                                    )
                            if roles_to_add:
                                await guild_member.add_roles(*roles_to_add)
                                logger.info(
                                    f"Added roles: {[r.name for r in roles_to_add]}"
                                )
                            if roles_to_remove:
                                await guild_member.remove_roles(*roles_to_remove)
                                logger.info(
                                    f"Removed roles: {[r.name for r in roles_to_remove]}"
                                )
                        else:
                            roles_to_add = []
                            for role_id in position_settings.get("denied_roles", []):
                                role = interaction.guild.get_role(int(role_id))
                                if role:
                                    roles_to_add.append(role)
                                    logger.info(
                                        f"Found role to add: {role.name} (ID: {role_id})"
                                    )
                            roles_to_remove = []
                            for role_id in position_settings.get("accepted_roles", []):
                                role = interaction.guild.get_role(int(role_id))
                                if role:
                                    roles_to_remove.append(role)
                                    logger.info(
                                        f"Found role to remove: {role.name} (ID: {role_id})"
                                    )
                            if roles_to_add:
                                await guild_member.add_roles(*roles_to_add)
                                logger.info(
                                    f"Added roles: {[r.name for r in roles_to_add]}"
                                )
                            if roles_to_remove:
                                await guild_member.remove_roles(*roles_to_remove)
                                logger.info(
                                    f"Removed roles: {[r.name for r in roles_to_remove]}"
                                )
                    else:
                        logger.error(
                            f"Could not find guild member for user ID: {application['user_id']}"
                        )
            except discord.Forbidden:
                dm_error = "The bot does not have permission to send DMs to this user."
            except discord.HTTPException as e:
                dm_error = f"Failed to send DM: {str(e)}"
            except Exception as e:
                dm_error = f"Unexpected error while sending DM: {str(e)}"
            application["status"] = (
                "approved" if self.action == "accept" else "rejected"
            )
            application["processed_by"] = {
                "id": str(interaction.user.id),
                "name": interaction.user.name,
                "with_reason": False,
            }
            with open(app_path, "w") as f:
                json.dump(application, f)
            try:
                message = await interaction.channel.fetch_message(
                    interaction.message.id
                )
                embed = message.embeds[0]
                embed.color = (
                    discord.Color.green()
                    if self.action == "accept"
                    else discord.Color.red()
                )
                current_title = embed.title
                status_prefix = (
                    "**[ACCEPTED]** - "
                    if self.action == "accept"
                    else "**[DENIED]** - "
                )
                if not current_title.startswith(
                    "**[ACCEPTED]** - "
                ) and not current_title.startswith("**[DENIED]** - "):
                    embed.title = status_prefix + current_title
                embed.add_field(
                    name="Processed by",
                    value=f"{interaction.user.mention} (Default message)",
                    inline=False,
                )
                await message.edit(embed=embed, view=None)
            except Exception as e:
                logger.error(f"Error updating embed: {e}")
            if dm_sent:
                await interaction.followup.send(
                    f"Application {self.action}ed.", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"Application {self.action}ed, but could not send DM to the applicant: {dm_error}",
                    ephemeral=True,
                )
class ApplicationResponseView(View):
    def __init__(self, application_id: str, position: str):
        super().__init__(timeout=None)
        self.application_id = application_id
        self.position = position
        self.add_item(ApplicationResponseButton("accept", application_id))
        self.add_item(ApplicationResponseButton("reject", application_id))
        self.add_item(
            ApplicationResponseButton("accept", application_id, with_reason=True)
        )
        self.add_item(
            ApplicationResponseButton("reject", application_id, with_reason=True)
        )
        self.bot = None
    def set_bot(self, bot):
        self.bot = bot
        bot.add_view(self)
        return self
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        questions = load_questions()
        position_settings = questions.get(self.position, {})
        user_roles = [str(role.id) for role in interaction.user.roles]
        if interaction.user.guild_permissions.administrator:
            return True
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
            button_type = "unknown"
            required_roles = position_settings.get("button_roles", [])
        has_required_role = any(role_id in user_roles for role_id in required_roles)
        has_button_role = any(
            role_id in user_roles
            for role_id in position_settings.get("button_roles", [])
        )
        if has_required_role or has_button_role:
            return True
        await interaction.response.send_message(
            f"You don't have permission to use the {button_type.replace('_', ' ').title()} button. Only administrators and users with the specified roles can use this button.",
            ephemeral=True,
        )
        return False
    async def on_error(
        self, error: Exception, item: Item, interaction: discord.Interaction
    ) -> None:
        logger.error(f"Error processing interaction: {error}")
        await interaction.response.send_message(
            "An error occurred while processing your request. Please try again later.",
            ephemeral=True,
        )
class ApplicationStartButton(Button):
    def __init__(self, action: str, user_id: str, position: str):
        custom_id = f"app_welcome_{action}_{user_id}_{position}"
        style = (
            discord.ButtonStyle.success
            if action == "start"
            else discord.ButtonStyle.danger
        )
        super().__init__(
            label="Start Application" if action == "start" else "Cancel Application",
            style=style,
            custom_id=custom_id,
        )
        self.action = action
        self.user_id = user_id
        self.position = position
    async def callback(self, interaction: discord.Interaction):
        app_data = self.view.application_data
        if self.action == "start":
            await interaction.response.defer()
            questions = load_questions()
            position = app_data.get("position", "")
            position_settings = questions.get(position, {})
            time_limit = position_settings.get(
                "time_limit", 60
            )
            if (
                hasattr(self.view.bot, "active_applications")
                and str(interaction.user.id) in self.view.bot.active_applications
            ):
                self.view.bot.active_applications[str(interaction.user.id)][
                    "start_time"
                ] = datetime.datetime.now(UTC).isoformat()
                self.view.bot.active_applications[str(interaction.user.id)][
                    "message_id"
                ] = str(interaction.message.id)
                save_active_applications(self.view.bot.active_applications)
            dm_channel = interaction.channel
            total_questions = len(app_data["questions"])
            await dm_channel.send(
                f"⏰ **Note:** You have {time_limit} minutes to complete all questions in this application."
            )
            await dm_channel.send(
                f"**Question 1 of {total_questions}:** {app_data['questions'][0]}"
            )
            original_embed = interaction.message.embeds[0]
            original_embed.color = discord.Color.green()
            original_embed.set_footer(text="Application has been started.")
            await interaction.message.edit(embed=original_embed, view=None)
        else:
            if (
                hasattr(self.view.bot, "active_applications")
                and str(interaction.user.id) in self.view.bot.active_applications
            ):
                del self.view.bot.active_applications[str(interaction.user.id)]
                save_active_applications(self.view.bot.active_applications)
            await interaction.response.defer()
            original_embed = interaction.message.embeds[0]
            original_embed.color = discord.Color.red()
            original_embed.set_footer(text="Application has been cancelled.")
            await interaction.message.edit(embed=original_embed, view=None)
        self.view.stop()
class ApplicationStartView(View):
    def __init__(self, bot, application_data):
        super().__init__(timeout=None)
        self.bot = bot
        self.application_data = application_data
        self.custom_id = f"app_welcome_view_{application_data['user_id']}_{application_data['position']}"
        self.add_item(
            ApplicationStartButton(
                "start", application_data["user_id"], application_data["position"]
            )
        )
        self.add_item(
            ApplicationStartButton(
                "cancel", application_data["user_id"], application_data["position"]
            )
        )
        bot.add_view(self)
    async def on_timeout(self):
        user_id = int(self.application_data["user_id"])
        user = self.bot.get_user(user_id)
        try:
            if user:
                dm_channel = await user.create_dm()
                await dm_channel.send(
                    "Your application has expired. Please start a new one."
                )
                if (
                    hasattr(self.bot, "active_applications")
                    and str(user_id) in self.bot.active_applications
                ):
                    del self.bot.active_applications[str(user_id)]
                    save_active_applications(self.bot.active_applications)
        except Exception as e:
            logger.error(f"Error sending expiration message: {e}")
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        user_id = str(interaction.user.id)
        app_user_id = self.application_data.get("user_id", "")
        if user_id != app_user_id:
            logger.warning(
                f"User {user_id} tried to interact with an application belonging to {app_user_id}"
            )
            await interaction.response.send_message(
                "This application doesn't belong to you.", ephemeral=True
            )
            return False
        return True
    @classmethod
    async def restore_view(cls, bot, application_data):
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
