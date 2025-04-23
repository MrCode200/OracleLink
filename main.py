from logging import DEBUG
import os

from dotenv import load_dotenv

from custom_logger import setup_logger
from bot import OracleLinkBot

load_dotenv(dotenv_path='.env.secret')

token: str = os.getenv("TEL_BOT_TOKEN")

def main():
    setup_logger(
        'oracle.link',
        DEBUG,
        './logs/bot.jsonl',
        log_in_json=False,
        stream_in_color=True,
        extra_log_args=['command'],
    )

    bot = OracleLinkBot(
        token = token
    )
    bot.run()

if __name__ == '__main__':
    main()