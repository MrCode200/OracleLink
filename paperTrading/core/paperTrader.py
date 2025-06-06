from paperTrading.models import Portfolio, OrderRequest, Position, TradeRecord
from paperTrading.enums import Side, Action
from apis.binanceApi import fetch_klines


class PaperTrader:
    def __init__(
        self, symbol: str, interval: str, limit: int,
        sleep_interval: int, initial_balance: float,
        strat: object,
    ):
        self.symbol = symbol
        self.interval = interval
        self.limit = limit
        self.sleep_interval = sleep_interval
        self.initial_balance = initial_balance
        self.strat = strat
        self.portfolio = Portfolio()


    def run(self):
        pass