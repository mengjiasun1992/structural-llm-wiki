"""Minimal TOML reader and editor for a wiki's Config.toml.

Python 3.9 and 3.10 have no tomllib, and the scripts use only the standard
library, so this reads the subset Config.toml needs: comments, [tables] and
[dotted.tables], bare and quoted keys, basic and literal strings, integers,
booleans, arrays (over several lines, with a trailing comma) and inline
tables. Anything else is an error, with its line number.

set_value() changes one value in place and keeps the file's comments and
layout, so the scripts can update settings the user also edits by hand.
"""

import re


class TomlError(Exception):
    pass


_BARE = re.compile(r'[A-Za-z0-9_-]+')
_INT = re.compile(r'[+-]?[0-9](?:_?[0-9])*')
_ESCAPES = {'b': '\b', 't': '\t', 'n': '\n', 'f': '\f', 'r': '\r', '"': '"', '\\': '\\'}


class _Parser:
    def __init__(self, text):
        self.s = text.replace('\r\n', '\n')
        self.i = 0

    @property
    def line(self):
        return self.s.count('\n', 0, self.i) + 1

    def fail(self, msg):
        raise TomlError(f'line {self.line}: {msg}')

    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else ''

    def ws(self, newlines=False):
        """Skip spaces (and comments and newlines when newlines is set)."""
        while self.i < len(self.s):
            c = self.s[self.i]
            if c in ' \t' or (newlines and c == '\n'):
                self.i += 1
            elif c == '#':
                while self.i < len(self.s) and self.s[self.i] != '\n':
                    self.i += 1
            else:
                break

    def end_of_line(self):
        self.ws()
        if self.peek() not in ('', '\n'):
            self.fail(f'unexpected "{self.peek()}" after the value')

    def key(self):
        parts = []
        while True:
            self.ws()
            c = self.peek()
            if c in '"\'':
                parts.append(self.string())
            else:
                m = _BARE.match(self.s, self.i)
                if not m:
                    self.fail('expected a key')
                parts.append(m.group())
                self.i = m.end()
            self.ws()
            if self.peek() != '.':
                return parts
            self.i += 1

    def string(self):
        quote = self.peek()
        if self.s.startswith(quote * 3, self.i):
            self.fail('multi-line strings are not supported in Config.toml')
        self.i += 1
        out = []
        while True:
            c = self.peek()
            if c in ('', '\n'):
                self.fail('unterminated string')
            self.i += 1
            if c == quote:
                return ''.join(out)
            if c == '\\' and quote == '"':
                e = self.peek()
                self.i += 1
                if e in _ESCAPES:
                    out.append(_ESCAPES[e])
                elif e in 'uU':
                    n = 4 if e == 'u' else 8
                    digits = self.s[self.i:self.i + n]
                    if not re.fullmatch(r'[0-9A-Fa-f]{%d}' % n, digits):
                        self.fail(f'bad \\{e} escape')
                    out.append(chr(int(digits, 16)))
                    self.i += n
                else:
                    self.fail(f'unknown escape "\\{e}"')
            else:
                out.append(c)

    def value(self):
        self.ws()
        c = self.peek()
        if c in '"\'':
            return self.string()
        if c == '[':
            self.i += 1
            items = []
            while True:
                self.ws(newlines=True)
                if self.peek() == ']':
                    self.i += 1
                    return items
                items.append(self.value())
                self.ws(newlines=True)
                if self.peek() == ',':
                    self.i += 1
                elif self.peek() != ']':
                    self.fail('expected "," or "]" in an array')
        if c == '{':
            self.i += 1
            table = {}
            self.ws()
            if self.peek() == '}':
                self.i += 1
                return table
            while True:
                parts = self.key()
                if self.peek() != '=':
                    self.fail('expected "=" after the key')
                self.i += 1
                self.assign(table, parts, self.value())
                self.ws()
                if self.peek() == '}':
                    self.i += 1
                    return table
                if self.peek() != ',':
                    self.fail('expected "," or "}" in an inline table')
                self.i += 1
        for word, val in (('true', True), ('false', False)):
            if self.s.startswith(word, self.i) and not _BARE.match(self.s, self.i + len(word)):
                self.i += len(word)
                return val
        m = _INT.match(self.s, self.i)
        if m and not re.match(r'[.eE:T-]', self.s[m.end():m.end() + 1]):
            self.i = m.end()
            return int(m.group().replace('_', ''))
        self.fail('expected a string, number, true/false, array or inline table')

    def assign(self, table, parts, val):
        for p in parts[:-1]:
            table = table.setdefault(p, {})
            if not isinstance(table, dict):
                self.fail(f'"{p}" is already a value, not a table')
        if parts[-1] in table:
            self.fail(f'duplicate key "{".".join(parts)}"')
        table[parts[-1]] = val

    def parse(self):
        root, seen = {}, set()
        current = root
        while True:
            self.ws(newlines=True)
            if self.i >= len(self.s):
                return root
            if self.peek() == '[':
                if self.s.startswith('[[', self.i):
                    self.fail('arrays of tables ([[…]]) are not supported in Config.toml')
                self.i += 1
                parts = self.key()
                if self.peek() != ']':
                    self.fail('expected "]" after the table name')
                self.i += 1
                self.end_of_line()
                name = '.'.join(parts)
                if name in seen:
                    self.fail(f'table [{name}] is defined twice')
                seen.add(name)
                current = root
                for p in parts:
                    current = current.setdefault(p, {})
                    if not isinstance(current, dict):
                        self.fail(f'"{p}" is already a value, not a table')
                continue
            parts = self.key()
            if self.peek() != '=':
                self.fail('expected "=" after the key')
            self.i += 1
            self.assign(current, parts, self.value())
            self.end_of_line()


