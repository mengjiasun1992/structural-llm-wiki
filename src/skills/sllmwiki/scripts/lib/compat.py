"""Narrative syntax that renders the same on GitHub, in Obsidian and in the
books (mdBook, and Sphinx with MyST-Parser).

- A citation is ` [\\[n\\]](<link>)`. The older ` [[n]](<link>)` renders the
  same on GitHub, but Obsidian reads `[[n]]` as a wikilink to a note named
  "n" (docs/obsidian_add_on_proposal.md).
- Display math is a `$$` block when that renders the same on GitHub: GitHub
  runs markdown over a `$$` block first, so a backslash before punctuation
  (`\\,`, `\\\\`, `\\{`, `\\_`, `\\&`) loses the backslash, and a `*` next to
  another character can turn into emphasis. A formula with them stays a
  ```math fence, which GitHub renders exactly and Obsidian shows as code.
  `&`, `_` subscripts, `\\alpha`, `\\left(` and a spaced ` * ` are fine
  (checked on github.com, 2026-10-20).

fix(text) rewrites the older forms (outside code and math) and changes
nothing else.
narrative-format reports them (CITATION_STYLE in lib/citations.py,
MATH_FENCE) and runs fix() for --fix-style.

check(text) finds markdown that renders differently in the two, outside code
and math:

- errors, Obsidian-only syntax that GitHub shows as plain text: a wikilink
  [[note]] (WIKILINK), an embed ![[file]] (EMBED), a ==highlight==
  (HIGHLIGHT), a %%comment%% (OBSIDIAN_COMMENT), and a callout GitHub has
  no alert for (CALLOUT: GitHub knows > [!NOTE], [!TIP], [!IMPORTANT],
  [!WARNING] and [!CAUTION], alone on their line);
- errors, a $$ block GitHub renders wrong: a backslash before punctuation
  or a * next to a character inside it (DOLLAR_MATH), which GitHub's
  markdown changes first;
- warnings: a #word, which Obsidian turns into a tag (INLINE_TAG); a
  ^block-id at the end of a line (BLOCK_ID); and a line of only bold text
  with text on the next line, which GitHub joins into one line
  (LINE_JOINED).

- errors, text a book renderer drops or rereads, everywhere but code:
  a line starting with % (LINE_COMMENT: a MyST comment, so Sphinx drops the
  line; write \\%), a heading ending in {…} (HEADING_ATTRS: mdBook takes it
  as the heading's id and classes; write …\\}), and {{#include …}} and the
  other mdBook directives, even in code (MDBOOK_DIRECTIVE; write \\{{#,
  which in code shows the backslash);
- warnings, syntax the renderers read differently: a bare URL (BARE_URL:
  GitHub and Obsidian link it, mdBook and Sphinx show text; write <url>), an
  emoji shortcode (EMOJI_SHORTCODE: only GitHub renders it; write the emoji),
  a $ before a number (DOLLAR_SIGN: Obsidian and MyST may start math there;
  write \\$), a pair of single tildes (TILDE_STRIKE: GitHub and mdBook strike
  the text through, Obsidian and MyST don't; write \\~), MyST's own syntax
  (MYST_SYNTAX: a (label)= target, a +++ break, a {role}`…` or a ```{name}
  directive fence, which GitHub shows as text), and a heading level that
  skips one or a second # title (HEADING_LEVEL: Sphinx warns and builds its
  table of contents from them).

Checked by rendering with mdBook 0.5.4 and Sphinx 9.1 with MyST-Parser 5.1
(2026-10-20). The book adapters configure the rest away: MyST's dollarmath,
amsmath and alert extensions and GitHub-style heading anchors; mdBook's
definition lists and smart punctuation off (a line starting with ": " after
a paragraph would become a definition).

escape(text) writes the backslashes the LINE_COMMENT, HEADING_ATTRS,
DOLLAR_SIGN and TILDE_STRIKE findings ask for and wraps bare URLs in <>;
each renders the same everywhere. narrative-format --fix-style runs it, and
the generated tag pages and index are written with it.

check_links(text, file_dir, root) finds links the renderers resolve differently:
a space in a link's path (LINK_SPACES; write %20), a relative path that
doesn't resolve from the file's own folder (LINK_PATH; Obsidian also finds
notes from the vault root or by name, GitHub doesn't), and a link to a folder
(LINK_FOLDER: GitHub lists it, the others find no page; link to a file).

Code is never checked or escaped: YAML front matter, fenced code, and an
indented code block (four spaces or a tab, after a blank line, outside a list,
whose indented lines continue the item instead; checked on GitHub, mdBook 0.5.4
and MyST-Parser 5.1, 2026-10-21).

narrative-format and obsidian-check.py report these.
"""

