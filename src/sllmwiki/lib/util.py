"""Small helpers every script uses: text files, JSON output, the git root, dates,
and a saved source's hash without its footer."""

import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

# A saved source ends with a generated footer (lib/footer.py), which its hash
# leaves out: the footer is "\n\n" + FOOTER_MARKER + its lines.
FOOTER_MARKER = '<!-- sllmwiki:original-source -->'
FOOTER_SEPARATOR = '\n\n'


def read_text(path):
    """A UTF-8 text file, its line endings kept."""
    with open(path, encoding='utf-8', newline='') as f:
        return f.read()


def read_bytes(path):
    with open(path, 'rb') as f:
        return f.read()


def write_text(path, text):
    """Write a UTF-8 text file as given, making its folder."""
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)


def dumps(obj):
    """JSON for --json output: indented, keys in insertion order, UTF-8 kept."""
    return json.dumps(obj, indent=2, ensure_ascii=False)


def setup_stdio():
    """Print UTF-8 whatever the terminal's locale, so source text never crashes a script."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')


def placeholder(path):
    """An empty file or folder, or something that isn't a file at all, such as a device: no code or
    documents in it. Claude Code's sandbox puts such placeholders over the config files it guards
    (.bashrc, .gitconfig, .mcp.json, .claude/settings.json)."""
    try:
        if os.path.islink(path):
            return False
        if os.path.isdir(path):
            return all(placeholder(os.path.join(path, n)) for n in os.listdir(path))
        return not os.path.isfile(path) or os.path.getsize(path) == 0
    except OSError:
        return True


def git_root(cwd=None):
    """The top folder of the git repository around cwd, or None outside one."""
    try:
        p = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=cwd or os.getcwd(),
                           capture_output=True, text=True, check=False)
    except OSError:
        return None
    return p.stdout.strip() if p.returncode == 0 and p.stdout.strip() else None


def today():
    return datetime.date.today().isoformat()


def is_date(value):
    """Whether value is a real calendar date written YYYY-MM-DD."""
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def split_footer(data):
    """(body, footer) of a saved source's bytes; footer is b'' when it has none."""
    marker = FOOTER_MARKER.encode()
    at = data.rfind(marker)
    if at < 0:
        return data, b''
    body = data[:at]
    sep = FOOTER_SEPARATOR.encode()
    if body.endswith(sep):
        body = body[:-len(sep)]
    return body, data[len(body):]


def md5(data):
    return hashlib.md5(data).hexdigest()


def source_hash(data):
    """The MD5 of a saved source's bytes without its footer: what narratives pin."""
    return md5(split_footer(data)[0])
