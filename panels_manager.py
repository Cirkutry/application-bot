import os
import json
import discord
import pathlib
from dotenv import load_dotenv
import uuid
from application_components import StaffApplicationView
import traceback
from panel_utils import load_panels, save_panels

# Get Discord bot token
load_dotenv()

# Ensure storage directory exists
pathlib.Path('storage').mkdir(exist_ok=True)

# Configure applications directory
APPS_DIRECTORY = 'storage/applications'
pathlib.Path(APPS_DIRECTORY).mkdir(exist_ok=True)

# Configure panels directory
PANELS_DIRECTORY = 'storage/panels'
pathlib.Path(PANELS_DIRECTORY).mkdir(exist_ok=True)
PANELS_FILE = os.path.join(PANELS_DIRECTORY, 'panels.json')

def load_panels():
    """Load saved panels from JSON file"""
    if not os.path.exists(PANELS_FILE):
        return {}
    
    try:
        with open(PANELS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading panels: {str(e)}")
        return {}

def save_panels(panels):
    """Save panels to JSON file"""
    try:
        with open(PANELS_FILE, 'w') as f:
            json.dump(panels, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving panels: {str(e)}")
        return False

async def register_panels(bot):
    """Register all panels with the bot"""
    panels = load_panels()
    
    # Clear existing views to prevent duplicates
    if hasattr(bot, 'views'):
        bot.views.clear()
    else:
        bot.views = {}
    
    registered_count = 0
    for panel_id, panel_data in panels.items():
        try:
            # Get the channel and message
            channel = bot.get_channel(int(panel_data['channel_id']))
            if not channel:
                continue
                
            try:
                message = await channel.fetch_message(int(panel_data['message_id']))
            except discord.NotFound:
                continue
            except discord.Forbidden:
                continue
                
            # Create select options from positions
            select_options = [
                discord.SelectOption(
                    label=position if isinstance(position, str) else position['name'],
                    description=f"Apply for {position if isinstance(position, str) else position['name']} position",
                    value=position if isinstance(position, str) else position['name']
                ) for position in panel_data['positions']
            ]
            
            # Create the view with the bot instance, select options, and panel ID
            view = StaffApplicationView(bot, select_options, panel_id)
            
            # Store the view in the bot's views dictionary with both panel_id and message_id
            bot.views[panel_id] = view
            bot.views[str(message.id)] = view  # Also store by message ID for faster lookup
            
            # Register the view with the bot and message ID
            bot.add_view(view, message_id=message.id)
            
            registered_count += 1
        except Exception as e:
            print(f"Error registering panel: {e}")
            print(f"Error traceback: {traceback.format_exc()}")
            continue  # Continue with next panel even if this one fails
    
    return registered_count

async def create_panel(bot, channel_id, positions, embed_data):
    """Create a new application panel"""
    try:
        # Create the embed
        embed = discord.Embed(
            title=embed_data.get('title', 'Staff Applications'),
            description=embed_data.get('description', 'Select a position below to apply!'),
            color=int(embed_data.get('color', '0x3498db').replace('0x', ''), 16)
        )
        
        # Add optional embed fields
        if embed_data.get('author_name'):
            embed.set_author(
                name=embed_data.get('author_name'),
                url=embed_data.get('author_url'),
                icon_url=embed_data.get('author_icon_url')
            )
        
        if embed_data.get('thumbnail_url'):
            embed.set_thumbnail(url=embed_data.get('thumbnail_url'))
        
        if embed_data.get('image_url'):
            embed.set_image(url=embed_data.get('image_url'))
        
        if embed_data.get('footer_text'):
            embed.set_footer(
                text=embed_data.get('footer_text'),
                icon_url=embed_data.get('footer_icon_url')
            )
        
        # Send the message
        channel = bot.get_channel(int(channel_id))
        if not channel:
            return None
            
        # Create select options for the positions
        select_options = [
            discord.SelectOption(
                label=position,
                value=position,
                description=f"Apply for {position} position"
            ) for position in positions
        ]
            
        # Create the view with the bot instance and panel ID
        panel_id = str(uuid.uuid4())
        view = StaffApplicationView(bot, select_options, panel_id)
        
        # Send the message
        message = await channel.send(embed=embed, view=view)
        
        # Register the view with the bot and message ID
        bot.add_view(view, message_id=message.id)
        
        # Save panel data
        panels = load_panels()
        panel_data = {
            'id': panel_id,
            'channel_id': str(channel.id),
            'message_id': str(message.id),
            'positions': positions
        }
        panels[panel_id] = panel_data
        if not save_panels(panels):
            return None
            
        return panel_id
        
    except Exception as e:
        print(f"Error creating panel: {e}")
        print(f"Error traceback: {traceback.format_exc()}")
        return None