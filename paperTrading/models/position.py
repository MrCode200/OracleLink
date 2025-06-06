from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID, uuid4

from paperTrading.enums import Side, Action

@dataclass
class Position:
    """
    :param uuid: universally unique identifier (uuid.uuid4())
    :param symbol: e.g. "BTCUSDT"
    :param timestamp: unix timestamp at which the asset was bought, timezone is UTC

    :param confidence: confidence level of the OrderRequest (-1.0 to 1.0) where -1 = max sell, 0 = neutral, +1 = max buy

    :param price: price at which the asset was bought
    :param side: Side.LONG or Side.SHORT
    :param action: Action.SELL or Action.BUY
    :param qty: quantity of the asset

    :param stop_loss: the price where the stop loss is placed
    :param take_profit: the price where the take profit is placed
    """
    symbol: str
    timestamp: float

    confidence: float

    price: float
    side: Side
    action: Action
    qty: float

    uuid: UUID = field(default_factory=uuid4)

    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None