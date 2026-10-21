"""A LaTeX source as markdown (design doc §4.3): its sections as headings, its
math kept as TeX, its formatting as markdown, the rest of its markup dropped.

  convert(tex, include=None) -> markdown
      include(name) returns the text of an \\input or \\include, or None.

Only the document's body is kept (its title as the # heading). Commands this
doesn't know are dropped and their arguments kept as text.
"""

import re

SECTIONS = ('part', 'chapter', 'section', 'subsection', 'subsubsection')
DISPLAY = r'equation|align|gather|multline|eqnarray|displaymath|flalign|alignat'
VERBATIM = r'verbatim|lstlisting|minted|Verbatim'
MAX_INPUTS = 50
INDENT = '\x02'  # a nested list's indent, kept through the whitespace cleanup
# command: (arguments it takes, how it's written; {0} is the first argument, rendered)
FORMATS = {
    'emph': (1, '*{0}*'), 'textit': (1, '*{0}*'), 'textsl': (1, '*{0}*'), 'textbf': (1, '**{0}**'), 'texttt': (1, '`{0}`'),
    'underline': (1, '{0}'), 'textsc': (1, '{0}'), 'textrm': (1, '{0}'), 'textsf': (1, '{0}'), 'mbox': (1, '{0}'), 'text': (1, '{0}'),
    'footnote': (1, ' (Footnote: {0})'), 'textcolor': (2, '{1}'),
    'ref': (1, '{0}'), 'autoref': (1, '{0}'), 'cref': (1, '{0}'), 'Cref': (1, '{0}'), 'pageref': (1, '{0}'), 'eqref': (1, '({0})'),
    'paragraph': (1, '**{0}** '), 'subparagraph': (1, '**{0}** '),
    'label': (1, ''), 'index': (1, ''), 'includegraphics': (1, ''), 'vspace': (1, ''), 'hspace': (1, ''),
    'bibliography': (1, ''), 'input': (1, ''), 'include': (1, ''), 'bibliographystyle': (1, ''), 'thanks': (1, ''), 'author': (1, ''), 'date': (1, ''), 'title': (1, ''),
}
WORDS = {'LaTeX': 'LaTeX', 'TeX': 'TeX', 'ldots': '…', 'dots': '…', 'textendash': '–', 'textemdash': '—', 'S': '§',
         'item': '\x01', 'par': '\n\n', 'newline': '\n'}
SYMBOLS = {'\\': '\n', '%': '%', '&': '&', '_': '_', '#': '#', '$': '$', '{': '{', '}': '}', ',': ' ', ';': ' ', ' ': ' ',
           '-': '', '/': '', '@': '', '!': ''}


def _strip_comments(tex):
    return re.sub(r'(?<!\\)%[^\n]*', '', tex)


def _group(s, i, open_='{', close='}'):
    """(the text of the group opening at s[i], the index after it); (None, i) when s[i] doesn't open one."""
    if i >= len(s) or s[i] != open_:
        return None, i
    depth, j = 0, i
    while j < len(s):
        if s[j] == '\\':
            j += 2
            continue
        depth += {open_: 1, close: -1}.get(s[j], 0)
        if not depth:
            return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)


def _skip_space(s, i):
    while i < len(s) and s[i] in ' \t\n':
        i += 1
    return i


def _args(s, i, n):
    """n brace arguments after s[i] (optional [..] ones skipped and returned first): ([optional], [args], index)."""
    optional, args = [], []
    while True:
        j = _skip_space(s, i)
        opt, k = _group(s, j, '[', ']')
        if opt is None:
            break
        optional.append(opt)
        i = k
    for _ in range(n):
        j = _skip_space(s, i)
        arg, k = _group(s, j)
        if arg is None:
            break
        args.append(arg)
        i = k
    return optional, args, i


def _inputs(tex, include, prepare, depth=0):
    if include is None or depth > 5:
        return tex
    count = [0]

    def sub(m):
        count[0] += 1
        text = include(m.group(1).strip()) if count[0] <= MAX_INPUTS else None
        return _inputs(prepare(text), include, prepare, depth + 1) if text is not None else ''
    return re.sub(r'\\(?:input|include)\s*\{([^}]*)\}', sub, tex)


