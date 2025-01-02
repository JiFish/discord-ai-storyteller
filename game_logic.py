import asyncio
from logger import logger
from random import randint
from datetime import datetime
from config import config
from context import save_game_context, backup_game_context, load_game_context, get_empty_context
from openai import OpenAI
import adventure_log

openai_client = OpenAI(api_key=config['openai']['api_key'])

game_lock = asyncio.Lock()

def locked():
    def decorator(func):
        async def wrapper(*args, **kwargs):
            async with game_lock:
                return await func(*args, **kwargs)
        return wrapper
    return decorator

def is_game_locked():
    return game_lock.locked()

def roll_dice():
    if not config['game']['dice']:
        return False
    return [randint(1, config['game']['dice']['dice_type'])
            for _ in range(config['game']['dice']['num_dice'])]

def _update_status(new_status):
    game_context["status"] = new_status
    game_context["last_status_update"] = datetime.now()

def _build_system_prompt():
    character_descriptions = [
        f"{char['name']} is a {char['race']} {char['class']} ({char['pronouns']} pronouns), {char['appearance']}"
        for char in game_context["characters"].values()
    ]
    return config['prompts']['base'] + "\nThe players are:\n" + "\n".join(character_descriptions)

@locked()
# user_id_or_name can be a integer user_id, a string user_id, or a string character name
async def character_leaves(user_id_or_name, custom_message=None):
    user_id_or_name = str(user_id_or_name).lower()
    characters = game_context['characters']

    # Resolve the user ID
    for user_id, char in characters.items():
        if user_id_or_name in (str(user_id), char["name"].lower()):
            break
    else:
        return f"⚠️ Character {user_id_or_name} not found."
    
    character_name = game_context["characters"][user_id]["name"]
    generic_message = f"{character_name} has left the party."
    story_message = custom_message if custom_message else generic_message
    # Give ChatGPT both messages, to ensure it knows the character has left
    context_message = (custom_message + " " if custom_message else "") + generic_message

    game_context["log"].append({"role": "system", "content": context_message})
    del game_context["characters"][user_id]
    _update_status(generic_message)
    save_game_context(game_context)
    adventure_log.add_action(story_message)
    return story_message

@locked()
async def create_character(user_id, name, race, pronouns, char_class, appearance):
    # Check limits
    max_length = config['game']['max_lengths']
    if len(name) > max_length['name']:
        return f"⚠️ Character name is too long. Maximum length is {max_length['name']} characters."
    if len(race) > max_length['race']:
        return f"⚠️ Race is too long. Maximum length is {max_length['race']} characters."
    if len(char_class) > max_length['class']:
        return f"⚠️ Class is too long. Maximum length is {max_length['class']} characters."
    if len(pronouns) > max_length['pronouns']:
        return f"⚠️ Pronouns are too long. Maximum length is {max_length['pronouns']} characters."
    if len(appearance) > max_length['appearance']:
        return f"⚠️ Appearance is too long. Maximum length is {max_length['appearance']} characters."

    # Check for empty fields
    if not all([name, race, pronouns, char_class, appearance]):
        return "⚠️ All fields must be filled."
    
    # Check the character name is not numeric
    if name.isnumeric():
        return "⚠️ Character name cannot be just a number. _I am not a number!_"

    characters = game_context['characters']

    # Check if the name is already in use (case insensitive)
    if any(char["name"].lower() == name.lower() for char in characters.values()):
        return f"⚠️ {name} is already a character name!"
    
    # If we got this far, the character is valid

    # If the user already has a character, deal with that first
    if user_id in characters:
        old_char = characters[user_id]
        log_message = f"{old_char['name']}, the {old_char['race']} {old_char['class']} ({old_char['pronouns']}), has left the party. "
        return_message = f"{old_char['name']} has left the party.\n\n"
        adventure_log.add_action(f"{old_char['name']} has left the party.")
    else:
        log_message = return_message = ""

    # Make changes to the game context
    characters[user_id] = {
        "name": name,
        "race": race,
        "pronouns": pronouns,
        "class": char_class,
        "appearance": appearance
    }
    log_message += f"{name} has joined the party!"
    game_context["log"].append({"role": "user", "content": log_message})
    game_context["log"][0]["content"] = _build_system_prompt()
    _update_status(log_message)
    save_game_context(game_context)

    arrival_message = f"{name} has joined the party! {name} is a {race} {char_class} ({pronouns}). Appearance: {appearance}."
    adventure_log.add_action(arrival_message)
    return return_message + arrival_message

@locked()
async def summarize_adventure():
    backup_game_context()

    summarise_log = game_context["log"].copy()
    summarise_log[0]['content'] = config['prompts']['summary']
    summarise_log.append({"role": "system", "content": config['prompts']['summary_instruction']})

    try:
        summary_text, _ = await _get_chatgpt_response(
            config['openai']['summary_model'],
            summarise_log,
            config['openai']['max_summary_tokens'],
            config['openai']['summary_temperature']
        )
    except Exception as e:
        logger.error(f"Summarization process failed. Error: {e}")
        return False
    
    # Start a new log begining with the summary
    new_log = [
        {"role": "system", "content": _build_system_prompt()},
        {"role": "assistant", "content": summary_text},
    ]
    # Add the last assistant message and all messages after it
    for entry in reversed(game_context["log"]):
        if entry["role"] == "assistant":
            new_log.extend(reversed(game_context["log"][game_context["log"].index(entry):]))
            break

    game_context["log"] = new_log
    game_context["token_usage"] = -1
    
    _update_status("The story so far...")
    save_game_context(game_context)
    return summary_text

