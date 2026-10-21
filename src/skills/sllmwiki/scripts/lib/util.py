"""Small helpers the scripts share: Unicode-wide whitespace matching and
trimming, how values print inside messages, lenient date parsing, JSON and
UTF-8 output, reading and writing text files, and the git root.

(The scripts began as JavaScript; the whitespace class, the message
formatting and the date parsing still follow JavaScript's rules, so output
stayed the same through the port.)
"""

import calendar
import email.utils
import json
import re
from datetime import datetime, timezone

# JavaScript's \s (and the characters String.prototype.trim removes).
WS_CHARS = '\t\n\x0b\x0c\r \xa0  -     　﻿'
WS = f'[{WS_CHARS}]'
_TRIM = ''.join(
    chr(c) for c in list(map(ord, '\t\n\x0b\x0c\r \xa0     　﻿')) + list(range(0x2000, 0x200B))
)


def trim(s):
    return s.strip(_TRIM)


def trim_end(s):
    return s.rstrip(_TRIM)


def jstr(v):
    """A value as JavaScript's String() / template literals print it."""
    if v is None:
        return 'null'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, float):
        if v != v:
            return 'NaN'
        if v.is_integer() and abs(v) < 1e21:
            return str(int(v))
        return repr(v)
    if isinstance(v, list):
        return ','.join('' if x is None else jstr(x) for x in v)
    if isinstance(v, dict):
        return '[object Object]'
    return str(v)


def as_list(v):
    if isinstance(v, list):
        return v
    return [] if v is None else [v]


def is_map(v):
    return isinstance(v, dict)


def same_number(a, b):
    """JavaScript's a === b for a YAML value and a number."""
    return isinstance(a, (int, float)) and not isinstance(a, bool) and a == b


def dumps(obj):
    """JSON.stringify(obj, null, 2)."""
    return json.dumps(obj, indent=2, ensure_ascii=False)


def to_utf8(s):
    """Buffer.from(s, 'utf8'): surrogate pairs combine, lone surrogates become U+FFFD."""
    return s.encode('utf-16-le', 'surrogatepass').decode('utf-16-le', 'replace').encode('utf-8')


# ---- dates: Date.parse and toISOString -------------------------------------

_ISO_DATE = re.compile(r'([+-][0-9]{6}|[0-9]{4})(?:-([0-9]{2})(?:-([0-9]{2}))?)?\Z')
_ISO_TIME = re.compile(
    r'([+-][0-9]{6}|[0-9]{4})-([0-9]{2})-([0-9]{2})[T ]([0-9]{2}):([0-9]{2})(?::([0-9]{2})(?:\.([0-9]+))?)?'
    r'(Z|[+-][0-9]{2}:?[0-9]{2})?\Z',
    re.I,
)


def date_parse(v):
    """Date.parse(v) in milliseconds, or None for NaN. Covers what the wiki
    files and HTTP servers use: ISO 8601 dates and date-times (a date alone is
    UTC; a date-time without an offset is local time, as in JavaScript) and
    RFC 2822 / HTTP dates."""
    if v is None or isinstance(v, bool):
        return None
    s = trim(jstr(v))
    try:
        m = _ISO_DATE.match(s)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2) or 1), int(m.group(3) or 1)
            return calendar.timegm((y, mo, d, 0, 0, 0)) * 1000
        m = _ISO_TIME.match(s)
        if m:
            y, mo, d, hh, mi = (int(m.group(i)) for i in range(1, 6))
            ss = int(m.group(6) or 0)
            ms = int((m.group(7) or '0')[:3].ljust(3, '0'))
            if hh == 24 and mi == 0 and ss == 0:
                hh, extra = 0, 86400
            else:
                extra = 0
            off = m.group(8)
            if off is None:
                local = datetime(y, mo, d, hh, mi, ss).timestamp()
                return int(local + extra) * 1000 + ms
            secs = calendar.timegm((y, mo, d, hh, mi, ss)) + extra
            if off.upper() != 'Z':
                sign = -1 if off[0] == '-' else 1
                digits = off[1:].replace(':', '')
                secs -= sign * (int(digits[:2]) * 3600 + int(digits[2:]) * 60)
            return secs * 1000 + ms
        t = email.utils.parsedate_tz(s)
        if t:
            return email.utils.mktime_tz(t) * 1000
    except (ValueError, OverflowError):
        return None
    return None


def iso(ms):
    """new Date(ms).toISOString() without milliseconds, or None."""
    if ms is None:
        return None
    return datetime.fromtimestamp(ms // 1000, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def iso_or_none(v):
    return iso(date_parse(v))


def now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


# ---- command-line plumbing ----------------------------------------------------

def setup_stdio():
    """UTF-8 output with \\n line endings on every platform, as Node writes it."""
    import sys

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', newline='\n')
        except (AttributeError, ValueError):
            pass


def git_root(cwd=None):
    """The repository root (git rev-parse --show-toplevel), or the current directory."""
    import os
    import subprocess

    try:
        out = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True, check=True, cwd=cwd)
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return os.getcwd()


def read_text(path):
    """A UTF-8 file as text, with line endings left as they are."""
    with open(path, encoding='utf-8', errors='replace', newline='') as fh:
        return fh.read()


def write_text(path, text):
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        fh.write(text)
