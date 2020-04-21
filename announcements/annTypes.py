from dataclasses import dataclass
from datetime import datetime, date, time
from enum import Enum
import logging
from pathlib import Path


_logger = logging.getLogger(__name__)


# _____________________________________________________________________________
# Enums
class Outcome(Enum):
    nil = 'Nil',
    cached = 'Cached',
    created = 'Created',
    updated = 'Updated',
    deleted = 'Deleted',
    archived = 'Archived'


class Result(Enum):
    nil = 'Nil',
    success = 'Success',
    warning = 'Warning',
    error = 'Error'


# _____________________________________________________________________________
@dataclass
class Announcement:
    __slots__ = ['symbol', 'date_time', 'title', 'is_price_sensitive', 'num_pages', 'file_size',
                'href', 'filepath', 'file_type', 'outcome', 'result']

    symbol: str
    date_time: datetime
    title: str
    is_price_sensitive: bool
    num_pages: int
    file_size: str
    href: str
    filepath: Path
    file_type: str
    outcome: Outcome
    result: Result


# _____________________________________________________________________________
@dataclass
class Deleted:
    __slots__ = ['symbol', 'file_date', 'filename', 'filepath', 'outcome', 'result']
    symbol: str
    file_date: date
    filename: str
    filepath: Path
    outcome: Outcome
    result: Result
