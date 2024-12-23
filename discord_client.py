import discord
from logger import logger
from config import config

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

public_channel = client.get_channel(int(config['discord']['channel_id']))

current_details = None
current_status = discord.Status.online

async def set_activity_presence(details, is_idle=False):
    global current_details, current_status

    status = discord.Status.idle if is_idle else discord.Status.online

    # Don't keep hitting the API with the same presence update
    if details == current_details and client.status == current_status:
        return

    activity = discord.Activity(
        type=discord.ActivityType.playing,
        name=config['discord']['activity_name'],
        state=details
    )

    await client.change_presence(activity=activity, status=status)
    current_details = details
    current_status = status

async def discord_safe_send(message, channel):
    if len(message) <= config['discord']['message_length']:
        await channel.send(message)
        return

    logger.info("AI message is too long, splitting into multiple messages. If this happens often, try reducing max_tokens")
    message_chunks = chunk_string(message)
    for chunk in message_chunks:
        await channel.send(chunk)

def chunk_string(text):
    chunks = []
    while text:
        if len(text) <= config['discord']['message_length']:
            chunks.append(text)
            break

        split_point = text.rfind('\n', 0, config['discord']['message_length'])
        if split_point == -1:
            split_point = text.rfind(' ', 0, config['discord']['message_length'])
        
        if split_point == -1:
            split_point = config['discord']['message_length']

        chunks.append(text[:split_point].rstrip())
        text = text[split_point:].lstrip()

    return chunks

def client_close():
    client.close()
