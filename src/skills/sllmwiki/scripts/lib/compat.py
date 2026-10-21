"""Markdown that GitHub, Obsidian, mdBook and Sphinx with MyST-Parser render alike
(design doc §4.8; AGENTS.md "Markdown compatibility").

check(text) lists what breaks it, as (severity, code, line, message):

  errors, which a renderer shows wrong:
    WIKILINK, EMBED        [[note]], ![[file]]: Obsidian links, plain text elsewhere
    CITATION_BRACKETS      [[3]](link): Obsidian reads [[3]] as a wikilink; write [\\[3\\]](link)
    HIGHLIGHT              ==text==: Obsidian only
    OBSIDIAN_COMMENT       %%text%%: Obsidian only
    CALLOUT                > [!info]: only GitHub's five alerts, alone on their line, render everywhere
    DOLLAR_MATH            a $$ block GitHub's markdown changes first: \\ before punctuation, or * by a character
    LINE_COMMENT           a % starting a line: a MyST comment, dropped by Sphinx; write \\%
    HEADING_ATTRS          {...} ending a heading: mdBook's id and classes; write ...\\}
    MDBOOK_DIRECTIVE       {{#include ...}}: expanded by mdBook, even in code; write \\{{#
  warnings, which renderers read differently:
    MATH_FENCE             a ```math block that renders the same as a $$ block, which Obsidian also renders
    INLINE_TAG             #word: an Obsidian tag
    BLOCK_ID               ^id ending a line: an Obsidian block ID
    LINE_JOINED            a bold line with text on the next: GitHub joins them
    BARE_URL               a bare URL: linked by GitHub and Obsidian, text in the books; write <url>
    EMOJI_SHORTCODE        :smile:: GitHub only
    DOLLAR_SIGN            $ before a number: Obsidian and MyST may start math; write \\$
    TILDE_STRIKE           ~text~: struck through by GitHub and mdBook only; write \\~
    MYST_SYNTAX            (label)=, +++, {role}`x`, ```{directive}: MyST only
    HEADING_LEVEL          a level skipped going down, or a second # title: Sphinx warns

escape(text) fixes what can be fixed mechanically: CITATION_BRACKETS,
LINE_COMMENT, HEADING_ATTRS, BARE_URL, DOLLAR_SIGN, TILDE_STRIKE and MATH_FENCE.
check_links(text, file_dir, root) lists LINK_SPACES, LINK_PATH and LINK_FOLDER.

Code is never checked or escaped: YAML front matter, fenced code, indented code
(four spaces or a tab after a blank line, outside a list, where the same indent
continues the item), code spans and $$ math. Only MDBOOK_DIRECTIVE looks inside
code, because mdBook expands it before reading the markdown. Every behavior here
was checked by rendering (tests/test_compat.py records where).
"""

import os
import re
import urllib.parse

GITHUB_ALERTS = ('NOTE', 'TIP', 'IMPORTANT', 'WARNING', 'CAUTION')

_FENCE = re.compile(r'( {0,3})(`{3,}|~{3,})[ \t]*([^\s`]*)')
_LIST = re.compile(r' {0,3}(?:[-*+]|[0-9]+[.)])(?:[ \t]|\Z)')
_HEADING = re.compile(r' {0,3}(#{1,6})(?:[ \t]|\Z)')
_CODE_SPAN = re.compile(r'(`+)(?!`).*?(?<!`)\1(?!`)')
_LINK_OR_AUTO = re.compile(r'!?\[[^\]\n]*\]\([^)\n]*\)|<[^>\n]+>')

