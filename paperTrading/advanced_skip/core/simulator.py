import time

import pandas as pd
from datetime import datetime, timezone
from typing import List, Optional
import math
import uuid

from paperTrading.advanced_skip.models import Portfolio, Position, TradeAdvice, Order
from paperTrading.advanced_skip.enums import Side, OrderType


class Simulator:
    """
    A simple backtesting/paper-trading engine. It:
      - Expects a DataFrame of OHLCV bars (with a datetime index or 'Open Time' column).
      - A single StrategyBase instance (or multiple, with aggregator).
      - Simulates order execution on the next bar’s open.
      - Tracks Portfolio over time.
    """

    def __init__(
        self,
        initial_balance: float,
        strategy: object,
        fee_rate: float = 0.00075,
        confidence_percentage_qty: bool = False,
        min_size: float = 0.0,
        slippage: float = 0.0,
    ):
        """
        :param initial_balance: Starting account equity (e.g. 10000 USD).
        :param strategy: A single strategy instance (subclass of StrategyBase).
        :param fee_rate: Proportional fee (e.g. 0.00075 = 0.075% per trade side).
        :param min_size: Minimum trade size (if some strategies return tiny signals, you can skip).
        :param slippage: Proportional slippage (e.g. 0.0005 for 0.05%).
        """
        self.portfolio = Portfolio(balance=initial_balance)
        self.strategy = strategy
        self.fee_rate = fee_rate
        self.min_size = min_size
        self.slippage = slippage
        self.confidence_percentage_qty = confidence_percentage_qty
        self.pending_orders: List[Order] = []

    def _create_order_from_advice(
        self, advice: TradeAdvice, timestamp: datetime, current_price: float
    ) -> Optional[Order]:
        """
        Translate a TradeAdvice into an Order. If advice.conf is near zero or advice.qty < min_size,
        return None.
        """
        conf = advice.confidence
        if abs(conf) < 1e-6:
            return None

        side = Side.BUY if conf > 0 else Side.SELL

        qty = advice.qty
        if qty is None:
            if side == Side.BUY:
                budget = self.portfolio.balance * abs(conf) if self.confidence_percentage_qty else self.portfolio.balance
                qty = math.floor(budget / current_price * 1000000) / 1000000 # truncate to 6 decimal places
            else:
                budget = self.portfolio.balance * abs(conf)
                qty = math.floor(budget / current_price * 1000000) / 1000000 # truncate to 6 decimal places

        if qty < self.min_size or qty <= 0:
            return None

        oid = str(uuid.uuid4())
        return Order(
            id=oid,
            symbol=advice.symbol,
            side=side,
            qty=qty,
            order_type=advice.order_type,
            timestamp=timestamp,
            price=advice.price,
            stop_price=advice.stop_price,
        )

    def _apply_fees_and_slippage(self, price: float, side: Side) -> float:
        """
        Returns the effective execution price after fees & slippage.
        - slippage: e.g. buy: price * (1 + slippage); sell: price * (1 – slippage).
        - fee: proportional on notional: deduct from balance separately.
        """
        if side == Side.BUY:
            price_ex = price * (1 + self.slippage)
        else:
            price_ex = price * (1 - self.slippage)
        return price_ex

    def _execute_order(
        self, order: Order, next_open: float, timestamp: datetime
    ):
        """
        “Fill” the order at next bar’s open price (with slippage & fee).
        - For a market buy:
            execution_price = _apply_fees_and_slippage(next_open, BUY)
            cost = execution_price * qty
            fee = cost * fee_rate
            actual balance deduction = cost + fee
          Then open a new Position.
        - For a market sell (i.e. close LONG or open new SHORT if no existing position),
          similar logic.
        """
        # Determine execution price
        exec_price = self._apply_fees_and_slippage(next_open, order.side)
        notional = exec_price * order.qty
        fee = notional * self.fee_rate

        # If side=BUY, opening a new long (or adding). If side=SELL:
        #   - if we have existing long(s), should we close? Here we assume each Order
        #     always opens a brand‐new position (so you could go short while long,
        #     but for simplicity we close any opposing first).
        # This can be altered to “netting” logic: check if there is an opposite position.
        # For clarity, let’s assume “each Order is independent” → a BUY always opens a LONG,
        # a SELL always opens a SHORT.
        # If you want to net positions, you need to inspect portfolio.positions.

        # Construct new Position
        pos_id = str(uuid.uuid4())
        new_pos = Position(
            id=pos_id,
            symbol=order.symbol,
            side=order.side,
            entry_price=exec_price,
            qty=order.qty,
            entry_timestamp=timestamp,
            stop_loss=order.stop_price or None,
            take_profit=None,  # if advice included take_profit, we’d pass it through
        )
        # But note: if advice.take_profit was provided, we’d want:
        # new_pos.take_profit = advice.take_profit

        # Update portfolio balance
        if order.side == Side.BUY:
            total_cost = notional + fee
            self.portfolio.balance -= total_cost
        else:  # SELL: proceeds – fee
            proceeds = notional - fee
            self.portfolio.balance += proceeds

        # Finally add position
        self.portfolio.positions.append(new_pos)

    def _check_position_exits(self, bar: pd.Series):
        """
        Check all open positions against this bar’s high/low to see if stop‐loss or take‐profit triggers.
        If hit, close the position at the trigger price (ignore partial fills).
        Order of checking: stops first, then take‐profit (or vice versa, up to you).
        Example:
          - If LONG and bar['Low'] <= stop_loss <= bar['High'], close at stop_loss.
          - If LONG and bar['High'] >= take_profit, close at take_profit.
          - Similarly for SHORT.
        """
        to_close = []
        for pos in list(self.portfolio.positions):
            side = pos.side
            low = float(bar["Low"])
            high = float(bar["High"])
            ts = pd.to_datetime(bar["Open Time"]) if "Open Time" in bar else bar.name

            exit_price = None
            # Check LONG stop‐loss
            if side == Side.BUY and pos.stop_loss is not None:
                if low <= pos.stop_loss <= high:
                    exit_price = pos.stop_loss

            # Check LONG take‐profit
            if side == Side.BUY and pos.take_profit is not None:
                if high >= pos.take_profit:
                    # If both stop and TP hit in same bar, decide priority: e.g. stop first?
                    # For simplicity, assume whichever occurred first. Here we pick:
                    exit_price = pos.take_profit

            # Check SHORT stop‐loss (i.e. price moving against you)
            if side == Side.SELL and pos.stop_loss is not None:
                if low <= pos.stop_loss <= high:
                    exit_price = pos.stop_loss

            # Check SHORT take‐profit (price moving in your favor)
            if side == Side.SELL and pos.take_profit is not None:
                if low <= pos.take_profit <= high:
                    exit_price = pos.take_profit

            if exit_price is not None:
                to_close.append((pos, exit_price, ts))

        # Close all triggered in this bar
        for pos, price, ts in to_close:
            self.portfolio.close_position(pos, exit_price=price, exit_timestamp=ts)

    def run_backtest(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "Open Time",
        price_col: str = "Open",
    ):
        """
        Main loop. Expects df to be sorted by timestamp ascending.
        :param df: DataFrame with columns at least ['Open Time','Open','High','Low','Close', …].
        :param timestamp_col: used to record equity timestamps.
        :param price_col: we execute all pending orders at next bar’s `price_col`.
        """
        df = df.reset_index(drop=True).copy()
        n = len(df)

        for i in range(n - 1):
            print(f"Processing bar {i} of {n}")
            row = df.iloc[i]
            next_row = df.iloc[i + 1]

            # 1. Let the strategy evaluate on data up to row i
            history = df.iloc[: i + 1]  # inclusive of current
            ts = pd.to_datetime(row[timestamp_col])
            last_close = float(row["Close"])

            conf = self.strategy.evaluate(history) # should return advice directly
            advice = TradeAdvice(
                confidence=conf,
                symbol = "",
                order_type=OrderType.MARKET
            )

            order = self._create_order_from_advice(
                advice, timestamp=ts, current_price=last_close
            )
            if order:
                self.pending_orders.append(order)

            # 2. Execute any pending orders at next bar’s open
            exec_price = float(next_row[price_col])
            exec_time = pd.to_datetime(next_row[timestamp_col])
            for ord_ in self.pending_orders:
                self._execute_order(ord_, exec_price, exec_time)
            self.pending_orders.clear()

            # 3. Check if any existing open positions get stopped or take‐profited in this bar
            self._check_position_exits(row)

            # 4. Record equity at current bar’s close (i.e. mark‐to‐market)
            equity = self.portfolio.total_equity(last_close)
            self.portfolio.equity_curve.append((ts, equity))

        # Handle the very last bar’s equity (since loop goes to n-2)
        final_ts = pd.to_datetime(df.iloc[-1][timestamp_col])
        final_close = float(df.iloc[-1]["Close"])
        self.portfolio.record_equity(final_ts, final_close)

        return self.portfolio


    def run_live(
        self,
        symbol: str,
        starting_limit: int = 100,
        timestamp_col: str = "Open Time",
        price_col: str = "Open",
        cooldown_sec: int = 1
    ):
        timeframe = '1m'

        df: pd.DataFrame = fetch_klines(symbol=symbol, interval=timeframe, limit=starting_limit)

        while True:
            time.sleep(cooldown_sec)

            latest_candle = fetch_klines(symbol=symbol, interval=timeframe, limit=1)
            if latest_candle.index[-1] != df.index[-1]:
                df.iloc[-1] = latest_candle

            conf = self.strategy.evaluate(df) # TODO: should return advice directly
            advice = TradeAdvice(
                confidence=conf,
                symbol = "",
                order_type=OrderType.MARKET
            )

            order = self._create_order_from_advice(
                advice, timestamp=datetime.now(tz=timezone.utc), current_price=float(df.iloc[-1][price_col])
            )

            if order:
                self.pending_orders.append(order)

            for ord_ in self.pending_orders:
                self._execute_order(ord_, float(df.iloc[-1][price_col]), datetime.now(tz=timezone.utc))
            self.pending_orders.clear()


if __name__ == '__main__':
    from tradingComponents.strategies import ShadowsTrendingTouch
    from apis.binanceApi.fetcher import fetch_klines

    strat = ShadowsTrendingTouch(
        sma_period = 7,
        shadow_to_body_ratio = 1.25,
        shadow_multiplier = 1,
        opposite_shadow_to_body_ratio_limit = 0.25,
        ignore_sma_touch = False
    )

    sim = Simulator(
        initial_balance = 10000,
        strategy = strat,
        fee_rate = 0.00075,
        min_size = 0.0,
        slippage = 0.0
    )

    df = fetch_klines(symbol='BTCUSDT', interval='1m', limit=100)

    result = sim.run_backtest(
        df=df,
        timestamp_col='Close Time',
    )

    print(result.equity_curve)