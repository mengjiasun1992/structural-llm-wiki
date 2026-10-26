"""Tests for lib/search.py, scripts/search.py and scripts/reading-plan.py."""

import json
import unittest

import helpers
from lib import manifest, search


class Ranking(unittest.TestCase):
    def test_bm25(self):
        docs = {'a': 'retry backoff retry', 'b': 'caching keeps data close', 'c': 'retry once'}
        ranked = search.bm25('how does retry work', docs)
        self.assertEqual([k for _, k in ranked], ['a', 'c'])  # stop words ignored; b doesn't match
        self.assertEqual(search.bm25('nothing here', docs), [])
        self.assertEqual(search.bm25('x', {}), [])
        self.assertEqual(search.tokens('The Retry-Budget, 2026!'), ['retry', 'budget', '2026'])


class Library(helpers.WikiTestCase):
    def test_finding(self):
        self.assertEqual(search.find_tags(self.root, 'beta caching')[0]['tag'], 'leaf-b')
        n = search.find_narratives(self.root, 'alpha')[0]
        self.assertEqual((n['slug'], n['question'], n['version'], n['tags']['primary']), ('what-is-alpha', 'What is alpha?', '1.0', ['leaf-a']))
        found = [s['slug'] for s in search.find_sources(self.root, 'retry caching gamma code')]
        self.assertEqual((found[0], set(found)), ('gamma-link', {'gamma-link', 'beta-doc', 'alpha-doc'}))  # two matching words rank first
        self.assertEqual([s['slug'] for s in search.find_sources(self.root, 'retry caching gamma code', tags=['leaf-b'])], ['beta-doc'])

    def test_narratives_skip_a_missing_file(self):
        manifest.save(self.root, 'narratives', 'gone', {'template': 't', 'tags': {'primary': ['leaf-a'], 'supporting': []}, 'read': {}})
        self.assertNotIn('gone', search.narratives(self.root))

    def test_resolve(self):
        for link in ('../sources/alpha-doc.md#details', 'sllmwiki/sources/alpha-doc.md#details', 'alpha-doc#details'):
            self.assertEqual(search.resolve(self.root, link), ('sllmwiki/sources/alpha-doc.md', 'details'), link)
        self.assertEqual(search.resolve(self.root, 'what-is-alpha'), ('sllmwiki/narratives/what-is-alpha.md', ''))
        self.assertEqual(search.resolve(self.root, '../../outside.md')[0], None)

    def test_sources_are_read_without_their_footer(self):
        text = search.read_file(self.root, 'sllmwiki/sources/alpha-doc.md')
        self.assertEqual(text, helpers.ALPHA)
        self.assertNotIn('Original source', [h['title'] for h in search.outline(text)])
        self.assertEqual(search.section(text, 'details'), '## Details\n\nEach retry waits twice as long as the last.\n')
        self.assertIsNone(search.section(text, 'nope'))


class Command(helpers.WikiTestCase):
    def s(self, *argv):
        return helpers.run('search.py', [*argv, '--root', self.root])

    def test_context(self):
        r = self.s('context', 'alpha retry')
        self.assertTrue(r.out.startswith('Tags: leaf-a (First leaf, about alpha systems)'))
        self.assertIn('## What is alpha?  (sllmwiki/narratives/what-is-alpha.md, version 1.0', r.out)
        self.assertEqual(json.loads(self.s('context', 'alpha', '--json').out)['narratives'][0]['slug'], 'what-is-alpha')
        self.assertIn('Tags: none match', self.s('context', 'zebra').out)
        self.assertIn('No narrative matches.', self.s('context', 'zebra').out)

    def test_narratives_and_sources(self):
        self.assertIn('## What is alpha?', self.s('narratives', 'alpha').out)
        self.assertEqual(self.s('narratives', 'zebra').out, 'No narrative matches.\n')
        self.assertEqual(json.loads(self.s('narratives', 'alpha', '--json').out)[0]['slug'], 'what-is-alpha')
        manifest.put_source(self.root, 'alpha-doc', abstract_draft=True)
        out = self.s('sources', 'alpha gamma').out
        self.assertIn('- alpha-doc [text] sllmwiki/sources/alpha-doc.md (draft abstract):', out)
        self.assertIn('- gamma-link [link] https://example.com/gamma:', out)
        self.assertEqual(json.loads(self.s('sources', 'beta', '--json').out)[0]['slug'], 'beta-doc')
        self.assertEqual(self.s('sources', 'zebra').out, 'No source matches.\n')

    def test_outline_and_section(self):
        out = self.s('outline', 'what-is-alpha').out
        self.assertIn('  5. How does it work?  #5-how-does-it-work  (', out)
        self.assertEqual(json.loads(self.s('outline', 'alpha-doc', '--json').out)['headings'][1]['anchor'], 'details')
        r = self.s('section', '../sources/alpha-doc.md#details')
        self.assertEqual(r.out, '<!-- sllmwiki/sources/alpha-doc.md#details -->\n## Details\n\nEach retry waits twice as long as the last.\n')
        self.assertEqual(json.loads(self.s('section', 'alpha-doc#details', '--json').out)['anchor'], 'details')

    def test_failures(self):
        self.assertIn('no such file: nope.md', self.s('section', 'nope.md#x').err)
        self.assertIn('has no section #nope; see search.py outline', self.s('section', 'alpha-doc#nope').err)
        self.assertIn('section needs a #anchor', self.s('section', 'alpha-doc').err)


