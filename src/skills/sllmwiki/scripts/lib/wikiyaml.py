"""Minimal YAML reader for sllmwiki files (tags.yaml and the two manifests).

Supported subset: block mappings, block sequences of scalars, flow sequences of
scalars ([a, "b"]), the empty flow mapping {}, quoted and plain scalars, null/~,
booleans, numbers, and # comments. Anything else raises YamlError with a line
number, so a wiki file is never misread silently.

Writing is done with targeted line edits (see set_field) so comments and key
order are preserved; files are never re-serialized.
"""

import json
import re

from .util import WS, jstr, trim, trim_end


class YamlError(Exception):
    def __init__(self, message, line=None):
        super().__init__(f'line {line}: {message}' if line else message)
        self.line = line


_WS1 = re.compile(WS)


def _strip_comment(text):
    quote = None
    i = 0
    while i < len(text):
        c = text[i]
        if quote:
            if c == '\\' and quote == '"':
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in ('"', "'"):
            quote = c
        elif c == '#' and (i == 0 or _WS1.match(text[i - 1])):
            return text[:i]
        i += 1
    return text


_INT = re.compile(r'[-+]?[0-9]+\Z')
_FLOAT = re.compile(r'[-+]?([0-9]+\.[0-9]*|\.[0-9]+)([eE][-+]?[0-9]+)?\Z')
_RESERVED = re.compile(r'[&*!|>%@`]')


def _parse_scalar(raw, line):
    s = trim(raw)
    if s in ('', '~', 'null'):
        return None
    if s == 'true':
        return True
    if s == 'false':
        return False
    if s.startswith('"'):
        if not s.endswith('"') or len(s) < 2:
            raise YamlError(f'unterminated double-quoted string: {s}', line)
        try:
            return json.loads(s)
        except ValueError:
            raise YamlError(f'invalid double-quoted string: {s}', line) from None
    if s.startswith("'"):
        if not s.endswith("'") or len(s) < 2:
            raise YamlError(f'unterminated single-quoted string: {s}', line)
        return s[1:-1].replace("''", "'")
    if s == '[]':
        return []
    if s == '{}':
        return {}
    if s.startswith('['):
        return _parse_flow_seq(s, line)
    if s.startswith('{'):
        raise YamlError('non-empty flow mappings are not supported', line)
    if _INT.match(s):
        return int(s)
    if _FLOAT.match(s):
        v = float(s)
        return int(v) if v.is_integer() and abs(v) < 2**53 else v  # JavaScript has one number type
    if _RESERVED.match(s):
        raise YamlError(f'unsupported YAML syntax: {s}', line)
    return s


def _parse_flow_seq(s, line):
    if not s.endswith(']'):
        raise YamlError(f'unterminated flow sequence: {s}', line)
    inner = s[1:-1]
    items = []
    cur = ''
    quote = None
    i = 0
    while i < len(inner):
        c = inner[i]
        if quote:
            cur += c
            if c == '\\' and quote == '"':
                i += 1
                cur += inner[i] if i < len(inner) else ''
                i += 1
                continue
            if c == quote:
                quote = None
        elif c in ('"', "'"):
            quote = c
            cur += c
        elif c in ('[', '{'):
            raise YamlError('nested flow collections are not supported', line)
        elif c == ',':
            items.append(cur)
            cur = ''
        else:
            cur += c
        i += 1
    if quote:
        raise YamlError(f'unterminated string in flow sequence: {s}', line)
    if trim(cur) != '' or items:
        items.append(cur)
    out = []
    for it in items:
        if trim(it) == '':
            raise YamlError(f'empty item in flow sequence: {s}', line)
        out.append(_parse_scalar(it, line))
    return out


_KEY = re.compile(rf'([^{WS[1:-1]}:#][^:#]*?){WS}*:({WS}|\Z)(.*)\Z', re.S)


