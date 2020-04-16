import concurrent.futures
from datetime import datetime, timedelta
import logging.config
import os
from pathlib import Path
import shutil
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
_BUFFER_SIZE = 1024 * 1024   # buffer for downloading remote resource


# _____________________________________________________________________________
class FetchFile:

    # _____________________________________________________________________________
    def __init__(self, app_config: config.AppConfig):
        _logger.debug('__init__')
        self._app_config = app_config

    # _____________________________________________________________________________
    def __fetch_announcements_all(self, anns: List[typ.Announcement]):
        _logger.debug('__fetch_announcements')

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future_entry = {executor.submit(self.__fetch_announcement, ann, id) for id, ann in enumerate(anns)}
            for future in concurrent.futures.as_completed(future_entry):
                ann, id = future.result()

    # _____________________________________________________________________________
    def __fetch_announcements(self, anns: List[typ.Announcement]):
        _logger.debug('__fetch_announcements')

        self.__fetch_announcement(anns[0], 1)

    # _____________________________________________________________________________
    def __fetch_announcement(self, ann: typ.Announcement, id: int):
        _logger.debug(f'> {id:4d} __fetch_item')
        ann.result = typ.Result.error
        ann.outcome = typ.Outcome.nil

        # Check file exists and, if so, if old
        is_file_exists = ann.filepath.exists()
        _logger.debug(f'> {id:4d} exists:     {str(is_file_exists):<5s}: "{ann.filepath.name}"')
        if is_file_exists:
            ann.result, ann.outcome = typ.Result.success, typ.Outcome.cached
            _logger.debug(f'> {id:4d} cached:     "{ann.filepath.name}"')
            return ann, id

        self.__fetch_file(ann, is_file_exists, id)
        return ann, id

    # _____________________________________________________________________________
    def __fetch_file(self, ann: typ.Announcement, is_file_exists: bool, id: int):
        _logger.debug(f'> {id:4d} __fetch_file')

        try:
            url = urllib.parse.urljoin(_URL, ann.href)
            rel_path = ann.filepath.relative_to(self._app_config.output_path)
            _logger.info(f'> {id:4d} fetching:   "{rel_path.name}" --> "{rel_path.parent}"')
            _logger.debug(f'> {id:4d} GET:        {url}')

            rsp_status, fetch_time = FetchFile.__stream_response(url, ann.filepath, id)
            if rsp_status == 200:
                ann.outcome = typ.Outcome.updated if is_file_exists else typ.Outcome.created

                # Update file datetime stamp
                pub_timestamp = time.mktime(ann.date_time.timetuple())
                file_path_str = str(ann.filepath)
                os.utime(file_path_str, (pub_timestamp, pub_timestamp))

                # Derive file size
                file_size = ann.filepath.stat().st_size
                ann.result = typ.Result.success
                _logger.debug(f'> {id:4d} fetch time, size: {fetch_time:.2f}s, {to_decimal_units(file_size)}')
            else:
                _logger.error(f'> {id:4d} HTTP code:  {rsp_status}')
                if ann.filepath.exists():
                    ann.filepath.unlink()
                    _logger.debug(f'> {id:4d} deleting:   "{rel_path}"')
                    ann.outcome = typ.Outcome.deleted
        except Exception as ex:
            _logger.exception(f'> {id:4d} generic exception')

    # _____________________________________________________________________________
    @staticmethod
    def __get_response(url: str, filepath: Path, id: int):
        # Must call release_conn() after file copied but opening/writing exception is possible
        rsp = None
        fetch_time = timedelta()
        try:
            redirect_count = 3
            start_time = time.time()
            rsp = url_client.request('GET', url, preload_content=False)
            _logger.debug(f'> {id:4d} resp code:  {rsp.status}')
            while rsp.status in urllib3.HTTPResponse.REDIRECT_STATUSES and redirect_count > 0:
                if location := rsp.headers.get('location', None):
                    _logger.debug(f'> {id:4d} redirct:      {url} --> {location}')
                    url = location
                    rsp.release_conn()
                    rsp = url_client.request('GET', location, preload_content=False)
                else:
                    raise RuntimeError('Response header "location" not found')
            if rsp.status == 200:
                _logger.debug(f'> {id:4d} write:      "{filepath.name}"')
                with filepath.open('wb', buffering=_BUFFER_SIZE) as rfp:
                    shutil.copyfileobj(rsp, rfp, length=_BUFFER_SIZE)
            fetch_time = time.time() - start_time
        except urllib3.exceptions.HTTPError as ex:
            _logger.exception(f'> {id:4d} HTTP error')
        except Exception as ex:
            _logger.exception('Unexpected')
            raise ex
        finally:
            if rsp:
                rsp.release_conn()

        return rsp.status, fetch_time

    # _____________________________________________________________________________
    @staticmethod
    def __stream_response(url: str, filepath: Path, id: int):
        # Must call release_conn() after file copied but opening/writing exception is possible
        rsp = None
        start_time, fetch_time = time.time(), timedelta()
        try:
            rsp = url_client.request('GET', url, preload_content=False)
            _logger.debug(f'> {id:4d} resp code:  {rsp.status}')
            while rsp.status in urllib3.HTTPResponse.REDIRECT_STATUSES:
                if location := rsp.headers.get('location', None):
                    _logger.debug(f'> {id:4d} redirct:      "{url} --> {location}')
                    url = location
                    rsp.release_conn()
                    rsp = url_client.request('GET', url, preload_content=False)
                    _logger.debug(f'> {id:4d} resp code:  {rsp.status}')
                else:
                    raise RuntimeError('Response header "location" not found')
            if rsp.status == 200:
                _logger.debug(f'> {id:4d} write:      "{filepath.name}"')
                with filepath.open('wb', buffering=_BUFFER_SIZE) as rfp:
                    shutil.copyfileobj(rsp, rfp, length=_BUFFER_SIZE)
            fetch_time = time.time() - start_time
        except urllib3.exceptions.HTTPError as ex:
            _logger.exception(f'> {id:4d} HTTP error')
        finally:
            if rsp:
                rsp.release_conn()

        return rsp.status, fetch_time

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
