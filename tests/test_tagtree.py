"""Tests for lib/tagtree.py and scripts/tag-tree.py."""

import json
import unittest

import helpers
from lib import tagtree
from lib.tagtree import Tree

TAGS = {
    'root': {'description': 'Root', 'parent': None},
    'a': {'description': 'A', 'parent': 'root'},
    'b': {'description': 'B', 'parent': 'root'},
    'a1': {'description': 'A1', 'parent': 'a'},
    'other-root': {'description': 'Other', 'parent': None},
}


class TreeShape(unittest.TestCase):
    def setUp(self):
        self.tree = Tree(TAGS, {'s': {'tags': ['a1', 'b']}}, {'n': {'tags': {'primary': ['a1'], 'supporting': ['b']}}})

    def test_relations(self):
        t = self.tree
        self.assertEqual((t.parent('a1'), t.children('root'), t.roots()), ('a', ['a', 'b'], ['root', 'other-root']))
        self.assertEqual((t.ancestors('a1'), t.ancestors('root')), (['a', 'root'], []))
        self.assertEqual((t.adjacent('a'), t.adjacent('root')), (['b'], ['other-root']))

    def test_what_is_filed_under_a_tag(self):
        t = self.tree
        self.assertEqual((t.sources_of('b'), t.sources_of('a')), (['s'], []))  # not rolled up to parents
        self.assertEqual(t.narratives_of('b'), {'primary': [], 'supporting': ['n']})

    def test_walk(self):
        self.assertEqual(self.tree.walk(), [(0, 'root'), (1, 'a'), (2, 'a1'), (1, 'b'), (0, 'other-root')])

    def test_problems(self):
        self.assertEqual(self.tree.problems(), [])
        tags = dict(TAGS, x={'description': 'X', 'parent': 'y'}, y={'description': 'Y', 'parent': 'x'},
                    z={'description': 'Z', 'parent': 'z'}, w={'description': 'W', 'parent': 'gone'})
        t = Tree(tags, {'s': {'tags': ['nope']}}, {'n': {'tags': {'primary': ['nope2'], 'supporting': []}}})
        self.assertEqual([(c, k) for c, k, _ in t.problems()],
                         [('TAG_CYCLE', 'x'), ('TAG_CYCLE', 'y'), ('TAG_CYCLE', 'z'), ('UNKNOWN_PARENT', 'w'), ('UNKNOWN_TAG', 's'), ('UNKNOWN_TAG', 'n')])
        self.assertEqual({tag for _, tag in t.walk()}, set(tags))  # every tag listed, cycles too


class Command(helpers.WikiTestCase):
    def tree(self, *argv):
        return helpers.run('tag-tree.py', ['--root', self.root, *argv])

    def test_tree(self):
        self.assertEqual(self.tree('tree').out, ('root-topic (0 sources, 0 narratives): The root topic\n'
                                                 '  leaf-a (2 sources, 1 narratives): First leaf, about alpha systems\n'
                                                 '  leaf-b (1 sources, 0 narratives): Second leaf, about beta caching\n'))
        self.assertEqual(self.tree('tree', '--brief').out.split('\n')[1], '  leaf-a (2 sources, 1 narratives)')
        rows = json.loads(self.tree('--json', 'tree').out)
        self.assertEqual(rows[1], {'tag': 'leaf-a', 'depth': 1, 'description': 'First leaf, about alpha systems', 'sources': 2, 'narratives': 1})

    def test_show(self):
        out = self.tree('show', 'leaf-a').out
        self.assertIn('  ancestors: root-topic\n  children: none\n  adjacent: leaf-b\n  sources: alpha-doc, gamma-link\n', out)
        self.assertIn('  narratives (primary): what-is-alpha\n  narratives (supporting): none\n  sme: @ann: wrote the alpha doc\n', out)
        d = json.loads(self.tree('--json', 'show', 'leaf-b').out)
        self.assertEqual((d['sources'], d['smes']), (['beta-doc'], []))
        r = self.tree('show', 'nope')
        self.assertEqual((r.code, r.err), (1, 'tag-tree.py: no tag nope\n'))

    def test_load(self):
        self.assertIn('leaf-a', tagtree.load(self.root).tags)


if __name__ == '__main__':
    unittest.main()
