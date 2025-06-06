from dataclasses import dataclass, field

from paperTrading.models import TradeRecord, Position


@dataclass
class Portfolio:
    positions: list[Position] = field(default_factory=list)
    trade_records: list[TradeRecord] = field(default_factory=list)

    def __post_init__(self):
        self.positions = []
        self.trade_records = []

    def add_position(self, position):
        self.positions.append(position)

    def close_position(self, position: Position, closed_at_price: float):
        closed_position = self.positions.pop(self.positions.index(position))
        self.trade_records.append(TradeRecord.from_position(closed_position, closed_at_price=closed_at_price))

    def create_xml(self):
        pass