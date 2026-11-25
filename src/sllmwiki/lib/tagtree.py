"""The tag tree and what is derived from it (design doc §4.1-§4.2): children,
ancestors, adjacent tags, and the sources and narratives filed under a tag.
Siblings, roots included, come in the order the owner set (a tag's order, from
sllmwiki manifest order-tags), then in file order; review() finds tags a reader
may not expect where they are, and narratives a new tag may be missing from."""

import os
import re
from collections import Counter

from . import layout, manifest, prerequisites
from .util import read_text

REVIEW = ('TAG_NO_PRIMARY', 'TAG_OTHER_ROOT', 'TAG_BUILDS_ON_ROOT', 'TAG_RETAG')


class Tree:
    def __init__(self, tags, sources, narratives):
        self.tags, self.sources, self.narratives = tags, sources, narratives

    def parent(self, tag):
        return self.tags[tag].get('parent')

    def _ordered(self, tags):
        place = {t: i for i, t in enumerate(self.tags)}
        order = {t: self.tags[t].get('order') for t in tags}
        return sorted(tags, key=lambda t: (not isinstance(order[t], int), order[t] if isinstance(order[t], int) else 0, place[t]))

    def children(self, tag):
        return self._ordered([t for t, e in self.tags.items() if e.get('parent') == tag])

    def roots(self):
        return self._ordered([t for t, e in self.tags.items() if not e.get('parent') or e['parent'] not in self.tags])

    def subtree(self, tag):
        """The tag and every tag under it."""
        out, todo = [], [tag]
        while todo:
            t = todo.pop(0)
            if t not in out:
                out.append(t)
                todo += self.children(t)
        return out

    def filed_under(self, tag):
        """The narratives filed, as primary or supporting, under the tag or a tag under it."""
        under = set(self.subtree(tag))
        return [n for n, e in self.narratives.items() if under & set(((e.get('tags') or {}).get('primary') or []) + ((e.get('tags') or {}).get('supporting') or []))]

    def _primary(self, slug):
        return [t for t in ((self.narratives.get(slug) or {}).get('tags') or {}).get('primary') or [] if t in self.tags]

    def root_of(self, tag):
        chain = self.ancestors(tag)
        return chain[-1] if chain else tag

    def ancestors(self, tag):
        """Parent first, up to the root; stops at a cycle."""
        out, cur = [], self.parent(tag)
        while cur and cur in self.tags and cur not in out and cur != tag:
            out.append(cur)
            cur = self.parent(cur)
        return out

    def adjacent(self, tag):
        """The tag's siblings."""
        parent = self.parent(tag)
        return [t for t in (self.children(parent) if parent else self.roots()) if t != tag]

    def sources_of(self, tag):
        return [s for s, e in self.sources.items() if tag in (e.get('tags') or [])]

    def narratives_of(self, tag):
        """{'primary': [...], 'supporting': [...]} of the narratives filed under the tag."""
        out = {'primary': [], 'supporting': []}
        for n, e in self.narratives.items():
            for role in out:
                if tag in ((e.get('tags') or {}).get(role) or []):
                    out[role].append(n)
        return out

    def walk(self):
        """(depth, tag) for every tag, each root's tree in turn, children in file order."""
        out, seen = [], set()

        def visit(tag, depth):
            if tag in seen:
                return
            seen.add(tag)
            out.append((depth, tag))
            for child in self.children(tag):
                visit(child, depth + 1)
        for root in self.roots():
            visit(root, 0)
        for tag in self.tags:  # tags on a cycle have no root
            visit(tag, 0)
        return out

    def problems(self):
        """(code, tag or entry, message) for a missing parent, a cycle, or a tag a manifest names that doesn't exist."""
        out = []
        for tag, e in self.tags.items():
            parent = e.get('parent')
            if parent and parent not in self.tags:
                out.append(('UNKNOWN_PARENT', tag, f'{tag}: its parent {parent} isn\'t a tag'))
            elif parent and tag in self.ancestors(parent) + [parent]:
                out.append(('TAG_CYCLE', tag, f'{tag}: its parents lead back to it'))
        for slug, e in self.sources.items():
            for t in e.get('tags') or []:
                if t not in self.tags:
                    out.append(('UNKNOWN_TAG', slug, f'source {slug}: no tag {t}'))
        for slug, e in self.narratives.items():
            for role in ('primary', 'supporting'):
                for t in (e.get('tags') or {}).get(role) or []:
                    if t not in self.tags:
                        out.append(('UNKNOWN_TAG', slug, f'narrative {slug}: no tag {t}'))
        return out


    def review(self, ties=None, new=()):
        """(code, tag, message) for a tag a reader may not expect where it is: a leaf no narrative has as a primary
        tag (TAG_NO_PRIMARY); a tag most of whose narratives have their other primary tags under one other root
        (TAG_OTHER_ROOT); with ties (narrative_ties()), a tag most of whose subtree's narratives link to, build on or
        need narratives under one other root (TAG_BUILDS_ON_ROOT), reported on the highest such tag; and for each tag
        in new, the narratives not filed under it that link to its narratives or name it (TAG_RETAG).
        A parent with no narratives of its own is fine: it groups its children."""
        out = []
        out += self._own_review()
        if ties:
            out += self._ties_review(ties[0], {t for c, t, _ in out if c == 'TAG_OTHER_ROOT'})
            for tag in new:
                out += self._retag(tag, *ties)
        return out

    def _ties_review(self, refs, flagged):
        out, said = [], {}
        for _, tag in self.walk():
            if tag in flagged:
                continue
            home, filed = self.root_of(tag), self.filed_under(tag)
            counts = Counter()
            for n in filed:
                counts.update({self.root_of(t) for r in refs.get(n, ()) for t in self._primary(r)} - {home})
            if not counts:
                continue
            other, count = counts.most_common(1)[0]
            if 2 * count > len(filed) and not any(said.get(a) == other for a in self.ancestors(tag)):
                said[tag] = other
                where = 'a root' if home == tag else f'under {home}'
                out.append(('TAG_BUILDS_ON_ROOT', tag, f'{tag} is {where}, but {count} of the {len(filed)} narrative(s) filed under it link to, '
                                                       f'build on or need narratives under {other}: check whether it is a kind of {other} '
                                                       f'or built on it, and move it there if so (sllmwiki manifest move-tag)'))
        return out

    def _retag(self, tag, refs, parts):
        """TAG_RETAG for the narratives that may use a new tag's subject but aren't filed under it."""
        under = set(self.subtree(tag))
        mine = {n for n in self.narratives if under & set(self._primary(n))}
        name = _named(tag)
        out = []
        for n in sorted(set(self.narratives) - set(self.filed_under(tag))):
            links = sorted(refs.get(n, set()) & mine)
            named = len(name.findall(re.sub(r'\]\([^)]*\)', ']', parts.get(n, ''))))
            if links or named:
                why = '; '.join(([f'links to, builds on or needs {", ".join(links)}'] if links else []) + ([f'names it {named} time(s)'] if named else []))
                out.append(('TAG_RETAG', tag, f'{n} may use {tag} ({why}): add it, at least as a supporting tag '
                                              f'(sllmwiki finish-narrative {n} --supporting <its supporting tags>,{tag})'))
        return out

    def _own_review(self):
        out = []
        for tag in self.tags:
            on = self.narratives_of(tag)
            if not on['primary'] and not self.children(tag):
                out.append(('TAG_NO_PRIMARY', tag, f'{tag}: no narrative has it as a primary tag; check it is where a reader would look, '
                                                   'or remove it (sllmwiki manifest remove tags)'))
            filed = on['primary'] + on['supporting']
            home, elsewhere = self.root_of(tag), Counter()
            for n in filed:
                roots = {self.root_of(t) for t in ((self.narratives[n].get('tags') or {}).get('primary') or []) if t != tag and t in self.tags}
                if roots and home not in roots:
                    elsewhere.update(roots)
            if elsewhere:
                other, count = elsewhere.most_common(1)[0]
                if 2 * count > len(filed):
                    out.append(('TAG_OTHER_ROOT', tag, f'{tag} is under {home}, but {count} of its {len(filed)} narrative(s) have their other '
                                                       f'primary tags under {other}: move it there if a reader would look for it there '
                                                       '(sllmwiki manifest move-tag)'))
        return out


def _stem(word):
    return word[:-1] if word.endswith('s') and len(word) > 3 else word


def _named(tag):
    """A tag's name as prose says it: neural-networks matches "neural network", "Neural Networks", "neural-network"."""
    words = [re.escape(_stem(w)) for w in tag.split('-')]
    return re.compile(r'(?<![\w-])' + r'[\s-]+'.join(words) + r'(?:e?s)?(?![\w-])', re.I)


def narrative_ties(root, narratives):
    """({slug: narratives it links to, builds on or needs first}, {slug: what a reader reads of it}): what
    review() follows between narratives."""
    refs, parts = {}, {}
    for slug, e in narratives.items():
        path = os.path.join(root, layout.NARRATIVES, f'{slug}.md')
        text = read_text(path) if os.path.isfile(path) else ''
        parts[slug] = prerequisites.read_part(text) if text else ''
        refs[slug] = ((prerequisites.linked(text) if text else set()) | set(e.get('built_on') or {}) | set(e.get('prerequisites') or {})) - {slug}
    return refs, parts


def load(root):
    return Tree(manifest.load(root, 'tags'), manifest.load(root, 'sources'), manifest.load(root, 'narratives'))
