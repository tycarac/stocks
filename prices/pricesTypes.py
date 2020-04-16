from dataclasses import dataclass
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum
import logging
from typing import List, Any

_logger = logging.getLogger(__name__)


# _____________________________________________________________________________
# Records
@dataclass
class Record:
    __slots__ = ['symbol', 'price', 'low', 'high', 'bid', 'ask', 'ref', 'refToPrice', 'alertLow', 'alertHigh', 'volume', 'date', 'time', 'name']

    symbol: str
    price: Decimal
    low: Decimal
    high: Decimal
    bid: Decimal
    ask: Decimal
    ref: Decimal
    refToPrice: Decimal
    alertLow: Decimal
    alertHigh: Decimal
    volume: int
    date: date
    time: time
    name: str

    # _____________________________________________________________________________
    def to_list(self) -> List[Any]:
        return [self.symbol, self.price, self.low, self.high, self.bid, self.ask,
                    self.ref, self.refToPrice, self.alertLow, self.alertHigh, self.volume,
                    self.date.strftime('%d-%m-%y'), self.time.strftime('%H:%M'), self.name]


# _____________________________________________________________________________
# Alerts
class AlertType(Enum):
    high = 'High',
    low = 'Low'


@dataclass
class Alert:
    __slots__ = ['symbol', 'alertType', 'price', 'alertTrigger', 'refToPrice', 'ref']

    symbol: str
    alertType: AlertType
    price: Decimal
    alertTrigger: Decimal
    refToPrice: Decimal
    ref: Decimal

    # _____________________________________________________________________________
    def to_list(self) -> List[Any]:
        return [self.symbol, self.alertType.name, self.price, self.alertTrigger, self.refToPrice, self.ref]

