"""Tests for reviewing the tag tree (issue #204): sllmwiki manifest move-tag and order-tags, the siblings' order
in the tree and the index, and tagtree's review (sllmwiki tag-tree review, and wiki-check's TAG_OTHER_ROOT)."""

import json
import unittest

import helpers
from sllmwiki.lib import manifest, schema, tagtree


class Review(helpers.WikiTestCase):
    def manifest(self, *argv):
        return helpers.run('manifest.py', ['--root', self.root, *argv])

    def tree(self, *argv):
        return helpers.run('tag-tree.py', ['--root', self.root, *argv])

    def add_root(self, name):
        self.assertEqual(self.manifest('add-tag', name, '--description', f'The {name} area').code, 0)

    def test_order_tags(self):
        self.add_root('basics')
        self.add_root('advanced')
        self.assertEqual([t for d, t in tagtree.load(self.root).walk() if d == 0], ['root-topic', 'basics', 'advanced'])
        r = self.manifest('order-tags', 'basics', 'root-topic')
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual([t for d, t in tagtree.load(self.root).walk() if d == 0], ['basics', 'root-topic', 'advanced'])  # the rest follow
        index = self.read('sllmwiki/.SLLMWIKI_INDICES.md')
        self.assertLess(index.index('- [basics]'), index.index('- [root-topic]'))
        self.assertLess(index.index('- [root-topic]'), index.index('- [advanced]'))
        self.assertEqual(self.manifest('order-tags', 'leaf-b', 'leaf-a').code, 0)  # a parent's children
        self.assertEqual(tagtree.load(self.root).children('root-topic'), ['leaf-b', 'leaf-a'])
        self.assertEqual(self.manifest('order-tags', 'leaf-a').code, 0)  # a new order replaces the old
        tags = manifest.load(self.root, 'tags')
        self.assertEqual((tags['leaf-a'].get('order'), tags['leaf-b'].get('order')), (1, None))
        self.assertEqual(tags['leaf-a']['smes'], ['@ann: wrote the alpha doc'])
        for bad in (['leaf-a', 'basics'], ['leaf-a', 'leaf-a'], ['nope']):
            r = self.manifest('order-tags', *bad)
            self.assertEqual(r.code, 1, bad)
        self.assertIn('order-tags orders siblings', self.manifest('order-tags', 'leaf-a', 'basics').err)

    def test_move_tag(self):
        self.add_root('basics')
        self.assertEqual(self.manifest('order-tags', 'leaf-a', 'leaf-b').code, 0)
        r = self.manifest('move-tag', 'leaf-a', '--parent', 'basics')
        self.assertEqual(r.code, 0, r.err)
        self.assertIn('moved tag leaf-a under basics', r.out)
        tags = manifest.load(self.root, 'tags')
        self.assertEqual(tags['leaf-a']['parent'], 'basics')
        self.assertNotIn('order', tags['leaf-a'])  # its place was among its old siblings
        self.assertIn('[basics](basics.md) / leaf-a', self.read('sllmwiki/tags/leaf-a.md'))
        self.assertIn('moved tag basics to the roots', self.manifest('move-tag', 'basics', '--no-parent').out)
        self.assertIn('can\'t move under itself', self.manifest('move-tag', 'basics', '--parent', 'leaf-a').err)
        self.assertIn('can\'t move under itself', self.manifest('move-tag', 'basics', '--parent', 'basics').err)
        self.assertIn('no parent tag nope', self.manifest('move-tag', 'basics', '--parent', 'nope').err)
        self.assertIn('no tag nope', self.manifest('move-tag', 'nope', '--no-parent').err)
        self.assertEqual(self.manifest('move-tag', 'basics').code, 2)

    def test_order_must_be_a_whole_number(self):
        for bad in (0, 'first', True):
            found = schema.validate('tags', {'a': {'description': 'A', 'parent': None, 'order': bad}}, 'tags.yaml')
            self.assertEqual([f['code'] for f in found], ['BAD_TYPE'], bad)

    def test_review(self):
        # leaf-b has no narrative of its own; root-topic is a parent, so it isn't flagged
        r = self.tree('review')
        self.assertEqual(r.code, 1)
        self.assertIn('root-topic (0 primary, 0 supporting): The root topic\n  leaf-a (1 primary, 0 supporting)', r.out)
        self.assertIn('TAG_NO_PRIMARY   leaf-b: no narrative has it as a primary tag', r.out)
        self.assertNotIn('root-topic: no narrative', r.out)
        # two of leaf-b's three narratives are mostly about another root's tag
        self.add_root('infra')
        self.assertEqual(self.manifest('add-tag', 'clusters', '--description', 'GPU clusters', '--parent', 'infra').code, 0)
        helpers.add_narrative(self.root, 'how-do-clusters-work', 'How do clusters work?', primary=('clusters', 'leaf-b'))
        helpers.add_narrative(self.root, 'what-do-clusters-cost', 'What do clusters cost?', primary=('clusters',), supporting=('leaf-b',))
        helpers.add_narrative(self.root, 'how-does-beta-cache', 'How does beta cache?', primary=('leaf-b',))
        found = {f['code']: f['message'] for f in json.loads(self.tree('--json', 'review').out)['findings']}
        self.assertEqual(found['TAG_OTHER_ROOT'], 'leaf-b is under root-topic, but 2 of its 3 narrative(s) have their other primary tags under '
                                                  'infra: move it there if a reader would look for it there (sllmwiki manifest move-tag)')
        self.assertNotIn('TAG_NO_PRIMARY', found)
        r = helpers.run('wiki-check.py', ['--json', '--root', self.root])
        codes = [f['code'] for f in json.loads(r.out)['findings']]
        self.assertIn('TAG_OTHER_ROOT', codes)
        self.assertNotIn('TAG_NO_PRIMARY', codes)  # mid-way through a run, a tag with no narrative yet is normal
        self.assertEqual(self.manifest('move-tag', 'leaf-b', '--parent', 'infra').code, 0)
        self.assertEqual(self.tree('review').code, 0)
        self.assertEqual(json.loads(self.tree('--json', 'review').out)['findings'], [])

    def test_a_home_root_among_the_others_is_home(self):
        self.add_root('infra')
        helpers.add_narrative(self.root, 'how-do-both-work', 'How do both work?', primary=('leaf-b', 'leaf-a', 'infra'))
        found = [(c, t) for c, t, _ in tagtree.load(self.root).review()]
        self.assertNotIn(('TAG_OTHER_ROOT', 'leaf-b'), found)  # one of its other primary tags is at home
        self.assertIn(('TAG_OTHER_ROOT', 'infra'), found)  # infra's one narrative is mostly root-topic's


