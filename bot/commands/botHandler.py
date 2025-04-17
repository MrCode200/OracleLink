from telegram import Update
from telegram.ext import ContextTypes

import logging

logger = logging.getLogger("oracle.link")

async def log_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user = update.message.from_user.username or "unknown"
        text = update.message.text or "<no text>"
        command = text.split()[0] if text.startswith("/") else "<not a command>"

        logger.info(f"Command received from '{user}': '{text}'", extra={"command": command})
    else:
        logger.info(f"Unknown update type: {update}")
        context.user_data