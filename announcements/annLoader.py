import csv
import logging
from pathlib import Path
from typing import Set, List

from common.common import re_yahoo_symbol

_logger = logging.getLogger(__name__)


# _____________________________________________________________________________
class ValuesLoader:

    # _____________________________________________________________________________
    def __init__(self, symbols_fp: Path):
        self._symbols = list()

        self._symbols_fp = symbols_fp
        self.__read()

    # _____________________________________________________________________________
    @property
    def symbols(self) -> List[str]:
        return self._symbols

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
