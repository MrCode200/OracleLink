import logging

logger = logging.getLogger("oracle.link")

command_descriptions = {}


async def help_command(update, context):
    commands_list = []
    for cmd, desc in command_descriptions.items():
        commands_list.append(f"/{cmd} - {desc}")
    
    message = "🚀 Crypto Trading Bot Commands\n\n"
    message += "\n".join(sorted(commands_list))
    
    await update.message.reply_text(message)