def _split_key(text, line):
    """(key, rest) for "key: rest" / "key:", or None if the line is not a mapping entry."""
    if text.startswith('"') or text.startswith("'"):
        q = text[0]
        end = 1
        while end < len(text) and not (text[end] == q and text[end - 1] != '\\'):
            end += 1
        if end >= len(text):
            raise YamlError(f'unterminated quoted key: {text}', line)
        key = _parse_scalar(text[: end + 1], line)
        rest = text[end + 1 :]
        if not rest.startswith(':'):
            return None
        rest = rest[1:]
    else:
        m = _KEY.match(text)
        if not m:
            return None
        key, rest = m.group(1), m.group(3)
    return jstr(key), rest


_LEAD_WS = re.compile(rf'{WS}*')
_LEAD_SP = re.compile(r' *')
_LINES = re.compile(r'\r?\n')


def _is_seq_item(text):
    return text.startswith('- ') or text == '-'


def parse_yaml(source):
    lines = []
    for idx, raw in enumerate(_LINES.split(source)):
        if '\t' in _LEAD_WS.match(raw).group(0):
            raise YamlError('tabs are not allowed in indentation', idx + 1)
        text = trim_end(_strip_comment(raw))
        if trim(text) in ('', '---'):
            continue
        lines.append({'indent': len(_LEAD_SP.match(text).group(0)), 'text': trim(text), 'line': idx + 1})

    if not lines:
        return None
    if lines[0]['indent'] == 0 and lines[0]['text'] in ('{}', '[]'):
        if len(lines) > 1:
            raise YamlError(
                f'content after "{lines[0]["text"]}": the file starts with an empty-collection placeholder and then continues. '
                'Remove the placeholder line.',
                lines[1]['line'],
            )
        return {} if lines[0]['text'] == '{}' else []

    pos = 0

    def parse_block(indent):
        return parse_seq(indent) if _is_seq_item(lines[pos]['text']) else parse_map(indent)

    def parse_seq(indent):
        nonlocal pos
        out = []
        while pos < len(lines) and lines[pos]['indent'] == indent and _is_seq_item(lines[pos]['text']):
            text, line = lines[pos]['text'], lines[pos]['line']
            item = '' if text == '-' else text[2:]
            if trim(item) == '' or _split_key(trim(item), line):
                raise YamlError('only scalar sequence items are supported', line)
            out.append(_parse_scalar(item, line))
            pos += 1
        if pos < len(lines) and lines[pos]['indent'] > indent:
            raise YamlError('unexpected indentation inside a sequence', lines[pos]['line'])
        return out

    def parse_map(indent):
        nonlocal pos
        out = {}
        while pos < len(lines) and lines[pos]['indent'] == indent:
            text, line = lines[pos]['text'], lines[pos]['line']
            if text.startswith('- '):
                raise YamlError('sequence item where a mapping key was expected', line)
            kv = _split_key(text, line)
            if not kv:
                raise YamlError(f'expected "key: value", got: {text}', line)
            key, rest = kv
            if key in out:
                raise YamlError(f'duplicate key "{key}"', line)
            pos += 1
            if trim(rest) != '':
                out[key] = _parse_scalar(rest, line)
            elif pos < len(lines) and lines[pos]['indent'] > indent:
                out[key] = parse_block(lines[pos]['indent'])
            elif pos < len(lines) and lines[pos]['indent'] == indent and lines[pos]['text'].startswith('- '):
                out[key] = parse_seq(indent)
            else:
                out[key] = None
        if pos < len(lines) and lines[pos]['indent'] > indent:
            raise YamlError('unexpected indentation', lines[pos]['line'])
        return out

    result = parse_block(lines[0]['indent'])
    if pos < len(lines):
        raise YamlError('unexpected content (check indentation)', lines[pos]['line'])
    return result