import os
import re
import urllib.parse

OLD_CITE = re.compile(r'\[\[([0-9]+)\]\]\(')
FENCE = re.compile(r'([ \t]*)(`{3,}|~{3,})[ \t]*([^`\s]*)[^`]*\Z')
CODE_SPAN = re.compile(r'(`+)[^`]*?\1')
UNSAFE_IN_DOLLARS = re.compile(r'\\[!-/:-@\[-`{-~]|(?<=\S)\*|\*(?=\S)')  # what GitHub's markdown changes inside a $$ block
WIKILINK = re.compile(r'(?<!!)\[\[([^\[\]\n]+)\]\](?!\()')  # not [[n]](link), the older citation
EMBED = re.compile(r'!\[\[([^\[\]\n]+)\]\]')
HIGHLIGHT = re.compile(r'(?<![=\w])==(?=\S)([^=\n]*?\S)==(?![=\w])')
CALLOUT = re.compile(r'[ \t]*>[ \t]*\[!([^\]\n]+)\]([-+]?)(.*)\Z')
GITHUB_ALERTS = {'NOTE', 'TIP', 'IMPORTANT', 'WARNING', 'CAUTION'}
INLINE_TAG = re.compile(r'(?:^|(?<=\s))#([A-Za-z_][\w/-]*)')
BLOCK_ID = re.compile(r'\s\^([A-Za-z0-9-]+)[ \t]*\Z')
BOLD_LINE = re.compile(r'[ \t]*\*\*[^*]+\*\*:?[ \t]*\Z')
NOT_PROSE = re.compile(r'[ \t]*([|>#*+-]|[0-9]+\.[ \t])')  # a table, quote, heading or list line
# What the book renderers read differently (checked on mdBook 0.5 and MyST-Parser 5.1 docs, 2026-10-20)
LINE_COMMENT = re.compile(r'([ \t]*(?:>[ \t]*)*(?:(?:[-*+]|\d+[.)])[ \t]+)?)%(?!%)')  # a MyST comment, after any quote or list marker
HEADING_ATTRS = re.compile(r'([ \t]*#{1,6}[ \t].*?)(\{[^{}]*?)(?<!\\)\}([ \t]*#*[ \t]*)\Z')  # mdBook's { #id .class }; \} stops it, \{ doesn't
MDBOOK_DIRECTIVE = re.compile(r'(?<!\\)\{\{#[ \t]*(include|rustdoc_include|playground|playpen|title)\b')
MYST_LINE = re.compile(r'[ \t]*(\([^()\s]+\)=[ \t]*\Z|\+\+\+)')  # a target, a block break
MYST_ROLE = re.compile(r'\{[A-Za-z][\w:.+-]*\}`')
HEADING = re.compile(r'[ \t]{0,3}(#{1,6})[ \t]')
EMOJI = re.compile(r'(?<![\w:/]):([a-z0-9_+-]*[a-z][a-z0-9_+-]*):(?![\w:])')
DOLLAR = re.compile(r'(?<![\\$\w])\$(?=\d[\d,.]*(?:[kKmMbB]|bn)?(?:[\s,;:)!?]|\Z))')  # $5, $1,000.
TILDES = re.compile(r'(?<![~\w\\])~(?=[^\s~])[^~\n]*?[^\s~\\]~(?![~\w])')
# a link (text and destination), a destination alone or an <autolink or tag>, left as is; else a bare URL
LIST_ITEM = re.compile(r'[ \t]{0,3}(?:[-*+]|\d+[.)])(?:[ \t]|\Z)')
LINK_OR_URL = re.compile(r'(\[[^\]\n]*\]\([^)\n]*\)|\]\([^)\n]*\)|<[^>\n]*>)|(?<![\w/.@-])((?:https?://|www\.)[^\s<>]*[^\s<>.,;:!?\'")\]*_~])')


