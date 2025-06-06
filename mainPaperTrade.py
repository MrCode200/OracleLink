from logging import DEBUG

from custom_logger import setup_logger
from paperTrading import PaperTrader


def main():
    setup_logger(
        'oracle.link',
        DEBUG,
        './logs/bot.jsonl',
        log_in_json=False,
        stream_in_color=True,
        extra_log_args=['command'],
    )

    pt = PaperTrader(
        symbol = input('Enter symbol: '),
        interval = input('Enter interval: '),
        limit = int(input('Enter limit: ')),
        sleep_interval = int(input('Enter sleep interval: ')),
        initial_balance = float(input('Enter initial balance: ')),
        strat = ...,
    )
    pt.run()

if __name__ == '__main__':
    main()