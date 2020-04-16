from datetime import datetime
import logging.handlers
from pathlib import Path
import pytz
import tzlocal

_logger = logging.getLogger(__name__)

local_tz = tzlocal.get_localzone()
asx_tz = pytz.timezone('Australia/Sydney')
today = datetime.now(local_tz)


# _____________________________________________________________________________
class AppConfig:

    # _____________________________________________________________________________
    def __init__(self, base_dp: Path):
        """Initialises the configuration class
        """

        # Initialize
        self._name = base_dp.stem

        # Cache
        self._cache_path = Path(base_dp, 'cache').resolve()
        self._cache_age_sec = 600

        # Output
        self._output_path = Path(base_dp, 'output').resolve()

    # _____________________________________________________________________________
    @property
    def name(self):
        return self._name

    # _____________________________________________________________________________
    @property
    def cache_age_sec(self):
        return self._cache_age_sec

    # _____________________________________________________________________________
    @property
    def cache_path(self):
        return self._cache_path

    # _____________________________________________________________________________
    @property
    def output_path(self):
        return self._output_path
