from logging import DEBUG

from custom_logger import setup_logger
from paperTrading import PaperTrader


def main():
    setup_logger(
        'oracle.link',
        DEBUG,
        './logs/paperTrade.jsonl',
        log_in_json=False,
        stream_in_color=True,
        extra_log_args=["open_timestamp"],
    )

    pt = PaperTrader(
        symbol = input('Enter symbol: '),
        interval = input('Enter interval: '),
        limit = int(input('Enter limit: ')),
        risk_per_position = float(input('Enter risk per position (%): ')),
        seconds_to_sleep= int(input('Enter sleep interval: ')),
        initial_balance = float(input('Enter initial balance: ')),
        leverage = float(input('Enter leverage: ')),
        stop_loss= float(input('Enter stop loss (%): ')),
        take_profit= float(input('Enter take profit (%): ')),
        buy_conf_threshold= float(input('Enter buy confidence threshold (0 to 1): ')),
        sell_conf_threshold= float(input('Enter sell confidence threshold (-1 to 0): ')),
        strat = ...,
    )
    pt.run()

if __name__ == '__main__':
    main()