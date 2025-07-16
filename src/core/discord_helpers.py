import datetime
import json
import logging
import os
import pathlib
from datetime import UTC

import discord
from question_manager import load_questions

logger = logging.getLogger(__name__)

APPS_DIRECTORY = "storage/applications"
pathlib.Path(APPS_DIRECTORY).mkdir(exist_ok=True)
ACTIVE_APPS_FILE = os.path.join("storage", "active_applications.json")


# TODO: Refactor this file into more relevant files/naming/structure rather than a generic helper filer


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
    start_time = datetime.datetime.fromisoformat(application["start_time"])
    current_time = datetime.datetime.now(UTC)
    time_elapsed = (current_time - start_time).total_seconds() / 60
    questions = load_questions()
    position_settings = questions.get(application["position"], {})
    time_limit = position_settings.get("time_limit", 60)
    if time_elapsed > time_limit:
        await message.channel.send(
            f"⌛ Your application has expired. You had {time_limit} minutes to complete it. Please start a new application if you wish to apply."
        )
        del bot.active_applications[str(message.author.id)]
        save_active_applications(bot.active_applications)
        return
    current_question = application["current_question"]
    questions_list = application["questions"]
    application["answers"].append(message.content)
    if current_question + 1 < len(questions_list):
        application["current_question"] += 1
        await message.channel.send(
            f"**Question {current_question + 2} of {len(questions_list)}:** {questions_list[current_question + 1]}"
        )
        save_active_applications(bot.active_applications)
    else:
        import uuid

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
        log_channel_id = position_settings.get("log_channel")
        if log_channel_id:
            try:
                log_channel = bot.get_channel(int(log_channel_id))
                if log_channel:
                    web_host = os.getenv("WEB_HOST", "localhost")
                    web_port = os.getenv("WEB_PORT", "8080")
                    application_url = f"http://{web_host}:{web_port}/application/{application_id}"
                    web_external = os.getenv("WEB_EXTERNAL")
                    if web_external:
                        application_url = f"{web_external}/application/{application_id}"
                    embed = discord.Embed(
                        title=f"{message.author.name}'s {application['position']} application",
                        description=f"Applicant: {message.author.mention} ({message.author.id})",
                        color=0x808080,
                    )
                    embed.description += f"\n\n[Click here to view the application]({application_url})"
                    guild = log_channel.guild
                    member = guild.get_member(message.author.id)
                    if member and member.joined_at:
                        embed.description += f"\n\nJoined server: <t:{int(member.joined_at.timestamp())}:R>"
                    embed.set_thumbnail(url=message.author.display_avatar.url)
                    embed.set_footer(text=f"{application_id}")
                    ping_mentions = ""
                    ping_roles = position_settings.get("ping_roles", [])
                    if ping_roles:
                        ping_mentions = " ".join([f"<@&{role_id}>" for role_id in ping_roles])
                    log_message = await log_channel.send(
                        content=ping_mentions if ping_mentions else None,
                        embed=embed,
                    )
                    if position_settings.get("auto_thread", False):
                        try:
                            thread_name = f"{application['position']} - {message.author.name}"
                            await log_message.create_thread(name=thread_name, auto_archive_duration=1440)
                        except Exception as e:
                            logger.error(f"Error creating thread: {e}")
            except Exception as e:
                logger.error(f"Error logging application: {e}")