def dollar_safe(body):
    """Whether a math fence's lines render the same as a $$ block on GitHub."""
    return not any(UNSAFE_IN_DOLLARS.search(line) for line in body)


def new_citations(line):
    """line with each older-form citation outside code spans rewritten; (line, count)."""
    out, at, n = [], 0, 0
    for m in list(CODE_SPAN.finditer(line)) + [None]:
        end = m.start() if m else len(line)
        part, k = OLD_CITE.subn(r'[\\[\1\\]](', line[at:end])
        out.append(part + (m.group(0) if m else ''))
        n += k
        at = m.end() if m else end
    return ''.join(out), n


def closing_fence(lines, start, marker):
    """The index of the line closing the fence opened at start with marker, or None."""
    for j in range(start + 1, len(lines)):
        m = FENCE.match(lines[j])
        if m and m.group(2)[0] == marker[0] and len(m.group(2)) >= len(marker) and not m.group(3):
            return j
    return None


def fix(text):
    """(text, citations rewritten, math fences rewritten)."""
    lines = text.split('\n')
    code = {i for i, kind in _code_lines(lines).items() if kind in ('front', 'indented')}  # fences are handled below
    cites = maths = 0
    fence = None  # (marker, is_math) of the open fence
    math = False  # inside a $$ block
    convert = set()  # opening lines of math fences safe to write as $$ blocks
    for i, line in enumerate(lines):
        m = FENCE.match(line)
        close = closing_fence(lines, i, m.group(2)) if m and m.group(3).lower() == 'math' else None
        if close is not None and dollar_safe(lines[i + 1:close]):
            convert.add(i)
    for i, line in enumerate(lines):
        if fence is None and line.strip() == '$$':
            math = not math
            continue
        m = FENCE.match(line)
        if m and fence is None:
            fence = (m.group(2), i in convert)
            if fence[1]:
                lines[i] = m.group(1) + '$$'
                maths += 1
            continue
        if m and fence and m.group(2)[0] == fence[0][0] and len(m.group(2)) >= len(fence[0]) and not m.group(3):
            if fence[1]:
                lines[i] = m.group(1) + '$$'
            fence = None
            continue
        if fence is None and not math and i not in code:
            lines[i], k = new_citations(line)
            cites += k
    return '\n'.join(lines), cites, maths


def _outside_code(line, change):
    """line with change(part) applied to each part outside code spans; (line, count)."""
    out, at, n = [], 0, 0
    for m in list(CODE_SPAN.finditer(line)) + [None]:
        end = m.start() if m else len(line)
        part, k = change(line[at:end])
        out.append(part + (m.group(0) if m else ''))
        n += k
        at = m.end() if m else end
    return ''.join(out), n


def _url_end(text, m):
    """The end of the bare URL m found: a ) closing a ( inside it belongs to it, as GitHub reads it."""
    end = m.end(2)
    while end < len(text) and text[end] == ')' and text[m.start(2):end].count('(') > text[m.start(2):end].count(')'):
        end += 1
    return end


def bare_urls(text):
    """(start, end) of each bare URL in text, outside links and <…>."""
    return [(m.start(2), _url_end(text, m)) for m in LINK_OR_URL.finditer(text) if m.group(2)]


def _escape_inline(part):
    n = 0
    spans = bare_urls(part)
    for start, end in reversed(spans):
        part = part[:start] + '<' + part[start:end] + '>' + part[end:]
    n += len(spans)
    part, k = DOLLAR.subn(r'\\$', part)
    n += k
    part, k = TILDES.subn(lambda m: '\\' + m.group(0), part)
    return part, n + k


def escape(text):
    """text with the book renderers' pitfalls escaped, outside code and math:
    a % starting a line, a {…} ending a heading, a $ before a number and a pair
    of single tildes get a backslash, and bare URLs get <>. (text, count)."""
    lines = text.split('\n')
    listed = _scan(lines)[1]
    n = 0
    for i, _ in list(_prose(lines)):
        line = lines[i]
        m = _comment(line, i, listed)
        if m:
            line = m.group(1) + '\\' + line[m.end(1):]
            n += 1
        m = HEADING_ATTRS.match(line)
        if m:
            line = m.group(1) + m.group(2) + '\\}' + m.group(3)
            n += 1
        line, k = _outside_code(line, _escape_inline)
        lines[i] = line
        n += k
    return '\n'.join(lines), n