def _indent_of_first_child(lines, start):
    for i in range(start + 1, len(lines)):
        t = trim(lines[i])
        if t == '' or t.startswith('#'):
            continue
        return len(_LEAD_SP.match(lines[i]).group(0))
    return -1


def set_field(source, entry, field, value):
    """Replace the value of `field` inside the top-level entry `entry`, keeping
    everything else (comments, order, formatting) unchanged. Returns the new
    text, or None if the field was not found."""
    lines = source.split('\n')
    _, i, m = _find_field(lines, entry, field)
    if not m:
        return None
    comment = re.match(rf'[^#]*?({WS}*#.*)?\Z', m.group(3), re.S).group(1)
    lines[i] = m.group(1) + m.group(2) + jstr(value) + (comment or '')
    return '\n'.join(lines)


# ---- targeted writers --------------------------------------------------------
# These edit YAML text in place (never re-serialize), so comments, blank lines
# and key order survive. They only handle the shapes the wiki files use.

_PLAIN_SAFE = re.compile(r'[A-Za-z0-9_./@][A-Za-z0-9_./@ +-]*\Z')
_KEYWORD = re.compile(r'(true|false|null|yes|no|on|off|~)\Z', re.I | re.A)
_NUMBERISH = re.compile(r'[-+]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][-+]?[0-9]+)?\Z')


def format_scalar(v, quote=False):
    """Format a scalar for writing. Strings that could be misread are double-quoted."""
    if v is None:
        return 'null'
    if isinstance(v, (bool, int, float)):
        return jstr(v)
    s = jstr(v)
    plain_safe = bool(_PLAIN_SAFE.match(s)) and not _KEYWORD.match(s) and not _NUMBERISH.match(s) and not s.endswith(' ')
    return json.dumps(s, ensure_ascii=False) if quote or not plain_safe else s


def _entry_range(lines, entry):
    e = re.escape(entry)
    key_re = re.compile(rf'({e}|"{e}"){WS}*:{WS}*(#.*)?\Z', re.S)
    start = next((i for i, l in enumerate(lines) if key_re.match(l)), -1)
    if start < 0:
        return None
    end = start + 1
    while end < len(lines) and (trim(lines[end]) == '' or re.match(WS, lines[end]) or trim(lines[end]).startswith('#')):
        end += 1
    # trailing blank/comment lines belong to the gap, not the entry
    while end - 1 > start and (trim(lines[end - 1]) == '' or trim(lines[end - 1]).startswith('#')):
        end -= 1
    return {'start': start, 'end': end, 'child_indent': _indent_of_first_child(lines, start)}


def _find_field(lines, entry, field):
    """(entry range, line index, match) of `field` directly under top-level
    `entry`; the match's groups are the key with its colon, the spaces after
    it, and the rest of the line. A missing field gives (range, range end,
    None); a missing entry (None, None, None)."""
    r = _entry_range(lines, entry)
    if not r:
        return None, None, None
    if r['child_indent'] >= 0:
        field_re = re.compile(rf'( {{{r["child_indent"]}}}{re.escape(field)}{WS}*:)({WS}*)(.*)\Z', re.S)
        for i in range(r['start'] + 1, r['end']):
            m = field_re.match(lines[i])
            if m:
                return r, i, m
    return r, r['end'], None


def remove_entry(source, entry):
    """source without top-level entry `entry` (its key line and nested lines,
    and the blank line after it). Unchanged when there is no such entry."""
    lines = source.split('\n')
    r = _entry_range(lines, entry)
    if r is None:
        return source
    end = r['end']
    if end < len(lines) and trim(lines[end]) == '':
        end += 1
    return '\n'.join(lines[:r['start']] + lines[end:])


