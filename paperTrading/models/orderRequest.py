from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4

from paperTrading.enums import Side, Action


@dataclass
class OrderRequest:
    """
    :param uuid: universally unique identifier (uuid.uuid4())
    :param symbol: e.g. "BTCUSDT"
    :param timestamp: unix timestamp, timezone is UTC

    :param confidence: confidence level (-1.0 to 1.0) where -1 = max sell, 0 = neutral, +1 = max buy, can be of type float

    :param price: price for limit orders, if none will buy/sell at current price
    :param side: Side.LONG or Side.SHORT
    :param action: Action.SELL or Action.BUY
    :param qty: quantity in base units, if none the Simulator will decide

    :param stop_loss: the price where the stop loss should be placed
    :param take_profit: the price where the take profit should be placed
    """
    symbol: str
    timestamp: float

    confidence: float

    price: Optional[float] = None
    side: Side = Side.LONG
    action: Action = Action.BUY
    qty: Optional[float] = None

    uuid: UUID = field(default_factory=uuid4)

    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
