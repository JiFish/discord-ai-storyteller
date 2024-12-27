import asyncio
import signal
from logger import logger
from datetime import datetime, timedelta
from config import config
import game_logic as game
from discord_client import client, discord_safe_send, set_activity_presence
import admin_commands

# Update status event
STATUS_REFRESH_INTERVAL = 30
status_update_task = None
async def update_status_task():
    idle_timeout = config['discord']['idle_timeout']
    if idle_timeout:
        idle_timeout = timedelta(minutes=idle_timeout)
        while True:
            await asyncio.sleep(STATUS_REFRESH_INTERVAL)
            is_idle = datetime.now() - game.game_context["last_status_update"] > idle_timeout
            await set_activity_presence(game.game_context["status"], is_idle)
    else:
        while True:
            await asyncio.sleep(STATUS_REFRESH_INTERVAL)
            await set_activity_presence(game.game_context["status"])

@client.event
async def on_ready():
    logger.info(f'Bot has connected as {client.user}')

    # Ensure task is started only once
    global status_update_task
    if status_update_task is None:
        status_update_task = client.loop.create_task(update_status_task())

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    user_message = message.content.strip()
    if not user_message:
        return

    user_id = message.author.id

    if message.guild is None and user_id in config['discord']['admin_ids']:
        await handle_admin_command(user_message, message.channel)
    elif message.channel.id == config['discord']['channel_id']:
        await handle_public_message(user_id, message, message.channel)

async def handle_admin_command(user_message, channel):
    lower_message = user_message.lower()

    command_handlers = {
        "!clearprev":    admin_commands.clear_previous_users,
        "!instructions": admin_commands.instructions,
        "!newgame":      admin_commands.new_game,
        "!nudge":        admin_commands.nudge,
        "!picture":      admin_commands.picture,
        "!ping":         admin_commands.ping,
        "!prompt":       admin_commands.prompt,
        "!shutdown":     admin_commands.shutdown,
        "!summarise":    admin_commands.summarize,
        "!summarize":    admin_commands.summarize,
        "!testdice":     admin_commands.test_dice,
        "!version":      admin_commands.version
    }

    for command, handler in command_handlers.items():
        if lower_message.startswith(command):
            params = user_message[len(command):].strip()
            await handler(channel, params)
            return

    await channel.send(f"{user_message}: Command not recognized.")

async def handle_public_message(user_id, message, channel):
    user_message = message.content.strip()
    lower_message = user_message.lower().lstrip("_*")

    # Commands that can be used without a character
    if lower_message.startswith("!newcharacter"):
        try:
            _, details = user_message.split(maxsplit=1)
            name, race, char_class, pronouns, appearance = [item.strip() for item in details.split(',')]
        except ValueError:
            await message.reply("Please use the format: `!newcharacter name, race, class, pronouns, appearance`.")
        else:
            response = game.create_character(user_id, name, race, pronouns, char_class, appearance)
            await message.reply(response)
    
    # Check if the player has a character
    elif user_id not in game.game_context["characters"]:
        await message.reply("Please create a character first using `!newcharacter name, race, class, pronouns`.")

    # Commands that require a character
    elif lower_message.startswith(("!say","(say)", ">")):
        # Remove the command prefix by length so the player can omit the space after the command.
        details = user_message[{'!': 4, '(': 5, '>': 1}[user_message[0]]:].lstrip()
        game.player_say(user_id, details)
        await message.add_reaction("💬")

    # Check if the player is trying to use some other command
    elif lower_message.startswith("!"):
        await message.reply(f"{user_message}: Command not recognized.")

    # Check if the player has taken a turn recently
    elif user_id in game.game_context["previous_users"]:
        remaining_turns = game.players_until_turn(user_id)
        player_word = "player" if remaining_turns == 1 else "players"
        await message.reply(
            f"You've already taken a turn recently. Please wait for {remaining_turns} more {player_word} to take a turn before acting again."
        )

    # If no command was issued, the player is taking an action
    else:
        await handle_player_action(user_id, user_message, channel)

async def handle_player_action(user_id, user_message, channel):
    async with channel.typing():
        chatgpt_response = await game.respond_to_player(user_id, user_message)
    await discord_safe_send(chatgpt_response, channel)

    if game.game_context["token_usage"] > config['game']['max_log_tokens']:
        async with channel.typing():
            chatgpt_response = await game.summarize_adventure()
        if chatgpt_response != False:
            await discord_safe_send(chatgpt_response, channel)
        else:
            logger.fatal("Summarization due to exceeding max_log_tokens failed. This is fatal, exiting.")
            client.close()

def handle_shutdown():
    logger.info("Shutdown signal received. Closing Discord client.")
    client.loop.create_task(client.close())

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, lambda s, f: handle_shutdown())
signal.signal(signal.SIGTERM, lambda s, f: handle_shutdown())

client.run(config['discord']['bot_token'])
