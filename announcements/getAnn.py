import argparse
from datetime import datetime
import logging
from pathlib import Path
from typing import List

from common.common import local_tz
from common.logTools import initialize_logger

import announcements.annTypes as typ
import announcements.annConfig as config
import announcements.annLoader as loader
import announcements.scrapeAnn as scrape
import announcements.annFetch as fetch
import announcements.annOutput as output
import announcements.annCleanup as cleanup

_logger = logging.getLogger(__name__)


# _____________________________________________________________________________
def load_symbols(symbols_fp: Path) -> List[typ.SharesAnnouncement]:
    _logger.debug(f'Loading symbols from "{symbols_fp}"')
    values_loader = loader.ValuesLoader(symbols_fp)
    return values_loader.share_codes


# _____________________________________________________________________________
def process_symbols(share_codes: List[typ.SharesAnnouncement], app_config: config.AppConfig) -> List[typ.Announcement]:
    _logger.debug('process_symbols')

    # Scrape list of announcements
    scraper = scrape.AnnPageScraper(app_config)
    announcements = scraper.get_announcements(share_codes)
    output.output_shares_announcements(share_codes)

    # Fetch announcements
    fetcher = fetch.FetchFile(app_config)
    fetcher.process(announcements)

    clean = cleanup.CleanOutput(app_config)
    deleted = clean.process()

    output.output_announcements_summary(announcements, deleted)
    output.write_report(announcements, deleted)

    return announcements


# _____________________________________________________________________________
def main():
    start_datetime = datetime.now(tz=local_tz)
    current_dp = Path(__file__).parent
    base_dp = current_dp.parent
    initialize_logger(Path(base_dp, 'logs'), current_dp.stem)
    _logger.info(f'Now: {start_datetime.strftime("%a  %d-%b-%y  %I:%M:%S %p")}')

    # Configure commandline parser
    argp = argparse.ArgumentParser(description='Retrieve stock prices from Yahoo Finance website')
    argp.add_argument('-s', '--symbols', action='store_true', help='Output symbols to be processed and exit')
    argp.add_argument('-f', '--file', action='store', nargs=1, default=['symbols.csv'],
                help='Input file name for symbols')

    try:
        args = argp.parse_args()
        app_config = config.AppConfig(base_dp)

        share_codes = load_symbols(Path(current_dp, args.file[0]))  # Expecting exactly 1 filename in list
        if args.symbols:
            output.output_symbols(share_codes)
        else:
            process_symbols(share_codes, app_config)
    except Exception as ex:
        _logger.exception('Catch all exception')
    finally:
        _logger.debug("done")


# _____________________________________________________________________________
if __name__ == '__main__':
    main()