@locked()
async def respond_to_admin(message):
    assistant_reply = await _respond_and_log(message, role="system")
    _update_status("The story was moved forward...")
    save_game_context(game_context)
    adventure_log.add_storyteller(assistant_reply)
    return assistant_reply

@locked()
async def respond_to_player(user_id, message, dice_values = None):
    # Update the previous users list
    if config['game']['max_previous_users'] > 0:
        game_context["previous_users"].append(user_id)
        if len(game_context["previous_users"]) > config['game']['max_previous_users']:
            game_context["previous_users"].pop(0)

    character_name = game_context["characters"][user_id]["name"]
    if dice_values:
        message += f" [{sum(dice_values)}]"
    assistant_reply = await _respond_and_log(f"{character_name}: {message}")
    _update_status(f"{character_name} made a decision...")
    save_game_context(game_context)
    adventure_log.add_quote(character_name, message)
    adventure_log.add_storyteller(assistant_reply)
    return assistant_reply

async def _respond_and_log(message, role = "user"):
    game_context["log"].append({"role": role, "content": message})
    try:
        assistant_reply, token_usage = await _get_chatgpt_response(
            config['openai']['main_model'],
            game_context["log"],
            config['openai']['max_tokens'],
            config['openai']['main_temperature']
        )
    except Exception:
        game_context["log"].pop()   # Remove the unprocessed message
        return "I'm experiencing technical issues. Please try again later."
    
    # Removes all entries with the role "system" from the game context log, except for the base prompt (entry 0).
    game_context["log"] = [entry for i, entry in enumerate(game_context["log"]) if entry["role"] != "system" or i == 0]
    game_context["log"].append({"role": "assistant", "content": assistant_reply})
    game_context["token_usage"] = token_usage
    
    return assistant_reply

async def _get_chatgpt_response(model, messages, max_tokens, temperature = 1.0):
    _update_status("Storyteller is thinking...")
    for attempt in range(config['openai']['max_attempts']):
        try:
            response = openai_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content, response.usage.total_tokens
        except Exception as e:
            if attempt < config['openai']['max_attempts'] - 1:
                logger.warning(f"ChatGPT request failed. Error: {e}. (Attempt #{attempt+1}.)")
                await asyncio.sleep(config['openai']['retry_delay'] * (2**attempt))
            else:
                logger.error(f"ChatGPT request failed. Error: {e}. (Attempt #{attempt+1}.)")
                raise

@locked()
async def player_say(user_id, user_message):
    character_name = game_context["characters"][user_id]["name"]
    game_context["log"].append({"role": "user", "content": f"{character_name} says: {user_message}"})
    _update_status(f"{character_name} has spoken...")
    save_game_context(game_context)
    adventure_log.add_quote(f"{character_name} says", user_message)

@locked()
async def admin_nudge(user_message):
    game_context["log"].append({"role": "system", "content": user_message})
    save_game_context(game_context)

@locked()
async def write_story(user_message):
    game_context["log"].append({"role": "assistant", "content": user_message})
    _update_status("The story was moved forward...")
    save_game_context(game_context)
    adventure_log.add_storyteller(user_message)

def _update_context_from_config():
    game_context["log"][0]["content"] = _build_system_prompt()
    if config['game']['max_previous_users'] < 1:
        game_context["previous_users"] = []
    else:
        game_context["previous_users"] = game_context["previous_users"][config['game']['max_previous_users']:]

@locked()
async def clear_previous_users():
    game_context["previous_users"] = []
    save_game_context(game_context)

@locked()
async def new_adventure(name=None):
    backup_game_context()
    game_context = get_empty_context()
    if name:
        game_context["game_name"] = name
    save_game_context(game_context)
    adventure_log.set_log_name(game_context["game_name"])

@locked()
async def rename_adventure(new_name):
    game_context["game_name"] = new_name
    save_game_context(game_context)
    adventure_log.rename_log(new_name)

def players_until_turn(user_id):
    if user_id in game_context["previous_users"]:
        return config['game']['max_previous_users'] - game_context["previous_users"].index(user_id)
    return 0

# Experimental feature
async def generate_image_from_scene():
    # Find the last assistant message in the log
    for entry in reversed(game_context["log"]):
        if entry["role"] == "assistant":
            break
    else:
        return False
    
    try:
        params = config['experimental']['image_generation']
        description_crop_length = params['prompt_length'] - len(params['prompt']) - 2
        del params['prompt_length']
        params['prompt'] = entry["content"][:description_crop_length] + ". " + params['prompt']
        response = openai_client.images.generate(**params)
        return response.data[0].url
    except Exception as e:
        logger.error(f"Image generation failed. Error: {e}")
        return False

## Load the game context
game_context = load_game_context()
_update_context_from_config()
adventure_log.set_log_name(game_context["game_name"])
logger.info(f"Game context loaded: {game_context['game_name']}")