def _front_matter_end(lines):
    """The index of the first line after a YAML front matter block (--- … --- at the top), else 0."""
    if lines and lines[0].strip() == '---':
        end = next((j for j in range(1, len(lines)) if lines[j].strip() in ('---', '...')), None)
        if end is not None:
            return end + 1
    return 0


def _indent(line):
    return len(line.expandtabs(4)) - len(line.expandtabs(4).lstrip(' '))


def _scan(lines):
    """({index: 'front' | 'open' | 'fence' | 'indented'} for each line of code:
    YAML front matter, a fenced block ('open' for its opening fence, 'fence' for
    the rest), and an indented code block (four spaces or a tab, after a blank
    line or more such code, outside a list, where indented lines continue the
    item instead); the set of other lines inside a list)."""
    code = {i: 'front' for i in range(_front_matter_end(lines))}
    listed = set()
    fence = None
    blank, in_list, indented = True, False, False
    for i, line in enumerate(lines):
        if i in code:
            continue
        m = FENCE.match(line)
        if fence is not None:
            code[i] = 'fence'
            if m and m.group(2)[0] == fence[0] and len(m.group(2)) >= len(fence) and not m.group(3):
                fence = None
            continue
        if not line.strip():
            blank = True
            continue
        if _indent(line) >= 4 and not in_list and (blank or indented):
            code[i], indented, blank = 'indented', True, False
            continue
        indented = False
        if m and _indent(line) < 4:
            code[i], fence = 'open', m.group(2)
        if LIST_ITEM.match(line):
            in_list = True
        elif _indent(line) == 0:
            in_list = False  # a line back at the margin ends the list
        if in_list:
            listed.add(i)
        blank = False
    return code, listed


def _code_lines(lines):
    return _scan(lines)[0]


def _comment(line, i, listed):
    """The LINE_COMMENT match for a line MyST reads as a comment: % within three
    spaces of its container's margin. At four spaces or more outside a list the
    line is paragraph text (or code); inside a list the margin is the item's."""
    m = LINE_COMMENT.match(line)
    if m and not HEADING.match(line) and (_indent(line) < 4 or i in listed):
        return m
    return None


def _prose(lines):
    """(index, line with code spans removed) for each line outside code (_code_lines) and $$ blocks."""
    code = _code_lines(lines)
    math = False
    for i, line in enumerate(lines):
        if i in code:
            continue
        if line.strip() == '$$':
            math = not math
            continue
        if not math:
            yield i, CODE_SPAN.sub('', line)


ONE_LINE_DOLLARS = re.compile(r'[ \t]*\$\$(.+)\$\$[ \t]*\Z')


def dollar_blocks(lines):
    """(index of the opening line, body lines) for each $$ math block outside code fences,
    including a one-line $$ … $$."""
    code = _code_lines(lines)
    start = None
    for i, line in enumerate(lines):
        if i in code and start is None:
            continue
        if line.strip() == '$$':
            if start is None:
                start = i
            else:
                yield start, lines[start + 1:i]
                start = None
            continue
        one = ONE_LINE_DOLLARS.match(line) if start is None else None
        if one:
            yield i, [one.group(1)]


