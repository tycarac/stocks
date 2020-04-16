from collections import Counter
import csv
from decimal import Decimal, getcontext, InvalidOperation
from io import StringIO
import json
import logging
import os
from pathlib import Path
from typing import Union, Sequence, List

from common.common import multisort, today
from common.metricPrefix import to_decimal_units

from announcements.annLoader import ValuesLoader
from announcements.annTypes import Announcement, Result, Outcome

_logger = logging.getLogger(__name__)

_PRICE_FORMAT_THRESHOLD = Decimal(1.0)
_PERCENT_FORMAT_THRESHOLD = Decimal(10.0)
_BLANK = f'{"":9s}'

_base_path = Path(Path(__file__).parent)
_output_base_path = Path(_base_path, 'output')
_output_base_path.mkdir(parents=True, exist_ok=True)


# _____________________________________________________________________________
def _make_backup_path(path: os.PathLike) -> Path:
    p = Path(path)
    return p.with_suffix('.bak' + p.suffix)


# _____________________________________________________________________________
def _outsym(symbol: str):
    return f'{symbol:6s}'


# _____________________________________________________________________________
def _outpercent(percent: Decimal):
    if percent:
        return f'{percent:8.1f} ' if percent >= _PERCENT_FORMAT_THRESHOLD else f'{percent:9.2f}'
    else:
        return f'{"":9s}'


# _____________________________________________________________________________
def _outn(number: int):
    return f'{number:9d}' if number else f'{"":9s}'


# _____________________________________________________________________________
def _outs(s: str):
    return f'{s:>9s}'


# _____________________________________________________________________________
def output_symbols(values: ValuesLoader):
    _logger.debug('output_symbols')

    with StringIO() as buf:
        buf.write(f'\n {"symbol":^6s}\n')
        for s in values.symbols:
            buf.write(f' {_outsym(s)}\n')
        print(buf.getvalue())


# _____________________________________________________________________________
def output_summary(recs: List[Announcement]):
    _logger.debug('build_summary')

    counter_outcome = Counter(map(lambda r: r.outcome, recs))
    counter_result = Counter(map(lambda r: r.result, recs))

    with StringIO() as buf:
        buf.write('Records:    %5d\n' % len(recs))
        buf.write('- Cached:   %5d\n' % counter_outcome[Outcome.cached])
        buf.write('- Created:  %5d\n' % counter_outcome[Outcome.created])
        # buf.write('- Updated:  %5d\n' % counter_outcome[Outcome.updated])
        buf.write('- Nil:      %5d\n' % counter_outcome[Outcome.nil])
        buf.write('  Archived: %5d\n' % counter_outcome[Outcome.archived])
        buf.write('  Deleted:  %5d\n' % counter_outcome[Outcome.deleted])
        buf.write('Results\n')
        buf.write('- Warnings: %5d\n' % counter_result[Result.warning])
        buf.write('- Errors:   %5d\n' % counter_result[Result.error])
        buf.write('- Nil:      %5d\n' % counter_result[Result.nil])
        print(buf.getvalue())


# _____________________________________________________________________________
def write_report(recs: List[Announcement]):
    report_fp = Path(_output_base_path, 'report.csv').resolve()
    _logger.debug(f'write_report "{report_fp.name}"')

    # Backup report
    if report_fp.exists():
        backup_fp = _make_backup_path(report_fp)
        try:
            backup_fp.write_text(report_fp.read_text())
        except PermissionError:
            _logger.warning(f'Cannot write to backup "{backup_fp.name}"')

    # Write report
    try:
        with report_fp.open(mode='w', newline='') as out:
            csv_writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL)
            row = ['symbol', 'date', 'time', 'title', 'is price sensitive', 'num pages', 'file size',
                        'outcome', 'result']
            csv_writer.writerow(row)
            for r in recs:
                row = [r.symbol, r.date_time.strftime('%d-%m-%y'), r.date_time.strftime('%H:%M'), r.title,
                    r.is_price_sensitive, r.num_pages, r.file_size, r.outcome.name, r.result.name]
                csv_writer.writerow(row)
    except PermissionError:
        _logger.error(f'Cannot write to "{report_fp.name}"')
        raise
