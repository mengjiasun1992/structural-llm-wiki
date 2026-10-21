"""The tag tree and what is derived from it (design doc §4.1-§4.2): children,
ancestors, adjacent tags, and the sources and narratives filed under a tag."""

from . import manifest


class Tree:
    def __init__(self, tags, sources, narratives):
        self.tags, self.sources, self.narratives = tags, sources, narratives

    def parent(self, tag):
        return self.tags[tag].get('parent')

    def children(self, tag):
        return [t for t, e in self.tags.items() if e.get('parent') == tag]

    def roots(self):
        return [t for t, e in self.tags.items() if not e.get('parent') or e['parent'] not in self.tags]

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


def load(root):
    return Tree(manifest.load(root, 'tags'), manifest.load(root, 'sources'), manifest.load(root, 'narratives'))
