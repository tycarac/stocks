"""Caches specific web data to local directory.

Notes:
     1. Key to data is by managled url path and used for local cache parh and filename.
     2. Caching usage is time-based and set on cache instance.
     3. Data is formated, by default, before being written to cache and returned.
     4. Data encoding for xml/html files are not inspected or changed (caches should not transform).
"""
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from io import BytesIO, StringIO
import logging
import json
from lxml import etree
from pathlib import Path
import time
from typing import Union, Dict
from urllib import parse
from urllib3 import exceptions

from common.common import url_client
import common.pathTools as pathTools

_logger = logging.getLogger(__name__)


# _____________________________________________________________________________
class UrlCache(ABC):

    _base_path = None

    # _____________________________________________________________________________
    def __init__(self, max_age, subfolder=None, format_on_write=True):
        if UrlCache._base_path is None:
            raise ValueError('Cache base path not set')
        self._cache_path = Path(UrlCache._base_path, subfolder).resolve() if subfolder else UrlCache._base_path
        if not pathTools.is_parent(UrlCache._base_path, self._cache_path):
            raise ValueError('subfolder not a child of cache path')
        self._max_age_sec = max_age
        self._format_on_write = format_on_write

    # _____________________________________________________________________________
    @staticmethod
    def set_cache_path(cache_base_path: Path):
        UrlCache._base_path = cache_base_path

    # _____________________________________________________________________________
    def __write_cached_text(self, data: Union[str, bytes], local_path: Path) -> str:
        _logger.debug(f'cache write text "{local_path.name}"')
        data_text = None
        try:
            data_text = data.decode('utf-8') if isinstance(data, bytes) else data
            local_path.write_text(data_text)
        except (UnicodeError, OSError):
            path = local_path.with_suffix('.raw.txt')
            _logger.exception(f'Decode error: {path.name}')
            path.write_bytes(data)

        return data_text

    # _____________________________________________________________________________
    def __write_cached_json(self, data: Union[str, bytes], local_path: Path):
        _logger.debug(f'cache write json "{local_path.name}"')
        data_json = None
        try:
            data_decoded = data.decode('utf-8') if isinstance(data, bytes) else data
            data_json = json.loads(data_decoded)
            if self._format_on_write:
                local_path.write_text(json.dumps(data_json, sort_keys=True, indent=2))
            else:
                local_path.write_text(data_decoded)
        except (UnicodeError, OSError, json.JSONDecodeError):
            path = local_path.with_suffix('.raw.json')
            _logger.exception(f'JSON parse error: {path.name}')
            path.write_bytes(data)

        return data_json

    # _____________________________________________________________________________
    def __write_cached_xml(self, data: bytes, local_path: Path):
        _logger.debug(f'cache write xml "{local_path.name}"')
        data_xml = None
        try:
            parser = etree.XMLParser(no_network=True, ns_clean=True, recover=True, remove_blank_text=True)
            data_xml = etree.parse(BytesIO(data), parser)
            if self._format_on_write:
                tos = etree.tostring(data_xml, pretty_print=True, method='xml', xml_declaration=True).decode()
                local_path.write_text(tos)
            else:
                local_path.write_bytes(data)
        except (UnicodeError, etree.SerialisationError, etree.ParseError) as ex:
            path = local_path.with_suffix('.raw.xml')
            _logger.exception(f'XML parse error: {path.name}')
            path.write_bytes(data)

        return data_xml

    # _____________________________________________________________________________
    def __write_cached_html(self, data: bytes, local_path: Path):
        _logger.debug(f'cache write html "{local_path.name}"')
        soup = None
        try:
            soup = BeautifulSoup(data, 'lxml')
            if self._format_on_write:
                tos = soup.prettify(formatter='html')
                local_path.write_text(tos)
            else:
                local_path.write_bytes(data)
        except (UnicodeError, Exception) as ex:
            path = local_path.with_suffix('.raw.html')
            _logger.exception(f'HTML parse error: {path.name}')
            path.write_bytes(data)

        return soup

    # _____________________________________________________________________________
    def __is_cached(self, local_path: Path) -> bool:
        if not pathTools.is_parent(UrlCache._base_path, local_path):
            raise ValueError('subpath not a child of cache path')

        # Test local path cache age
        is_cached = False
        if self._max_age_sec > 0 and local_path.exists():
            is_cached = local_path.stat().st_mtime > (time.time() - self._max_age_sec)

        _logger.debug(f'Cache tag, is cached: "{local_path.name}", {str(is_cached)}')
        return is_cached

    # _____________________________________________________________________________
    def __make_path_from_subpath(self, subpath: str) -> (Path, bool):
        # Determine paths
        local_path = Path(self._cache_path, subpath)
        return local_path, self.__is_cached(local_path)

    # _____________________________________________________________________________
    def __make_path_from_url(self, url: str) -> (Path, bool):
        url_parts = parse.urlparse(url)
        local_path = Path(self._cache_path, pathTools.sanitize_filename(url_parts.path))
        return local_path, self.__is_cached(local_path)

    # _____________________________________________________________________________
    def get(self, url: str, fields: Dict[str, str] = None, cache_tag: str = None) -> (str, str, bool):
        _logger.debug('get')

        filepath, is_cached = self.__make_path_from_subpath(cache_tag) if cache_tag else self.__make_path_from_url(url)
        _logger.debug(f'get filepath {filepath.relative_to(UrlCache._base_path)}')
        suffix = filepath.suffix.lower()

        data = None
        if is_cached:
            try:
                if suffix == '.xml':
                    data = etree.parse(str(filepath))
                elif suffix in ('.html', '.xhtml'):
                    data = BeautifulSoup(filepath.read_bytes(), 'lxml')
                elif suffix == '.json':
                    data = json.loads(filepath.read_bytes())
                else:
                    data = filepath.read_text()
            except (TypeError, json.JSONDecodeError, etree.ParseError) as ex:
                _logger.exception(f'Error reading cache')
        else:
            if not filepath.parent.exists():
                filepath.parent.mkdir(parents=True, exist_ok=True)
            try:
                rsp = url_client.request('GET', url, fields=fields)
                if rsp.status == 200:
                    if suffix in ('.xml', '.xhtml'):
                        data = self.__write_cached_xml(rsp.data, filepath)
                    elif suffix == '.html':
                        data = self.__write_cached_html(rsp.data, filepath)
                    elif suffix == '.json':
                        data = self.__write_cached_json(rsp.data, filepath)
                    else:
                        data = self.__write_cached_text(rsp.data, filepath)
                else:
                    _logger.debug(f'Bad response status {rsp.status} for {url}')
            except (exceptions.HTTPError, exceptions.SSLError):
                _logger.exception(f'GET error: {url}')

        return data, suffix, is_cached
