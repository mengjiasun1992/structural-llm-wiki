"""What a run cost (design doc §5.3): its model, its time since sllmwiki publish start,
and the turns and tokens of this session's API requests since then, read from the
session's own transcript; and what it saved, from the caller. A session knows its tokens, not its price, so dollars
come only from the caller.
"""

import datetime
import glob
import json
import os
import re

TOKENS_IN = ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def parse_time(text):
    """A transcript or state timestamp as an aware datetime, or None."""
    if not isinstance(text, str):
        return None
    try:
        t = datetime.datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)


def transcript(session_id=None, config_dir=None):
    """This Claude Code session's transcript file, or None."""
    session_id = session_id or os.environ.get('CLAUDE_CODE_SESSION_ID')
    if not session_id or not re.fullmatch(r'[\w-]+', session_id):
        return None
    base = config_dir or os.environ.get('CLAUDE_CONFIG_DIR') or os.path.join(os.path.expanduser('~'), '.claude')
    found = sorted(glob.glob(os.path.join(base, 'projects', '*', f'{session_id}.jsonl')))
    return found[0] if found else None


_REPLIES = {}  # path -> ((mtime, size), replies): a PR's Run section asks for the model and the usage


def _replies(path):
    """The transcript's assistant entries, parsed once per state of the file; None if unreadable."""
    try:
        st = os.stat(path)
    except (OSError, TypeError):
        return None
    stamp = (st.st_mtime_ns, st.st_size)
    if path not in _REPLIES or _REPLIES[path][0] != stamp:
        replies = []
        try:
            with open(path, encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                    except ValueError:
                        continue
                    if isinstance(entry, dict) and entry.get('type') == 'assistant':
                        replies.append(entry)
        except OSError:
            return None
        _REPLIES[path] = (stamp, replies)
    return _REPLIES[path][1]


def model(path):
    """The model of the session's latest reply, or None."""
    found = None
    for entry in _replies(path) or ():
        name = (entry.get('message') or {}).get('model')
        if isinstance(name, str) and name != '<synthetic>':  # <synthetic>: a reply the CLI wrote itself, such as an error
            found = name
    return found


def usage(path, since):
    """{'turns', 'tokens_in', 'cached', 'tokens_out'} for the requests after since, or None if unreadable.

    A request's reply can span several transcript lines that repeat its usage,
    so each request counts once."""
    replies = _replies(path)
    if replies is None:
        return None
    requests = {}
    for entry in replies:
        at = parse_time(entry.get('timestamp'))
        u = (entry.get('message') or {}).get('usage')
        if at is not None and at >= since and isinstance(u, dict):
            requests[entry.get('requestId') or entry.get('uuid')] = u

    def total(keys):
        return sum(int(u.get(k) or 0) for u in requests.values() for k in keys)
    return {'turns': len(requests), 'tokens_in': total(TOKENS_IN), 'cached': total(('cache_read_input_tokens',)),
            'tokens_out': total(('output_tokens',))}


def duration(seconds):
    minutes = max(0, round(seconds / 60))
    return f'{minutes // 60} h {minutes % 60} min' if minutes >= 60 else f'{minutes} min'


def section(started, cost=None, at=None, path=None, saved=()):
    """The pull request's "Run" section, as lines; saved: lines saying what the run saved."""
    at = at or now()
    start = parse_time(started)
    lines = ['## Run', '']
    name = model(path)
    if name:
        lines.append(f'- Model: {name}')
    lines.append(f'- Time: {duration((at - start).total_seconds())} since the run started' if start else '- Time: not recorded')
    stats = usage(path, start) if path and start else None
    if stats:
        lines.append(f'- Turns: {stats["turns"]:,}; tokens: {stats["tokens_in"]:,} in ({stats["cached"]:,} of them from the cache), '
                     f'{stats["tokens_out"]:,} out (this session only, not its subagents)')
    elif not start:
        lines.append('- Turns and tokens: not counted, since the run has no start time')
    else:
        lines.append('- Turns and tokens: no session transcript to read them from')
    lines += list(saved)
    if cost is not None:
        lines.append(f'- Cost: ${cost:,.2f}')
    return lines