class _Converter:
    def __init__(self, levels):
        self.levels, self.kept = levels, []

    def keep(self, text):
        """A placeholder for text kept as it is (math, code)."""
        self.kept.append(text)
        return f'\x00{len(self.kept) - 1}\x00'

    def verbatim(self, s):
        """Verbatim text out of the way, before comments are stripped."""
        s = re.sub(r'\\begin\{(' + VERBATIM + r')\}(?:\[[^\]]*\])?(?:\{[^}]*\})?\n?(.*?)\\end\{\1\}',
                   lambda m: self.keep('\n\n```\n' + m.group(2).rstrip('\n') + '\n```\n\n'), s, flags=re.S)
        return re.sub(r'\\verb(.)(.*?)\1', lambda m: self.keep('`' + m.group(2) + '`'), s)

    def prepare(self, s):
        return _strip_comments(self.verbatim(s))

    def protect(self, s):
        """Math out of the way of everything else."""
        s = re.sub(r'\\begin\{((?:' + DISPLAY + r')\*?)\}(.*?)\\end\{\1\}', lambda m: self._display(m.group(2)), s, flags=re.S)
        s = re.sub(r'\\\[(.*?)\\\]|\$\$(.*?)\$\$', lambda m: self._display(m.group(1) or m.group(2)), s, flags=re.S)
        s = re.sub(r'\\\((.*?)\\\)|(?<!\\)\$(.+?)(?<!\\)\$', lambda m: self.keep('$' + (m.group(1) or m.group(2)).strip() + '$'), s, flags=re.S)
        return s

    def _display(self, math):
        math = re.sub(r'\\label\{[^}]*\}', '', math).strip()
        return self.keep('\n\n$$\n' + math + '\n$$\n\n')

    def render(self, s):
        out, i = [], 0
        while i < len(s):
            c = s[i]
            if c == '\\':
                m = re.match(r'\\([A-Za-z]+)\*?', s[i:])
                if not m:
                    out.append(SYMBOLS.get(s[i + 1:i + 2], s[i + 1:i + 2]))
                    i += 2
                    continue
                text, i = self.command(m.group(1), s, i + m.end())
                out.append(text)
            elif c == '{':
                inner, i = _group(s, i)
                out.append(self.render(inner))
            elif c == '}':
                i += 1
            elif c == '~':
                out.append(' ')
                i += 1
            else:
                out.append(c)
                i += 1
        text = ''.join(out)
        return text.replace('---', '\u2014').replace('--', '\u2013').replace('``', '\u201c').replace("''", '\u201d')

    def command(self, name, s, i):
        """(the command's text, the index after it and its arguments)."""
        if name == 'begin':
            return self.environment(s, i)
        if name in SECTIONS:
            _, args, i = _args(s, i, 1)
            level = self.levels.index(name) + 2 if name in self.levels else 2
            return f'\n\n{"#" * min(level, 6)} {" ".join(self.render(args[0]).split()) if args else ""}\n\n', i
        if name in ('cite', 'citep', 'citet', 'citeauthor', 'citeyear', 'nocite', 'citealp'):
            optional, args, i = _args(s, i, 1)
            keys = ', '.join(k.strip() for k in (args[0] if args else '').split(',') if k.strip())
            return ('' if name == 'nocite' else f'[{", ".join([keys] + [self.render(o) for o in optional[::-1] if o])}]'), i
        if name == 'bibitem':
            _, args, i = _args(s, i, 1)
            return f'\n- [{args[0] if args else ""}] ', i
        if name == 'caption':
            _, args, i = _args(s, i, 1)
            return f'\n\nCaption: {self.render(args[0]) if args else ""}\n\n', i
        if name in ('url', 'href'):
            _, args, i = _args(s, i, 2 if name == 'href' else 1)
            url = self.keep(args[0].strip()) if args else ''
            return (f'<{url}>' if name == 'url' else f'[{self.render(args[1]) if len(args) > 1 else ""}]({url})'), i
        if name in FORMATS:
            n, fmt = FORMATS[name]
            _, args, i = _args(s, i, n)
            return fmt.format(*[self.render(a) for a in args + [''] * (n - len(args))]), i
        if name in WORDS:
            return WORDS[name], (i + 2 if s[i:i + 2] == '{}' else i)
        return '', i  # an unknown command: dropped, and any arguments read as text

    def environment(self, s, i):
        name, i = _group(s, _skip_space(s, i))
        name = name or ''
        depth, j = 1, i
        pattern = re.compile(r'\\(begin|end)\s*\{' + re.escape(name) + r'\}')
        while depth:
            m = pattern.search(s, j)
            if not m:
                body, after = s[i:], len(s)
                break
            depth += 1 if m.group(1) == 'begin' else -1
            body, after, j = s[i:m.start()], m.end(), m.end()
        base = name.rstrip('*')
        if base == 'thebibliography':
            _, _, k = _args(body, 0, 1)  # the widest label
            return '\n\n' + self.render(body[k:]) + '\n\n', after
        if base in ('itemize', 'enumerate', 'description'):
            return self.items(base, body), after
        if base == 'abstract':
            return '\n\n## Abstract\n\n' + self.render(body) + '\n\n', after
        if base in ('tabular', 'tabularx', 'longtable'):
            return self.table(body), after
        if base in ('quote', 'quotation'):
            return '\n\n' + '\n'.join('> ' + line for line in _paragraphs(self.render(body)).split('\n')) + '\n\n', after
        if base in ('theorem', 'lemma', 'proposition', 'corollary', 'definition', 'proof', 'example', 'remark'):
            optional, _, k = _args(body, 0, 0)
            label = base.capitalize() + (f' ({optional[0]})' if optional else '')
            return f'\n\n**{label}.** ' + self.render(body[k:]).strip() + '\n\n', after
        if base in ('figure', 'table', 'wrapfigure'):
            _, _, k = _args(body, 0, 0)
            return '\n\n' + self.render(body[k:]) + '\n\n', after
        return self.render(body), after

    def items(self, kind, body):
        text = self.render(body)
        out = []
        for part in text.split('\x01')[1:]:
            label, rest = '', part
            m = re.match(r'\s*\[([^\]]*)\]', part)
            if m:
                label, rest = m.group(1), part[m.end():]
            first, *more = _paragraphs(rest).split('\n') or ['']
            rest = '\n'.join([first] + [INDENT + line if line else '' for line in more])
            if kind == 'enumerate':
                out.append(f'{len(out) + 1}. {rest}')
            else:
                out.append(f'- **{label}** {rest}' if label else f'- {rest}')
        return '\n\n' + '\n'.join(out) + '\n\n'

    def table(self, body):
        _, _, k = _args(body, 0, 1)  # the column spec
        body = re.sub(r'\\(hline|toprule|midrule|bottomrule|cline\{[^}]*\})', '', body[k:])
        rows = [r for r in re.split(r'\\\\(?:\[[^\]]*\])?', body) if r.strip()]
        cells = [[' '.join(self.render(c).split()).replace('|', '\\|') for c in re.split(r'(?<!\\)&', r)] for r in rows]
        if not cells:
            return ''
        width = max(len(r) for r in cells)
        cells = [r + [''] * (width - len(r)) for r in cells]
        lines = ['| ' + ' | '.join(cells[0]) + ' |', '|' + '---|' * width] + ['| ' + ' | '.join(r) + ' |' for r in cells[1:]]
        return '\n\n' + self.keep('\n'.join(lines)) + '\n\n'


