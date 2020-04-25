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
        def strip_csv(iterator):
            for ln in iterator:
                # Skip lines with no content for start wth comment char '#'
                if (ln := ln.strip()) and ln[0] != '#':
                    yield ln

        with self._symbols_fp.open(mode='r', newline='') as fp:
            csv_reader = csv.reader(strip_csv(fp), quoting=csv.QUOTE_MINIMAL)
            next(csv_reader, None)  # skip csv header

            for row in csv_reader:
                row = [r.strip() for r in row]
                if len(row) > 0 and (symbol := row[0].upper()):
                    if not (match := re_yahoo_symbol.fullmatch(symbol)):
                        _logger.error(f'symbol {symbol} invalid')
                        continue
                    if symbol not in self._symbols:
                        self._symbols.append(match.group(1))
                    else:
                        _logger.error(f'Ignoring duplicate symbol {symbol} at line {csv_reader.line_num}')
                    if len(row) > 1 and (value := row[1]):
                        try:
                            self._alert_lows[symbol] = Decimal(value).quantize(config.quant)
                        except InvalidOperation:
                            _logger.error(f'symbol {symbol} has invalid low {value}')
                    if len(row) > 2 and (value := row[2]):
                        try:
                            self._alert_highs[symbol] = Decimal(value).quantize(config.quant)
                        except InvalidOperation:
                            _logger.error(f'symbol {symbol} has invalid high {value}')
                    if len(row) > 3 and (value := row[3]):
                        try:
                            self._price_refs[symbol] = Decimal(value).quantize(config.quant)
                        except InvalidOperation:
                            _logger.error(f'symbol {symbol} has invalid reference {value}')
