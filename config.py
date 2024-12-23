import yaml
import sys
from logger import logger
import sys

VERSION = "v0.6 (bleeding edge)"

# Load the config
config_filename = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
with open(config_filename, "r") as file:
    config = yaml.safe_load(file)

# Extract dice string
try:
    num_dice, dice_type = map(int, config['game']['dice'].split('d'))
    if num_dice < 1 or dice_type < 1:
        raise ValueError
except ValueError:
    logger.fatal(f"Invalid dice string: {config['game']['dice']}. Exiting.")
    sys.exit(1)
config['game']['dice'] = {'num_dice': num_dice, 'dice_type': dice_type}

# Ensure discord IDs are strings
config['discord']['channel_id'] = str(config['discord']['channel_id'])
config['discord']['admin_ids'] = [str(admin_id) for admin_id in config['discord']['admin_ids']]
