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
        token = "7749426469:AAF40HNdDQU_79FfqzsAUUNsTEUnswRLtDY"
    )
    bot.run()

if __name__ == '__main__':
    main()