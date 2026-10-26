"""Sources without markdown headings, made citable inside (design doc §4.3).

  standard(text) -> markdown, or None: a plain-text standard (an RFC) with its
      numbered sections as headings, each section's text verbatim in a fenced
      block, page headers and footers left out
  rst(text) -> markdown, or None: reStructuredText with its section titles as
      headings, levels in the order their adornments first appear, the rest verbatim
  code(text, name) -> markdown: a code file verbatim in one fenced block, so
      its line numbers are the file's own
  lines(markdown, anchor) -> the code lines an #L<start>-L<end> anchor names, or None
"""

import os
import re

from .util import split_footer

SECTION = re.compile(r'(?P<number>(?:\d+\.)*\d+\.?|Appendix [A-Z]\.?)\s{1,4}(?P<title>[A-Z][^\n]{1,80}?)\s*\Z')
LINES = re.compile(r'L(?P<start>[1-9][0-9]*)(?:-L(?P<end>[1-9][0-9]*))?\Z')
MIN_SECTIONS = 3
LANGUAGES = {'.py': 'python', '.go': 'go', '.c': 'c', '.h': 'c', '.cc': 'cpp', '.cpp': 'cpp', '.hpp': 'cpp', '.java': 'java',
             '.js': 'javascript', '.ts': 'typescript', '.rs': 'rust', '.rb': 'ruby', '.sh': 'bash', '.scala': 'scala',
             '.kt': 'kotlin', '.swift': 'swift', '.cs': 'csharp', '.erl': 'erlang', '.ex': 'elixir', '.hs': 'haskell'}


def _fence(body):
    """A fence longer than any run of backticks in body."""
    longest = max((len(m) for m in re.findall(r'`+', body)), default=0)
    return '`' * max(3, longest + 1)


def _page_furniture(lines):
    """Lines without the page breaks and the header and footer around each."""
    out, after_break = [], False
    for line in lines:
        if '\f' in line:
            after_break = True
            continue
        if re.search(r'\[Page \d+\]\s*\Z', line) or (after_break and line.strip()):
            after_break = False
            continue
        out.append(line)
    return out


def standard(text):
    lines = _page_furniture(text.replace('\r\n', '\n').split('\n'))
    heads = [i for i, line in enumerate(lines) if SECTION.match(line) and (i == 0 or not lines[i - 1].strip())]
    if len(heads) < MIN_SECTIONS:
        return None
    parts, start = [], 0
    for i in heads + [len(lines)]:
        body = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines[start:i]).strip('\n'))  # page breaks leave runs of blank lines
        if body.strip():
            fence = _fence(body)
            parts.append(f'{fence}text\n{body}\n{fence}')
        if i < len(lines):
            m = SECTION.match(lines[i])
            number = m.group('number').rstrip('.')
            depth = 1 if number.startswith('Appendix') else number.count('.') + 1
            parts.append(f'{"#" * min(depth + 1, 6)} {number}. {m.group("title")}')
            start = i + 1
    return '\n\n'.join(parts) + '\n'


ADORNMENT = re.compile(r'([!-/:-@\[-`{-~])\1{2,}\s*\Z')  # one punctuation character, repeated


def rst(text):
    lines = text.replace('\r\n', '\n').split('\n')
    styles, out, i, found = [], [], 0, 0
    while i < len(lines):
        over = ADORNMENT.match(lines[i]) and i + 2 < len(lines) and lines[i + 2].strip() == lines[i].strip()
        at = i + 1 if over else i
        title = lines[at].strip() if at < len(lines) else ''
        under = lines[at + 1] if at + 1 < len(lines) else ''
        if (title and not ADORNMENT.match(lines[at]) and (over or not lines[at][:1].isspace()) and ADORNMENT.match(under)
                and len(under.strip()) >= len(title) and (at == 0 or over or not lines[at - 1].strip())):
            style = (under.strip()[0], bool(over))
            if style not in styles:
                styles.append(style)
            out.append(f'{"#" * min(styles.index(style) + 1, 6)} {title}')
            found += 1
            i = at + 2
            continue
        out.append(lines[i])
        i += 1
    return '\n'.join(out) if found else None


def code(text, name):
    body = text.rstrip('\n')
    fence = _fence(body)
    lang = LANGUAGES.get(os.path.splitext(name.split('?')[0].split('#')[0])[1].lower(), '')
    return f'{fence}{lang}\n{body}\n{fence}\n'


def lines(markdown, anchor):
    """The code lines #L<start>-L<end> names, in a code source (one fenced block, then its footer); None when it has none."""
    m = LINES.match(anchor or '')
    body = split_footer(markdown.encode())[0].decode().strip('\n')
    block = re.fullmatch(r'(`{3,})[^\n]*\n(.*)\n\1', body, re.S)
    if not m or not block:
        return None
    code_lines = block.group(2).split('\n')
    start = int(m.group('start'))
    end = int(m.group('end') or start)
    if end < start or end > len(code_lines):
        return None
    return code_lines[start - 1:end]
