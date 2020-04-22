from bs4 import BeautifulSoup
from dateutil.parser import parse
import logging
from operator import itemgetter, attrgetter
from typing import List, Dict
import urllib.parse

from common.common import sleep
from common.urlCache import UrlCache
from announcements.annTypes import Announcement, SharesAnnouncement, Outcome, Result
from announcements.annConfig import AppConfig

_logger = logging.getLogger(__name__)

_URL = 'https://www.asx.com.au/asx/statistics/announcements.do'
_fields = {
    'by': 'asxCode',
    'timeframe': 'D',
    'period': 'M'
}


# _____________________________________________________________________________
class AnnPageScraper:

    # _____________________________________________________________________________
    def __init__(self, app_config: AppConfig):
        _logger.debug('__init__')
        self._app_config = app_config
        UrlCache.set_cache_path(app_config.cache_path)

    # _____________________________________________________________________________
    @staticmethod
    def __build_url(asx_code: str) -> (str, Dict[str, str]):
        fields = _fields.copy()
        fields['asxCode'] = asx_code.upper()
        return _URL, fields

    # _____________________________________________________________________________
    @staticmethod
    def __extract_announcements(shares_ann: SharesAnnouncement, data: BeautifulSoup) -> List[Announcement]:
        _logger.debug('__extract_announcements')

        # Find data
        if (data_tag := data.find('announcement_data')) is None:
            _logger.error(f'Error parsing announcements for {shares_ann.symbol}')
            return []
        rows = data_tag.find('table').find('tbody').find_all('tr')

        # Extract data
        announcements = []
        for row in rows:
            num_pages, file_size, file_type = None, None, None

            cells = row.find_all('td')
            assert len(cells) == 3

            text = ' '.join(cells[0].text.split())
            date_time = parse(text, dayfirst=True)

            is_price_sensitive = cells[1].find('img') is not None

            link = cells[2].find('a')
            if tag := cells[2].find('span', attrs={'class': 'page'}):
                num_pages = tag.text.split()[0]
            if tag := cells[2].find('span', attrs={'class': 'filesize'}):
                file_size = ' '.join(tag.text.split())
            href = link.get('href')
            title = ' '.join(link.contents[0].split())

            # Derive
            params = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
            if (display := params.get('display', None)) and len(display):
                file_type = display[0]

            ann = Announcement(shares_ann.symbol, date_time, title, is_price_sensitive,
                        num_pages, file_size, href, None, file_type, Outcome.nil, Result.nil)
            announcements.append(ann)

        return announcements

    # _____________________________________________________________________________
    def get_announcements(self, shares_anns: List[SharesAnnouncement]) -> List[Announcement]:
        _logger.debug('get_announcements')

        # Initialise cache
        url_cache = UrlCache(self._app_config.cache_age_sec)

        # Fetch Service landing page xml
        announcements = []
        for shares_ann in shares_anns:
            symbol = shares_ann.symbol
            _logger.debug(f'Getting announcements for {symbol}')
            url, fields = self.__build_url(symbol)
            cache_tag = f'{symbol.lower()}-webpage.html'
            data, suffix, is_cached = url_cache.get(url, fields, cache_tag)
            if data is None:
                _logger.error(f'Could not fetch data for {shares_ann}')
                continue

            if lst := self.__extract_announcements(shares_ann, data):
                announcements.extend(lst)
                rec = max(lst, key=attrgetter('date_time'))
                shares_ann.most_recent = rec.date_time
                shares_ann.count = len(lst)
                _logger.debug(f'symbol: {symbol:6s} most recent {rec.date_time}, found {len(lst)}')
            else:
                _logger.debug(f'symbol: {symbol:6s} has no announcements')

            if not is_cached:
                sleep(0.1, 0.2)

        return announcements
