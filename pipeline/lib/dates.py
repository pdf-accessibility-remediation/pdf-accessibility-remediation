"""lib/dates.py: dates and times as a person reads them, wherever the app, the dashboards and review.md show one
(decided 2026-10-31, #38): "October 31, 2026" and "4:32 PM". Stored records keep ISO; only the display changes.

    day('2026-10-31T16:32:05')    == 'October 31, 2026'
    clock('2026-10-31T16:32:05')  == '4:32 PM'
    when('2026-10-31T16:32:05')   == 'October 31, 2026 at 4:32 PM'
    when('2026-10-31')            == 'October 31, 2026'

Takes YYYY-MM-DD and ISO date-times (T or a space, with or without seconds and fractional seconds). The month names come
from a fixed table, never strftime's %B (it follows the machine's locale). No time-zone conversion: every value a person
reads is written as local time with no offset; a value with an offset is shown in its own time. A value that does not
parse (review_workorder.py's --date is free text) is shown as written; a missing one reads "date not recorded". The same
rule is in webapp/panel.js and review/page.html (fmtDay, fmtClock), which parse the string themselves, never with Date
(new Date('2026-10-31') is midnight UTC: October 30 in Honolulu).
"""
import re

MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December')
ISO = re.compile(r'^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?)?(?:Z|[+-]\d{2}:?\d{2})?$')
MISSING = 'date not recorded'

def parse(v):
    """(year, month, day, hour or None, minute or None), or None when v is not an ISO date."""
    m = ISO.match(str(v or '').strip())
    if not m: return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    h, mi = (int(m.group(4)), int(m.group(5))) if m.group(4) else (None, None)
    if not (1 <= mo <= 12 and 1 <= d <= 31) or (h is not None and not (h <= 23 and mi <= 59)): return None
    return y, mo, d, h, mi

def day(v, missing=MISSING):
    if v is None or not str(v).strip(): return missing
    p = parse(v)
    return f'{MONTHS[p[1] - 1]} {p[2]}, {p[0]}' if p else str(v).strip()

def clock(v, missing='time not recorded'):
    p = parse(v)
    if not p or p[3] is None: return missing if v is None or not str(v).strip() or p else str(v).strip()
    h, mi = p[3], p[4]
    return f'{(h % 12) or 12}:{mi:02d} {"AM" if h < 12 else "PM"}'

def when(v, missing=MISSING):
    p = parse(v)
    if not p or p[3] is None: return day(v, missing)
    return f'{day(v)} at {clock(v)}'
