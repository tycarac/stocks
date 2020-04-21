from datetime import datetime, date, time
import logging
import random
import uuid
import re
import time
from typing import List, Any, Tuple
import tzlocal
import urllib3

_logger = logging.getLogger(__name__)

local_tz = tzlocal.get_localzone()
today = datetime.now(local_tz)

ran = random.Random(uuid.uuid4().hex)
re_yahoo_symbol = re.compile(r'([A-Z0-9]{2,6})(?:\.AX)?', re.IGNORECASE)


# _____________________________________________________________________________
url_headers = urllib3.make_headers(keep_alive=True, accept_encoding=True)
url_retries = urllib3.Retry(total=4, backoff_factor=5, status_forcelist=[500, 502, 503, 504])
url_client = urllib3.PoolManager(timeout=urllib3.Timeout(total=15.0), retries=url_retries, headers=url_headers,
            block=True, maxsize=10)


# _____________________________________________________________________________
def multisort(coll: List, specs):
    for key, reverse in reversed(specs):
        coll.sort(key=key, reverse=reverse)
    return coll


# _____________________________________________________________________________
def sleep(value: float, min_value: float = 0):
    time.sleep(ran.uniform(min_value, value))
