"""A generated page per tag, next to tags.yaml (design doc §4.8): the tag's
description, its parent and children, its narratives and sources, and its SMEs.
The pages make each topic browsable on GitHub and put the tag tree in
Obsidian's graph. A page without the generated marker is someone's own and is
left alone."""

import re

from . import layout
from .compat import escape

GENERATED = '<!-- sllmwiki:generated: rewritten by wiki-check.py --fix; edit tags.yaml and the manifests instead -->'


def path(tag):
    return f'{layout.TAGS_DIR}/{tag}.md'


def _first_sentence(text, limit=30):
    words = (text or '').split()
    short = ' '.join(words[:limit])
    m = re.match(r'(.+?[.!?])(\s|\Z)', short)
    return m.group(1) if m else short + ('…' if len(words) > limit else '')


def render(tree, tag, questions, minutes=None):
    """The page for tag; questions maps a narrative slug to its question, and minutes to its reading time."""
    minutes = minutes or {}
    e = tree.tags[tag]
    lines = [f'# {tag}', '', GENERATED, '', e.get('description') or '', '']
    chain = list(reversed(tree.ancestors(tag)))
    if chain:
        lines += ['**Path:** ' + ' / '.join(f'[{t}]({t}.md)' for t in chain) + f' / {tag}', '']
    children = tree.children(tag)
    if children:
        lines += ['## Subtopics', ''] + [f'- [{c}]({c}.md): {tree.tags[c].get("description") or ""}' for c in children] + ['']
    narratives = tree.narratives_of(tag)
    if narratives['primary'] or narratives['supporting']:
        lines += ['## Narratives', '']
        for role in ('primary', 'supporting'):
            lines += [f'- [{questions.get(n, n)}](../narratives/{n}.md){f" · {minutes[n]} min" if minutes.get(n) else ""}'
                      f'{" (supporting)" if role == "supporting" else ""}' for n in narratives[role]]
        lines.append('')
    sources = tree.sources_of(tag)
    if sources:
        lines += ['## Sources', '']
        for s in sources:
            src = tree.sources[s]
            target = f'../sources/{s}.md' if src.get('file') else f'<{src.get("url")}>'
            note = ' (abstract not written yet)' if src.get('abstract_draft') else ''
            lines.append(f'- [{s}]({target}){note}: {_first_sentence(src.get("abstract"))}')
        lines.append('')
    smes = e.get('smes') or []
    if smes:
        lines += ['## Who to ask', ''] + [f'- {s}' for s in smes] + ['']
    return escape('\n'.join(lines).rstrip('\n') + '\n')[0]


def is_generated(text):
    return GENERATED in text
