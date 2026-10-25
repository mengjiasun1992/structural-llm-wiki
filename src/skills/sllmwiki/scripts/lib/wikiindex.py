"""SLLMWIKI_INDICES.md, GitHub's map of the wiki (design doc §4.8): a mermaid
diagram of the tag tree whose nodes open the tag pages, and the same tree as a
nested list; and pages(), every generated page with its text."""

import os

from . import layout, metadata, tagpages, tagtree
from .compat import escape
from .util import read_text

GENERATED = '<!-- sllmwiki:generated: rewritten by wiki-check.py --fix -->'


def render(tree, questions):
    lines = ['# Index of this wiki', '', GENERATED, '',
             'The topics this wiki covers. Each opens a page with its narratives, sources and who to ask.', '']
    walk = tree.walk()
    if not walk:
        return '\n'.join(lines + ['No topics yet.', ''])
    ids = {tag: f't{i}' for i, (_, tag) in enumerate(walk)}
    lines += ['```mermaid', 'graph LR']
    for _, tag in walk:
        lines.append(f'    {ids[tag]}["{tag}"]')
    for _, tag in walk:
        parent = tree.parent(tag)
        if parent in ids:
            lines.append(f'    {ids[parent]} --> {ids[tag]}')
    for _, tag in walk:
        lines.append(f'    click {ids[tag]} "{tagpages.path(tag)}"')
    lines += ['```', '']
    for depth, tag in walk:
        count = sum(len(v) for v in tree.narratives_of(tag).values())
        lines.append(f'{"  " * depth}- [{tag}]({tagpages.path(tag)}): {tree.tags[tag].get("description") or ""}'
                     + (f' ({count} narrative{"s" if count != 1 else ""})' if count else ''))
    return escape('\n'.join(lines) + '\n')[0]


def questions(root, tree):
    out = {}
    for slug in tree.narratives:
        path = os.path.join(root, layout.NARRATIVES, f'{slug}.md')
        if os.path.isfile(path):
            out[slug] = metadata.title(read_text(path)) or slug
    return out


def minutes(root, tree):
    """{slug: reading time in minutes} of every narrative with a file."""
    out = {}
    for slug in tree.narratives:
        path = os.path.join(root, layout.NARRATIVES, f'{slug}.md')
        if os.path.isfile(path):
            out[slug] = metadata.reading(read_text(path))[1]
    return out


def pages(root):
    """{repository-relative path: text} of every page the wiki generates."""
    tree = tagtree.load(root)
    qs = questions(root, tree)
    mins = minutes(root, tree)
    out = {layout.INDEX: render(tree, qs)}
    for tag in tree.tags:
        out[tagpages.path(tag)] = tagpages.render(tree, tag, qs, mins)
    return out


def sync(root, write):
    """(findings, changed paths) for the generated pages: outdated or missing,
    or a generated tag page whose tag is gone; with write, rewritten or removed.
    A page someone wrote by hand (no generated marker) is reported, never touched."""
    want = pages(root)
    findings, changed = [], []
    for rel, text in want.items():
        path = os.path.join(root, rel)
        have = read_text(path) if os.path.isfile(path) else None
        if have == text:
            continue
        if have is not None and not (tagpages.is_generated(have) or GENERATED in have):
            findings.append(('warning', 'PAGE_HANDWRITTEN', rel, f'{rel} has no generated marker, so it\'s left alone; rename it to let the wiki generate it'))
            continue
        findings.append(('error', 'INDEX_OUTDATED' if rel == layout.INDEX else 'TAG_PAGE_OUTDATED', rel, f'{rel} is out of date (wiki-check.py --fix)'))
        if write:
            os.makedirs(os.path.dirname(path) or root, exist_ok=True)
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(text)
            changed.append(rel)
    folder = os.path.join(root, layout.TAGS_DIR)
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        rel = f'{layout.TAGS_DIR}/{name}'
        if name.endswith('.md') and rel not in want and tagpages.is_generated(read_text(os.path.join(root, rel))):
            findings.append(('error', 'TAG_PAGE_ORPHAN', rel, f'{rel} is for a tag that no longer exists (wiki-check.py --fix)'))
            if write:
                os.remove(os.path.join(root, rel))
                changed.append(rel)
    return findings, changed
