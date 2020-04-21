from bs4 import BeautifulSoup
from dateutil.parser import parse
import logging
from operator import itemgetter, attrgetter
from typing import List, Dict
import urllib.parse

from common.common import sleep
from common.urlCache import UrlCache
from announcements.annTypes import Announcement, Outcome, Result
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
    def __extract_announcements(symbol: str, data: BeautifulSoup) -> List[Announcement]:
        _logger.debug('__extract_announcements')

        announcements = []

        table = data.find('announcement_data').find('table')
        table_body = table.find('tbody')
        rows = table_body.find_all('tr')
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

            ann = Announcement(symbol, date_time, title, is_price_sensitive, num_pages, file_size, href,
                        None, file_type, Outcome.nil, Result.nil)
            announcements.append(ann)

        return announcements

    # _____________________________________________________________________________
    def get_announcements(self, symbols: List[str]) -> List[Announcement]:
        _logger.debug('get_announcements')

        # Initialise cache
        url_cache = UrlCache(self._app_config.cache_age_sec)

        # Fetch Service landing page xml
        announcements = []
        for symbol in symbols:
            url, fields = self.__build_url(symbol)
            data, suffix, is_cached = url_cache.get(url, fields=fields, cache_tag=f'{symbol.lower()}-webpage.html')
            if data is None:
                _logger.error(f'Could not fetch data for {symbol}')
                continue

            lst = self.__extract_announcements(symbol, data)
            announcements.extend(lst)

            rec = max(lst, key=attrgetter('date_time'))
            _logger.info(f'symbol: {symbol:6s} most recent {rec.date_time}, found {len(lst)}')
            if not is_cached:
                sleep(0.7, 0.2)

        return announcements