def replace_field_block(source, entry, field, new_lines):
    """Replace field `field` of top-level entry `entry` (its line and any nested
    lines under it) with `new_lines` (already indented). Appends the field at
    the end of the entry if it is missing."""
    lines = source.split('\n')
    r, i, m = _find_field(lines, entry, field)
    if not r:
        return None
    ind = r['child_indent']
    if not m:
        lines[r['end'] : r['end']] = new_lines
        return '\n'.join(lines)
    j = i + 1
    while j < r['end'] and (trim(lines[j]) == '' or len(_LEAD_SP.match(lines[j]).group(0)) > ind):
        j += 1
    lines[i:j] = new_lines
    return '\n'.join(lines)


def append_entry(source, entry, fields):
    """Append a new top-level entry. `fields` is a list of (key, value) where
    value is a formatted scalar string or a list of already-indented lines for
    a nested block. Removes a lone `{}` placeholder."""
    text = re.sub(rf'\n?^\{{\}}{WS}*$', '', source, count=1, flags=re.M)
    if not text.endswith('\n'):
        text += '\n'
    out = [f'{entry}:']
    for k, v in fields:
        if isinstance(v, list):
            out.append(f'  {k}:')
            out.extend(v)
        else:
            out.append(f'  {k}: {v}')
    return re.sub(r'\n+\Z', '\n', text) + '\n' + '\n'.join(out) + '\n'


def add_list_item(source, entry, field, item):
    """Add `item` to the list field `field` of entry `entry` (block or `[]`
    form). No-op if the item is already present."""
    lines = source.split('\n')
    r, i, m = _find_field(lines, entry, field)
    if not r:
        return None
    ind = r['child_indent']
    formatted = format_scalar(item)
    if not m:
        lines[r['end'] : r['end']] = [f"{' ' * ind}{field}:", f"{' ' * (ind + 2)}- {formatted}"]
        return '\n'.join(lines)
    head, rest = m.group(1), m.group(3)
    value = trim(_strip_comment(rest))
    if value in ('[]', ''):
        j = i + 1
        items = []
        while j < r['end'] and re.match(rf'{WS}*- ', lines[j]) and len(_LEAD_SP.match(lines[j]).group(0)) > ind:
            items.append(_parse_scalar(trim(lines[j])[2:], j + 1))
            j += 1
        if item in items:
            return source
        item_indent = len(_LEAD_SP.match(lines[i + 1]).group(0)) if j > i + 1 else ind + 2
        lines[i] = head
        lines[j:j] = [f"{' ' * item_indent}- {formatted}"]
        return '\n'.join(lines)
    if value.startswith('['):
        items = _parse_flow_seq(value, i + 1)
        if item in items:
            return source
        lines[i] = f"{head} [{', '.join(format_scalar(x) for x in [*items, item])}]"
        return '\n'.join(lines)
    raise YamlError(f'{entry}.{field} is not a list', i + 1)


def remove_list_item(source, entry, field, item):
    """Remove `item` from the list field `field` of entry `entry` (block or
    flow form); an emptied list becomes `[]`. No-op if it isn't there."""
    lines = source.split('\n')
    r, i, m = _find_field(lines, entry, field)
    if not r:
        return None
    ind = r['child_indent']
    if not m:
        return source
    head, value = m.group(1), trim(_strip_comment(m.group(3)))
    if value.startswith('['):
        items = _parse_flow_seq(value, i + 1)
        if item not in items:
            return source
        lines[i] = f"{head} [{', '.join(format_scalar(x) for x in items if x != item)}]"
        return '\n'.join(lines)
    if value != '':
        raise YamlError(f'{entry}.{field} is not a list', i + 1)
    j, kept, found = i + 1, [], False
    while j < r['end'] and re.match(rf'{WS}*- ', lines[j]) and len(_LEAD_SP.match(lines[j]).group(0)) > ind:
        if _parse_scalar(trim(lines[j])[2:], j + 1) == item:
            found = True
        else:
            kept.append(lines[j])
        j += 1
    if not found:
        return source
    lines[i:j] = [head, *kept] if kept else [f'{head} []']
    return '\n'.join(lines)
