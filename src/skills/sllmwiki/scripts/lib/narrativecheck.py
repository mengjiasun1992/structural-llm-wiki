"""The checks narrative-format.py and finish-narrative.py run on a narrative
(design doc §4.5, §4.8, §4.10): template sections, diagrams, numbers, lengths,
citations, markers, placeholders and markdown every renderer reads alike."""

import os
import re

from . import citations, compat, manifest, markers, mdlinks, metadata, numbering, quotes
from .compat import mask_code_spans, mask_math_spans, scan

PLACEHOLDER = re.compile(r'<(?!https?://|mailto:|/)[^<>\n]*\s[^<>\n]*>')
# A formula written as text: x_t or s_{t-1}, or a Greek letter beside an operator
FORMULA = re.compile(r'(?<![\w\\/])[A-Za-z]{1,6}_(?:\{[^}\s]+\}|[A-Za-z0-9]{1,3})(?!\w)|[\u03b1-\u03c9\u0391-\u03a9]\s*[\u00b7\u00d7]|[=\u00b7\u00d7]\s*\(?[\u03b1-\u03c9\u0391-\u03a9]')
SHARED_TOP = ('Abstract', 'Terminology')
SHARED_BOTTOM = ('SMEs', 'References', 'Metadata')


def words(lines):
    """The words of these lines, without markdown punctuation, code fences or table rules."""
    text = '\n'.join(line for line in lines if not re.match(r'\s*(```|~~~|\|?[-: |]+\|?\s*\Z)', line))
    return len(re.findall(r'[\w\'’-]+', re.sub(r'\]\([^)]*\)', ']', text)))


def check_sections(text, template):
    """Findings for the ## sections against the template's."""
    out = []
    heads = [h for h in numbering.headings(text) if h.level == 2]
    want = template.sections()
    pos = 0
    for h in heads:
        at = next((j for j in range(pos, len(want)) if want[j].matches(h.title)), None)
        if at is None:
            if any(s.matches(h.title) for s in want):
                out.append(('error', 'SECTION_ORDER', h.line + 1, f'"{h.title}" is out of order: the template has {", ".join(s.title for s in want)}'))
            else:
                out.append(('warning', 'EXTRA_SECTION', h.line + 1, f'"{h.title}" isn\'t one of {template.name}\'s sections'))
            continue
        for skipped in want[pos:at]:
            if not skipped.optional:
                out.append(('error', 'MISSING_SECTION', h.line + 1, f'the template needs "{skipped.title}" before "{h.title}"'))
        if want[at].diagram and not _has_diagram(text, h):
            out.append(('error', 'MISSING_DIAGRAM', h.line + 1, f'"{h.title}" needs a ```mermaid diagram'))
        pos = at + 1
    return out  # every skeleton ends with Metadata, where the template is named, so a missing section is always one skipped before it


def _has_diagram(text, head):
    """Whether the section has a ```mermaid block with more than comments in it."""
    span = numbering.section(text, numbering.anchor(head.text))
    inside = drawn = False
    for line in text.split('\n')[span[0]:span[1]]:
        if line.strip().startswith('```'):
            if inside and drawn:
                return True
            inside, drawn = line.strip().startswith('```mermaid'), False
        elif inside and line.strip() and not line.strip().startswith('%%'):
            drawn = True
    return False


def body_lines(text):
    """The lines of the template's own sections: after Terminology, before the appendices."""
    heads = [h for h in numbering.headings(text) if h.level == 2]
    lines = text.split('\n')
    start = next((h.line for h in heads if h.title.lower() not in [s.lower() for s in SHARED_TOP]), None)
    end = next((h.line for h in heads if h.title.lower() in [s.lower() for s in SHARED_BOTTOM]), len(lines))
    return lines[start:end] if start is not None and start < end else []


def check_citation_targets(root, rel, text):
    out = []
    sources = manifest.load(root, 'sources')
    for c in citations.cites(text):
        if not c.slug:
            continue
        if c.slug not in sources:
            out.append(('error', 'CITATION_SOURCE', c.line + 1, f'[{c.n}] cites {c.slug}, which isn\'t a recorded source'))
        elif sources[c.slug].get('kind') == 'link':
            out.append(('error', 'CITATION_SOURCE', c.line + 1, f'[{c.n}] cites {c.slug}, a link with no saved copy; cite a saved source'))
        else:
            problem = mdlinks.problem(root, rel, c.target)
            if problem:
                out.append(('error', 'CITATION_BROKEN', c.line + 1, f'[{c.n}] {problem}'))
    return out


def check(root, rel, text, settings, offered):
    """Every finding for one narrative, in line order."""
    out = []
    if not re.match(r'# \S', text):
        out.append(('error', 'NO_TITLE', 1, 'a narrative starts with its question as the # title'))
    name = metadata.read(text)['template']
    template = offered.get(name)
    if not name:
        out.append(('error', 'NO_TEMPLATE', 1, 'Metadata names no template (- **Template:** <name>)'))
    elif not template:
        out.append(('error', 'UNKNOWN_TEMPLATE', 1, f'no template {name}; there are {", ".join(sorted(offered))}'))
    else:
        out += check_sections(text, template)
        n = words(metadata.abstract(text).split('\n'))
        lo, hi = template.abstract_words
        if not lo <= n <= hi:
            out.append(('error', 'ABSTRACT_LENGTH', 1, f'the Abstract has {n} words; {template.name} wants {lo}-{hi}'))
        body = words(body_lines(text))
        if body > template.max_words:
            out.append(('warning', 'BODY_LENGTH', 1, f'the body has {body} words, over {template.name}\'s budget of {template.max_words}'))
    out += numbering.check(text)
    out += citations.check(text)
    out += check_citation_targets(root, rel, text)
    out += markers.check(text, settings['markers'])
    out += quotes.check(root, rel, text, settings['max_quote_words'])
    lines = text.split('\n')
    kinds, _ = scan(lines)
    for i, line in enumerate(lines):
        m = PLACEHOLDER.search(mask_code_spans(line)) if kinds[i] == 'text' else None
        if m:
            out.append(('error', 'PLACEHOLDER', i + 1, f'"{m.group(0)}" is the skeleton\'s placeholder; write the content'))
        m = FORMULA.search(mask_math_spans(mask_code_spans(line))) if kinds[i] == 'text' else None
        if m:
            out.append(('warning', 'MATH_AS_TEXT', i + 1, f'"{m.group(0)}" looks like a formula written as text; write it as TeX, $...$'))
    out += compat.check(text)
    out += compat.check_links(text, os.path.dirname(os.path.join(root, rel)), root)
    return sorted(out, key=lambda f: f[2])
