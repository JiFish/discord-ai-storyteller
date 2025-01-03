import os
from config import config

# Ensure the directory adventure_logs/ is created when imported
log_dir = config['files']['adventure_logs']
logging_enabled = bool(log_dir)

if logging_enabled and not os.path.exists(log_dir):
    os.makedirs(log_dir)

current_log_path = None

def set_log_name(log_name):
    global current_log_path
    if logging_enabled:
        # Make filename safe
        log_file_name = "".join(c for c in log_name if c.isalnum() or c in (' ','-','_')).rstrip()
        current_log_path = os.path.join(log_dir, f"{log_file_name}.md")

def _append_to_log(content):
    if current_log_path is None:
        raise ValueError("Log name is not set. Call set_log_name() first.")
    with open(current_log_path, "a", encoding="utf-8") as log_file:
        log_file.write(content + "\n\n")

def rename_log(new_log_name):
    global current_log_path
    if logging_enabled:
        if current_log_path is None:
            raise ValueError("Log name is not set. Call set_log_name() first.")
        new_log_path = os.path.join(log_dir, f"{new_log_name}.md")
        os.rename(current_log_path, new_log_path)
        current_log_path = new_log_path

def add_storyteller(quote):
    if logging_enabled:
        # Add "> " before each line in quote
        quote = "\n".join([f"> {line}" for line in quote.split("\n")])
        _append_to_log(quote)

def add_quote(speaker, quote):
    if logging_enabled:
        content = f"#### {speaker}\n{quote}"
        _append_to_log(content)

def add_action(action_text):
    if logging_enabled:
        content = f"_{action_text}_"
        _append_to_log(content)
