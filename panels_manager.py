import json
import logging
import os
import pathlib
import traceback
import uuid
import discord
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()
pathlib.Path("storage").mkdir(exist_ok=True)
APPS_DIRECTORY = "storage/applications"
pathlib.Path(APPS_DIRECTORY).mkdir(exist_ok=True)
PANELS_DIRECTORY = "storage"
pathlib.Path(PANELS_DIRECTORY).mkdir(exist_ok=True)
PANELS_FILE = os.path.join(PANELS_DIRECTORY, "panels.json")


def load_panels():
    if not os.path.exists(PANELS_FILE):
        return {}
    try:
        with open(PANELS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading panels: {str(e)}")
        return {}


def save_panels(panels):
    try:
        with open(PANELS_FILE, "w") as f:
            json.dump(panels, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving panels: {str(e)}")
        return False


async def register_panels(bot):
    from application_components import StaffApplicationView

    panels = load_panels()
    if hasattr(bot, "views"):
        bot.views.clear()
    else:
        bot.views = {}
    registered_count = 0
    for panel_id, panel_data in panels.items():
        try:
            channel = bot.get_channel(int(panel_data["channel_id"]))
            if not channel:
                continue
            try:
                message = await channel.fetch_message(int(panel_data["message_id"]))
            except discord.NotFound:
                continue
            except discord.Forbidden:
                continue
            select_options = [
                discord.SelectOption(
                    label=position if isinstance(position, str) else position["name"],
                    description=f"Apply for {position if isinstance(position, str) else position['name']} position",
                    value=position if isinstance(position, str) else position["name"],
                )
                for position in panel_data["positions"]
            ]
            view = StaffApplicationView(bot, select_options, panel_id)
            bot.views[panel_id] = view
            bot.views[str(message.id)] = view
            bot.add_view(view, message_id=message.id)
            registered_count += 1
        except Exception as e:
            logger.error(f"Error registering panel: {e}")
            logger.error(f"Error traceback: {traceback.format_exc()}")
            continue
    return registered_count


async def create_panel(bot, channel_id, positions, embed_data):
    from application_components import StaffApplicationView

    try:
        embed = discord.Embed(
            title=embed_data.get("title", "Staff Applications"),
            description=embed_data.get(
                "description", "Select a position below to apply!"
            ),
            color=int(embed_data.get("color", "0x3498db").replace("0x", ""), 16),
        )
        if embed_data.get("author_name"):
            embed.set_author(
                name=embed_data.get("author_name"),
                url=embed_data.get("author_url"),
                icon_url=embed_data.get("author_icon_url"),
            )
        if embed_data.get("thumbnail_url"):
            embed.set_thumbnail(url=embed_data.get("thumbnail_url"))
        if embed_data.get("image_url"):
            embed.set_image(url=embed_data.get("image_url"))
        if embed_data.get("footer_text"):
            embed.set_footer(
                text=embed_data.get("footer_text"),
                icon_url=embed_data.get("footer_icon_url"),
            )
        channel = bot.get_channel(int(channel_id))
        if not channel:
            return None
        select_options = [
            discord.SelectOption(
                label=position,
                value=position,
                description=f"Apply for {position} position",
            )
            for position in positions
        ]
        panel_id = str(uuid.uuid4())
        view = StaffApplicationView(bot, select_options, panel_id)
        message = await channel.send(embed=embed, view=view)
        bot.add_view(view, message_id=message.id)
        panels = load_panels()
        panel_data = {
            "id": panel_id,
            "channel_id": str(channel.id),
            "message_id": str(message.id),
            "positions": positions,
        }
        panels[panel_id] = panel_data
        if not save_panels(panels):
            return None
        return panel_id
    except Exception as e:
        logger.error(f"Error creating panel: {e}")
        logger.error(f"Error traceback: {traceback.format_exc()}")
        return None
