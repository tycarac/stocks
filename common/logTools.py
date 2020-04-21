"""

Notes:
- The logging Formatter formats an exception as a string and caches it.  The first Logging handler does the exception
formating and caching.  Subsequent calls to logging handlers use the same cached exception text.  The cached exception
string is stored in LogRecord record.exec_text and must be cleared if a different exception format is required.  Thus
custom logging formatters should be added after standard Logging formatters.
"""
import logging
import logging.config
from os import environ, PathLike
from pathlib import Path
from sys import exc_info, stdout

_logger = logging.getLogger(__name__)


# _____________________________________________________________________________
def initialize_logger(logger_dp: PathLike, log_basename: str):
    Path(logger_dp).mkdir(parents=True, exist_ok=True)

    console_formatter = logging.Formatter(fmt='%(msg)s')
    context_formatter = logging.Formatter(fmt='%(levelname)-6s %(msg)s')

    console_handler = logging.StreamHandler(stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    console_handler.addFilter(lambda r: not r.name.startswith('urllib'))

    output_fp = Path(logger_dp, log_basename).with_suffix('.log')
    output_handler = PathFileHandler(output_fp, mode='w')
    output_handler.setFormatter(context_formatter)
    output_handler.setLevel(logging.INFO)
    console_handler.addFilter(lambda r: not r.name.startswith('urllib'))

    debug_fp = Path(logger_dp, log_basename).with_suffix('.debug.log')
    debug_handler = PathFileHandler(debug_fp, mode='w')
    debug_handler.setFormatter(context_formatter)
    debug_handler.setLevel(logging.DEBUG)

    root = logging.getLogger()
    root.propagate = False
    root.setLevel(environ.get('LOGLEVEL', logging.DEBUG))
    root.addHandler(output_handler)
    root.addHandler(debug_handler)
    root.addHandler(console_handler)

    logging.captureWarnings(True)
    _logger.debug(f'initialize_logger "{log_basename}" "{logger_dp}"')


# _____________________________________________________________________________
class NoExceptionFormatter(logging.Formatter):
    """Remove exception details from logger formatter so to declutter log output
    """
    def format(self, record: logging.LogRecord):
        record.exc_text = ''
        return super().format(record)

    def formatException(self, ei: exc_info):
        return ''


# _____________________________________________________________________________
class MessageFormatter(logging.Formatter):
    """Remove all exception details from logger formatter except for message so to declutter log output
    """
    def format(self, record: logging.LogRecord):
        record.exc_text = ''
        return super().format(record)

    def formatException(self, ei: exc_info):
        lei = (ei[0], ei[1], None)
        return repr(super().formatException(lei))


# _____________________________________________________________________________
class OneLineFormatter(logging.Formatter):
    """Covert exception details to single line to simplify log output processing
    """
    def format(self, record: logging.LogRecord):
        if text := super().format(record):
            text = text.strip().replace('\n', '|')
        return text

    def formatException(self, exc_info):
        result = super().formatException(exc_info)
        return repr(result)


# _____________________________________________________________________________
class PathFileHandler(logging.FileHandler):
    """Extends FileHandler to create the directory, if required, for the log file.

    Note this has some security risk as the file path is arbitrary and could be any location.
    """
    def __init__(self, filename, mode='a', encoding=None, delay=False):
        Path.mkdir(Path(filename).parent, parents=True, exist_ok=True)
        super().__init__(filename, mode, encoding, delay)
