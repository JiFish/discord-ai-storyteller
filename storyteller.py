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
        await handle_admin_command(user_message, message)
    elif message.channel.id == config['discord']['channel_id']:
        await handle_public_message(user_id, user_message, message)

async def handle_admin_command(user_message, message):
    for command, handler, reject_if_game_locked in admin_commands.command_handlers:
        if user_message.lower().startswith(command):
            user_message, _ = user_message_extract(user_message, message)
            params = user_message[len(command):].lstrip()

            # Deal with blocking actions
            if reject_if_game_locked and game.is_game_locked():
                await message.reply("I'm currently busy processing an action. Please try again in a moment.")
            else:
                await handler(message.channel, params)
            return

    await message.channel.send(f"{user_message}: Command not recognized.")

def user_message_extract(user_message, message):
    fourth_wall = False
    for user in message.mentions:
        if user.id in game.game_context["characters"]:
            char_name = game.game_context["characters"][user.id]["name"]
            user_message = user_message.replace(user.mention, char_name)
        else:
            fourth_wall = True

    return user_message, fourth_wall

async def handle_public_message(user_id, user_message, message):
    lower_message = user_message.lstrip("_*").lower()

    # Ignore whispers up front, no need to process them
    if lower_message.startswith(("!w", "(w)", "(whisper")):
        return

    user_message, fourth_wall = user_message_extract(user_message, message)

    # Commands that can be used without a character
    if lower_message.startswith("!newcharacter"):
        try:
            _, details = user_message.split(maxsplit=1)
            name, race, char_class, pronouns, appearance = [item.strip() for item in details.split(',')]
        except ValueError:
            await message.reply("Please use the format: `!newcharacter name, race, class, pronouns, appearance`.")
        else:
            response = await game.create_character(user_id, name, race, pronouns, char_class, appearance)
            await message.reply(response)
    
    # Check if the player has a character
    elif user_id not in game.game_context["characters"]:
        await message.reply("Please create a character first using `!newcharacter name, race, class, pronouns`.")

    # Check if the player is breaking the fourth wall command
    elif fourth_wall:
        await message.reply("Mentioned users must have characters in the game. Don't break the fourth wall!")

    # Commands that require a character
    elif lower_message.startswith(("!say","(say)", ">")):
        # Remove the command prefix by length so the player can omit the space after the command.
        quote = user_message[{'!': 4, '(': 5, '>': 1}[user_message[0]]:].lstrip()
        await game.player_say(user_id, quote)
        if config['game']['say_react']:
            await message.add_reaction(config['game']['say_react'])

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
        if not game.is_game_locked():
            await handle_player_action(user_id, user_message, message)
        else:
            await message.reply("I'm currently busy processing an action. Please try again in a moment.")

async def add_dice_reactions(message, dice_values):
    for i, value in enumerate(dice_values):
        await message.add_reaction(config['game']['dice_reacts'][i][value - 1])

async def handle_player_action(user_id, user_message, message):
    channel = message.channel
    async with channel.typing():
        response_prefix = ""
        dice_values = game.roll_dice()
        # Start the AI processing the player's action, we do this so we can send dice reactions while the AI is working
        respond_to_player_task = client.loop.create_task(game.respond_to_player(user_id, user_message, dice_values))
        # Dice as reactions
        if dice_values and config['game']['dice_reacts']:
            await add_dice_reactions(message, dice_values)
        # Dice in response text
        elif dice_values:
            dice_result = " ".join(config['game']['dice_strings'][value - 1] for value in dice_values)
            response_prefix = f"You rolled: {dice_result}\n\n"

        response = await respond_to_player_task
        await discord_safe_send(response_prefix + response, channel)

    if game.game_context["token_usage"] > config['game']['max_log_tokens']:
        async with channel.typing():
            response = await game.summarize_adventure()
        if response != False:
            await discord_safe_send(response, channel)
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