_WIKILINK = re.compile(r'(?<![!\[\\])\[\[([^\[\]\n]+)\]\](?!\()')
_EMBED = re.compile(r'!\[\[([^\[\]\n]+)\]\]')
_OLD_CITE = re.compile(r'(?<![\\\[])\[\[([0-9]+)\]\]\(')
_HIGHLIGHT = re.compile(r'(?<![=\w])==(?=\S)([^=\n]*?\S)==(?![=\w])')
_CALLOUT = re.compile(r' {0,3}>[ \t]*\[!([^\]\n]+)\]([-+]?)(.*)\Z')
_TAG = re.compile(r'(?:(?<=\s)|^)#([A-Za-z_][\w/-]*)')
_BLOCK_ID = re.compile(r'\s\^([A-Za-z0-9-]+)[ \t]*\Z')
_BOLD_LINE = re.compile(r'[ \t]*\*\*[^*\n]+\*\*:?[ \t]*\Z')
_BLOCK_START = re.compile(r'[ \t]*(?:[|>#]|[-*+][ \t]|[0-9]+[.)][ \t]|```|~~~)')
_COMMENT = re.compile(r'((?:[ \t]*>)*[ \t]*(?:(?:[-*+]|[0-9]+[.)])[ \t]+)?)%(?!%)')
_ATTRS = re.compile(r'( {0,3}#{1,6}[ \t].*?)(\{[^{}]*?)(?<!\\)\}([ \t]*#*[ \t]*)\Z')
_DIRECTIVE = re.compile(r'(?<!\\)\{\{#[ \t]*(include|rustdoc_include|playground|playpen|title)\b')
_URL = re.compile(r'(?<![\w/.@-])(?:https?://|www\.)[^\s<>]*[^\s<>.,;:!?\'")\]*_~]')
_EMOJI = re.compile(r'(?<![\w:/]):([a-z0-9_+-]*[a-z][a-z0-9_+-]*):(?![\w:])')
_DOLLAR = re.compile(r'(?<![\\$\w])\$(?=[0-9])')
_TILDES = re.compile(r'(?<![~\w\\])~(?=[^\s~])[^~\n]*?[^\s~\\]~(?![~\w])')
_MYST_LINE = re.compile(r'[ \t]*(?:\([^()\s]+\)=[ \t]*\Z|\+\+\+)')
_MYST_ROLE = re.compile(r'\{[A-Za-z][\w:.+-]*\}`')
_UNSAFE_IN_DOLLARS = re.compile(r'\\[!-/:-@\[-`{-~]|(?<=\S)\*|\*(?=\S)')
_ONE_LINE_DOLLARS = re.compile(r'[ \t]*\$\$(.+)\$\$[ \t]*\Z')


def _indent(line):
    expanded = line.expandtabs(4)
    return len(expanded) - len(expanded.lstrip(' '))


def scan(lines):
    """A kind for each line: 'front', 'fence' (opening, body and closing fence lines),
    'indented', 'math' ($$ lines and their body) or 'text'; and the set of text
    lines inside a list. A fence opener is marked 'open'."""
    kinds = ['text'] * len(lines)
    if lines and lines[0].strip() == '---':
        end = next((j for j in range(1, len(lines)) if lines[j].strip() in ('---', '...')), None)
        if end is not None:
            kinds[:end + 1] = ['front'] * (end + 1)
    listed = set()
    fence, math = None, False
    blank, in_list, indented = True, False, False
    for i, line in enumerate(lines):
        if kinds[i] == 'front':
            continue
        if fence:
            kinds[i] = 'fence'
            m = _FENCE.match(line)
            if m and m.group(2)[0] == fence[0] and len(m.group(2)) >= len(fence) and not m.group(3) and not line[m.end():].strip():
                fence = None
            continue
        if math:
            kinds[i] = 'math'
            math = line.strip() != '$$'
            continue
        if not line.strip():
            blank = True
            continue
        if _indent(line) >= 4 and not in_list and (blank or indented):
            kinds[i], indented, blank = 'indented', True, False
            continue
        indented = False
        m = _FENCE.match(line)
        if m:
            kinds[i], fence = 'open', m.group(2)
        elif line.strip() == '$$':
            kinds[i], math = 'math', True
        if _LIST.match(line):
            in_list = True
        elif _indent(line) == 0:
            in_list = False  # back at the margin: the list has ended
        if in_list and kinds[i] == 'text':
            listed.add(i)
        blank = False
    return kinds, listed


def mask_code_spans(line):
    """line with each code span's content replaced by spaces, so columns stay put."""
    return _CODE_SPAN.sub(lambda m: m.group(1) + ' ' * (len(m.group(0)) - 2 * len(m.group(1))) + m.group(1), line)


