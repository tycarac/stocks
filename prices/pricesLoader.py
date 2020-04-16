import csv
from decimal import Decimal, InvalidOperation
import logging
from pathlib import Path
from typing import List

from common.common import re_yahoo_symbol
import prices.pricesConfig as config

_logger = logging.getLogger(__name__)


# _____________________________________________________________________________
class ValuesLoader:

    # _____________________________________________________________________________
    def __init__(self, symbols_fp: Path):
        self._symbols = list()
        self._alert_lows = dict()
        self._alert_highs = dict()
        self._price_refs = dict()

        self._symbols_fp = symbols_fp
        self.__read()

    # _____________________________________________________________________________
    @property
    def symbols(self) -> List[str]:
        return self._symbols

    # _____________________________________________________________________________
    def alert_low(self, symbol: str) -> Decimal:
        return self._alert_lows.get(symbol, None)

    # _____________________________________________________________________________
    def alert_high(self, symbol: str) -> Decimal:
        return self._alert_highs.get(symbol, None)

    # _____________________________________________________________________________
    def price_ref(self, symbol: str) -> Decimal:
        return self._price_refs.get(symbol, None)

    # _____________________________________________________________________________
    def __read(self):
        with self._symbols_fp.open(mode='r', newline='') as fp:
            csv_reader = csv.reader(filter(lambda r: r.strip() and r[0] != '#', fp), quoting=csv.QUOTE_MINIMAL)
            next(csv_reader, None)  # skip csv header

            for line in csv_reader:
                if line and (symbol := line[0].strip().upper()):
                    if not (match := re_yahoo_symbol.fullmatch(symbol)):
                        _logger.error(f'symbol {symbol} invalid')
                        continue
                    if symbol not in self._symbols:
                        self._symbols.append(match.group(1))
                    else:
                        _logger.error(f'Ignoring duplicate symbol {symbol} at line {csv_reader.line_num}')
                    if len(line) > 1 and (value := line[1].strip()):
                        try:
                            self._alert_lows[symbol] = Decimal(value).quantize(config.quant)
                        except InvalidOperation:
                            _logger.error(f'symbol {symbol} has invalid low {value}')
                    if len(line) > 2 and (value := line[2].strip()):
                        try:
                            self._alert_highs[symbol] = Decimal(value).quantize(config.quant)
                        except InvalidOperation:
                            _logger.error(f'symbol {symbol} has invalid high {value}')
                    if len(line) > 3 and (value := line[3].strip()):
                        try:
                            self._price_refs[symbol] = Decimal(value).quantize(config.quant)
                        except InvalidOperation:
                            _logger.error(f'symbol {symbol} has invalid reference {value}')
