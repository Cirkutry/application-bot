import os
import discord
from discord import app_commands
from dotenv import load_dotenv
import asyncio
import json
import pathlib
import datetime
import logging
from question_manager import load_questions
from application_components import StaffApplicationView, ApplicationResponseView
import traceback

# Get logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TOKEN')
APPS_DIRECTORY = 'storage/applications'

# Create applications directory if it doesn't exist
pathlib.Path(APPS_DIRECTORY).mkdir(exist_ok=True)

class ApplicationBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)
        self.active_applications = {}
        self.views = {}  # Add views dictionary to store persistent views

    async def setup_hook(self):
        # Add the application panel handler
        self.add_listener(handle_dm_message, 'on_message')
        
        # Register saved panels
        from panels_manager import register_panels
        try:
            await register_panels(self)
            logger.info("Successfully registered saved panels")
        except Exception as e:
            logger.error(f"Error registering panels: {e}")
            logger.error(f"Error traceback: {traceback.format_exc()}")
            
        # Sync commands
        try:
            await self.tree.sync()
            logger.info("Successfully synced application commands")
        except Exception as e:
            logger.error(f"Error syncing commands: {e}")
            logger.error(f"Error traceback: {traceback.format_exc()}")

    async def on_ready(self):
        logger.info(f'Logged in as {self.user.name} ({self.user.id})')
        
        # Sync commands
        await self.tree.sync()

    async def on_message(self, message):
        # Ignore messages from the bot itself
        if message.author == self.user:
            return

        # Check if this is a DM and if the user has an active application
        if isinstance(message.channel, discord.DMChannel) and str(message.author.id) in self.active_applications:
            app_data = self.active_applications[str(message.author.id)]
            logger.info(f"Found active application for {message.author.name}: {app_data}")
            
            # If the application is being processed, ignore this message
            if app_data.get('processing', False):
                logger.info(f"Message from {message.author.name} ignored - application is being processed")
                return
            
            # Set processing flag
            app_data['processing'] = True
            logger.info(f"Processing message from {message.author.name}: {message.content}")
            logger.debug(f"Current application state: {app_data}")
            
            try:
                # Get the current question index
                current_q_index = app_data['current_question']
                logger.debug(f"Current question index: {current_q_index}")
                logger.debug(f"Total questions: {len(app_data['questions'])}")
                logger.debug(f"Questions array: {app_data['questions']}")
                
                # Add the answer
                app_data['answers'].append(message.content)
                logger.debug(f"Added answer: {message.content}")
                logger.debug(f"Updated answers array: {app_data['answers']}")
                
                # Check if we have all answers
                if len(app_data['answers']) >= len(app_data['questions']):
                    logger.info("All questions answered, completing application")
                    await self._complete_application(message, app_data)
                else:
                    # Update current question index and send next question
                    app_data['current_question'] = current_q_index + 1
                    next_q_index = app_data['current_question']
                    logger.debug(f"Sending next question: {next_q_index}")
                    
                    if next_q_index < len(app_data['questions']):
                        next_question = app_data['questions'][next_q_index]
                        logger.debug(f"Next question content: {next_question}")
                        
                        # Add a delay to ensure messages are processed in order
                        await asyncio.sleep(1)
                        try:
                            logger.debug(f"Attempting to send question: {next_question}")
                            await message.channel.send(f"**Question {next_q_index + 1}:** {next_question}")
                            logger.info(f"Successfully sent question {next_q_index + 1}")
                        except Exception as e:
                            logger.error(f"Error sending next question: {e}")
                            logger.error(f"Error type: {type(e)}")
                            logger.error(f"Error traceback: {traceback.format_exc()}")
                            # Try to send an error message to the user
                            try:
                                await message.channel.send("Sorry, there was an error sending the next question. Please try again.")
                            except:
                                pass
                    else:
                        logger.error("Error: next_q_index is out of bounds")
            except Exception as e:
                logger.error(f"Error processing application message: {e}")
                logger.error(f"Error type: {type(e)}")
                logger.error(f"Error traceback: {traceback.format_exc()}")
                try:
                    await message.channel.send("Sorry, there was an error processing your answer. Please try again.")
                except:
                    pass
            finally:
                # Clear processing flag
                if str(message.author.id) in self.active_applications:
                    self.active_applications[str(message.author.id)]['processing'] = False
                    logger.debug(f"Cleared processing flag for {message.author.name}")
                logger.info(f"Finished processing message from {message.author.name}")
            
            return

        # Process commands for non-application messages
        await self.process_commands(message)
    
    async def _complete_application(self, message, app_data):
        logger.info("All questions answered, preparing submission")
        
        # Format questions and answers
        qa_pairs = []
        for i in range(len(app_data['questions'])):
            qa_pairs.append({
                "question": app_data['questions'][i],
                "answer": app_data['answers'][i]
            })
        
        # Create the final application data
        final_app_data = {
            "user_id": app_data['user_id'],
            "user_name": app_data['user_name'],
            "position": app_data['position'],
            "questions_answers": qa_pairs,
            "status": "pending"
        }
        
        # Generate application ID
        app_id = f"{message.author.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Save application
        json_path = os.path.join(APPS_DIRECTORY, f"{app_id}.json")
        with open(json_path, 'w') as f:
            json.dump(final_app_data, f, indent=4)
        
        # Send confirmation
        await message.channel.send("Thank you! Your application has been submitted for review. 🎉")
        
        # Get position settings
        questions = load_questions()
        position_settings = questions.get(app_data['position'], {})
        
        # Log the application
        log_channel_id = position_settings.get('log_channel')
        if log_channel_id:
            log_channel = self.get_channel(int(log_channel_id))
            if log_channel:
                # Create ping string for roles
                ping_roles = position_settings.get('ping_roles', [])
                ping_string = ' '.join([f'<@&{role_id}>' for role_id in ping_roles]) if ping_roles else ''
                
                embed = discord.Embed(
                    title="New Application Received",
                    description=f"User: {message.author.mention}\nPosition: {app_data['position']}",
                    color=discord.Color.green()
                )
                embed.add_field(name="Application ID", value=app_id)
                # Add masked link to application
                web_url = f"http://{os.getenv('WEB_HOST', 'localhost')}:{os.getenv('WEB_PORT', '8080')}/application/{app_id}"
                embed.add_field(name="View Application", value=f"[Click Here]({web_url})", inline=False)
                
                # Create and register view with the bot - single clean way
                view = ApplicationResponseView(app_id, app_data['position']).set_bot(self)
                
                # Send message with ping roles if any are set
                if ping_string:
                    log_message = await log_channel.send(ping_string, embed=embed, view=view)
                else:
                    log_message = await log_channel.send(embed=embed, view=view)
                    
                # Create thread if auto_thread is enabled
                if position_settings.get('auto_thread', False):
                    try:
                        thread_name = f"{message.author.name}'s {app_data['position']} Application"
                        await log_message.create_thread(name=thread_name, auto_archive_duration=1440)
                    except Exception as e:
                        logger.error(f"Error creating thread: {e}")
        
        # Remove the active application
        if str(message.author.id) in self.active_applications:
            del self.active_applications[str(message.author.id)]
        logger.info(f"Application for {message.author.name} submitted and removed from active applications")

# Create bot instance
bot = ApplicationBot()

# Add commands
@bot.tree.command(name="setup_applications", description="Set up the staff application system")
@app_commands.default_permissions(administrator=True)
async def setup_applications(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Staff Applications",
        description="Select a position below to apply for our staff team!",
        color=0x808080
    )
    embed.set_footer(text="Applications are processed by our admin team")
    
    # Create view with all available positions
    view = StaffApplicationView(bot)
    
    # Add the view to persistent views before sending
    bot.add_view(view)
    
    # Send the message
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="panel_create", description="Create a new application panel through the dashboard")
@app_commands.default_permissions(administrator=True)
async def panel_create(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Please use the web dashboard to create and manage panels. Visit the dashboard at "
        f"http://{os.getenv('WEB_HOST', 'localhost')}:{os.getenv('WEB_PORT', 8080)}/panels/create",
        ephemeral=True
    )

# Run the bot
if __name__ == '__main__':
    bot.run(TOKEN)