def check(text):
    """Findings (severity, code, line, message) for markdown that renders differently on GitHub and in Obsidian."""
    out = []
    lines = text.split('\n')
    for start, body in dollar_blocks(lines):
        if not dollar_safe(body):
            out.append(('error', 'DOLLAR_MATH', start + 1, 'GitHub runs markdown over a $$ block first: a backslash before punctuation (\\\\, \\, \\{ \\_) loses it, and a * next '
                        'to a character can become emphasis (Obsidian is fine). Rewrite without them (\\ast for *), or use a ```math block: GitHub renders it exactly, Obsidian shows it as code'))
    code, listed = _scan(lines)
    for i, line in enumerate(lines):  # mdBook expands these before it reads the markdown, code too
        m = MDBOOK_DIRECTIVE.search(line)
        if m:
            out.append(('error', 'MDBOOK_DIRECTIVE', i + 1, f'"{{{{#{m.group(1)}" is an mdBook directive, which the book would expand, even in code; write \\{{{{#'))
        m = FENCE.match(line) if code.get(i) == 'open' else None
        if m and m.group(3).startswith('{'):
            out.append(('warning', 'MYST_SYNTAX', i + 1, f'"{m.group(2)}{m.group(3)}" opens a MyST directive, which GitHub, Obsidian and mdBook show as code; use a plain fence'))
    prose = list(_prose(lines))
    level, titles = 0, 0
    for at, (i, line) in enumerate(prose):
        n = i + 1
        h = HEADING.match(line)
        if h:
            new = len(h.group(1))
            titles += new == 1
            if new > level + 1 and level:
                out.append(('warning', 'HEADING_LEVEL', n, f'a level-{new} heading after a level-{level} one: Sphinx warns and leaves a gap in the book\'s table of contents; don\'t skip a level'))
            elif new == 1 and titles == 2:
                out.append(('warning', 'HEADING_LEVEL', n, 'a second # title: Sphinx makes the page\'s title from the first one and nests the rest oddly; use ## for sections'))
            level = new
        if _comment(line, i, listed):
            out.append(('error', 'LINE_COMMENT', n, 'a line starting with % is a MyST comment, which Sphinx drops from the book; write \\% (narrative-format --fix-style)'))
        m = HEADING_ATTRS.match(line)
        if m:
            out.append(('error', 'HEADING_ATTRS', n, f'"{m.group(2)}}}" at the end of a heading is read by mdBook as its id and classes, and dropped; write \\}} (narrative-format --fix-style)'))
        spans = [m.span() for m in CODE_SPAN.finditer(lines[i])]
        roles = [m for m in MYST_ROLE.finditer(lines[i]) if not any(a <= m.start() < b for a, b in spans)]  # {name} right before a code span
        if MYST_LINE.match(line) or roles:
            out.append(('warning', 'MYST_SYNTAX', n, 'a MyST target "(label)=", block break "+++" or role "{name}`…`", which GitHub, Obsidian and mdBook show as text'))
        for start, end in bare_urls(line):
            out.append(('warning', 'BARE_URL', n, f'"{line[start:end]}": GitHub and Obsidian link a bare URL, mdBook and Sphinx show it as text; write <{line[start:end]}> or [text](url) (narrative-format --fix-style)'))
        plain = LINK_OR_URL.sub(lambda m: ' ' if m.group(1) else m.group(0), line)
        for m in EMOJI.finditer(plain):
            out.append(('warning', 'EMOJI_SHORTCODE', n, f'":{m.group(1)}:" is an emoji only GitHub renders; write the emoji itself, or reword it'))
        if DOLLAR.search(plain):
            out.append(('warning', 'DOLLAR_SIGN', n, 'a $ before a number can start math in Obsidian and MyST; write \\$ (narrative-format --fix-style)'))
        for m in TILDES.finditer(plain):
            out.append(('warning', 'TILDE_STRIKE', n, f'"{m.group(0)}": GitHub and mdBook strike the text between single tildes through, Obsidian and MyST don\'t; write \\~ (narrative-format --fix-style)'))
        for m in EMBED.finditer(line):
            out.append(('error', 'EMBED', n, f'"![[{m.group(1)}]]" is an Obsidian embed, which GitHub shows as text; use ![alt](path) or [text](path)'))
        for m in WIKILINK.finditer(line):
            out.append(('error', 'WIKILINK', n, f'"[[{m.group(1)}]]" is an Obsidian wikilink, which GitHub shows as text; use a markdown link, [text](file.md#heading)'))
        for m in HIGHLIGHT.finditer(line):
            out.append(('error', 'HIGHLIGHT', n, f'"=={m.group(1)}==" is an Obsidian highlight, which GitHub shows with the = signs; use **bold**'))
        if '%%' in line:
            out.append(('error', 'OBSIDIAN_COMMENT', n, '"%%" starts an Obsidian comment, which GitHub shows as text; use an HTML comment, <!-- … -->'))
        m = CALLOUT.match(line)
        if m and (m.group(1).strip().upper() not in GITHUB_ALERTS or m.group(2) or m.group(3).strip()):
            out.append(('error', 'CALLOUT', n, f'"[!{m.group(1)}]{m.group(2)}{m.group(3)}" is an Obsidian callout GitHub doesn\'t render; both render '
                        '> [!NOTE], [!TIP], [!IMPORTANT], [!WARNING] and [!CAUTION], alone on their line'))
        if not line.lstrip().startswith('#'):  # a heading's own #s aren't tags
            for m in INLINE_TAG.finditer(line):
                out.append(('warning', 'INLINE_TAG', n, f'"#{m.group(1)}" becomes a tag in Obsidian; put it in backticks or reword it'))
        m = BLOCK_ID.search(line)
        if m:
            out.append(('warning', 'BLOCK_ID', n, f'"^{m.group(1)}" at the end of a line is an Obsidian block ID, which GitHub shows as text'))
        nxt = prose[at + 1][1] if at + 1 < len(prose) and prose[at + 1][0] == i + 1 else ''
        if BOLD_LINE.match(line) and nxt.strip() and not NOT_PROSE.match(nxt):
            out.append(('warning', 'LINE_JOINED', n, 'GitHub joins this bold line and the next into one line; put a blank line between them'))
    return out