def _mask_links(line):
    """line with links, images and <autolinks> blanked: what's inside isn't prose."""
    return _LINK_OR_AUTO.sub(lambda m: ' ' * len(m.group(0)), line)


def _is_comment(line, i, listed):
    """MyST reads % as a comment within three spaces of its container's margin;
    four spaces into a paragraph outside a list, it's text."""
    m = _COMMENT.match(line)
    if m and not _HEADING.match(line) and (_indent(line) < 4 or i in listed):
        return m
    return None


def _bare_urls(line):
    """(start, end) of each bare URL in a masked line; a ) closing a ( inside the URL is part of it."""
    masked = _mask_links(line)
    out = []
    for m in _URL.finditer(masked):
        end = m.end()
        while end < len(line) and line[end] == ')' and line[m.start():end].count('(') > line[m.start():end].count(')'):
            end += 1
        out.append((m.start(), end))
    return out


def dollar_safe(body):
    """Whether these math lines render the same in a $$ block on GitHub."""
    return not any(_UNSAFE_IN_DOLLARS.search(line) for line in body)


def _math_blocks(lines, kinds):
    """(first line, body lines) of each $$ block, one-line $$...$$ included."""
    i = 0
    while i < len(lines):
        if kinds[i] == 'math' and lines[i].strip() == '$$':
            j = i + 1
            while j < len(lines) and lines[j].strip() != '$$':
                j += 1
            yield i, lines[i + 1:j]
            i = j + 1
            continue
        m = _ONE_LINE_DOLLARS.match(lines[i]) if kinds[i] == 'text' else None
        if m:
            yield i, [m.group(1)]
        i += 1


def _math_fences(lines, kinds):
    """(opening line, closing line) of each ```math block that a $$ block renders the same."""
    for i, kind in enumerate(kinds):
        m = _FENCE.match(lines[i]) if kind == 'open' else None
        if m and m.group(3).lower() == 'math':
            j = i + 1
            while j < len(lines) and kinds[j] == 'fence' and not (_FENCE.match(lines[j]) and not _FENCE.match(lines[j]).group(3)):
                j += 1
            if j < len(lines) and kinds[j] == 'fence' and dollar_safe(lines[i + 1:j]):
                yield i, j


