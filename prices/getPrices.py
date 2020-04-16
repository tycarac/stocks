import argparse
from datetime import datetime
from decimal import Decimal
import logging
from pathlib import Path
from typing import Dict, Iterable, List
import urllib3

from common.common import url_client, local_tz, re_yahoo_symbol
from common.logTools import initialize_logger

import prices.pricesLoader as loader
import prices.pricesConfig as config
import prices.pricesTypes as common
import prices.pricesOutput as output

_logger = logging.getLogger(__name__)


# _____________________________________________________________________________
def load_symbols(symbols_fp: Path) -> loader.ValuesLoader:
    _logger.debug(f'Loading symbols from "{symbols_fp}"')
    return loader.ValuesLoader(symbols_fp)


# _____________________________________________________________________________
def fetch_data(values: loader.ValuesLoader, basename: str) -> (Dict[str, common.Record]):
    _logger.debug('fetch_data')

    # Fetch
    data_json = fetch_remote_data(values.symbols, basename)
    recs = transform_data(data_json, values)

    # Check for missing codes from retrieved data
    for symbol in (set(values.symbols) - set(r.symbol for r in recs)):
        _logger.error(f'Symbol {symbol} not retrieved')

    return recs


# _____________________________________________________________________________
def fetch_remote_data(symbols: Iterable[str], basename: str):
    _logger.debug(f'fetch_remote_data')

    yahoo_symbols = set(map(lambda x: x + '.AX', symbols))  # Yahoo stock symbols have suffix '.AX'
    fields = {'symbols': ','.join(yahoo_symbols)}
    _logger.debug(f'Fetching {len(yahoo_symbols)} symbols')

    data_json = None
    try:
        rsp = url_client.request('GET', config.URL, fields=fields)
        _logger.debug(f'response status  {rsp.status}')
        if rsp.status == 200:
            data_json = output.write_json(rsp.data, basename)
    except urllib3.exceptions.HTTPError as ex:
        _logger.exception(f'HTTPError')
        raise

    return data_json


# _____________________________________________________________________________
def transform_data(data_json: Dict, values: loader.ValuesLoader) -> List[common.Record]:
    _logger.debug(f'transform_data')
    dec100 = Decimal(100.000)
    recs = []
    for data in data_json['quoteResponse']['result']:
        symbol = match.group(1) if (match := re_yahoo_symbol.fullmatch(data['symbol'])) else data['symbol']
        price = Decimal(data["regularMarketPrice"]).quantize(config.quant)
        low = Decimal(data["regularMarketDayLow"]).quantize(config.quant)
        high = Decimal(data["regularMarketDayHigh"]).quantize(config.quant)
        bid = Decimal(data["bid"]).quantize(config.quant)
        ask = Decimal(data["ask"]).quantize(config.quant)
        volume = int(data["regularMarketVolume"])
        dt = datetime.fromtimestamp(data['regularMarketTime'], local_tz)
        name = data['longName']
        if ref := values.price_ref(symbol):
            ref_to_price = (dec100 - price / ref * dec100).quantize(Decimal('0.0'))
        else:
            ref_to_price = None
        alert_low = values.alert_low(symbol)
        alert_high = values.alert_high(symbol)
        recs.append(common.Record(symbol, price, low, high, bid, ask, ref, ref_to_price, alert_low, alert_high,
                    volume, dt.date(), dt.time(), name))
    return recs


# _____________________________________________________________________________
def process_data(recs: List[common.Record], values: loader.ValuesLoader) -> List[common.Alert]:
    _logger.debug('process_data')

    alerts = list()
    for r in recs:
        if (price_low := values.alert_low(r.symbol)) and r.price <= price_low:
            alerts.append(common.Alert(r.symbol, common.AlertType.low, r.price, r.alertLow, r.refToPrice, r.ref))
        if (price_high := values.alert_high(r.symbol)) and r.price >= price_high:
            alerts.append(common.Alert(r.symbol, common.AlertType.high, r.price, r.alertHigh, r.refToPrice, r.ref))

    return alerts


# _____________________________________________________________________________
def main():
    main_basename = Path(__file__).stem
    logger_dp = Path(Path(__file__).parent, 'logs')
    initialize_logger(logger_dp, main_basename)
    start_datetime = datetime.now(tz=local_tz)
    _logger.info(f'Now: {start_datetime.strftime("%a  %d-%b-%y  %I:%M:%S %p")}')

    # Configure commandline parser
    argp = argparse.ArgumentParser(description='Retrieve stock prices from Yahoo Finance website')
    argp.add_argument('-s', '--symbols', action='store_true', help='Output symbols to be processed and exit')
    argp.add_argument('-b', '--brief', action='store_true', help='Run and output brief')
    argp.add_argument('-p', '--prices', action='store_true', help='Run and output prices')
    argp.add_argument('-f', '--file', action='store', nargs=1, default=['symbols.csv'],
                help='Input file name for symbols')

    try:
        args = argp.parse_args()
        symbols_basename = Path(args.file[0]).stem
        values, recs = [], []

        try:
            values = load_symbols(Path(Path(__file__).parent, args.file[0]))  # Expecting exactly 1 filename in list
        finally:
            if args.symbols and values:
                output.output_symbols(values)
                return

        alerts = []
        try:
            recs = fetch_data(values, symbols_basename)
            alerts = process_data(recs, values)
            output.write_report(recs, symbols_basename)
            output.write_alerts(alerts, symbols_basename)

            to_report_all = not(args.prices or args.brief)
            if args.prices or to_report_all:
                output.output_prices(recs, values.symbols)
            if args.brief or to_report_all:
                output.output_brief(recs)
        finally:
            output.output_alerts(alerts)
    except Exception as ex:
        _logger.exception('Catch all exception')
    finally:
        _logger.debug("done")


# _____________________________________________________________________________
if __name__ == '__main__':
    main()
