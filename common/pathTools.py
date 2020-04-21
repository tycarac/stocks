from datetime import timedelta, date, datetime, time
import io
import os
from pathlib import Path
import string
from typing import List, Tuple
import unicodedata
from urllib import parse
import zipfile

# https://docs.microsoft.com/en-us/windows/win32/fileio/naming-a-file
_FOLDER_SEPARATOR_CHARS = ['\\', '/']
_DASH_CHARS = ['\u2012', '\u2013', '\u2014', '\u2015', '\u2053']
_WINDOWS_INVALID_CHARS = [':', '*', '|', '?', '>', '<', '"']
_WINDOWS_INVALID_FILENAME_CHARS = _WINDOWS_INVALID_CHARS + _FOLDER_SEPARATOR_CHARS
_FILENAME_REPLACE_CHARS = _WINDOWS_INVALID_FILENAME_CHARS + _DASH_CHARS
_PATHNAME_REPLACE_CHARS = _WINDOWS_INVALID_CHARS + _DASH_CHARS
_URL_STRIP_CHARS = string.whitespace + '/'
_SPACE_CHARS = ['\u00A0', '\u2002', '\u2003']  # Does not include HTML specialized spaces


# _____________________________________________________________________________
def file_suffix(fp: str) -> str:
    """Extract the file suffix from a path

    :param fp:
    :return: file suffix or empty string
    """
    loc = max(fp.rfind('\\'), fp.rfind('/')) + 1
    if (pos := fp.rfind('.', loc)) > 0 and fp[loc] != '.':
        return fp[pos:]
    return ''


# _____________________________________________________________________________
def is_parent(parent: Path, path: Path) -> bool:
    """Returns True is path has the same parent path as parent
    :param parent:
    :param path:
    :return: True if parent path is contained in path
    """
    return str(path.resolve()).startswith(str(parent.resolve()))


# _____________________________________________________________________________
def delete_empty_directories(path: os.PathLike) -> List[str]:
    """Deletes all empty child folders under a parent folder
    :param path:
    :return: List of deleted folders
    """
    deleted_folders = []
    for parent, dirs, _ in os.walk(str(path), topdown=False):
        for dir in [os.path.join(parent, d) for d in dirs]:
            with os.scandir(dir) as it:
                if next(it, None) is None:
                    try:
                        os.rmdir(dir)
                        deleted_folders.append(dir)
                    except PermissionError:
                        pass

    return deleted_folders


# _____________________________________________________________________________
def delete_empty_old_files(path: os.PathLike, age: timedelta = None) -> (List[str], List[str]):
    """Deletes all empty child folders under a parent folder
    :param path: parent folder
    :param age:
    :param include_empty:
    :return: Tuple of deleted files, deleted folders and errors
    """
    cutoff = (datetime.now() - age).replace(hour=0, minute=0, second=0).timestamp() if age else None

    deleted_folders, deleted_files, errors = [], [], []
    for parent, dirs, files in os.walk(str(path), topdown=False):
        # Delete empty and old files
        for file in [os.path.join(parent, f) for f in files]:
            if (cutoff and os.path.getmtime(file) < cutoff) or os.path.getsize(file) == 0:
                try:
                    os.remove(file)
                    deleted_files.append(file)
                except PermissionError:
                    errors.append(file)

        # Delete empty directories
        for dir in [os.path.join(parent, d) for d in dirs]:
            with os.scandir(dir) as it:
                if next(it, None) is None:
                    try:
                        os.rmdir(dir)
                        deleted_folders.append(dir)
                    except PermissionError:
                        errors.append(dir)

    return deleted_files, deleted_folders, errors


# _____________________________________________________________________________
def sanitize_filename(filename: str, replace_dot=False) -> str:
    """Returns MS-Windows sanitized filename using ASCII character set
    :param filename: string
    :param replace_dot: bool
    :return: sanitized filename

    Remove URL character encodings and leading/trailing whitespaces.
    Replace whitespaces with '-' character (for Linux ease-of-use)
    Convert Unicode dashes to ASCII dash, but other unicode characters removed.
    Optionally, remove dot character but not from leading
    No checks on None, for leading/trailing dots, or filename length.
    """
    join_ch = ' ' if os.name == 'nt' else '-'
    fname = join_ch.join(parse.unquote(filename).split())
    for ch in _FILENAME_REPLACE_CHARS:
        if ch in fname:
            fname = fname.replace(ch, '-')
    if not fname.isascii():
        fname = unicodedata.normalize('NFKD', fname).encode('ASCII', 'ignore').decode('ASCII')
    if replace_dot and fname.find('.', 1) > 0:
        fname = fname[0] + fname[1:].replace('.', '-')

    return fname


# _____________________________________________________________________________
def join_urlpath(url, *paths: str) -> str:
    """Returns URL by combining url with each of the arguments in turn
    :param url: base URL
    :param paths: paths to be added
    :return: URL

    Does not validate URL
    """
    u = url.strip(_URL_STRIP_CHARS)
    p = '/'.join(map(lambda x: x.strip(_URL_STRIP_CHARS), paths))
    return f'{u}/{p}' if p else u


# _____________________________________________________________________________
def urlpath_to_pathname(url: str) -> str:
    """Returns MS-Windows sanitized filepath from a URL
    :param url: string
    :return: sanitized filename

    RFC 8089: The "file" URI Scheme
    """
    urlp = parse.urlparse(' '.join(parse.unquote(url).strip().split()))
    path = urlp.path.strip(_URL_STRIP_CHARS).replace('/', '\\')

    if not urlp.hostname:
        pathname = path
    else:
        pathname = f'{urlp.hostname}\\{path}' if path else urlp.hostname

    for ch in _PATHNAME_REPLACE_CHARS:
        if ch in pathname:
            pathname = pathname.replace(ch, '-')
    if not pathname.isascii():
        pathname = unicodedata.normalize('NFKD', pathname).encode('ASCII', 'ignore').decode('ASCII')

    return pathname


# _____________________________________________________________________________
def url_suffix(url: str) -> str:
    """
    The final component's last suffix, if any.  Includes leading period (eg: .'html').

    Parsing:
    1. Use urlparse to remove any trailing URL parameters.  Note a) "path" will contain the hostname when the URL
    does not start with '//' and b) "path" can be empty string but never None.
    2. Strip traling URL separator '/' and remove LHS far right URL separator
    """
    path = parse.urlparse(parse.unquote(url)).path.strip()
    if (j := path.rfind('.', path.rfind('/') + 1, len(path) - 1)) >= 0:
        return path[j:]
    return ''


# _____________________________________________________________________________
def open_files(path: str or os.PathLike) -> Tuple[str, int]:
    """Iterate over a root path returning an open file handle for each file found - including file in archives
    :return: Tuple[filename:str,file handle:int]
    """
    for root, _, filenames in os.walk(str(path)):
        # Iterate over files found in directory
        for filename in filenames:
            path = Path(root, filename).resolve()
            rel_path_str = str(Path(path.relative_to(path), path.name))

            # Test if file is an archive
            if file_suffix(filename) in ['.zip', '.gzip', '.gz']:
                with zipfile.ZipFile(io.BytesIO(path.read_bytes())) as zp:
                    # Iterate over files inside archive
                    for zipinfo in filter(lambda z: not z.is_dir(), zp.infolist()):
                        with zp.open(zipinfo) as file_handle:
                            yield f'{rel_path_str}|{zipinfo.filename}', file_handle
            else:
                # Yield non-archive file
                with open(path) as file_handle:
                    yield rel_path_str, file_handle
