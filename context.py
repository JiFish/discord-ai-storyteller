import os
import json
import shutil
from datetime import datetime
from logger import logger
from config import config

# Create the backup directory if it doesn't exist
if not os.path.exists(config['files']['backup_dir']):
    os.makedirs(config['files']['backup_dir'])

def get_empty_context():
    return {
        "characters": {},
        "log": [{"role": "system", "content": config['prompts']['base']}],
        "previous_users": [],
        "token_usage": -1,
        "status": "Starting a new adventure!",
        "last_status_update": datetime.now()
    }

def load_game_context():
    if os.path.exists(config['files']['game']):
        with open(config['files']['game'], 'r') as f:
            context = json.load(f)
        # Convert timestamps back to datetime objects
        if "last_status_update" in context:
            context["last_status_update"] = datetime.fromisoformat(context["last_status_update"])
        # Fill in missing fields
        context = {**get_empty_context(), **context}
        return context

    return get_empty_context()

def save_game_context(game_context):
    with open(config['files']['game'], 'w') as f:
        json.dump(game_context, f, default=str)

def backup_game_context():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = os.path.join(config['files']['backup_dir'], f"{timestamp}.json")
    shutil.copy(config['files']['game'], backup_filename)
    logger.info(f"Backup created: {backup_filename}")