LINK_DEST = re.compile(r'\]\(([^)\n]*)\)')
TITLE = re.compile(r'(\S+)[ \t]+("[^"]*"|\'[^\']*\')[ \t]*\Z')  # [text](dest "title")
SCHEME = re.compile(r'[A-Za-z][A-Za-z0-9+.-]*:')


def link_targets(text):
    """(line, destination) for each markdown link and image outside code and math."""
    for i, line in _prose(text.split('\n')):
        for m in LINK_DEST.finditer(line):
            yield i + 1, m.group(1).strip()


def check_links(text, file_dir, root, resolve=True):
    """Findings for links GitHub and Obsidian resolve differently, in a file in
    file_dir of the repository (and vault) at root:
    - LINK_SPACES (error): a space in a link's path. GitHub doesn't read
      [My Project](My Project.md) as a link at all; write My%20Project.md.
    - LINK_PATH (error, with resolve): a relative path that doesn't resolve
      from the file's own folder. Obsidian also finds a note from the vault
      root, or by its name alone; GitHub resolves only from the file's folder,
      which both understand.
    - LINK_FOLDER (warning, with resolve): a link to a folder. GitHub lists
      its files; Obsidian, mdBook and Sphinx find no page there."""
    out = []
    for n, dest in link_targets(text):
        m = TITLE.match(dest)
        path = m.group(1) if m else dest
        if path.startswith('<') and path.endswith('>'):
            path = path[1:-1]
        if not path or SCHEME.match(path) or path.startswith('#'):
            continue
        if re.search(r'\s', path):
            out.append(('error', 'LINK_SPACES', n, f'"{path}": a link\'s path can\'t contain spaces (GitHub doesn\'t read it as a link); write each space as %20: '
                        f'{urllib.parse.quote(path, safe="/#%:")}'))
            continue
        if not resolve or re.search(r'<[^>]*>|\{\{|…', path):  # a template skeleton's placeholder, not a path
            continue
        file = urllib.parse.unquote(path.split('#')[0].split('?')[0])
        if not file:
            continue
        base = root if file.startswith('/') else file_dir
        target = os.path.normpath(os.path.join(base, file.lstrip('/')))
        if os.path.isdir(target):
            out.append(('warning', 'LINK_FOLDER', n, f'"{path}" is a folder: GitHub lists it, but Obsidian, mdBook and Sphinx find no page there; link to a file in it, such as its README.md'))
            continue
        if os.path.exists(target):
            continue
        found = os.path.join(root, file.lstrip('/'))
        if not os.path.exists(found):
            named = [os.path.join(d, os.path.basename(file)) for d, dirs, files in os.walk(root)
                     if os.path.basename(file) in files and '/.' not in d.replace(os.sep, '/') + '/']
            found = named[0] if len(named) == 1 else None
        if found:
            rel = os.path.relpath(found, file_dir).replace(os.sep, '/')
            out.append(('error', 'LINK_PATH', n, f'"{path}" resolves in Obsidian (from the vault root, or by name) but not on GitHub, which resolves paths from this file\'s folder; write {rel}'))
        else:
            out.append(('error', 'LINK_PATH', n, f'"{path}" doesn\'t resolve: no such file from this file\'s folder'))
    return out
