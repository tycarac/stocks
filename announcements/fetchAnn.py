from bs4 import BeautifulSoup
import concurrent.futures
import logging.config
import os
from pathlib import Path
import time
from typing import List
import urllib.parse
import urllib3

from common.common import url_client
from common.metricPrefix import to_decimal_units
from common.pathTools import sanitize_filename

import announcements.annConfig as config
import announcements.annTypes as typ

_logger = logging.getLogger(__name__)

_URL = 'https://www.asx.com.au/'
_URL_PATH = '/asx/statistics/announcementTerms.do'


# _____________________________________________________________________________
class FetchFile:

    # _____________________________________________________________________________
    def __init__(self, app_config: config.AppConfig):
        _logger.debug('__init__')
        self._app_config = app_config

    # _____________________________________________________________________________
    def __fetch_announcements(self, anns: List[typ.Announcement]):
        _logger.debug('__fetch_announcements')

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future_entry = {executor.submit(self.__fetch_announcement, ann, id) for id, ann in enumerate(anns)}
            for future in concurrent.futures.as_completed(future_entry):
                ann, id = future.result()

    # _____________________________________________________________________________
    def __fetch_announcement(self, ann: typ.Announcement, id: int):
        _logger.debug(f'> {id:4d} __fetch_item')
        _logger.debug(f'> {id:4d} symbol {ann.symbol:6s} : {ann.title}')
        ann.result = typ.Result.error
        ann.outcome = typ.Outcome.nil

        # Check file exists and, if so, if old
        is_file_exists = ann.filepath.exists()
        _logger.debug(f'> {id:4d} exists:     {str(is_file_exists):<5s}: "{ann.filepath.name}"')
        if is_file_exists:
            ann.result, ann.outcome = typ.Result.success, typ.Outcome.cached
            _logger.debug(f'> {id:4d} cached:     "{ann.filepath.name}"')
            return ann, id

        # Fetch file
        self.__fetch_file(ann, is_file_exists, id)

        # Update file datetime stamp
        pub_timestamp = time.mktime(ann.date_time.timetuple())
        file_path_str = str(ann.filepath)
        os.utime(file_path_str, (pub_timestamp, pub_timestamp))

        return ann, id

    # _____________________________________________________________________________
    def __fetch_file(self, ann: typ.Announcement, is_file_exists: bool, id: int):
        _logger.debug(f'> {id:4d} __fetch_file')

        try:
            url = urllib.parse.urljoin(_URL, ann.href)
            rel_path = ann.filepath.relative_to(self._app_config.output_path)
            _logger.debug(f'> {id:4d} fetching:   "{rel_path.name}" --> "{rel_path.parent}"')

            rsp = None
            try:
                _logger.debug(f'> {id:4d} GET:        {url}')
                rsp = url_client.request('GET', url)
                _logger.debug(f'> {id:4d} GET status:  {rsp.status}')
                if rsp.status == 200 and ((content_type := rsp.headers.get('Content-Type', ''))
                                          and content_type.find('text/html') >= 0):
                    # Process "Agree and continue" page for document link
                    url = urllib.parse.urljoin(_URL, _URL_PATH)
                    soup = BeautifulSoup(rsp.data, 'lxml')
                    href = soup.find('input', {'name': 'pdfURL'})['value']
                    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                    fields = {'pdfURL': href}
                    _logger.debug(f'> {id:4d} POST:       {url}')
                    rsp = url_client.request('POST', url, headers=headers, fields=fields, encode_multipart=False)
                    _logger.debug(f'> {id:4d} POST status:  {rsp.status}')
                if rsp.status == 200 and ((content_type := rsp.headers.get('Content-Type', ''))
                                          and content_type.find('application/pdf') >= 0):
                    # Save file
                    ann.filepath.write_bytes(rsp.data)
                    ann.result, ann.outcome = typ.Result.success, typ.Outcome.created
            except urllib3.exceptions.HTTPError as ex:
                _logger.exception(f'> {id:4d} HTTP error')

            return rsp.status
        except Exception as ex:
            _logger.exception(f'> {id:4d} exception fetching file')

    # _____________________________________________________________________________
    def process(self, announcements: List[typ.Announcement]):
        _logger.debug('process')

        # Prepare record data for fetching
        dirs = set()
        for ann in announcements:
            filename = f'{ann.title}-{ann.date_time.strftime("%Y-%m-%d")}'
            if ann.file_type:
                filename = f'{filename}.{ann.file_type}'
            ann.filepath = Path(self._app_config.output_path, ann.symbol.lower(), sanitize_filename(filename)).resolve()
            dirs.add(ann.filepath.parent)

        # Create output directories
        for dir in dirs:
            dir.mkdir(parents=True, exist_ok=True)

        # Fetch announcements
        self.__fetch_announcements(announcements)
