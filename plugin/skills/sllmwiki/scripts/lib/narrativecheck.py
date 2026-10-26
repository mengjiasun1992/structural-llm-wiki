"""The checks narrative-format.py and finish-narrative.py run on a narrative
(design doc §4.5, §4.8, §4.10): template sections, diagrams, numbers, lengths,
citations, markers, placeholders, doubled punctuation and markdown every
renderer reads alike."""

import os
import re

from . import citations, compat, figures, language, layout, manifest, markers, mdlinks, metadata, numbering, quotes, xrefs
from .compat import mask_code_spans, mask_math_spans, scan

PLACEHOLDER = re.compile(r'<(?!https?://|mailto:|/)[^<>\n]*\s[^<>\n]*>')
# A formula written as text: x_t or s_{t-1}, or a Greek letter beside an operator
FORMULA = re.compile(r'(?<![\w\\/])[A-Za-z]{1,6}_(?:\{[^}\s]+\}|[A-Za-z0-9]{1,3})(?!\w)|[\u03b1-\u03c9\u0391-\u03a9]\s*[\u00b7\u00d7]|[=\u00b7\u00d7]\s*\(?[\u03b1-\u03c9\u0391-\u03a9]')
# Punctuation doubled by an edit: ,, ;; or .. that isn't an ellipsis or a ../ path
DOUBLED = re.compile(r'([,;])\s*\1|(?<![./])\.\.(?![./])')
SHARED_TOP = ('Abstract', 'Terminology')
SHARED_BOTTOM = ('Appendix', 'SMEs', 'References', 'Metadata')


def words(lines):
    """The words of these lines, without markdown punctuation, code fences or table rules; CJK text counts
    its characters, at language.CJK_CHARACTERS_PER_WORD."""
    text = '\n'.join(line for line in lines if not re.match(r'\s*(```|~~~|\|?[-: |]+\|?\s*\Z)', line))
    return language.words(re.sub(r'\]\([^)]*\)', ']', text))


def _titles(english):
    """The lowercase titles a shared section goes by: its English one and every language pack's."""
    return {t.lower() for e in english for t in language.names(e)}


def check_sections(text, template):
    """Findings for the ## sections against the template's."""
    out = []
    heads = [h for h in numbering.headings(text) if h.level == 2]
    want = template.sections()
    pos = 0
    for h in heads:
        h.title = markers.unmark(h.title)  # a marked heading is still its section
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
            out.append(('error', 'MISSING_DIAGRAM', h.line + 1, f'"{h.title}" needs a ```mermaid diagram, or a figure'))
        pos = at + 1
    return out  # every skeleton ends with Metadata, where the template is named, so a missing section is always one skipped before it


def _has_diagram(text, head):
    """Whether the section has a ```mermaid block with more than comments in it, or a figure."""
    span = numbering.section(text, numbering.anchor(head.text))
    if any(span[0] <= i < span[1] for i, _, _ in figures.images(text)):
        return True
    inside = drawn = False
    for line in text.split('\n')[span[0]:span[1]]:
        if line.strip().startswith('```'):
            if inside and drawn:
                return True
            inside, drawn = line.strip().startswith('```mermaid'), False
        elif inside and line.strip() and not line.strip().startswith('%%'):
            drawn = True
    return False


def check_language(text, template, default):
    """Findings for a narrative's language: a language with no pack, and a heading left in English that its pack translates."""
    tag, pack = language.for_narrative(text, default)
    if pack is language.ENGLISH and tag.lower().split('-')[0] != 'en':
        return [('warning', 'LANGUAGE_PACK', 1, f'no language pack for {tag}: its headings stay English; '
                                                 f'add {layout.TEMPLATES}/{language.FOLDER}/{tag}.md to translate them')]
    out = []
    sections = template.sections()
    for h in numbering.headings(text):
        title = markers.unmark(h.title)
        if h.level == 2:
            english = next((s.title for s in sections if s.matches_english(title)), None)
        else:
            english = title if title in pack.strings else None
        if english and pack.t(english) != english and title.lower() == english.lower():
            out.append(('warning', 'HEADING_LANGUAGE', h.line + 1, f'"{title}" is in English; in {tag} it is "{pack.t(english)}"'))
    return out