def check(text):
    """Findings (severity, code, line, message) for markdown the renderers read differently."""
    lines = text.split('\n')
    kinds, listed = scan(lines)
    out = []

    def add(sev, code, i, msg):
        out.append((sev, code, i + 1, msg))

    for i, line in enumerate(lines):  # mdBook expands these before reading the markdown, so code counts too
        m = _DIRECTIVE.search(line)
        if m:
            add('error', 'MDBOOK_DIRECTIVE', i, f'"{{{{#{m.group(1)}" is an mdBook directive, expanded even in code; write \\{{{{#')
        f = _FENCE.match(line) if kinds[i] == 'open' else None
        if f and f.group(3).startswith('{'):
            add('warning', 'MYST_SYNTAX', i, f'"{f.group(2)}{f.group(3)}" opens a MyST directive, which the other renderers show as code; use a plain fence')
    for start, body in _math_blocks(lines, kinds):
        if not dollar_safe(body):
            add('error', 'DOLLAR_MATH', start, 'GitHub runs markdown over a $$ block first: a \\ before punctuation loses it and a * by a character '
                'becomes emphasis; rewrite without them (\\ast for *), or use a ```math block')
    for start, _ in _math_fences(lines, kinds):
        add('warning', 'MATH_FENCE', start, 'this ```math block renders the same as a $$ block, which Obsidian renders too; write $$ (escape() does)')

    level, titles = 0, 0
    for i, raw in enumerate(lines):
        if kinds[i] != 'text':
            continue
        line = mask_code_spans(raw)
        h = _HEADING.match(line)
        if h:
            new = len(h.group(1))
            titles += new == 1
            if level and new > level + 1:
                add('warning', 'HEADING_LEVEL', i, f'a level-{new} heading after a level-{level} one: Sphinx warns; don\'t skip a level')
            elif new == 1 and titles == 2:
                add('warning', 'HEADING_LEVEL', i, 'a second # title: Sphinx titles the page from the first; use ## for sections')
            level = new
        if _is_comment(line, i, listed):
            add('error', 'LINE_COMMENT', i, 'a % starting a line is a MyST comment, which Sphinx drops; write \\%')
        m = _ATTRS.match(line)
        if m:
            add('error', 'HEADING_ATTRS', i, f'"{m.group(2)}}}" ending a heading is read by mdBook as its id and classes; write \\}}')
        if _MYST_LINE.match(line) or [r for r in _MYST_ROLE.finditer(raw) if line[r.start()] == '{']:
            add('warning', 'MYST_SYNTAX', i, 'a MyST target "(label)=", break "+++" or role "{name}`x`", which the other renderers show as text')
        for m in _OLD_CITE.finditer(line):
            add('error', 'CITATION_BRACKETS', i, f'"[[{m.group(1)}]](" reads as a wikilink in Obsidian; write [\\[{m.group(1)}\\]]( (escape() does)')
        for m in _EMBED.finditer(line):
            add('error', 'EMBED', i, f'"![[{m.group(1)}]]" is an Obsidian embed, text elsewhere; use ![alt](path)')
        for m in _WIKILINK.finditer(line):
            add('error', 'WIKILINK', i, f'"[[{m.group(1)}]]" is an Obsidian wikilink, text elsewhere; use [text](file.md#heading)')
        for m in _HIGHLIGHT.finditer(line):
            add('error', 'HIGHLIGHT', i, f'"=={m.group(1)}==" is an Obsidian highlight; use **bold**')
        if '%%' in line:
            add('error', 'OBSIDIAN_COMMENT', i, '"%%" starts an Obsidian comment, text elsewhere; use <!-- ... -->')
        m = _CALLOUT.match(line)
        if m and (m.group(1).strip().upper() not in GITHUB_ALERTS or m.group(2) or m.group(3).strip()):
            add('error', 'CALLOUT', i, f'"[!{m.group(1)}]{m.group(2)}{m.group(3)}" isn\'t one of GitHub\'s alerts; use > [!NOTE], [!TIP], [!IMPORTANT], '
                '[!WARNING] or [!CAUTION], alone on its line')
        plain = _mask_links(line)
        if not h:
            for m in _TAG.finditer(plain):
                add('warning', 'INLINE_TAG', i, f'"#{m.group(1)}" becomes an Obsidian tag; put it in backticks or reword it')
        m = _BLOCK_ID.search(plain)
        if m:
            add('warning', 'BLOCK_ID', i, f'"^{m.group(1)}" ending a line is an Obsidian block ID')
        for start, end in _bare_urls(line):
            add('warning', 'BARE_URL', i, f'"{line[start:end]}": the books show a bare URL as text; write <{line[start:end]}>')
        for m in _EMOJI.finditer(plain):
            add('warning', 'EMOJI_SHORTCODE', i, f'":{m.group(1)}:" renders only on GitHub; write the emoji, or reword it')
        if _DOLLAR.search(plain):
            add('warning', 'DOLLAR_SIGN', i, 'a $ before a number can start math in Obsidian and MyST; write \\$')
        for m in _TILDES.finditer(plain):
            add('warning', 'TILDE_STRIKE', i, f'"{m.group(0)}": GitHub and mdBook strike it through, Obsidian and MyST don\'t; write \\~')
        nxt = i + 1
        if _BOLD_LINE.match(line) and nxt < len(lines) and kinds[nxt] == 'text' and lines[nxt].strip() and not _BLOCK_START.match(lines[nxt]):
            add('warning', 'LINE_JOINED', i, 'GitHub joins this bold line with the next; put a blank line between them')
    return sorted(out, key=lambda f: f[2])


