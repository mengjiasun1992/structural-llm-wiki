"""The "Original source" footer every saved source ends with: its URL and license
(design doc §4.3). The source's hash leaves it out (lib/util.py's source_hash),
so writing a footer never makes a source look changed."""

import re

from .util import FOOTER_MARKER, FOOTER_SEPARATOR, split_footer


def render(url, license, license_url=None):
    """The footer's text, starting with its separator."""
    shown = f'[{license}](<{license_url}>)' if license_url else license
    return f'{FOOTER_SEPARATOR}{FOOTER_MARKER}\n## Original source\n\n- URL: <{url}>\n- License: {shown}\n'


def add(body, url, license, license_url=None):
    """body (bytes) with a fresh footer, any earlier one replaced."""
    return split_footer(body)[0] + render(url, license, license_url).encode()


def read(data):
    """{url, license} from a saved source's footer, or None without one."""
    footer = split_footer(data)[1].decode('utf-8', 'replace')
    if not footer:
        return None
    url = re.search(r'^- URL: <([^>\n]+)>', footer, re.M)
    lic = re.search(r'^- License: (?:\[([^\]\n]+)\]\(<[^>\n]*>\)|(.+))$', footer, re.M)
    return {'url': url.group(1) if url else None, 'license': (lic.group(1) or lic.group(2)).strip() if lic else None}
