"""The YAML the skill writes: tags.yaml and the two manifests (design doc §4.6).

A file is a mapping of entries, each a mapping of fields. Values are:
  - scalars: null, true, false, whole numbers, "double-quoted" (JSON escapes),
    'single-quoted' ('' for a quote) and plain strings;
  - lists of scalars, written [a, b] or as "- item" lines one level deeper;
  - mappings, as "key: value" lines one level deeper, or {} when empty.
Each level is indented two spaces. Comments are whole lines or " # ..." after a
value. Anything else (tabs, anchors and aliases, tags, | and > blocks,
non-empty flow mappings, lists of mappings, plain words YAML 1.1 reads as
booleans or numbers, repeated keys) is a YamlError naming its line, so a file
is never misread silently.

The writer re-renders one entry at a time (upsert_entry, remove_entry), so the
file's other entries and its comments between entries are kept as they are.
"""

import json
import re

_KEY = r'[A-Za-z0-9_][A-Za-z0-9_.-]*'
_LINE = re.compile(rf'( *)({_KEY}):(?: +(.*))?\Z')
_ITEM = re.compile(r'( *)- +(.*)\Z')
_INT = re.compile(r'[+-]?[0-9]+\Z')
# plain words YAML 1.1 parsers (PyYAML) read as booleans, numbers or dates
_RESERVED = re.compile(r'(?i)(y|n|yes|no|on|off|true|false|null|~)\Z|[+-]?(\.[0-9]+|[0-9]+\.[0-9]*)([eE][+-]?[0-9]+)?\Z|[+-]?\.(inf|nan)\Z|0[xob]'
                       r'|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}([Tt ]|\Z)|[0-9]+(:[0-5]?[0-9])+\Z')
_PLAIN_START = re.compile(r'[^\s\[\]{},&*!|>\'"%@`#?:-]|[?:-][^\s]')
_PLAIN_SAFE = re.compile(r'[A-Za-z0-9_./+@-][A-Za-z0-9_./+@:=,()?&%~ -]*\Z')


class YamlError(Exception):
    def __init__(self, line, msg):
        super().__init__(f'line {line}: {msg}')
        self.line = line


def _quoted_spans(text):
    """Yield (index, char, inside_quotes) for text, minding \\ escapes in "..." and '' in '...'."""
    quote, escaped = None, False
    for i, c in enumerate(text):
        inside = quote is not None
        if quote == '"':
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == '"':
                quote = None
        elif quote == "'":
            if c == "'":
                quote = None
        elif c in '"\'':
            quote = c
        yield i, c, inside or quote is not None


def _strip_comment(text):
    """text without a trailing " # comment", minding quotes."""
    for i, c, quoted in _quoted_spans(text):
        if c == '#' and not quoted and (i == 0 or text[i - 1] in ' \t'):
            return text[:i].rstrip()
    return text.rstrip()


def _scalar(raw, n):
    if raw in ('null', '~'):
        return None
    if raw in ('true', 'false'):
        return raw == 'true'
    if _INT.match(raw):
        return int(raw)
    if raw.startswith('"'):
        try:
            value = json.loads(raw)
        except ValueError:
            raise YamlError(n, f'not one closed double-quoted string: {raw}') from None
        return value
    if raw.startswith("'"):
        if len(raw) < 2 or not raw.endswith("'") or "'" in raw[1:-1].replace("''", ''):
            raise YamlError(n, 'a single-quoted string must close on its line')
        return raw[1:-1].replace("''", "'")
    if raw.startswith(('|', '>')):
        raise YamlError(n, 'block scalars (| and >) aren\'t used; write one quoted line')
    if raw.startswith(('&', '*', '!')):
        raise YamlError(n, 'anchors, aliases and tags aren\'t used')
    if raw.startswith('{'):
        raise YamlError(n, 'flow mappings aren\'t used, except {} for an empty one')
    if _RESERVED.match(raw):
        raise YamlError(n, f'{raw} reads differently in YAML parsers: quote it')
    if not _PLAIN_START.match(raw) or ': ' in raw or raw.endswith(':'):
        raise YamlError(n, f'quote this value: {raw}')
    return raw


def _flow_list(raw, n):
    inner = raw[1:-1].strip()
    if not inner:
        return []
    items, buf, quoted = [], '', False
    for _, c, quoted in _quoted_spans(inner):
        if not quoted and c == ',':
            items.append(buf.strip())
            buf = ''
        elif not quoted and c in '[]{}':
            raise YamlError(n, 'a list holds scalars only')
        else:
            buf += c
    if quoted:
        raise YamlError(n, 'a quoted string in a list must close')
    if buf.strip():
        items.append(buf.strip())  # else a trailing comma
    if any(not item for item in items):
        raise YamlError(n, 'an empty item in a list')
    return [_scalar(item, n) for item in items]


def _value(raw, n):
    if raw == '{}':
        return {}
    if raw.startswith('['):
        if not raw.endswith(']'):
            raise YamlError(n, 'a [list] must close on its line')
        return _flow_list(raw, n)
    return _scalar(raw, n)