def body_lines(text):
    """The lines of the template's own sections: after Terminology, before the appendices."""
    heads = [h for h in numbering.headings(text) if h.level == 2]
    lines = text.split('\n')
    top, bottom = _titles(SHARED_TOP), _titles(SHARED_BOTTOM)
    start = next((h.line for h in heads if h.title.lower() not in top), None)
    end = next((h.line for h in heads if h.title.lower() in bottom), len(lines))
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
    meta = metadata.read(text)
    name = meta['template']
    template = offered.get(name)
    if meta['words'] and meta['words'] != metadata.reading_label(text):
        at = next(i for i, line in enumerate(text.split('\n'), 1) if line.startswith('- **Words:**'))
        out.append(('warning', 'WORDS_OUTDATED', at, f'Metadata says {meta["words"]} words; it is {metadata.reading_label(text)} now '
                                                    '(finish-narrative.py updates it)'))
    if not name:
        out.append(('error', 'NO_TEMPLATE', 1, 'Metadata names no template (- **Template:** <name>)'))
    elif not template:
        out.append(('error', 'UNKNOWN_TEMPLATE', 1, f'no template {name}; there are {", ".join(sorted(offered))}'))
    else:
        out += check_sections(text, template)
        out += check_language(text, template, settings['language'])
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
    out += figures.check(root, rel, text, settings['images'])
    out += figures.check_captions(text)
    out += xrefs.check(root, rel, text)
    lines = text.split('\n')
    kinds, _ = scan(lines)
    for i, line in enumerate(lines):
        m = PLACEHOLDER.search(mask_code_spans(line)) if kinds[i] == 'text' else None
        if m:
            out.append(('error', 'PLACEHOLDER', i + 1, f'"{m.group(0)}" is the skeleton\'s placeholder; write the content'))
        m = FORMULA.search(mask_math_spans(mask_code_spans(line))) if kinds[i] == 'text' else None
        if m:
            out.append(('warning', 'MATH_AS_TEXT', i + 1, f'"{m.group(0)}" looks like a formula written as text; write it as TeX, $...$'))
        m = DOUBLED.search(re.sub(r'\]\([^)]*\)', ']', mask_math_spans(mask_code_spans(line)))) if kinds[i] == 'text' else None
        if m:
            out.append(('error', 'DOUBLED_PUNCTUATION', i + 1, f'"{m.group(0)}": punctuation doubled, likely by an edit'))
    out += compat.check(text)
    out += compat.check_links(text, os.path.dirname(os.path.join(root, rel)), root)
    return sorted(out, key=lambda f: f[2])


def stats(root, rel, text, offered):
    """The numbers lint grades a narrative's aim with: its body against the budget, the words in each of
    its template's sections, its subsections, citations by the authority of what they cite, markers and pictures."""
    name = metadata.read(text)['template']
    template = offered.get(name)
    heads = [h for h in numbering.headings(text) if h.level == 2]
    lines = text.split('\n')
    sections = []
    for i, h in enumerate(heads):
        title = markers.unmark(h.title)
        if title.lower() in _titles(SHARED_TOP + SHARED_BOTTOM) - _titles(['Appendix']):
            continue
        end = heads[i + 1].line if i + 1 < len(heads) else len(lines)
        part = '\n'.join(lines[h.line + 1:end])
        sections.append({'section': title, 'words': words(lines[h.line + 1:end]),
                         'subsections': sum(1 for s in numbering.headings(part) if s.level in (3, 4)),
                         'citations': len(citations.CITE.findall(part)),
                         'markers': sum(1 for j, _, _ in markers.uses(text) if h.line <= j < end)})
    slug = os.path.splitext(os.path.basename(rel))[0]
    grades = (manifest.load(root, 'narratives').get(slug) or {}).get('grades') or {}
    by = {'A': 0, 'B': 0, 'C': 0, 'ungraded': 0}
    for c in citations.cites(text):
        if c.slug:
            by[(grades.get(c.slug) or {}).get('authority', 'ungraded')] += 1
    used = markers.uses(text)
    return {'file': rel, 'template': name, 'budget': template.max_words if template else None,
            'body_words': words(body_lines(text)), 'abstract_words': words(metadata.abstract(text).split('\n')),
            'sections': sections, 'citations': by,
            'markers': {'statements': sum(1 for i, _, _ in used if not lines[i].lstrip().startswith('#')),
                        'headings': sum(1 for i, _, _ in used if lines[i].lstrip().startswith('#'))},
            'pictures': len(figures.pictures(text))}
