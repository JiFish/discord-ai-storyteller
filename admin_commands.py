import discord
from logger import logger
import game_logic as game
from discord_client import get_public_channel, discord_safe_send, client_close
from config import config, VERSION

async def picture(channel, params):
    if not config['experimental']['image_generation']:
        await channel.send("Image generation is disabled.")
        return
    async with get_public_channel().typing():
        image_url = await game.generate_image_from_scene()
    if image_url == False:
        await channel.send("Image generation failed.")
        return
    logger.info(f"Generated image: {image_url}")
    await get_public_channel().send(embed=discord.Embed().set_image(url=image_url))

async def instructions(channel, params):
    with open(config['files']['instructions'], "r") as f:
        instructions = f.read()
    await discord_safe_send(instructions, get_public_channel())

async def summarize(channel, params):
    async with get_public_channel().typing():
        chatgpt_response = await game.summarize_adventure()
    if chatgpt_response != False:
        await discord_safe_send(chatgpt_response, get_public_channel())
    else:
        await channel.send("Summarization failed.")

async def new_game(channel, params):
    await game.new_adventure(name=params)
    await discord_safe_send("**A new adventure is beginning. Please create new characters!**", get_public_channel())

async def rename(channel, params):
    if not params:
        await channel.send("Please provide a new name for the adventure.")
    else:
        await game.rename_adventure(params)

async def test_dice(channel, params):
    dice_test = " ".join(config['game']['dice_strings'])
    if config['game']['dice_reacts']:
        for dice_reacts in config['game']['dice_reacts']:
            dice_test += "\n" + " ".join(dice_reacts)
    await channel.send(dice_test)

async def ping(channel, params):
    logger.info('Pong! (Received !ping command.)')
    await channel.send("Pong!")

async def version(channel, params):
    await channel.send(VERSION)

async def shutdown(channel, params):
    logger.info("Received !shutdown command")
    await channel.send("Going offline...")
    await client_close()

async def prompt(channel, params):
    if not params:
        await channel.send("Please provide prompt after the command.")
    else:
        async with get_public_channel().typing():
            admin_response = await game.respond_to_admin(params)
        await discord_safe_send(admin_response, get_public_channel())

async def nudge(channel, params):
    if not params:
        await channel.send("Please provide prompt after the command.")
    else:
        await game.admin_nudge(params)
        await channel.send("Nudge added.")

async def echo(channel, params):
    await discord_safe_send(params, get_public_channel())

async def write(channel, params):
    await game.write_story(params)
    await discord_safe_send(params, get_public_channel())

async def clear_previous_users(channel, params):
    await game.clear_previous_users()
    await channel.send("Previous users cleared.")

async def stats(channel, params):
    stats = f"""
    **Game Name:** {game.game_context['game_name']}
    **Last Token Usage:** {game.game_context['token_usage']}
    **Last Status Update:** {game.game_context['last_status_update']}
    **Log entries:** {len(game.game_context['log'])}
    **Characters:** {len(game.game_context['characters'])}
    **Users awaiting turn:** {len(game.game_context['previous_users'])}
    """
    await channel.send(stats)

async def kick(channel, params):
    if not params:
        await channel.send("Please provide a character to kick.")
        return
    # Params is user_id_or_name and custom_message (optional)
    params = params.split(",", 1)
    user_id_or_name = params[0].rstrip()
    custom_message = params[1].lstrip() if len(params) > 1 else None
    response = await game.character_leaves(user_id_or_name, custom_message)
    await get_public_channel().send(response)

# (command, handler, reject_if_game_locked)
command_handlers = [
    ("!clearprev",                clear_previous_users, False),
    ("!echo",                     echo,                 False),
    ("!instructions",             instructions,         False),
    ("!kick",                     kick,                 False),
    ("!newgame",                  new_game,             False),
    ("!nudge",                    nudge,                False),
    ("!picture",                  picture,              False),
    ("!ping",                     ping,                 False),
    ("!prompt",                   prompt,               True ),
    ("!rename",                   rename,               False),
    ("!shutdown",                 shutdown,             False),
    ("!stats",                    stats,                False),
    # User actions can automatically trigger a summarization, so reject just in case
    (("!summarise","!summarize"), summarize,            True ),
    ("!testdice",                 test_dice,            False),
    ("!version",                  version,              False),
    ("!write",                    write,                True ),
]
