"""A narrative's reading plan (design doc §7.1): the candidates for a question's
tags, and the order to read them in once each is graded."""

import json
import os

from . import layout, metadata, tagtree
from .util import read_text

RELEVANCE = ('high', 'medium', 'low')
AUTHORITY = ('A', 'B', 'C')


def candidates(root, primary, supporting):
    tree = tagtree.load(root)
    unknown = [t for t in primary + supporting if t not in tree.tags]
    if unknown:
        raise ValueError(f'no such tag(s): {", ".join(unknown)}')
    tags = primary + supporting
    narratives = []
    for slug in dict.fromkeys(n for t in tags for role in ('primary', 'supporting') for n in tree.narratives_of(t)[role]):
        path = os.path.join(root, layout.NARRATIVES, f'{slug}.md')
        if os.path.isfile(path):
            text = read_text(path)
            narratives.append({'slug': slug, 'question': metadata.title(text), 'created': metadata.read(text)['created'] or '',
                               'path': f'{layout.NARRATIVES}/{slug}.md'})
    sources = []
    for slug in dict.fromkeys(s for t in tags for s in tree.sources_of(t)):
        e = tree.sources[slug]
        path = os.path.join(root, layout.in_content(e['file'])) if e.get('file') else None
        sources.append({'slug': slug, 'kind': e.get('kind'), 'bytes': os.path.getsize(path) if path and os.path.isfile(path) else None,
                        'date': e.get('published') or '', 'abstract': e.get('abstract'),
                        'abstract_draft': bool(e.get('abstract_draft')), 'tags': e.get('tags')})
    noted = sorted({a for t in tags for a in tree.ancestors(t) + tree.adjacent(t)} - set(tags))
    return {'narratives': narratives, 'sources': sources, 'noted_not_read': noted}


def order(found, grades):
    """(plan rows, problems): each row {step, read, slug, why}."""
    problems = []
    graded = {}
    for s in found['sources']:
        g = grades.get(s['slug'])
        if s['kind'] == 'link':
            continue
        if not isinstance(g, dict) or g.get('relevance') not in RELEVANCE or g.get('authority') not in AUTHORITY:
            problems.append(f'{s["slug"]}: needs {{"relevance": "high|medium|low", "authority": "A|B|C"}}')
        else:
            graded[s['slug']] = (g, s)
    narratives = {}  # an existing narrative is graded by relevance only; ungraded, it is background
    for n in sorted(found['narratives'], key=lambda n: n['created']):
        g = grades.get(n['slug'])
        level = g.get('relevance') if isinstance(g, dict) else None
        if g is not None and level not in RELEVANCE:
            problems.append(f'{n["slug"]}: an existing narrative needs {{"relevance": "high|medium|low"}}')
        narratives.setdefault(level if level in RELEVANCE else None, []).append(n)
    rows = [{'read': 'in full', 'slug': n['slug'], 'why': 'existing narrative, background'} for n in narratives.get(None, [])]
    rows += [{'read': 'in full', 'slug': n['slug'], 'why': 'existing narrative, medium relevance'} for n in narratives.get('medium', [])]
    for level in ('medium', 'high'):
        chosen = [(g, s) for g, s in graded.values() if g['relevance'] == level]
        for g, s in sorted(chosen, key=lambda gs: (-AUTHORITY.index(gs[0]['authority']), gs[1]['date'])):
            rows.append({'read': 'in full', 'slug': s['slug'], 'why': f'{level} relevance, authority {g["authority"]}, {s["date"] or "undated"}'})
    # built on: read last, so its wording is the freshest when the narrative reuses it
    rows += [{'read': 'in full', 'slug': n['slug'], 'why': 'existing narrative, high relevance: built on'} for n in narratives.get('high', [])]
    rows += [{'read': 'abstract only', 'slug': n['slug'], 'why': 'existing narrative, low relevance'} for n in narratives.get('low', [])]
    rows += [{'read': 'abstract only', 'slug': s['slug'], 'why': 'low relevance'} for g, s in graded.values() if g['relevance'] == 'low']
    rows += [{'read': 'not read', 'slug': s['slug'], 'why': 'a link, no saved copy'} for s in found['sources'] if s['kind'] == 'link']
    for i, r in enumerate(rows, 1):
        r['step'] = i
    return rows, problems


def load_grades(path):
    """The grades file's {slug: {relevance, authority}} for sources and {slug: {relevance}} for existing
    narratives; ValueError when unreadable."""
    try:
        with open(path, encoding='utf-8') as f:
            grades = json.load(f)
    except (OSError, ValueError) as e:
        raise ValueError(f'can\'t read the grades: {e}') from None
    if not isinstance(grades, dict):
        raise ValueError('the grades must be a mapping of source slug to {"relevance": ..., "authority": ...}')
    return grades


def plan_path(grades_path):
    """Where reading-plan.py order keeps the plan it printed: beside the grades file."""
    return grades_path + '.plan.json'


def narratives_read(grades_path):
    """The narratives the saved plan had the reader read, or None without a saved plan."""
    try:
        with open(plan_path(grades_path), encoding='utf-8') as f:
            rows = json.load(f)
    except (OSError, ValueError):
        return None
    return {r.get('slug') for r in rows if isinstance(r, dict) and str(r.get('why', '')).startswith('existing narrative')}


def metadata_lines(rows):
    """The plan's steps as the Metadata's Reading plan lists them."""
    return [f'`{r["slug"]}`, {r["read"]}: {r["why"]}' for r in rows]