def loads(text):
    """Parse TOML text (the subset above) into a dict."""
    return _Parser(text).parse()


def dumps_value(v):
    """A value as TOML: strings, integers, booleans and lists of them."""
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return '"' + ''.join('\\' + c if c in '"\\' else ('\\n' if c == '\n' else c) for c in v) + '"'
    if isinstance(v, (list, tuple)):
        return '[' + ', '.join(dumps_value(x) for x in v) + ']'
    raise TypeError(f'cannot write {type(v).__name__} to Config.toml')


def set_value(text, table, key, value):
    """text with `key = value` set in [table], keeping comments and layout:
    the existing line's value is replaced (its trailing comment kept), or the
    line is added at the end of the table, or the table is added at the end."""
    lines = text.split('\n')
    start = None
    for n, line in enumerate(lines):
        m = re.match(r'\s*\[([^\[\]]+)\]\s*(#.*)?$', line)
        if m and m.group(1).strip() == table:
            start = n
            break
    new = f'{key} = {dumps_value(value)}'
    if start is None:
        body = text.rstrip('\n')
        return (body + '\n\n' if body else '') + f'[{table}]\n{new}\n'
    end = next((n for n in range(start + 1, len(lines)) if re.match(r'\s*\[', lines[n])), len(lines))
    for n in range(start + 1, end):
        m = re.match(r'(\s*)' + re.escape(key) + r'\s*=\s*', lines[n])
        if m:
            rest = lines[n][m.end():]
            p = _Parser(rest)
            try:
                p.value()
            except TomlError:
                p.i = len(rest)
            comment = rest[p.i:].strip()
            line = m.group(1) + new
            if comment.startswith('#'):  # keep the comment's column when there is room
                column = lines[n].index(comment, m.end())
                line += ' ' * max(2, column - len(line)) + comment
            lines[n] = line
            return '\n'.join(lines)
    insert = end
    while insert > start + 1 and lines[insert - 1].strip() == '':
        insert -= 1
    lines.insert(insert, new)
    return '\n'.join(lines)
