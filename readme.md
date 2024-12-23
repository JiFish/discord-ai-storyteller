# Discord AI Storyteller v0.6

**(aka Storyteller Bot)**

This Discord bot designed to act as a Game Master for a simplified ttrpg-like experience. Think Dungeons & Dragons.

## Quick Setup Guide

1. **Install Requirements:** Ensure you have Python 3 installed and install the required libraries:

   ```bash
   pip install openai discord.py pyyaml
   ```

2. **Get your API keys**

   - **Create a Discord Bot Account:** Sign up for a bot account and then invite that bot to your server. Make sure it's been granted the "Message Content" intent. See the discord.py documentation for [instructions](https://discordpy.readthedocs.io/en/stable/discord.html).

   - **Get an OpenAI key:** Get your personal API key [here](https://platform.openai.com/account/api-keys).

3. **Set Configuration:** Make a copy of `config_example.yaml` with the name `config.yaml`, and fill in your settings:

   - `discord.bot_token`: Your Discord bot token.
   - `openai.api_key`: Your OpenAI API key.
   - `discord.channel_id`: The ID of the Discord channel where the bot will operate. The bot needs a dedicated channel for the story.
   - `discord.admin_ids`: The IDs of the Discord users with administrative privileges for bot commands.

4. **Run the Script:** Execute the script to start the bot.

   ```bash
   python storyteller.py [config_filename]
   ```

   If the optional config filename is provided, the script will default to `config.yaml`.

5. **Prompt the Bot to start the story:** (Optional) Send the Bot a DM from the admin account, prompting it to start the adventure. Examples:

    - `!prompt Please start the story.`
    - `!prompt Please start the story in a tavern called The Kobold Arms.`
    - `!prompt Please start the story in an elven village. The party's goal is to defeat an evil sorcerer.`

## Playing

To play, users interact with the bot by sending messages in the configured Discord channel. The bot acts as the Game Master, narrating the story and responding to player actions. When a player sends an action in the channel, 2d6 are rolled to help the Bot determine how well the player's action went.

To prevent any single player from dominating the spotlight, after a player takes their turn, 1 more must take a turn before that player can go again.

Gameplay can be configured, see [Gameplay Settings](#gameplay-settings) below.

### Commands

- `!newcharacter name, race, class, pronouns`

  - Create a new character for the game.
  - Example: `!newcharacter Zara, Elf, Wizard, she/her`
  - Replaces your old character if you had one.

- `!whisper` or `(whisper)` or `!w ` or `(w)`

  - Send a message that the bot won't hear. For out-of-character chat.
  - e.g. `(whisper) I won't be able to play this evening.`

- `!say` or `(say)` or `> `

  - Say something in-character. It will be recorded in the adventure log, but won't prompt a reply from the bot.
  - The bot will react with "💬" to show it heard you.
  - e.g. `!say I've got a bad feeling about this.`
  
- **All other messages in the channel are treated as in-game actions.**

## Administrating

Admins can make narrative changes or issue commands by privately messaging the bot. The following admin commands are available:

- `!clearprev`

  Clear the list of previous users who have taken a turn.

- `!instructions`

  Send the contents of `instructions.md` to the public channel. You probably want to customise this file first.

- `!newgame`

  Makes a backup, then resets the game context and starts a new adventure. **Note: This deletes all the player's characters.**

- `!nudge (prompt text)`

  Nudge the bot with a specific prompt. Works like `!prompt`, but rather than invoking an immediate response, the prompt will be send along with the next message that does. Perfect for minor narrative adjustments.

- `!picture` **(Experimental!)**

  Generate an image from the bot's last scene description and post it to the public channel. To enable this feature, ensure the proper config settings have been set. The image generator has no understanding of the story's continutity, so character, object and location appearances will change between images.

- `!ping`

  Check if the bot is responsive.

- `!prompt (prompt text)`

  Send a prompt to the bot to respond to. For example, you can instruct the bot to begin the story, bring it to a close, or start a new chapter. **The bot will respond to these instructions with a visible message in the channel**, so consider carefully what you send. While the bot's response will be saved in the game log, the original prompt message will not. This method is ideal for giving quick narrative prompts but is not suitable for long-term instructions. For persistent changes, update the `prompts.base` in the configuration. Examples:

  - "Please start the story in a mysterious cave."
  - "Describe a fierce dragon that lands outside the village, demanding tribute."
  - "Wrap up the current chapter and set the scene for the party's journey to the capital city."

- `!shutdown`

  Disconnect and close bot script.

- `!summarize` or `!summarise`

  Trigger a manual summarization of the adventure. See 'Summarization' below.

- `!testdice`

  Test dice rolls strings by replying with all possible outcomes as a DM.

## Config Variables

### Discord Settings

- `discord.bot_token`: The authentication token for your Discord bot.
- `discord.channel_id`: The ID of the Discord channel where the bot will operate. If not set, the bot will ignore messages from all channels.
- `discord.admin_ids`: The IDs of the Discord users with administrative privileges for bot commands.
- `discord.message_length`: Default: `2000`. The maximum length of a message the bot can send in Discord. Messages longer than this will be split.
- `discord.idle_timeout`: Default: `60`. Number of minutes without story interaction before the bot goes idle. Set to `false` to disable.

### OpenAI Settings

- `openai.api_key`: Your OpenAI API key to access GPT models.
- `openai.max_tokens`: Default: `500`. The maximum number of tokens for GPT responses. Higher values make the bot more verbose, but you might start hitting the discord maximum message length.
- `openai.max_summary_tokens`: Default: `500`. Maximum number of tokens for the summary task.
- `openai.main_model`: Default: `gpt-4o-mini`. The primary model used for player interaction responses.
- `openai.summary_model`: Default: `gpt-4o`. The model used for the summarization task.
- `openai.max_attempts`: Default: `3`. The number of attempts for OpenAI API calls in case of failure.
- `openai.retry_delay`: Default: `5`. The exponential delay (in seconds) between attempts. So with the default the delay would be 5 seconds, 10, 20, 40...

### Gameplay Settings

- `game.max_previous_users`: Default: `1`. The number of turns a player must wait before acting again.
- `game.max_log_tokens`: Default: `50000`. The maximum number of tokens in the bot's log before triggering a summary.
- `game.dice`: Default `2d6`. The dice rolled when a player takes an action. `false` to disable rolling dice. If you change this, you should update `prompts.base` and maybe `game.dice_strings`, too.
- `game.dice_strings`: Default: `['⚀', '⚁', '⚂', '⚃', '⚄', '⚅']`. Strings that get sent representing dice roll results. You can replace these strings with Discord emoji codes for enhanced visuals. See the [Discord documentation on message formatting](https://discord.com/developers/docs/reference#message-formatting) for details.
- `game.max_lengths`: Configurable limits for character creation.
  - `name`: Default: `30`. Maximum length for character names.
  - `race`: Default: `20`. Maximum length for character races.
  - `class`: Default: `30`. Maximum length for character classes.
  - `pronouns`: Default: `15`. Maximum length for character pronouns.
- **Prompts:**
  - `prompts.base`: The primary prompt to guide the bot's behavior as a GM.
  - `prompts.summary`: The prompt when summarizing the adventure.
  - `prompts.summary_instruction`: The specific instruction to summarize the adventure.

### Files

- `files.game`: Default: `game_context.json`. The file where the bot's game state is saved.
- `files.backup_dir`: Default: `backups`. Directory where game context backups are stored.

## Experimental Features
- `experimental.image_generation`: Default: `false`. To enable, set to a dict of params to pass to openAI's [create image API](https://platform.openai.com/docs/api-reference/images/create). The scene description will be appended to `experimental.image_generation.prompt`. The extra value `experimental.image_generation.prompt_length` sets the maximum length of the combined prompt. When enabled, you can use the `!picture` admin command.

## Summarization

Summarization condenses the game log into a brief summary of the story so far. This helps the bot operate within the token limits of GPT models while maintaining story continuity. However, once summarization occurs, all detailed messages from the game log are replaced by the summary, and only the key points of the story remain. So there is a record of the lost information, the bot creates a backup of the game context before summarizing.

Once `context.max_log_token` is reached, the summary is created using `openai.summary_model`, `prompts.summary` and `prompts.summary_instruction`. Admins can also trigger this manually using the `!summarize` command.

Summaries are also sent to the channel as a recap for players.

## Contributing

### Issues

If you encounter any bugs or have feature suggestions, please open an issue with:

- A clear description of the problem.
- Steps to reproduce the issue.
- Any relevant logs or screenshots.

### Pull Requests

Thank you! Contributions are welcome. To submit a pull request:

1. Fork the repository.
2. Create a new branch for your changes.
3. Test your changes thoroughly.
4. Submit a pull request with a clear description of your updates.