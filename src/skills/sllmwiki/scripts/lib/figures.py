"""The figures a narrative embeds (design doc §4.5): images it generates for what
a mermaid diagram can't show well, kept in narratives/figures/<slug>/, and the
numbered caption under every diagram and image.

check(root, rel, text, on) -> findings for one narrative's images:
  IMAGE_OFF         an image while Config.toml's images setting is false
  IMAGE_PLACE       an image that isn't an .svg or .png in figures/<slug>/
  IMAGE_FORMAT      a file whose content isn't the SVG or PNG its name says
  IMAGE_ALT         an image without alt text
  IMAGE_UNSAFE      an SVG with a script, an event handler, a link or an embedded image
  IMAGE_BACKGROUND  an SVG with no opaque background, so dark themes hide its dark text (warning)
  IMAGE_SIZE        an SVG over MAX_SVG_BYTES, or a PNG over MAX_PNG_BYTES or MAX_PNG_WIDTH (warning)
check_captions(text) -> findings for captions:
  FIGURE_CAPTION    a diagram or image without its caption line, *Figure 5-1: what it shows.*
  FIGURE_NUMBER     a caption numbered out of place (renumber() fixes it)
  FIGURE_REF        a "Figure 5-1" in the text that no caption carries (warning)
renumber(text) -> (text, captions changed): numbers each caption by its ## section
and its place in it, and updates the text's references to match.
unused(root) -> findings for figures no narrative shows (FIGURE_UNUSED, warning).
"""

import os
import re

from . import language, layout, numbering
from .compat import mask_code_spans, scan
from .util import read_bytes, read_text

FOLDER = 'figures'
KINDS = ('.svg', '.png')  # what GitHub, Obsidian, mdBook and Sphinx's HTML builder all show
MAX_SVG_BYTES = 40_000    # an SVG is text an agent may read: keep it to a few thousand tokens
MAX_PNG_BYTES = 150_000
MAX_PNG_WIDTH = 1600      # pixels: wider only costs bytes and tokens, no page shows more
IMAGE = re.compile(r'!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)')
PNG = b'\x89PNG\r\n\x1a\n'
_MERMAID = re.compile(r' {0,3}(`{3,}|~{3,})[ \t]*mermaid\b')
_UNSAFE = re.compile(r'<script|<foreignObject|\son\w+\s*=|(?:xlink:)?href\s*=\s*["\'](?!#)', re.I)
_BACKGROUND = re.compile(r'<rect\b[^>]*\bfill\s*=\s*["\'](?!none|transparent)|background(?:-color)?\s*:', re.I)


def _word():
    """The word a caption starts with, in English or any language pack's: (?:Figure|图)."""
    return '(?:' + '|'.join(re.escape(w) for w in language.names('Figure')) + ')'


def caption_re():
    """*Figure 5-1: what it shows.*, or its language pack's form, *图 5-1：……*"""
    return re.compile(r'\*' + _word() + r' ?(\d+)-(\d+)[:：] ?\S.*\*\Z')


def label_re():
    """A reference to a figure in the text: Figure 5-1."""
    return re.compile(r'(?<![A-Za-z0-9_])(' + _word() + r' ?)(\d+)-(\d+)(?!\w)')


def images(text):
    """[(line index, alt, path)] for each image in the narrative's prose."""
    lines = text.split('\n')
    kinds, _ = scan(lines)
    return [(i, m.group(1), m.group(2)) for i, line in enumerate(lines) if kinds[i] == 'text'
            for m in IMAGE.finditer(mask_code_spans(line))]


def check(root, rel, text, on=True):
    """Findings (severity, code, line, message) for the narrative at rel."""
    slug = os.path.splitext(os.path.basename(rel))[0]
    out = []
    for i, alt, path in images(text):
        n = i + 1
        if not on:
            out.append(('error', 'IMAGE_OFF', n, f'{path}: Config.toml turns images off; draw it as a mermaid diagram'))
            continue
        parts = path.split('/')
        if len(parts) != 3 or parts[:2] != [FOLDER, slug] or os.path.splitext(path)[1].lower() not in KINDS:
            out.append(('error', 'IMAGE_PLACE', n, f'{path}: a figure is an .svg or .png in {FOLDER}/{slug}/, generated for this narrative'))
            continue
        if not alt.strip():
            out.append(('error', 'IMAGE_ALT', n, f'{path}: give it alt text saying what it shows'))
        full = os.path.join(root, os.path.dirname(rel), path)
        if not os.path.isfile(full):
            continue  # compat.check_links reports it as LINK_PATH
        out += _check_file(full, path, n)
    return out