def _escape_prose(line):
    """(line, count) with the inline fixes applied outside code spans and links."""
    n = 0
    for start, end in reversed(_bare_urls(mask_code_spans(line))):
        line = line[:start] + '<' + line[start:end] + '>' + line[end:]
        n += 1
    masked = _mask_links(mask_code_spans(line))
    edits = [(m.start(), '\\') for m in _DOLLAR.finditer(masked)] + [(m.start(), '\\') for m in _TILDES.finditer(masked)]
    for at, ins in sorted(edits, reverse=True):
        line = line[:at] + ins + line[at:]
    n += len(edits)
    cites = list(_OLD_CITE.finditer(mask_code_spans(line)))
    for m in reversed(cites):
        line = line[:m.start()] + f'[\\[{m.group(1)}\\]](' + line[m.end():]
    return line, n + len(cites)


def escape(text):
    """(text, fixes) with every mechanical fix applied; code and math untouched."""
    lines = text.split('\n')
    kinds, listed = scan(lines)
    n = 0
    for start, end in list(_math_fences(lines, kinds)):
        indent = _FENCE.match(lines[start]).group(1)
        lines[start], lines[end] = indent + '$$', indent + '$$'
        n += 1
    for i, line in enumerate(lines):
        if kinds[i] != 'text':
            continue
        masked = mask_code_spans(line)
        m = _is_comment(masked, i, listed)
        if m:
            line = line[:m.end(1)] + '\\' + line[m.end(1):]
            n += 1
        m = _ATTRS.match(mask_code_spans(line))
        if m:
            line = line[:m.end(2)] + '\\}' + line[m.end(2) + 1:]
            n += 1
        line, k = _escape_prose(line)
        lines[i] = line
        n += k
    return '\n'.join(lines), n


_DEST = re.compile(r'\]\(([^)\n]*)\)')
_TITLE = re.compile(r'(\S+)[ \t]+("[^"]*"|\'[^\']*\')[ \t]*\Z')
_SCHEME = re.compile(r'[A-Za-z][A-Za-z0-9+.-]*:')


def check_links(text, file_dir, root):
    """Findings for links the renderers resolve differently, in a file in file_dir
    of the repository at root: LINK_SPACES (a space in a path, which GitHub doesn't
    read as a link; write %20), LINK_PATH (a path that doesn't resolve from the
    file's own folder, which is all GitHub tries), LINK_FOLDER (a link to a folder,
    which only GitHub lists)."""
    lines = text.split('\n')
    kinds, _ = scan(lines)
    out = []
    for i, line in enumerate(lines):
        if kinds[i] != 'text':
            continue
        for m in _DEST.finditer(mask_code_spans(line)):
            dest = m.group(1).strip()
            t = _TITLE.match(dest)
            path = t.group(1) if t else dest
            if path.startswith('<') and path.endswith('>'):
                path = path[1:-1]
            if not path or path.startswith('#') or _SCHEME.match(path):
                continue
            if re.search(r'\s', path):
                out.append(('error', 'LINK_SPACES', i + 1, f'"{path}": write each space as %20: {urllib.parse.quote(path, safe="/#%")}'))
                continue
            if re.search(r'<|>|\{\{|…', path):
                continue  # a template's placeholder, not a path
            file = urllib.parse.unquote(path.split('#')[0].split('?')[0])
            if not file:
                continue
            target = os.path.normpath(os.path.join(root if file.startswith('/') else file_dir, file.lstrip('/')))
            if os.path.isdir(target):
                out.append(('warning', 'LINK_FOLDER', i + 1, f'"{path}" is a folder: only GitHub lists it; link to a file in it'))
            elif not os.path.exists(target):
                named = [os.path.join(d, os.path.basename(file)) for d, _, files in os.walk(root)
                         if os.path.basename(file) in files and '/.' not in d.replace(os.sep, '/') + '/']
                found = os.path.join(root, file.lstrip('/')) if os.path.exists(os.path.join(root, file.lstrip('/'))) else (named[0] if len(named) == 1 else None)
                hint = f'; write {os.path.relpath(found, file_dir).replace(os.sep, "/")}' if found else ''
                out.append(('error', 'LINK_PATH', i + 1, f'"{path}" doesn\'t resolve from this file\'s folder, which is all GitHub tries{hint}'))
    return out