def _paragraphs(text):
    """Lines trimmed, runs of spaces and blank lines collapsed."""
    lines = [' '.join(line.split()) for line in text.split('\n')]
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


def convert(tex, include=None):
    conv = _Converter([])
    tex = _inputs(conv.prepare(tex), include, conv.prepare)
    m = re.search(r'\\title\s*(?:\[[^\]]*\])?\s*\{', tex)
    title = _group(tex, m.end() - 1)[0] if m else None
    body = re.search(r'\\begin\{document\}(.*?)(\\end\{document\}|\Z)', tex, re.S)
    body = body.group(1) if body else tex
    conv.levels = [name for name in SECTIONS if re.search(r'\\' + name + r'\*?\s*[\[{]', body)]
    text = _paragraphs(conv.render(conv.protect(body)))
    if title:
        text = f'# {" ".join(conv.render(conv.protect(title)).split())}\n\n{text}'
    text = '\n'.join('\\' + line if line.startswith(('#', '>')) and not re.match(r'(#{1,6} |> )', line) else line
                     for line in text.split('\n'))
    text = text.replace(INDENT, '   ')
    while '\x00' in text:
        text = re.sub(r'\x00(\d+)\x00', lambda m: conv.kept[int(m.group(1))], text)
    return re.sub(r'\n{3,}', '\n\n', text).strip() + '\n'
