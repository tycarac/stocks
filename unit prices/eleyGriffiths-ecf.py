"""Transform and filter unit prices for Eley Giffiths funds

Prices are provided in PDF files.  To extract unit prices:
1. Load PDF and use "File > Save as text ..." to create text file
2. Run python script over text file to create csv file.
"""
from pathlib import Path
import re
from io import StringIO

re_date = re.compile(r'(20[\d]{6})')
re_price = re.compile(r'(\d+(?:\.\d+))')


# _____________________________________________________________________________
def strip_lines(iterator):
    for ln in iterator:
        # Skip lines with no content and not starting with a digit
        if (ln := ln.strip()) and ln[0].isdigit():
            yield ln


lines = Path('data/Historical-Unit-Prices-ECF.txt').read_text().splitlines()

row, rows = list(), list()
for line in strip_lines(lines):
    if match_date := re_date.match(line):
        if len(row) > 1:
            rows.append(row)
        row = list()
        row.append(line)
    elif match_price := re_price.match(line):
        row.append(line)
if len(row) > 1:
    rows.append(row)

outlines = ''
with StringIO() as buf:
    buf.write(f'date,redeem\n')
    for row in rows:
        date = row[0]
        buf.write(f'{date[0:4]}-{date[4:6]}-{date[6:8]},{row[2]}\n')
    outlines = buf.getvalue()
Path('data/Historical-Unit-Prices-ECF.csv').write_text(outlines)