def parse(text):
    """The mapping in text; raises YamlError."""
    lines = []
    started = False
    for n, line in enumerate(text.split('\n'), 1):
        line = line.rstrip('\r')
        if '\t' in line[:len(line) - len(line.lstrip())]:
            raise YamlError(n, 'indent with spaces, not tabs')
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or stripped == '---' and not started:
            started = started or stripped == '---'
            continue
        if stripped in ('---', '...'):
            raise YamlError(n, 'one document per file')
        started = True
        lines.append((n, len(line) - len(line.lstrip(' ')), _strip_comment(line.strip())))
    if len(lines) == 1 and lines[0][2] == '{}' and lines[0][1] == 0:
        return {}
    return _block(lines, 0, 0)[0]  # _block reports any line it can't place


def _block(lines, at, indent):
    """(mapping, next index) for the lines at this indent."""
    out = {}
    while at < len(lines):
        n, ind, body = lines[at]
        if ind < indent:
            break
        if ind > indent:
            raise YamlError(n, 'unexpected indentation')
        if body.startswith('- ') or body == '-':
            raise YamlError(n, 'a list item needs a key above it')
        m = _LINE.match(' ' * ind + body)
        if not m:
            raise YamlError(n, f'expected "key: value": {body}')
        key, raw = m.group(2), m.group(3)
        if key in out:
            raise YamlError(n, f'{key} is repeated')
        at += 1
        if raw:
            out[key] = _value(raw, n)
            continue
        if at < len(lines) and lines[at][1] > ind:
            child = lines[at]
            if child[1] != ind + 2:
                raise YamlError(child[0], 'indent each level by two spaces')
            if child[2].startswith('- ') or child[2] == '-':
                out[key], at = _items(lines, at, ind + 2)
            else:
                out[key], at = _block(lines, at, ind + 2)
        else:
            out[key] = None
    return out, at


def _items(lines, at, indent):
    items = []
    while at < len(lines) and lines[at][1] == indent and (lines[at][2].startswith('- ') or lines[at][2] == '-'):
        n, ind, body = lines[at]
        m = _ITEM.match(body)
        if not m:
            raise YamlError(n, 'an empty list item')
        raw = m.group(2).strip()
        if _LINE.match(raw) and not raw.startswith(('"', "'")):
            raise YamlError(n, 'a list holds scalars only, not mappings')
        if raw.startswith('[') or raw == '{}':
            raise YamlError(n, 'a list holds scalars only')
        items.append(_scalar(raw, n))
        at += 1
    if at < len(lines) and lines[at][1] > indent:
        raise YamlError(lines[at][0], 'unexpected indentation')
    return items, at


def format_scalar(value):
    """A scalar as the writer writes it: plain when that reads back the same, else double-quoted."""
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, int):
        return str(value)
    if not isinstance(value, str):
        raise TypeError(f'not a scalar: {value!r}')
    if (_PLAIN_SAFE.match(value) and not value.endswith((' ', ':')) and ': ' not in value and ' #' not in value
            and not _RESERVED.match(value) and not _INT.match(value) and _PLAIN_START.match(value)):
        return value
    return json.dumps(value, ensure_ascii=False)


def _render(key, value, indent):
    pad = ' ' * indent
    if isinstance(value, dict):
        if not value:
            return [f'{pad}{key}: {{}}']
        lines = [f'{pad}{key}:']
        for k, v in value.items():
            lines += _render(k, v, indent + 2)
        return lines
    if isinstance(value, list):
        flow = '[' + ', '.join(format_scalar(v) for v in value) + ']'
        words = all(not isinstance(v, str) or ' ' not in v for v in value)  # tags, slugs: one line; sentences: one per line
        if words and len(pad) + len(key) + len(flow) <= 100:
            return [f'{pad}{key}: {flow}']
        return [f'{pad}{key}:'] + [f'{pad}  - {format_scalar(v)}' for v in value]
    return [f'{pad}{key}: {format_scalar(value)}']


def render_entry(key, fields):
    """An entry's lines, as text ending in a newline."""
    return '\n'.join(_render(key, fields, 0)) + '\n'


def _span(lines, key):
    """(start, end) of the entry's lines (end exclusive, before trailing blanks and comments), or None."""
    start = next((i for i, line in enumerate(lines) if re.match(rf'{re.escape(key)}:(\s|$)', line)), None)
    if start is None:
        return None
    end = start + 1
    last = start + 1
    while end < len(lines):
        line = lines[end]
        if line.strip() and not line.startswith((' ', '\t')):
            break
        if line.startswith((' ', '\t')) and line.strip() and not line.strip().startswith('#'):
            last = end + 1
        end += 1
    return start, last


def upsert_entry(text, key, fields):
    """text with the entry key rendered from fields: replaced where it is, else appended."""
    lines = text.split('\n')
    span = _span(lines, key)
    block = render_entry(key, fields).rstrip('\n').split('\n')
    if span:
        lines[span[0]:span[1]] = block
        return '\n'.join(lines)
    body = text.rstrip('\n')
    return (body + '\n\n' if body else '') + '\n'.join(block) + '\n'


def remove_entry(text, key):
    """text without the entry key (and the blank line after it); unchanged when it isn't there."""
    lines = text.split('\n')
    span = _span(lines, key)
    if not span:
        return text
    start, end = span
    while end < len(lines) - 1 and not lines[end].strip():
        end += 1
    del lines[start:end]
    return '\n'.join(lines)
