"""The order to read the wiki in (design doc §4.8, issue #206), computed from the
tag tree and the narratives' prerequisites, so it is always current.

- A narrative's **home** is its most specific primary tag: a primary tag that is
  an ancestor of another of its primary tags drops out, and the first that is
  left is the home. Unrelated tags keep the order the narrative lists them in,
  since depths in different trees don't compare.
- **Roots** come in dependency order: a root whose narratives need another
  root's comes after it; otherwise the owner's order (sllmwiki manifest
  order-tags), then file order.
- A root's **reading path** is the narratives homed under it, each after its
  prerequisites, ties broken by where its home sits in the tree, then template
  (what-is before how-does), then question.
- A tag page lists its narratives each after its prerequisites among them,
  ties broken primary before supporting, then question.
"""

import heapq

from . import prerequisites

# "what is X" before "how does X work" and "X or Y"; a wiki's own template goes last (docs/book_design.md §5.2)
TEMPLATE_ORDER = ('concept_brief_overview', 'survey', 'technical_brief_overview', 'comparison', 'case_study')


def template_rank(template):
    return TEMPLATE_ORDER.index(template) if template in TEMPLATE_ORDER else len(TEMPLATE_ORDER)


def home(tree, primary):
    """The home tag among a narrative's primary tags, or None when none is in the tree."""
    tags = [t for t in primary or [] if t in tree.tags]
    keep = [t for t in tags if not any(o != t and t in tree.ancestors(o) for o in tags)]
    return keep[0] if keep else None


def homes(tree):
    """{slug: home tag} for every narrative with a primary tag in the tree."""
    out = {}
    for slug, e in tree.narratives.items():
        h = home(tree, ((e or {}).get('tags') or {}).get('primary'))
        if h:
            out[slug] = h
    return out


def topological(items, before, key):
    """items with each after the ones before[item] names among them, ties by key; items on a cycle last, by key."""
    items = list(items)
    within = {s: {b for b in before.get(s, ()) if b in items and b != s} for s in items}
    waiting = {s: len(b) for s, b in within.items()}
    ready = [(key(s), s) for s in items if not waiting[s]]
    heapq.heapify(ready)
    out = []
    while ready:
        _, s = heapq.heappop(ready)
        out.append(s)
        for t, b in within.items():
            if s in b:
                waiting[t] -= 1
                if not waiting[t]:
                    heapq.heappush(ready, (key(t), t))
    return out + sorted((s for s in items if s not in out), key=key)


class Order:
    """The wiki's reading order: titles maps a narrative's slug to its question."""

    def __init__(self, tree, titles):
        self.tree, self.titles = tree, titles
        self.needs = prerequisites.graph(tree.narratives)
        self.homes = {s: h for s, h in homes(tree).items() if s in titles}
        place = {t: i for i, (_, t) in enumerate(tree.walk())}
        self._place = place

    def _title(self, slug):
        return (self.titles.get(slug) or slug).casefold()

    def roots(self):
        """The roots, each after the roots its narratives' prerequisites are homed under."""
        owner = self.tree.roots()
        rank = {r: i for i, r in enumerate(owner)}
        before = {r: set() for r in owner}
        for s, h in self.homes.items():
            mine = self.tree.root_of(h)
            for p in self.needs.get(s, ()):
                if p in self.homes and self.tree.root_of(self.homes[p]) != mine:
                    before.setdefault(mine, set()).add(self.tree.root_of(self.homes[p]))
        return topological(owner, before, lambda r: (rank[r], r))

    def path(self, root):
        """The slugs of the narratives homed under root, in reading order."""
        mine = [s for s, h in self.homes.items() if self.tree.root_of(h) == root]
        template = {s: (self.tree.narratives[s] or {}).get('template') for s in mine}
        return topological(mine, self.needs, lambda s: (self._place.get(self.homes[s], 0), template_rank(template[s]), self._title(s), s))

    def place(self, slug):
        """(root, position from 1) of a narrative in its root's path, or None."""
        if slug not in self.homes:
            return None
        root = self.tree.root_of(self.homes[slug])
        return root, self.path(root).index(slug) + 1

    def tag(self, tag):
        """[(slug, role)] of the narratives filed under tag, in reading order."""
        filed = self.tree.narratives_of(tag)
        role = {s: r for r in ('supporting', 'primary') for s in filed[r]}
        return [(s, role[s]) for s in topological(role, self.needs, lambda s: (role[s] != 'primary', self._title(s), s))]
