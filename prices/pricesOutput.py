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
from .pricesLoader import ValuesLoader
from .pricesTypes import Alert, AlertType, Record

_logger = logging.getLogger(__name__)

_PRICE_FORMAT_THRESHOLD = Decimal(1.0)
_PERCENT_FORMAT_THRESHOLD = Decimal(10.0)
_BLANK = f'{"":9s}'

_base_path = Path(Path(__file__).parent)
_data_base_path = Path(_base_path, 'data')
_data_base_path.mkdir(parents=True, exist_ok=True)


# _____________________________________________________________________________
def _make_backup_path(path: os.PathLike) -> Path:
    p = Path(path)
    return p.with_suffix('.bak' + p.suffix)


# _____________________________________________________________________________
def _outsym(symbol: str):
    return f'{symbol:6s}'


# _____________________________________________________________________________
def _fmtp(prices: Sequence[Decimal], ref=None) -> Sequence[str]:
    """Returns transformed sequence of decimal prices as formatted strings with two/three decimal places
    by testing if reference number is less than threshold
    """
    if prices is None:
        raise ValueError('prices')
    if not ref and len(prices):
        ref = prices[0]

    if ref >= _PRICE_FORMAT_THRESHOLD:
        return list(map(lambda p: f'{p:8.2f} ' if p else _BLANK, prices))
    else:
        return list(map(lambda p: f'{p:9.3f}' if p else _BLANK, prices))


# _____________________________________________________________________________
def _outp(price: Decimal):
    if price:
        return f'{price:8.2f} ' if price >= _PRICE_FORMAT_THRESHOLD else f'{price:9.3f}'
    else:
        return f'{"":9s}'


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
        buf.write(f'\n {"symbol":^6s} | {"low":^9s}   {"high":^9s}   {"ref":^9s}\n')
        for i, s in enumerate(values.symbols, 1):
            buf.write(f' {_outsym(s)} | {_outp(values.alert_low(s))}   {_outp(values.alert_high(s))}'
                      f'   {_outp(values.price_ref(s))}\n')
            if i % 4 == 0:
                buf.write('\n')
        print(buf.getvalue())


# _____________________________________________________________________________
def output_alerts(alerts: List[Alert]):
    _logger.debug('output_alerts')

    if not alerts:
        return
    with StringIO() as buf:
        buf.write('\n')
        for i, a in enumerate(alerts, 1):
            buf.write(f'ALERT {a.alertType.name.upper():<5s}: {a.symbol}  price {_outp(a.price)}  '
                      f'for {_outp(a.alertTrigger)}')
            if i % 4 == 0:
                buf.write('\n')
        print(buf.getvalue())


# _____________________________________________________________________________
def output_prices(recs: List[Record], symbols: List[str] = None):
    _logger.debug('output_prices')

    if not recs:
        return
    if symbols:
        recs = sorted(recs, key=lambda x: symbols.index(x.symbol))
    with StringIO() as buf:
        buf.write(f'\n {"symbol":^6s} | {"price":^9s}   {"low":^9s}   {"high":^9s}   {"ask":^9s}   {"buy":^9s}'
                  f'  | {"volume":^9s}\n')
        for i, r in enumerate(recs, 1):
            prices = _fmtp([r.price, r.low, r.high, r.ask, r.bid], r.low)
            buf.write(f' {_outsym(r.symbol)} | {prices[0]}   {prices[1]}   {prices[2]}'
                      f'   {prices[3]}    {prices[4]} | {_outs(to_decimal_units(r.volume))}\n')
            if i % 4 == 0:
                buf.write('\n')
        print(buf.getvalue())


# _____________________________________________________________________________
def output_brief(recs: List[Record]):
    _logger.debug('output_brief')

    if not recs:
        return
    recs = multisort(recs, ((lambda x: abs(x.refToPrice) if x.refToPrice else Decimal(0.0), True),
                (lambda y: y.symbol, False)))
    with StringIO() as buf:
        buf.write(f'\n {"symbol":^6s} | {"price":^9s}   {"% ref":^9s}   {"ref":^9s} | {"L alert":^9s}'
                  f'   {"H alert":^9s}\n')
        for i, r in enumerate(recs, 1):
            buf.write(f' {_outsym(r.symbol)} | {_outp(r.price)}   {_outpercent(r.refToPrice)}   {_outp(r.ref)}'
                      f' | {_outp(r.alertLow)}   {_outp(r.alertHigh)}\n')
            if i % 4 == 0:
                buf.write('\n')
        print(buf.getvalue())


# _____________________________________________________________________________
def write_json(data: Union[str, bytes], basename: str):
    data_fp = Path(_data_base_path, f'{basename}.data-{today.strftime("%Y-%m-%d")}.json').resolve()
    _logger.debug(f'write_json "{data_fp.name}"')

    data_json = None
    try:
        data_json = json.loads(data.decode('utf-8') if isinstance(data, bytes) else data)
        data_fp.write_text(json.dumps(data_json, sort_keys=True, indent=2))
    except PermissionError:
        _logger.error(f'Cannot write to "{data_fp.name}"')
        raise
    except (json.JSONDecodeError, UnicodeError, OSError):
        path = data_fp.with_suffix('.raw.json')
        _logger.exception(f'JSON parse error: {path.name}')
        path.write_bytes(data)

    return data_json


# _____________________________________________________________________________
def write_alerts(alerts: List[Alert], basename: str):
    alert_fp = Path(f'{basename}.alerts-{today.strftime("%Y-%m-%d")}.csv').resolve()
    _logger.debug(f'write_alerts "{alert_fp.name}"')

    # Write alerts
    if alerts:
        # Backup alerts
        if alert_fp.exists():
            backup_fp = _make_backup_path(alert_fp)
            try:
                backup_fp.write_text(alert_fp.read_text())
            except PermissionError:
                _logger.warning(f'Cannot write to backup "{backup_fp.name}"')

        # Write alerts
        try:
            with alert_fp.open(mode='wt', newline='') as out:
                csv_writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL)
                csv_writer.writerow(Record.__slots__)
                for alert in alerts:
                    csv_writer.writerow(alert.to_list())
        except PermissionError:
            _logger.error(f'Cannot write to "{alert_fp.name}"')
            raise

        fp_iter = filter(lambda x: x != alert_fp, _base_path.glob('*.alerts-*.*'))
    else:
        fp_iter = _base_path.glob('*.alerts-*.*')

    # Move old alert files
    for fp in fp_iter:
        try:
            fp.replace(Path(_data_base_path, fp.name))
        except PermissionError:
            _logger.warning(f'Could not move file "{fp.name}"')


# _____________________________________________________________________________
def write_report(recs: List[Record], basename: str):
    report_fp = Path(_data_base_path, f'{basename}.report-{today.strftime("%Y-%m-%d")}.csv').resolve()
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
        with report_fp.open(mode='wt', newline='') as out:
            csv_writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(Record.__slots__)
            for rec in recs:
                csv_writer.writerow(rec.to_list())
    except PermissionError:
        _logger.error(f'Cannot write to "{report_fp.name}"')
        raise