def _check_file(full, path, n):
    data = read_bytes(full)
    if path.lower().endswith('.png'):
        if not data.startswith(PNG) or len(data) < 24:
            return [('error', 'IMAGE_FORMAT', n, f'{path} isn\'t a PNG')]
        width = int.from_bytes(data[16:20], 'big')
        if len(data) > MAX_PNG_BYTES or width > MAX_PNG_WIDTH:
            return [('warning', 'IMAGE_SIZE', n, f'{path} is {len(data) // 1000} KB and {width} px wide; keep a PNG under '
                                                 f'{MAX_PNG_BYTES // 1000} KB and {MAX_PNG_WIDTH} px, or draw it as an SVG')]
        return []
    svg = data.decode('utf-8', 'replace')
    if not re.match(r'\s*(?:<\?xml[^>]*\?>\s*)?(?:<!--.*?-->\s*)*<svg\b', svg, re.S):
        return [('error', 'IMAGE_FORMAT', n, f'{path} isn\'t an SVG: it starts with <svg>')]
    out = []
    if _UNSAFE.search(svg):
        out.append(('error', 'IMAGE_UNSAFE', n, f'{path}: an SVG figure is self-contained: no scripts, event handlers, links or embedded images'))
    elif not _BACKGROUND.search(svg):
        out.append(('warning', 'IMAGE_BACKGROUND', n, f'{path} has no opaque background, so dark themes hide its dark text; '
                                                     'start it with a light <rect> the size of the figure'))
    if len(data) > MAX_SVG_BYTES:
        out.append(('warning', 'IMAGE_SIZE', n, f'{path} is {len(data) // 1000} KB; keep an SVG under {MAX_SVG_BYTES // 1000} KB: '
                                               'fewer points, rounded coordinates, shared styles, no metadata'))
    return out


def pictures(text):
    """[(first line, last line, caption line or None)] for each ```mermaid block and
    each image on a line of its own; the caption is the next non-blank line, when it
    starts *Figure."""
    lines = text.split('\n')
    kinds, _ = scan(lines)
    out = []
    i = 0
    while i < len(lines):
        if kinds[i] == 'open' and _MERMAID.match(lines[i]):
            end = i
            while end + 1 < len(lines) and kinds[end + 1] == 'fence':
                end += 1
        elif kinds[i] == 'text' and IMAGE.fullmatch(lines[i].strip()):
            end = i
        else:
            i += 1
            continue
        k = end + 1
        while k < len(lines) and not lines[k].strip():
            k += 1
        caption = k if k < len(lines) and kinds[k] == 'text' and re.match(r'\*' + _word(), lines[k].strip()) else None
        out.append((i, end, caption))
        i = end + 1
    return out


def _labels(text):
    """[(caption line, label it should carry)] in order: the ## section's number, then the figure's place in it."""
    sections = [(h.line, h.number or '0') for h in numbering.headings(text) if h.level == 2]
    counts, out = {}, []
    for start, _, caption in pictures(text):
        if caption is None:
            continue
        section = next((num for line, num in reversed(sections) if line < start), '0').split('.')[0]
        counts[section] = counts.get(section, 0) + 1
        out.append((caption, f'{section}-{counts[section]}'))
    return out


def check_captions(text):
    """Findings (severity, code, line, message) for diagram and image captions."""
    lines = text.split('\n')
    out = []
    for start, _, caption in pictures(text):
        if caption is None:
            out.append(('error', 'FIGURE_CAPTION', start + 1, 'follow each diagram and image with its caption, on its own line: '
                                                               '*Figure 5-1: what it shows.*'))
    want = dict(_labels(text))
    carried = set()
    for line, label in want.items():
        m = caption_re().match(lines[line].strip())
        if not m:
            out.append(('error', 'FIGURE_CAPTION', line + 1, 'write the caption as *Figure 5-1: what it shows.*, in one line'))
            continue
        carried.add(f'{m.group(1)}-{m.group(2)}')
        if f'{m.group(1)}-{m.group(2)}' != label:
            out.append(('error', 'FIGURE_NUMBER', line + 1, f'this is Figure {label} (finish-narrative.py renumbers)'))
    kinds, _ = scan(lines)
    for i, line in enumerate(lines):
        if kinds[i] == 'text' and i not in want:
            for m in label_re().finditer(mask_code_spans(line)):
                if f'{m.group(2)}-{m.group(3)}' not in carried:
                    out.append(('warning', 'FIGURE_REF', i + 1, f'"{m.group(0)}": no caption carries that number'))
    return out


def renumber(text):
    """(text, captions changed): each caption numbered by its place, and the text's references moved with it."""
    lines = text.split('\n')
    moves, changed = {}, 0
    for line, label in _labels(text):
        m = caption_re().match(lines[line].strip())
        if not m:
            continue
        old = f'{m.group(1)}-{m.group(2)}'
        if old != label:
            moves.setdefault(old, label)
            lines[line] = re.sub(r'(' + _word() + r' ?)' + re.escape(old) + r'(?=[:：])', lambda x: x.group(1) + label, lines[line], count=1)
            changed += 1
    if moves:
        captions = {line for line, _ in _labels(text)}
        kinds, _ = scan(lines)
        for i, line in enumerate(lines):
            if kinds[i] == 'text' and i not in captions:
                lines[i] = label_re().sub(lambda m: m.group(1) + moves.get(f'{m.group(2)}-{m.group(3)}', f'{m.group(2)}-{m.group(3)}'), line)
    return '\n'.join(lines), changed


def unused(root):
    """[(severity, code, file, message)] for each figure no narrative shows."""
    base = os.path.join(root, layout.NARRATIVES, FOLDER)
    if not os.path.isdir(base):
        return []
    out = []
    for slug in sorted(os.listdir(base)):
        folder = os.path.join(base, slug)
        if not os.path.isdir(folder):
            continue
        page = os.path.join(root, layout.NARRATIVES, slug + '.md')
        shown = {p for _, _, p in images(read_text(page))} if os.path.isfile(page) else set()
        for name in sorted(os.listdir(folder)):
            if f'{FOLDER}/{slug}/{name}' not in shown:
                out.append(('warning', 'FIGURE_UNUSED', f'{layout.NARRATIVES}/{FOLDER}/{slug}/{name}',
                            f'no narrative shows it; delete it, or link it from {slug}.md'))
    return out