class Ties(helpers.WikiTestCase):
    """The owner's dry run (#209): roots added before the one they build on, and narratives that predate a tag."""

    def setUp(self):
        super().setUp()
        for tag, parent in (('large-language-models', None), ('llm-architectures', 'large-language-models'), ('machine-learning', None),
                            ('neural-networks', 'machine-learning'), ('ml-workload-math', 'machine-learning'),
                            ('ai-infrastructure', None), ('gpu-clusters', 'ai-infrastructure')):
            manifest.add_tag(self.root, tag, f'The {tag} area', parent)
        add = helpers.add_narrative
        add(self.root, 'how-does-a-neural-network-compute', 'How does a neural network compute?', primary=('neural-networks',))
        add(self.root, 'what-is-a-gpu-cluster', 'What is a GPU cluster?', primary=('gpu-clusters',))
        add(self.root, 'how-does-attention-work', 'How does attention work?', primary=('llm-architectures',),
            built_on=('how-does-a-neural-network-compute',))
        add(self.root, 'how-does-an-llm-generate-text', 'How does an LLM generate text?', primary=('llm-architectures',))
        self.write('sllmwiki/narratives/how-does-an-llm-generate-text.md', self.read('sllmwiki/narratives/how-does-an-llm-generate-text.md').replace(
            'Requests fail, and', 'Each layer is a [Neural Network](how-does-a-neural-network-compute.md#3-background), and'))
        add(self.root, 'what-does-a-training-step-cost', 'What does a training step cost?', primary=('ml-workload-math',),
            built_on=('what-is-a-gpu-cluster',))
        self.write('sllmwiki/narratives/what-is-alpha.md', self.read('sllmwiki/narratives/what-is-alpha.md').replace(
            'Requests fail, and', 'Unlike neural networks, alpha systems are simple. Requests fail, and'))

    def review(self, *argv):
        r = helpers.run('tag-tree.py', ['--root', self.root, '--json', 'review', *argv])
        return r, [(f['code'], f['tag'], f['message']) for f in json.loads(r.out)['findings']] if r.out else []

    def test_a_root_built_on_another(self):
        r, found = self.review()
        self.assertEqual(r.code, 1)
        built = {t: m for c, t, m in found if c == 'TAG_BUILDS_ON_ROOT'}
        self.assertEqual(sorted(built), ['large-language-models', 'ml-workload-math'])  # not llm-architectures: its root says it
        self.assertEqual(built['large-language-models'], 'large-language-models is a root, but 2 of the 2 narrative(s) '
                         'filed under it link to, build on or need narratives under machine-learning: check whether it is a kind of '
                         'machine-learning or built on it, and move it there if so (sllmwiki manifest move-tag)')
        self.assertIn('ml-workload-math is under machine-learning, but 1 of the 1 narrative(s)', built['ml-workload-math'])
        self.assertNotIn('machine-learning', built)  # 1 of its 2 narratives
        self.assertNotIn('TAG_BUILDS_ON_ROOT', [c for c, _, _ in tagtree.load(self.root).review()])  # it needs the ties
        manifest.move_tag(self.root, 'large-language-models', 'machine-learning')
        manifest.move_tag(self.root, 'ml-workload-math', 'ai-infrastructure')
        self.assertEqual([c for c, _, _ in self.review()[1] if c == 'TAG_BUILDS_ON_ROOT'], [])

    def test_retag(self):
        found = [(t, m) for c, t, m in self.review('--new', 'neural-networks')[1] if c == 'TAG_RETAG']
        self.assertEqual([m.split(' may use')[0] for _, m in found], ['how-does-an-llm-generate-text', 'how-does-attention-work', 'what-is-alpha'])
        self.assertEqual(found[0][1], 'how-does-an-llm-generate-text may use neural-networks (links to, builds on or needs '
                         'how-does-a-neural-network-compute; names it 1 time(s)): add it, at least as a supporting tag '
                         '(sllmwiki finish-narrative how-does-an-llm-generate-text --supporting <its supporting tags>,neural-networks)')
        self.assertIn('(names it 1 time(s))', found[2][1])
        r, _ = self.review('--new', 'nope')
        self.assertEqual(r.code, 2)
        self.assertIn('--new names no tag nope', r.err)

    def test_named(self):
        name = tagtree._named('neural-networks')
        self.assertEqual(len(name.findall('A neural network, Neural Networks and a neural-network; not neural-networking.')), 3)
        self.assertTrue(tagtree._named('rag').search('Use RAG here.'))


if __name__ == '__main__':
    unittest.main()
