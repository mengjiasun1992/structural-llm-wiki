"""The figures a narrative embeds (design doc §4.5): images it generates for what
a mermaid diagram can't show well, kept in narratives/figures/<slug>/.

check(root, rel, text, on) -> findings for one narrative:
  IMAGE_OFF         an image while Config.toml's images setting is false
  IMAGE_PLACE       an image that isn't an .svg or .png in figures/<slug>/
  IMAGE_ALT         an image without alt text
  IMAGE_UNSAFE      an SVG with a script, an event handler or a link to another file
  IMAGE_BACKGROUND  an SVG with no opaque background, so dark themes hide its dark text (warning)
  IMAGE_SIZE        a figure over MAX_BYTES (warning)
unused(root) -> findings for figures no narrative shows (FIGURE_UNUSED, warning).
"""

import os
import re

from . import layout
from .compat import mask_code_spans, scan
from .util import read_text

FOLDER = 'figures'
KINDS = ('.svg', '.png')
MAX_BYTES = 500_000
IMAGE = re.compile(r'!\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)')
_UNSAFE = re.compile(r'<script|<foreignObject|\son\w+\s*=|(?:xlink:)?href\s*=\s*["\'](?!#)', re.I)
_BACKGROUND = re.compile(r'<rect\b[^>]*\bfill\s*=\s*["\'](?!none|transparent)|background(?:-color)?\s*:', re.I)


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
        if os.path.getsize(full) > MAX_BYTES:
            out.append(('warning', 'IMAGE_SIZE', n, f'{path} is over {MAX_BYTES // 1000} KB; simplify it'))
        if path.lower().endswith('.svg'):
            svg = read_text(full)
            if _UNSAFE.search(svg):
                out.append(('error', 'IMAGE_UNSAFE', n, f'{path}: an SVG figure is self-contained: no scripts, event handlers or links to other files'))
            elif not _BACKGROUND.search(svg):
                out.append(('warning', 'IMAGE_BACKGROUND', n, f'{path} has no opaque background, so dark themes hide its dark text; '
                                                             'start it with a light <rect> the size of the figure'))
    return out


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
