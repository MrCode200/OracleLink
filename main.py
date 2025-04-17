from logging import DEBUG

from custom_logger import setup_logger
from bot import OracleLinkBot

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
        token = "7471067960:AAEVHls1fXUhds0puBk0TuK5KgSh5lQl_gc"
    )
    bot.run()

if __name__ == '__main__':
    main()