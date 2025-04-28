import discord
from discord.ui import Select, View, Button, Modal, TextInput, Item
import datetime
from datetime import UTC
import os
from question_manager import get_questions, load_questions
import json
from dotenv import load_dotenv
import uuid
import traceback
import pathlib
import logging
from panels_manager import load_panels

# Get logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Ensure storage directory exists
pathlib.Path('storage').mkdir(exist_ok=True)

# Configure applications directory
APPS_DIRECTORY = 'storage/applications'
pathlib.Path(APPS_DIRECTORY).mkdir(exist_ok=True)
ACTIVE_APPS_FILE = os.path.join('storage', 'active_applications.json')

# Function to load active applications from file
def load_active_applications():
    if not os.path.exists(ACTIVE_APPS_FILE):
        return {}
    
    try:
        with open(ACTIVE_APPS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading active applications: {str(e)}")
        return {}

# Function to save active applications to file
def save_active_applications(applications):
    try:
        # Ensure the directory exists
        if not os.path.exists(APPS_DIRECTORY):
            os.makedirs(APPS_DIRECTORY)
        with open(ACTIVE_APPS_FILE, 'w') as f:
            json.dump(applications, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving active applications: {str(e)}")
        return False

# Remove the @bot.event decorator and create a function instead
async def handle_dm_message(bot, message):
    # Only process DMs
    if not isinstance(message.channel, discord.DMChannel):
        return
    
    # Ignore bot messages
    if message.author.bot:
        return

    # Initialize active_applications if needed
    if not hasattr(bot, 'active_applications'):
        bot.active_applications = load_active_applications()

    application = bot.active_applications.get(str(message.author.id))
    if not application:
        return
        
    if 'start_time' not in application:
        return
        
    # Check if the application has a start_time and if the time limit has passed
    if 'start_time' in application:
        start_time = datetime.datetime.fromisoformat(application['start_time'])
        current_time = datetime.datetime.now(UTC)
        time_elapsed = (current_time - start_time).total_seconds() / 60  # Convert to minutes
        
        # Get position settings to get the time limit
        questions = load_questions()
        position_settings = questions.get(application['position'], {})
        time_limit = position_settings.get('time_limit', 60)  # Default to 60 minutes if not set
        
        # If more than the time limit has passed, cancel the application
        if time_elapsed > time_limit:
            # Send expiration message
            await message.channel.send(f"⌛ Your application has expired. You had {time_limit} minutes to complete it. Please start a new application if you wish to apply.")
            
            # Remove from active applications
            del bot.active_applications[str(message.author.id)]
            save_active_applications(bot.active_applications)
            return
    
    # Get current question index
    current_question = application['current_question']
    questions = application['questions']
    
    # Store the answer
    application['answers'].append(message.content)
    
    # Check if there are more questions
    if current_question + 1 < len(questions):
        # Send next question
        application['current_question'] += 1
        await message.channel.send(f"**Question {current_question + 2} of {len(questions)}:** {questions[current_question + 1]}")
        
        # Save updated state to file
        save_active_applications(bot.active_applications)
    else:
        # All questions answered, create application
        application_id = str(uuid.uuid4())
        application_data = {
            'id': application_id,
            'user_id': application['user_id'],
            'user_name': application['user_name'],
            'position': application['position'],
            'questions': application['questions'],
            'answers': application['answers'],
            'status': 'pending'
        }
        
        # Save application
        app_path = os.path.join(APPS_DIRECTORY, f'{application_id}.json')
        with open(app_path, 'w') as f:
            json.dump(application_data, f)
        
        # Remove from active applications
        del bot.active_applications[str(message.author.id)]
        
        # Save updated active applications
        save_active_applications(bot.active_applications)
        
        # Get position settings for completion message
        questions = load_questions()
        position_settings = questions.get(application['position'], {})
        completion_message = position_settings.get('completion_message', f"Thank you for completing your application for {application['position']}! Your responses have been submitted and will be reviewed soon.")
        
        # Send completion message
        await message.channel.send(completion_message.format(position=application['position']))
        
        # Log the application
        questions = load_questions()
        position_settings = questions.get(application['position'], {})
        log_channel_id = position_settings.get('log_channel')
        if log_channel_id:
            try:
                log_channel = bot.get_channel(int(log_channel_id))
                if log_channel:
                    # Add link to application in web dashboard
                    web_host = os.getenv('WEB_HOST', 'localhost')
                    web_port = os.getenv('WEB_PORT', '8080')
                    application_url = f"http://{web_host}:{web_port}/application/{application_id}"
                    
                    # Create embed for the application
                    embed = discord.Embed(
                        title=f"{message.author.name}'s {application['position']} application",
                        description=f"Applicant: {message.author.mention} ({message.author.id})",
                        color=0x808080
                    )
                    
                    # Add application URL and joined timestamp to the description
                    embed.description += f"\n\n[Click here to view the application]({application_url})"
                    
                    # Get guild member to access joined_at timestamp
                    guild = log_channel.guild
                    member = guild.get_member(message.author.id)
                    if member and member.joined_at:
                        embed.description += f"\n\nJoined server: <t:{int(member.joined_at.timestamp())}:R>"
                    
                    # Set the user's avatar as thumbnail
                    embed.set_thumbnail(url=message.author.display_avatar.url)
                    
                    # Set footer with App ID
                    embed.set_footer(text=f"{application_id}")
                    
                    # Add view with buttons
                    view = ApplicationResponseView(application_id, application['position'])
                    view.bot = bot
                    
                    # Send the embed
                    log_message = await log_channel.send(embed=embed, view=view)
                    
                    # Create thread if auto_thread is enabled
                    if position_settings.get('auto_thread', False):
                        try:
                            thread_name = f"{message.author.name}'s {application['position']} Application"
                            await log_message.create_thread(name=thread_name, auto_archive_duration=1440)
                        except Exception as e:
                            logger.error(f"Error creating thread: {e}")
                    
                    # Ping roles if specified
                    ping_roles = position_settings.get('ping_roles', [])
                    if ping_roles:
                        ping_mentions = ' '.join([f"<@&{role_id}>" for role_id in ping_roles])
                        await log_channel.send(ping_mentions)
            except Exception as e:
                logger.error(f"Error logging application: {e}")

class StaffApplicationSelect(Select):
    def __init__(self, bot, options, panel_id=None):
        self.bot = bot
        # Ensure panel_id is always a string
        self.panel_id = str(panel_id) if panel_id is not None else "default"
        # Set the custom_id to include the panel_id and make it consistent
        custom_id = f"staff_application_select_{self.panel_id}"
        super().__init__(
            placeholder="Select a position to apply for...",
            options=options,
            custom_id=custom_id,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            # Get the selected position
            position = self.values[0]
            
            # Check if position is disabled
            questions_data = load_questions()
            position_settings = questions_data.get(position, {})
            if not position_settings.get('enabled', True):
                await interaction.response.send_message(
                    f"This position is currently not taking applicants. Please try again later.",
                    ephemeral=True
                )
                # Refresh the select menu for other users
                await self.refresh_select_menu(interaction)
                return
            
            # Check if user already has an active application
            if hasattr(self.view.bot, 'active_applications'):
                active_app = self.view.bot.active_applications.get(str(interaction.user.id))
                if active_app:
                    # If the position and panel match, resume the application process
                    if active_app['position'] == position and active_app['panel_id'] == self.panel_id:
                        # Check if application has been started
                        if 'start_time' not in active_app:
                            await interaction.response.send_message(
                                f"You have an active application but haven't started it yet. Please check your DMs to start or cancel the application.",
                                ephemeral=True
                            )
                            # Refresh the select menu for other users
                            await self.refresh_select_menu(interaction)
                            return
                            
                        # Calculate which question to send next
                        current_question = active_app['current_question']
                        questions = active_app['questions']
                        
                        # Always use DM for questions, not ephemeral responses
                        try:
                            # Defer the interaction response first
                            await interaction.response.defer(ephemeral=True)
                            
                            # Create DM channel
                            dm = await interaction.user.create_dm()
                            
                            # If there are still questions to answer
                            if current_question < len(questions):
                                # Send the current question via DM
                                await dm.send(f"**Continuing your application...**\n**Question {current_question + 1} of {len(questions)}:** {questions[current_question]}")
                                
                                # Send followup message
                                await interaction.followup.send(f"I've sent you a DM to continue your application!", ephemeral=True)
                            else:
                                # All questions answered, send a message to continue in DMs
                                await interaction.followup.send(f"You have already answered all questions. Please continue in your DMs with the bot.", ephemeral=True)
                            
                            # Refresh the select menu for other users
                            await self.refresh_select_menu(interaction)
                            return
                        except Exception as e:
                            logger.error(f"Error sending DM: {e}")
                            await interaction.followup.send("Failed to send you a DM to start the application! Please check your Privacy settings for this server and make sure Direct Messages are enabled and try again.", ephemeral=True)
                            # Refresh the select menu for other users
                            await self.refresh_select_menu(interaction)
                            return
                    elif active_app['position'] == position:
                        await interaction.response.send_message(
                            f"You have an active application but haven't started it yet. Please check your DMs to start or cancel the application.",
                            ephemeral=True
                        )
                        # Refresh the select menu for other users
                        await self.refresh_select_menu(interaction)
                        return
                    else:
                        # Check if application has been started
                        if 'start_time' not in active_app:
                            await interaction.response.send_message(
                                f"You have an active application for a different position but haven't started it yet. Please check your DMs to start or cancel the application.",
                                ephemeral=True
                            )
                        else:
                            await interaction.response.send_message(
                                f"You already have an active application for a different position. Please complete it or wait for it to be reviewed.",
                                ephemeral=True
                            )
                        # Refresh the select menu for other users
                        await self.refresh_select_menu(interaction)
                        return
            
            # Get questions for the position
            questions = get_questions(position)
            
            if not questions or len(questions) == 0:
                logger.error(f"No questions loaded for position {position}")
                await interaction.response.send_message(
                    "This position has no questions set up. Please contact an administrator.",
                    ephemeral=True
                )
                # Refresh the select menu for other users
                await self.refresh_select_menu(interaction)
                return

            # Check if log channel is set
            questions_data = load_questions()
            position_settings = questions_data.get(position, {})
            log_channel_id = position_settings.get('log_channel')
            if not log_channel_id:
                logger.error(f"No log channel set for position {position}")
                await interaction.response.send_message(
                    "This position has no log channel set up. Please contact an administrator.",
                    ephemeral=True
                )
                # Refresh the select menu for other users
                await self.refresh_select_menu(interaction)
                return
            
            # Create application data
            application_data = {
                'user_id': str(interaction.user.id),
                'user_name': interaction.user.name,
                'position': position,
                'questions': questions,
                'answers': [],
                'current_question': 0,  # Track current question index
                'panel_id': self.panel_id  # Store the panel ID in the application
            }
            
            # Store the active application
            if not hasattr(self.view.bot, 'active_applications'):
                self.view.bot.active_applications = load_active_applications()
                
            self.view.bot.active_applications[str(interaction.user.id)] = application_data
            
            # Save active applications to file
            save_active_applications(self.view.bot.active_applications)
            
            # Defer the interaction response first
            await interaction.response.defer(ephemeral=True)
            
            # Send DM to user
            dm_success = False
            try:
                # Create DM channel
                dm = await interaction.user.create_dm()
                
                # Get position settings to access welcome message
                questions_data = load_questions()
                position_settings = questions_data.get(position, {})
                welcome_message = position_settings.get('welcome_message', f"Thank you for applying for the {position} position!")
                
                # Send welcome message with Start and Cancel buttons
                welcome_view = ApplicationStartView(self.view.bot, application_data)
                welcome_message = await dm.send(welcome_message.format(position=position), view=welcome_view)
                
                if str(interaction.user.id) in self.view.bot.active_applications:
                    self.view.bot.active_applications[str(interaction.user.id)]['message_id'] = str(welcome_message.id)
                    save_active_applications(self.view.bot.active_applications)
                
                # Make sure questions are loaded properly
                if not application_data['questions'] or len(application_data['questions']) == 0:
                    logger.error(f"No questions found for position {position}")
                    await dm.send("ERROR: No questions were found for this position. Please contact an administrator.")
                    await interaction.followup.send("Error: No questions found for this position. Please contact an administrator.", ephemeral=True)
                    
                    # Remove the application since it can't proceed
                    del self.view.bot.active_applications[str(interaction.user.id)]
                    save_active_applications(self.view.bot.active_applications)
                    
                    # Refresh the select menu for other users
                    await self.refresh_select_menu(interaction)
                    return

                # Set success flag
                dm_success = True
                
                # Send followup message
                await interaction.followup.send(f"I've sent you a DM with the application questions! Please check your DMs to start or cancel the application.", ephemeral=True)
                
                # Refresh the select menu for other users
                await self.refresh_select_menu(interaction)
            except Exception as e:
                logger.error(f"Error sending DM questions: {e}")
                logger.error(f"Application data: {application_data}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Try to send at least a notification about the error to the user's DM if we got that far
                try:
                    if 'dm' in locals():
                        await dm.send("An error occurred while sending your questions. Please contact an administrator.")
                except:
                    pass
                    
                # Only show error message if success message wasn't shown
                if not dm_success:
                    await interaction.followup.send(f"Failed to send you a DM to start the application! Please check your Privacy settings for this server and make sure Direct Messages are enabled and try again.", ephemeral=True)
                
                # Remove the application since it encountered an error
                if str(interaction.user.id) in self.view.bot.active_applications:
                    del self.view.bot.active_applications[str(interaction.user.id)]
                    save_active_applications(self.view.bot.active_applications)
                
                # Refresh the select menu for other users
                await self.refresh_select_menu(interaction)
                return
        except Exception as e:
            logger.error(f"Error in StaffApplicationSelect callback: {e}")
            logger.error(f"Error traceback: {traceback.format_exc()}")
            try:
                await interaction.response.send_message(
                    "An error occurred while processing your selection. Please try again later.",
                    ephemeral=True
                )
                # Try to refresh the select menu even on error
                await self.refresh_select_menu(interaction)
            except:
                try:
                    await interaction.followup.send(
                        "An error occurred while processing your selection. Please try again later.",
                        ephemeral=True
                    )
                    # Try to refresh the select menu even on error
                    await self.refresh_select_menu(interaction)
                except:
                    pass
                    
    async def refresh_select_menu(self, interaction: discord.Interaction):
        try:
            # Create a new view with the same options
            panels = load_panels()
            panel_data = panels.get(self.panel_id)
            
            if panel_data:
                new_view = StaffApplicationView(self.view.bot, panel_id=self.panel_id)
                # Update the original message with the new view
                await interaction.message.edit(view=new_view)
        except Exception as e:
            logger.error(f"Error refreshing select menu: {e}")
            logger.error(f"Error traceback: {traceback.format_exc()}")

class StaffApplicationView(View):
    def __init__(self, bot, options=None, panel_id=None):
        super().__init__(timeout=None)  # Set timeout to None for persistent views
        self.bot = bot
        
        # Ensure panel_id is always a string
        self.panel_id = str(panel_id) if panel_id is not None else "default"
        
        # Create the select menu
        if options:
            select = StaffApplicationSelect(bot, options, self.panel_id)
            self.add_item(select)
        else:
            # If no options provided, try to get them from the panel data
            panels = load_panels()
            panel_data = panels.get(self.panel_id)
            if panel_data:
                select_options = [
                    discord.SelectOption(
                        label=position if isinstance(position, str) else position['name'],
                        description=f"Apply for {position if isinstance(position, str) else position['name']} position",
                        value=position if isinstance(position, str) else position['name']
                    ) for position in panel_data['positions']
                ]
                select = StaffApplicationSelect(bot, select_options, self.panel_id)
                self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        try:
            return True
        except Exception as e:
            logger.error(f"Error in interaction check: {e}")
            return False

    async def on_error(self, error: Exception, item: Item, interaction: discord.Interaction) -> None:
        logger.error(f"Error processing interaction: {error}")
        await interaction.response.send_message("An error occurred while processing your request. Please try again later.", ephemeral=True)

class ReasonModal(Modal):
    def __init__(self, action: str, application_id: str):
        super().__init__(title=f"{action.capitalize()} Application")
        self.action = action
        self.application_id = application_id
        self.reason = TextInput(
            label="Reason",
            placeholder="Enter your reason here...",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        # Defer the interaction response
        await interaction.response.defer(ephemeral=True)
        
        # Get the application data
        app_path = os.path.join(APPS_DIRECTORY, f'{self.application_id}.json')
        with open(app_path, 'r') as f:
            application = json.load(f)
        
        # Check if application is already processed
        if application.get('status') in ['accept', 'reject']:
            await interaction.followup.send("This application has already been processed.", ephemeral=True)
            return
        
        # Get the applicant - use bot.get_user instead of guild.get_member
        applicant = interaction.client.get_user(int(application['user_id']))
        if not applicant:
            await interaction.followup.send("Could not find the applicant.", ephemeral=True)
            return
        
        # Get position settings
        questions = load_questions()
        position_settings = questions.get(application['position'], {})
        
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
            if self.action == 'accept':
                await dm_channel.send(f"## ACCEPTED!\n\n{self.reason.value}")
            else:
                await dm_channel.send(f"## DENIED!\n\n{self.reason.value}")
            dm_sent = True
            
            # Only proceed with role changes if DM was sent successfully
            if dm_sent:
                # Get the guild member for role management
                guild_member = interaction.guild.get_member(int(application['user_id']))
                if guild_member:
                    if self.action == 'accept':
                        
                        # Check bot's permissions
                        bot_member = interaction.guild.get_member(interaction.client.user.id)
                        if not bot_member.guild_permissions.manage_roles:
                            logger.error("Bot does not have permission to manage roles!")
                            await interaction.followup.send("Bot does not have permission to manage roles. Please check bot permissions.", ephemeral=True)
                            return
                        
                        # Assign accepted roles
                        roles_to_add = []
                        for role_id in position_settings.get('accepted_roles', []):
                            role = interaction.guild.get_role(int(role_id))
                            if role:
                                # Check if bot can manage this role
                                if role.position >= bot_member.top_role.position:
                                    logger.error(f"Bot cannot manage role {role.name} (position too high)")
                                    await interaction.followup.send(f"Bot cannot manage role {role.name} (position too high). Please adjust role hierarchy.", ephemeral=True)
                                    return
                                roles_to_add.append(role)
                                logger.info(f"Found role to add: {role.name} (ID: {role.id})")
                        
                        # Remove denied roles
                        roles_to_remove = []
                        for role_id in position_settings.get('denied_roles', []):
                            role = interaction.guild.get_role(int(role_id))
                            if role:
                                # Check if bot can manage this role
                                if role.position >= bot_member.top_role.position:
                                    logger.error(f"Bot cannot manage role {role.name} (position too high)")
                                    await interaction.followup.send(f"Bot cannot manage role {role.name} (position too high). Please adjust role hierarchy.", ephemeral=True)
                                    return
                                roles_to_remove.append(role)
                                logger.info(f"Found role to remove: {role.name} (ID: {role.id})")
                        
                        # Apply role changes
                        try:
                            if roles_to_add:
                                await guild_member.add_roles(*roles_to_add)
                                logger.info(f"Added roles: {[r.name for r in roles_to_add]}")
                            if roles_to_remove:
                                await guild_member.remove_roles(*roles_to_remove)
                                logger.info(f"Removed roles: {[r.name for r in roles_to_remove]}")
                        except discord.Forbidden as e:
                            logger.error(f"Permission error while managing roles: {e}")
                            await interaction.followup.send(f"Permission error while managing roles: {e}", ephemeral=True)
                            return
                        except Exception as e:
                            logger.error(f"Error while managing roles: {e}")
                            await interaction.followup.send(f"Error while managing roles: {e}", ephemeral=True)
                            return
                    else:
                        
                        # Assign denied roles
                        roles_to_add = []
                        for role_id in position_settings.get('denied_roles', []):
                            role = interaction.guild.get_role(int(role_id))
                            if role:
                                roles_to_add.append(role)
                                logger.info(f"Found role to add: {role.name} (ID: {role.id})")
                        
                        # Remove accepted roles
                        roles_to_remove = []
                        for role_id in position_settings.get('accepted_roles', []):
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
        
        # Update application status and add processed by info
        application['status'] = 'approved' if self.action == 'accept' else 'rejected'
        application['processed_by'] = {
            'id': str(interaction.user.id),
            'name': interaction.user.name,
            'with_reason': True,
            'reason': self.reason.value
        }
        with open(app_path, 'w') as f:
            json.dump(application, f)
        
        # Update the embed
        try:
            # Get the original message
            message = await interaction.channel.fetch_message(interaction.message.id)
            
            # Create a new embed with updated color and information
            embed = message.embeds[0]
            embed.color = discord.Color.green() if self.action == 'accept' else discord.Color.red()
            
            # Update title to indicate status for colorblind users
            current_title = embed.title
            status_prefix = "**[ACCEPTED]** - " if self.action == 'accept' else "**[DENIED]** - "
            if not current_title.startswith("**[ACCEPTED]** - ") and not current_title.startswith("**[DENIED]** - "):
                embed.title = status_prefix + current_title
            
            # Add processed by information
            embed.add_field(
                name="Processed by",
                value=f"{interaction.user.mention} (With reason)",
                inline=False
            )
            embed.add_field(
                name="Reason",
                value=self.reason.value,
                inline=False
            )
            
            # Update the message with new embed and remove buttons
            await message.edit(embed=embed, view=None)
        except Exception as e:
            logger.error(f"Error updating embed: {e}")
        
        # Send followup message
        if dm_sent:
            await interaction.followup.send(f"Application {self.action}ed with reason.", ephemeral=True)
        else:
            await interaction.followup.send(f"Application {self.action}ed with reason, but could not send DM to the applicant: {dm_error}", ephemeral=True)

class ApplicationResponseButton(Button):
    def __init__(self, action: str, application_id: str, with_reason: bool = False):
        super().__init__(
            label=f"{action.capitalize()}{' with Reason' if with_reason else ''}",
            style=discord.ButtonStyle.success if action == 'accept' else discord.ButtonStyle.danger,
            custom_id=f"app_{action}_{'reason' if with_reason else 'simple'}_{application_id}"
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
            app_path = os.path.join(APPS_DIRECTORY, f'{self.application_id}.json')
            with open(app_path, 'r') as f:
                application = json.load(f)
            
            # Check if application is already processed
            if application.get('status') in ['accept', 'reject']:
                await interaction.followup.send("This application has already been processed.", ephemeral=True)
                return
            
            # Get the applicant - use bot.get_user instead of guild.get_member
            applicant = interaction.client.get_user(int(application['user_id']))
            if not applicant:
                await interaction.followup.send("Could not find the applicant.", ephemeral=True)
                return
            
            # Get position settings
            questions = load_questions()
            position_settings = questions.get(application['position'], {})
            
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
                if self.action == 'accept':
                    message = position_settings.get('accepted_message', 'Your application has been accepted!')
                    await dm_channel.send(f"## ACCEPTED!\n\n{message.format(position=application['position'])}")
                else:
                    message = position_settings.get('denied_message', 'Your application has been denied.')
                    await dm_channel.send(f"## DENIED!\n\n{message.format(position=application['position'])}")
                dm_sent = True
                
                # Only proceed with role changes if DM was sent successfully
                if dm_sent:
                    # Get the guild member for role management
                    guild_member = interaction.guild.get_member(int(application['user_id']))
                    if guild_member:
                        if self.action == 'accept':
                            
                            # Assign accepted roles
                            roles_to_add = []
                            for role_id in position_settings.get('accepted_roles', []):
                                role = interaction.guild.get_role(int(role_id))
                                if role:
                                    roles_to_add.append(role)
                                    logger.info(f"Found role to add: {role.name} (ID: {role.id})")
                            
                            # Remove denied roles
                            roles_to_remove = []
                            for role_id in position_settings.get('denied_roles', []):
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
                            for role_id in position_settings.get('denied_roles', []):
                                role = interaction.guild.get_role(int(role_id))
                                if role:
                                    roles_to_add.append(role)
                                    logger.info(f"Found role to add: {role.name} (ID: {role_id})")
                            
                            # Remove accepted roles
                            roles_to_remove = []
                            for role_id in position_settings.get('accepted_roles', []):
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
            application['status'] = 'approved' if self.action == 'accept' else 'rejected'
            application['processed_by'] = {
                'id': str(interaction.user.id),
                'name': interaction.user.name,
                'with_reason': False
            }
            with open(app_path, 'w') as f:
                json.dump(application, f)
            
            # Update the embed
            try:
                # Get the original message
                message = await interaction.channel.fetch_message(interaction.message.id)
                
                # Create a new embed with updated color and information
                embed = message.embeds[0]
                embed.color = discord.Color.green() if self.action == 'accept' else discord.Color.red()
                
                # Update title to indicate status for colorblind users
                current_title = embed.title
                status_prefix = "**[ACCEPTED]** - " if self.action == 'accept' else "**[DENIED]** - "
                if not current_title.startswith("**[ACCEPTED]** - ") and not current_title.startswith("**[DENIED]** - "):
                    embed.title = status_prefix + current_title
                
                # Add processed by information
                embed.add_field(
                    name="Processed by",
                    value=f"{interaction.user.mention} (Default message)",
                    inline=False
                )
                
                # Update the message with new embed and remove buttons
                await message.edit(embed=embed, view=None)
            except Exception as e:
                logger.error(f"Error updating embed: {e}")
            
            # Send followup message
            if dm_sent:
                await interaction.followup.send(f"Application {self.action}ed.", ephemeral=True)
            else:
                await interaction.followup.send(f"Application {self.action}ed, but could not send DM to the applicant: {dm_error}", ephemeral=True)

class ApplicationResponseView(View):
    def __init__(self, application_id: str, position: str):
        super().__init__(timeout=None)  # Make the view persistent
        self.application_id = application_id
        self.position = position
        
        # Add all buttons
        self.add_item(ApplicationResponseButton('accept', application_id))
        self.add_item(ApplicationResponseButton('reject', application_id))
        self.add_item(ApplicationResponseButton('accept', application_id, with_reason=True))
        self.add_item(ApplicationResponseButton('reject', application_id, with_reason=True))
        
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
        custom_id = interaction.data.get('custom_id', '')
        button_type = ''
        
        if custom_id.startswith('app_accept_simple'):
            button_type = 'accept'
            required_roles = position_settings.get('accept_roles', [])
        elif custom_id.startswith('app_reject_simple'):
            button_type = 'reject'
            required_roles = position_settings.get('reject_roles', [])
        elif custom_id.startswith('app_accept_reason'):
            button_type = 'accept_reason'
            required_roles = position_settings.get('accept_reason_roles', [])
        elif custom_id.startswith('app_reject_reason'):
            button_type = 'reject_reason'
            required_roles = position_settings.get('reject_reason_roles', [])
        else:
            # If we can't determine button type, fall back to the general button_roles
            button_type = 'unknown'
            required_roles = position_settings.get('button_roles', [])
        
        # Check if user has any of the required roles for this button type
        has_required_role = any(role_id in user_roles for role_id in required_roles)
        
        # Check the general button_roles
        has_button_role = any(role_id in user_roles for role_id in position_settings.get('button_roles', []))
        
        # Allow interaction if user has either specific role for this button or a general button role
        if has_required_role or has_button_role:
            return True
            
        # Send ephemeral error message if user doesn't have permissions
        await interaction.response.send_message(
            f"You don't have permission to use the {button_type.replace('_', ' ').title()} button. Only administrators and users with the specified roles can use this button.",
            ephemeral=True
        )
        return False

    async def on_error(self, error: Exception, item: Item, interaction: discord.Interaction) -> None:
        logger.error(f"Error processing interaction: {error}")
        await interaction.response.send_message("An error occurred while processing your request. Please try again later.", ephemeral=True)

class ApplicationStartButton(Button):
    def __init__(self, action: str, user_id: str, position: str):
        custom_id = f"app_welcome_{action}_{user_id}_{position}"
        
        style = discord.ButtonStyle.success if action == 'start' else discord.ButtonStyle.danger
        super().__init__(
            label="Start Application" if action == 'start' else "Cancel Application",
            style=style,
            custom_id=custom_id
        )
        self.action = action
        self.user_id = user_id
        self.position = position

    async def callback(self, interaction: discord.Interaction):
        # Get the application data from the view
        app_data = self.view.application_data
        
        # Handle button press
        if self.action == 'start':
            # Acknowledge the interaction
            await interaction.response.defer()
            
            # Get position settings for time limit
            questions = load_questions()
            position = app_data.get('position', '')
            position_settings = questions.get(position, {})
            time_limit = position_settings.get('time_limit', 60)  # Default to 60 minutes if not set
            
            # Add a start_time to the application data to track the time limit
            if hasattr(self.view.bot, 'active_applications') and str(interaction.user.id) in self.view.bot.active_applications:
                self.view.bot.active_applications[str(interaction.user.id)]['start_time'] = datetime.datetime.now(UTC).isoformat()
                self.view.bot.active_applications[str(interaction.user.id)]['message_id'] = str(interaction.message.id)
                save_active_applications(self.view.bot.active_applications)
            
            # Send the first question to the DM channel
            dm_channel = interaction.channel
            total_questions = len(app_data['questions'])
            await dm_channel.send(f"⏰ **Note:** You have {time_limit} minutes to complete all questions in this application.")
            await dm_channel.send(f"**Question 1 of {total_questions}:** {app_data['questions'][0]}")
            
            # Remove the buttons in the original message
            await interaction.message.edit(view=None)
        else:
            # Cancel the application
            # Remove the application from active applications
            if hasattr(self.view.bot, 'active_applications') and str(interaction.user.id) in self.view.bot.active_applications:
                del self.view.bot.active_applications[str(interaction.user.id)]
                save_active_applications(self.view.bot.active_applications)
            
            # Acknowledge the interaction and inform the user
            await interaction.response.defer()
            await interaction.channel.send("Application cancelled. You can apply again at any time.")
            
            # Remove the buttons in the original message
            await interaction.message.edit(view=None)
        
        # Stop listening for button presses
        self.view.stop()

class ApplicationStartView(View):
    def __init__(self, bot, application_data):
        super().__init__(timeout=None)
        self.bot = bot
        self.application_data = application_data
        
        # Add a custom_id to the view for persistence
        self.custom_id = f"app_welcome_view_{application_data['user_id']}_{application_data['position']}"
        
        # Add start and cancel buttons with custom_ids
        self.add_item(ApplicationStartButton('start', application_data['user_id'], application_data['position']))
        self.add_item(ApplicationStartButton('cancel', application_data['user_id'], application_data['position']))
        
        bot.add_view(self)
    
    async def on_timeout(self):
        # Get the DM channel to send expiration message
        user_id = int(self.application_data['user_id'])
        user = self.bot.get_user(user_id)
        
        try:
            if user:
                # Create DM channel if needed
                dm_channel = await user.create_dm()
                await dm_channel.send("Your application has expired. Please start a new one.")
                
                # Remove from active applications
                if hasattr(self.bot, 'active_applications') and str(user_id) in self.bot.active_applications:
                    del self.bot.active_applications[str(user_id)]
                    save_active_applications(self.bot.active_applications)
        except Exception as e:
            logger.error(f"Error sending expiration message: {e}")
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Verify that the interaction is coming from the user who owns this application
        user_id = str(interaction.user.id)
        app_user_id = self.application_data.get('user_id', '')
        
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

        if 'message_id' in application_data:
            try:
                message_id = int(application_data['message_id'])
                bot.add_view(view, message_id=message_id)
                logger.info(f"Registered view with specific message ID: {message_id}")
            except Exception as e:
                logger.error(f"Error registering view with message ID: {e}")
        
        return view 