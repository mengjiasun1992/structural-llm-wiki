"""Tests for the reading order (issue #206): a narrative's home tag, roots in dependency order, each root's
reading path in the index, tag pages in reading order, and the book following prerequisites."""

import unittest

import helpers
from sllmwiki.lib import book, layout, manifest, readingorder, tagtree, wikiindex

NN, LEARN, GPU, STEP, NAMES = ('how-does-a-neural-network-compute', 'how-does-a-network-learn', 'what-is-a-gpu-cluster',
                               'what-happens-in-a-training-step', 'what-are-the-gpu-names')


class Order(helpers.WikiTestCase):
    def setUp(self):
        super().setUp()
        # ai-infrastructure was made first, though it builds on machine-learning (the owner's wiki, #204 and #206)
        for tag, parent in (('ai-infrastructure', None), ('gpu-clusters', 'ai-infrastructure'), ('machine-learning', None),
                            ('neural-networks', 'machine-learning'), ('training', 'neural-networks')):
            manifest.add_tag(self.root, tag, f'The {tag} area', parent)
        add = helpers.add_narrative
        add(self.root, NN, 'How does a neural network compute?', primary=('neural-networks',))
        add(self.root, LEARN, 'How does a network learn?', primary=('machine-learning', 'training'))  # home: training, the deeper
        add(self.root, GPU, 'What is a GPU cluster?', primary=('gpu-clusters', 'leaf-a'), supporting=('neural-networks',))
        add(self.root, NAMES, 'What are the GPU names?', template='concept_brief_overview', primary=('gpu-clusters',), built_on=(GPU,))
        add(self.root, STEP, 'What happens in a training step?', primary=('gpu-clusters',))
        self.need(LEARN, NN)
        self.need(STEP, GPU, LEARN)
        self.need(GPU, NAMES)  # a reader needs the names first, though the names narrative was built on the cluster one

    def need(self, slug, *firsts):
        e = manifest.load(self.root, 'narratives')[slug]
        manifest.put_narrative(self.root, slug, e['template'], e['tags']['primary'], e['tags']['supporting'], ['alpha-doc'],
                               built_on=list(e.get('built_on') or {}), prerequisites=list(firsts))

    def order(self):
        tree = tagtree.load(self.root)
        return readingorder.Order(tree, wikiindex.questions(self.root, tree))

    def test_home(self):
        tree = tagtree.load(self.root)
        self.assertEqual(readingorder.home(tree, ['machine-learning', 'training']), 'training')  # an ancestor drops out
        self.assertEqual(readingorder.home(tree, ['training', 'machine-learning']), 'training')
        self.assertEqual(readingorder.home(tree, ['leaf-b', 'leaf-a']), 'leaf-b')  # siblings: the first
        self.assertEqual(readingorder.home(tree, ['gpu-clusters', 'training']), 'gpu-clusters')  # unrelated: the first
        self.assertIsNone(readingorder.home(tree, ['nope']))

    def test_roots_and_paths(self):
        o = self.order()
        self.assertEqual(o.roots(), ['root-topic', 'machine-learning', 'ai-infrastructure'])  # after the root it needs
        self.assertEqual(o.path('machine-learning'), [NN, LEARN])
        self.assertEqual(o.path('ai-infrastructure'), [NAMES, GPU, STEP])
        self.assertEqual(o.place(STEP), ('ai-infrastructure', 3))
        self.assertIsNone(o.place('nope'))
        self.assertEqual(o.tag('neural-networks'), [(NN, 'primary'), (GPU, 'supporting')])

    def test_the_index(self):
        tree = tagtree.load(self.root)
        text = wikiindex.pages(self.root)[layout.INDEX]
        self.assertLess(text.index('- [machine-learning]'), text.index('- [ai-infrastructure]'))
        self.assertIn('## Reading paths\n\nEach topic\'s narratives in the order to read them: "needs" names the ones to read first.\n\n'
                      '### root-topic\n\n1. [What is alpha?](narratives/what-is-alpha.md) (1 min)\n\n'
                      '### machine-learning\n\n'
                      '1. [How does a neural network compute?](narratives/how-does-a-neural-network-compute.md) (1 min)\n'
                      '2. [How does a network learn?](narratives/how-does-a-network-learn.md) (1 min), needs 1\n\n'
                      '### ai-infrastructure\n\n'
                      '1. [What are the GPU names?](narratives/what-are-the-gpu-names.md) (1 min)\n'
                      '2. [What is a GPU cluster?](narratives/what-is-a-gpu-cluster.md) (1 min), needs 1\n'
                      '3. [What happens in a training step?](narratives/what-happens-in-a-training-step.md) (1 min), '
                      'needs 2 and [machine-learning 2](#machine-learning)\n', text)
        self.assertNotIn('## Reading paths', wikiindex.render(tagtree.Tree(tree.tags, {}, {}), {}))

    def test_a_tag_page(self):
        text = wikiindex.pages(self.root)['sllmwiki/tags/gpu-clusters.md']
        self.assertIn('## Narratives\n\nIn the order to read them.\n\n'
                      '1. [What are the GPU names?](../narratives/what-are-the-gpu-names.md) · 1 min\n'
                      '2. [What is a GPU cluster?](../narratives/what-is-a-gpu-cluster.md) · 1 min\n'
                      '3. [What happens in a training step?](../narratives/what-happens-in-a-training-step.md) · 1 min, '
                      'needs [How does a network learn?](../narratives/how-does-a-network-learn.md)\n', text)

    def test_the_book(self):
        b = book.model(self.root)
        self.assertEqual([p.tag for p in b.parts], ['root-topic', 'machine-learning', 'ai-infrastructure'])
        self.assertEqual(b.chapters[LEARN].tag, 'training')
        self.assertEqual(b.order()[-3:], [NAMES, GPU, STEP])  # the prerequisite wins over the reversed built_on
        self.assertEqual(b.problems, [])

    def test_a_cycle_keeps_the_rest_in_order(self):
        self.assertEqual(readingorder.topological(['c', 'b', 'a'], {'a': ['b'], 'b': ['a']}, lambda s: s), ['c', 'a', 'b'])
        self.assertEqual(readingorder.topological(['b', 'a'], {'b': ['a', 'zzz']}, lambda s: s), ['a', 'b'])


if __name__ == '__main__':
    unittest.main()