class ReadingPlan(helpers.WikiTestCase):
    def plan(self, *argv):
        return helpers.run('reading-plan.py', [*argv, '--root', self.root])

    def grades(self, data):
        return helpers.write(self.tmp, 'grades.json', json.dumps(data))

    def test_undated_sources_count_as_oldest(self):
        from lib import readingplan
        found = {'narratives': [], 'sources': [{'slug': s, 'kind': 'text', 'date': d} for s, d in (('new', '2026-01-01'), ('nodate', ''), ('old', '2001-01-01'))]}
        rows, problems = readingplan.order(found, {s: {'relevance': 'high', 'authority': 'A'} for s in ('new', 'nodate', 'old')})
        self.assertEqual(([r['slug'] for r in rows], problems), (['nodate', 'old', 'new'], []))  # the newest read last
        self.assertTrue(rows[0]['why'].endswith('undated'))

    def test_list(self):
        out = self.plan('list', '--primary', 'leaf-a', '--supporting', 'leaf-b').out
        self.assertIn('narrative what-is-alpha: What is alpha?', out)
        self.assertIn('source alpha-doc [text, 215 bytes, 2026-09-01]: Alpha systems', out)
        self.assertIn('source gamma-link [link, no saved copy, undated]', out)
        self.assertIn('noted, not read: root-topic', out)
        found = json.loads(self.plan('list', '--primary', 'leaf-b', '--json').out)
        self.assertEqual(([s['slug'] for s in found['sources']], found['noted_not_read']), (['beta-doc'], ['leaf-a', 'root-topic']))

    def test_order(self):
        g = self.grades({'alpha-doc': {'relevance': 'high', 'authority': 'A'}, 'beta-doc': {'relevance': 'high', 'authority': 'C'}})
        rows = json.loads(self.plan('order', '--primary', 'leaf-a', '--supporting', 'leaf-b', '--grades', g, '--json').out)['plan']
        self.assertEqual([(r['step'], r['read'], r['slug']) for r in rows],
                         [(1, 'in full', 'what-is-alpha'), (2, 'in full', 'beta-doc'), (3, 'in full', 'alpha-doc'), (4, 'not read', 'gamma-link')])
        g = self.grades({'alpha-doc': {'relevance': 'medium', 'authority': 'B'}, 'beta-doc': {'relevance': 'low', 'authority': 'A'}})
        out = self.plan('order', '--primary', 'leaf-a', '--supporting', 'leaf-b', '--grades', g).out
        self.assertIn('| 2 | in full | alpha-doc | medium relevance, authority B, 2026-09-01 |', out)
        self.assertIn('| 3 | abstract only | beta-doc | low relevance |', out)
        self.assertIn('Noted, not read: root-topic.', out)

    def test_graded_narratives(self):
        from lib import readingplan
        found = {'narratives': [{'slug': n, 'created': c} for n, c in (('built-on', '1'), ('side', '2'), ('far', '3'), ('plain', '4'))],
                 'sources': [{'slug': 'doc', 'kind': 'text', 'date': ''}]}
        grades = {'doc': {'relevance': 'high', 'authority': 'A'}, 'built-on': {'relevance': 'high'}, 'side': {'relevance': 'medium'},
                  'far': {'relevance': 'low'}}
        rows, problems = readingplan.order(found, grades)
        self.assertEqual(problems, [])
        self.assertEqual([(r['slug'], r['read'], r['why']) for r in rows],
                         [('plain', 'in full', 'existing narrative, background'), ('side', 'in full', 'existing narrative, medium relevance'),
                          ('doc', 'in full', 'high relevance, authority A, undated'),
                          ('built-on', 'in full', 'existing narrative, high relevance: built on'),
                          ('far', 'abstract only', 'existing narrative, low relevance')])
        self.assertIn('plain: an existing narrative needs', readingplan.order(found, {**grades, 'plain': {'relevance': 'very'}})[1][0])
        path = helpers.write(self.tmp, 'g.json', '{}')
        helpers.write(self.tmp, 'g.json.plan.json', json.dumps(rows))
        self.assertEqual(readingplan.narratives_read(path), {'plain', 'side', 'built-on', 'far'})

    def test_order_by_date_within_authority(self):
        manifest.put_source(self.root, 'beta-doc', tags=['leaf-a'], published='2020-01-01')
        g = self.grades({'alpha-doc': {'relevance': 'high', 'authority': 'A'}, 'beta-doc': {'relevance': 'high', 'authority': 'A'}})
        rows = json.loads(self.plan('order', '--primary', 'leaf-a', '--grades', g, '--json').out)['plan']
        self.assertEqual([r['slug'] for r in rows if r['read'] == 'in full'][1:], ['beta-doc', 'alpha-doc'])  # older first, newest last

    def test_refusals(self):
        self.assertIn('no such tag(s): nope', self.plan('list', '--primary', 'nope').err)
        self.assertEqual(self.plan('order', '--primary', 'leaf-a').code, 2)
        self.assertIn('can\'t read the grades', self.plan('order', '--primary', 'leaf-a', '--grades', '/nope.json').err)
        g = self.grades({'alpha-doc': {'relevance': 'very', 'authority': 'A'}})
        r = self.plan('order', '--primary', 'leaf-a', '--grades', g)
        self.assertEqual(r.code, 1)
        self.assertIn('alpha-doc: needs', r.err)
        self.assertIn('the grades must be a mapping', self.plan('order', '--primary', 'leaf-a', '--grades', self.grades(['x'])).err)


if __name__ == '__main__':
    unittest.main()
