"""The TOML subset Config.toml uses (Python 3.9 has no tomllib).

Supported: comments; [table] and [dotted.table] headers of bare keys; bare
`key = value` lines; values that are basic "strings" (with \\ \" \n \t \r and
\\uXXXX escapes), 'literal strings', integers, true or false, and arrays of
them, which may span lines and end with a comma. Anything else (floats, dates,
inline tables, multi-line strings, dotted or quoted keys, arrays of tables) is
an error naming its line, never a silent misread.
"""

import json
import re

BARE = r'[A-Za-z0-9_-]+'
_HEADER = re.compile(rf'\[\s*({BARE}(?:\s*\.\s*{BARE})*)\s*\]\s*(?:#.*)?\Z')
_KEY = re.compile(rf'({BARE})\s*=\s*')
_INT = re.compile(r'[+-]?(?:0|[1-9][0-9]*)')
_ESCAPES = {'\\': '\\', '"': '"', 'n': '\n', 't': '\t', 'r': '\r'}


class TomlError(Exception):
    def __init__(self, line, msg):
        super().__init__(f'line {line}: {msg}')
        self.line = line


class _Reader:
    def __init__(self, text):
        self.text, self.i, self.line = text, 0, 1

    def error(self, msg):
        raise TomlError(self.line, msg)

    def peek(self):
        return self.text[self.i] if self.i < len(self.text) else ''

    def skip_space(self, newlines=False):
        while self.i < len(self.text):
            c = self.text[self.i]
            if c in ' \t':
                self.i += 1
            elif c == '#':
                while self.i < len(self.text) and self.text[self.i] != '\n':
                    self.i += 1
            elif newlines and c in '\r\n':
                self.line += c == '\n'
                self.i += 1
            else:
                break

    def value(self):
        c = self.peek()
        if c == '"':
            return self.basic_string()
        if c == "'":
            end = self.text.find("'", self.i + 1)
            if end < 0 or '\n' in self.text[self.i:end]:
                self.error('a literal string must close on its line')
            s, self.i = self.text[self.i + 1:end], end + 1
            return s
        if c == '[':
            return self.array()
        for word, val in (('true', True), ('false', False)):
            if self.text.startswith(word, self.i) and not re.match(r'[A-Za-z0-9_]', self.text[self.i + len(word):self.i + len(word) + 1]):
                self.i += len(word)
                return val
        m = _INT.match(self.text, self.i)
        if m and not re.match(r'[0-9A-Za-z_.:+-]', self.text[m.end():m.end() + 1]):
            self.i = m.end()
            return int(m.group(0))
        self.error('expected a string, a whole number, true or false, or an array (Config.toml uses no other values)')

    def basic_string(self):
        out = []
        self.i += 1
        while True:
            c = self.peek()
            if c in ('', '\n'):
                self.error('a string must close on its line')
            self.i += 1
            if c == '"':
                return ''.join(out)
            if c != '\\':
                out.append(c)
                continue
            e = self.peek()
            self.i += 1
            if e in _ESCAPES:
                out.append(_ESCAPES[e])
            elif e == 'u' and re.fullmatch(r'[0-9A-Fa-f]{4}', self.text[self.i:self.i + 4]):
                out.append(chr(int(self.text[self.i:self.i + 4], 16)))
                self.i += 4
            else:
                self.error(f'unknown escape \\{e}')

    def array(self):
        self.i += 1
        items = []
        while True:
            self.skip_space(newlines=True)
            if self.peek() == ']':
                self.i += 1
                return items
            if self.peek() == '':
                self.error('an array must close')
            items.append(self.value())
            self.skip_space(newlines=True)
            if self.peek() == ',':
                self.i += 1
            elif self.peek() == '':
                self.error('an array must close')
            elif self.peek() != ']':
                self.error('expected , or ] in an array')


def loads(text):
    """The tables and values in text, as nested dicts; raises TomlError."""
    data, table = {}, None
    defined = set()
    r = _Reader(text)
    while r.i < len(text):
        r.skip_space()
        c = r.peek()
        if c in ('\n', '\r'):
            r.line += c == '\n'
            r.i += 1
            continue
        if c == '':
            break
        end = text.find('\n', r.i)
        end = len(text) if end < 0 else end
        rest = text[r.i:end].rstrip('\r')
        if c == '[':
            if rest.startswith('[['):
                r.error('arrays of tables aren\'t used in Config.toml')
            m = _HEADER.match(rest)
            if not m:
                r.error(f'not a table header: {rest}')
            names = [n.strip() for n in m.group(1).split('.')]
            key = '.'.join(names)
            if key in defined:
                r.error(f'table [{key}] is defined twice')
            defined.add(key)
            table = data
            for n in names:
                nxt = table.setdefault(n, {})
                if not isinstance(nxt, dict):
                    r.error(f'[{key}] clashes with the value {n}')
                table = nxt
            r.i = end
            continue
        m = _KEY.match(text, r.i)
        if not m or m.start() != r.i:
            r.error(f'expected key = value: {rest}')
        target = data if table is None else table
        k = m.group(1)
        if k in target:
            r.error(f'{k} is set twice')
        r.i = m.end()
        target[k] = r.value()
        r.skip_space()
        if r.peek() not in ('', '\n', '\r'):
            r.error('expected the end of the line after a value')
    return data


def dumps_value(value):
    """A value written as Config.toml writes it."""
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return '[' + ', '.join(dumps_value(v) for v in value) + ']'
    raise TypeError(f'Config.toml has no {type(value).__name__} values')
