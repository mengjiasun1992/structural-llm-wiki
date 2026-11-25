"""sllmwiki/.SLLMWIKI_INDICES.md, GitHub's map of the wiki (design doc §4.8): a mermaid
diagram of the tag tree, and the same tree as a nested list of links to the tag pages;
and pages(), every generated page with its text. Under the tree, the reading paths: each
root's narratives in the order to read them (lib/readingorder.py), roots in dependency order.

GitHub draws a mermaid diagram in an iframe on another host, so a relative `click` link
resolves there and breaks (issue #199). When origin is on GitHub, each node opens its tag
page by an absolute URL on the default branch (`blob/HEAD`, which needs no branch name, so
a CI checkout and a clone write the same page); elsewhere the nodes don't click, and the
list below the diagram, whose relative links work in every renderer, opens the pages."""

import os

from . import layout, metadata, policy, readingorder, tagpages, tagtree
from .compat import escape
from .util import read_text

GENERATED = '<!-- sllmwiki:generated: rewritten by sllmwiki wiki-check -->'  # no double hyphen: XML forbids it in a comment


def _rel(path):
    """A repository path as a link from the index, which sits in the content folder."""
    return os.path.relpath(path, os.path.dirname(layout.INDEX)).replace(os.sep, '/')


def render(tree, questions, repo=None, minutes=None):
    """The index's text; repo, (owner, name) on GitHub, makes the diagram's nodes open their tag pages;
    minutes, {slug: reading time}, goes beside each narrative in the reading paths."""
    lines = ['# Index of this wiki', '', GENERATED, '',
             'The topics this wiki covers. Each opens a page with its narratives, sources and who to ask.', '']
    order = readingorder.Order(tree, questions)
    roots = order.roots()
    walk = tree.walk(roots)
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
    for _, tag in walk if repo else ():
        lines.append(f'    click {ids[tag]} "https://github.com/{repo[0]}/{repo[1]}/blob/HEAD/{tagpages.path(tag)}"')
    lines += ['```', '']
    for depth, tag in walk:
        count = sum(len(v) for v in tree.narratives_of(tag).values())
        lines.append(f'{"  " * depth}- [{tag}]({_rel(tagpages.path(tag))}): {tree.tags[tag].get("description") or ""}'
                     + (f' ({count} narrative{"s" if count != 1 else ""})' if count else ''))
    return escape('\n'.join(lines + _paths(order, roots, questions, minutes or {})) + '\n')[0]


def _paths(order, roots, questions, minutes):
    """The Reading paths section: a numbered list per root with narratives, each with the numbers of the
    narratives it needs in its own path, and a link to the place of one it needs in another."""
    paths = [(r, order.path(r)) for r in roots]
    paths = [(r, p) for r, p in paths if p]
    if not paths:
        return []
    out = ['', '## Reading paths', '', 'Each topic\'s narratives in the order to read them: "needs" names the ones to read first.']
    for root, path in paths:
        out += ['', f'### {root}', '']
        for i, slug in enumerate(path, 1):
            here, there = [], []
            for p in order.needs.get(slug, ()):
                at = order.place(p)
                if at and at[0] == root:
                    here.append(at[1])
                elif at:
                    there.append(f'[{at[0]} {at[1]}](#{at[0]})')
            needs = [str(n) for n in sorted(here)] + there
            out.append(f'{i}. [{questions.get(slug, slug)}]({_rel(f"{layout.NARRATIVES}/{slug}.md")})'
                       + (f' ({minutes[slug]} min)' if minutes.get(slug) else '')
                       + (f', needs {", ".join(needs[:-1]) + " and " + needs[-1] if len(needs) > 1 else needs[0]}' if needs else ''))
    return out


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
    out = {layout.INDEX: render(tree, qs, policy.origin_repo(root), mins)}
    order = readingorder.Order(tree, qs)
    for tag in tree.tags:
        out[tagpages.path(tag)] = tagpages.render(tree, tag, qs, mins, order)
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
        if have is not None and not tagpages.is_generated(have):
            findings.append(('warning', 'PAGE_HANDWRITTEN', rel, f'{rel} has no generated marker, so it\'s left alone; rename it to let the wiki generate it'))
            continue
        findings.append(('error', 'INDEX_OUTDATED' if rel == layout.INDEX else 'TAG_PAGE_OUTDATED', rel, f'{rel} is out of date (sllmwiki wiki-check --fix)'))
        if write:
            os.makedirs(os.path.dirname(path) or root, exist_ok=True)
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(text)
            changed.append(rel)
    folder = os.path.join(root, layout.TAGS_DIR)
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        rel = f'{layout.TAGS_DIR}/{name}'
        if name.endswith('.md') and rel not in want and tagpages.is_generated(read_text(os.path.join(root, rel))):
            findings.append(('error', 'TAG_PAGE_ORPHAN', rel, f'{rel} is for a tag that no longer exists (sllmwiki wiki-check --fix)'))
            if write:
                os.remove(os.path.join(root, rel))
                changed.append(rel)
    return findings, changed
