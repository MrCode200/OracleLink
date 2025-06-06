from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from apis.binanceApi import fetch_klines
from paperTrading.enums import Side, Action
from paperTrading.models import Position


@dataclass
class TradeRecord:
    """
    :param uuid: universally unique identifier (uuid.uuid4())
    :param symbol: e.g. "BTCUSDT"
    :param entry_timestamp: unix timestamp at which the asset was bought, timezone is UTC
    :param exit_timestamp: unix timestamp at which the asset was sold, timezone is UTC

    :param confidence: confidence level (-1.0 to 1.0) where -1 = max sell, 0 = neutral, +1 = max buy

    :param entry_price: price at which the asset was bought
    :param side: Side.LONG or Side.SHORT
    :param action: Action.SELL or Action.BUY
    :param qty: quantity in base units, if none the Simulator will decide

    :param pnl: profit/loss in quote currency

    :param stop_loss: stop loss if used
    :param take_profit: take profit if used
    """
    symbol: str
    entry_timestamp: float
    exit_timestamp: float

    confidence: float

    entry_price: float
    side: Side
    action: Action
    qty: float

    pnl: float

    uuid: UUID = field(default_factory=uuid4)

    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    @classmethod
    def from_position(cls, position: Position, pnl: Optional[float] = None, closed_at_price: Optional[float] = None) -> "TradeRecord":
        """
        Creates a TradeRecord from a Position

        :param position: A Position
        :param pnl: If None will be calculated from closed_at_price
        :param closed_at_price: Price at which the asset was sold
        :return: A TradeRecord object
        """
        if pnl is None and closed_at_price is None:
            raise ValueError("Either pnl or closed_at_price must be provided")

        if pnl is None:
            if position.side == Side.LONG:
                pnl = (closed_at_price - position.price) * position.qty
            else:
                pnl = (position.price - closed_at_price) * position.qty

        return cls(
            uuid=position.uuid,

            symbol=position.symbol,
            entry_timestamp=position.timestamp,
            exit_timestamp=datetime.now().timestamp(),

            confidence=position.confidence,

            entry_price=position.price,
            side=position.side,
            action=position.action,
            qty=position.qty,

            pnl=pnl,

            stop_loss=position.stop_loss,
            take_profit=position.take_profit
        )
