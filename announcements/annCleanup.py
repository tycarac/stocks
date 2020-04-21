from datetime import timedelta, date, datetime, time
import logging.config
import os
from pathlib import Path
from typing import List, Set

import announcements.annTypes as typ
import announcements.annConfig as config

_logger = logging.getLogger(__name__)


# _____________________________________________________________________________
class CleanOutput:

    # _____________________________________________________________________________
    def __init__(self, app_config: config.AppConfig):
        _logger.debug('__init__')
        self._app_config = app_config

    # _____________________________________________________________________________
    @staticmethod
    def __delete_old_empty_files(path: os.PathLike, age: timedelta) -> List[typ.Deleted]:
        cutoff = (datetime.now() - age).replace(hour=0, minute=0, second=0).timestamp() if age else None

        delete_records = []
        for parent, dirs, files in os.walk(str(path), topdown=False):
            # Delete empty and old files
            for file in [os.path.join(parent, f) for f in files]:
                if (mtime := os.path.getmtime(file)) < cutoff or os.path.getsize(file) == 0:
                    result = typ.Result.error
                    try:
                        os.remove(file)
                        result = typ.Result.success
                        _logger.debug(f'Deleted file "{file}"')
                    except PermissionError:
                        _logger.warning(f'Cannot delete file "{file}"')
                    finally:
                        symbol = os.path.basename(os.path.dirname(path))
                        file_date_time = datetime.fromtimestamp(mtime, config.asx_tz)
                        delete_records.append(typ.Deleted(symbol, file_date_time, os.path.basename(file),
                                    Path(file), typ.Outcome.deleted, result))

            # Delete empty directories
            for dir in [os.path.join(parent, d) for d in dirs]:
                with os.scandir(dir) as it:
                    if next(it, None) is None:
                        try:
                            os.rmdir(dir)
                            _logger.debug(f'Deleted directory "{dir}"')
                        except PermissionError:
                            _logger.warning(f'Cannot delete directory "{dir}"')

        return delete_records

    # _____________________________________________________________________________
    def process(self) -> List[typ.Deleted]:
        _logger.debug('process')

        return self.__delete_old_empty_files(self._app_config.output_path, self._app_config.announcement_age_days)
