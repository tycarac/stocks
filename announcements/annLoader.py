import csv
import logging
from pathlib import Path
from typing import List

from common.common import re_asx_shares_symbol

from announcements.annTypes import SharesAnnouncement

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
    def share_codes(self) -> List[SharesAnnouncement]:
        return self._symbols

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
                symbol = row[0].strip().upper()  # Assumes lines with no content have been filtered out
                if not (match := re_asx_shares_symbol.fullmatch(symbol)):
                    _logger.error(f'symbol {symbol} invalid')
                elif symbol in self._symbols:
                    _logger.error(f'Ignoring duplicate symbol {symbol} at line {csv_reader.line_num}')
                else:
                    self._symbols.append(SharesAnnouncement(match.group(1), 0, None))
