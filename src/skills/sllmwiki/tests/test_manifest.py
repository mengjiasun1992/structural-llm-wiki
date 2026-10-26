"""Tests for lib/manifest.py and scripts/manifest.py."""

import os
import unittest

import helpers
from lib import manifest, wikiyaml
from lib.manifest import ManifestError


def run(root, *argv):
    return helpers.run('manifest.py', ['--root', root, *argv])


class Library(helpers.WikiTestCase):
    def test_load_and_a_missing_file(self):
        self.assertIn('alpha-doc', manifest.load(self.root, 'sources'))
        self.assertEqual(manifest.load(self.tmp + '/nowhere', 'tags'), {})

    def test_save_orders_fields_and_refuses_bad_entries(self):
        manifest.save(self.root, 'tags', 'new-tag', {'parent': None, 'description': 'New'})
        self.assertIn('new-tag:\n  description: New\n  parent: null\n', self.read('sllmwiki/tags/tags.yaml'))
        with self.assertRaises(ManifestError) as e:
            manifest.save(self.root, 'tags', 'bad', {'description': 'x'})
        self.assertIn('parent is required', str(e.exception))

    def test_a_new_file_gets_its_header(self):
        import os
        os.remove(f'{self.root}/sllmwiki/narratives/manifest.yaml')
        manifest.put_narrative(self.root, 'what-is-alpha', 'technical_brief_overview', ['leaf-a'], [], ['alpha-doc', 'gamma-link'])
        text = self.read('sllmwiki/narratives/manifest.yaml')
        self.assertTrue(text.startswith('# Narratives, keyed by question slug'))
        entry = wikiyaml.parse(text)['what-is-alpha']
        self.assertEqual(entry['read'], {'alpha-doc': helpers.md5(helpers.ALPHA.encode())})  # the link isn't pinned

    def test_put_source(self):
        manifest.put_source(self.root, 'delta', kind='link', url='https://e.com/d', ingested='2026-10-21', license='unknown',
                            tags=['leaf-b'], abstract='Delta.')
        manifest.put_source(self.root, 'alpha-doc', tags=['leaf-a', 'leaf-b'])
        sources = manifest.load(self.root, 'sources')
        self.assertEqual(sources['delta']['kind'], 'link')
        self.assertEqual((sources['alpha-doc']['tags'], sources['alpha-doc']['file']), (['leaf-a', 'leaf-b'], 'sources/alpha-doc.md'))
        with self.assertRaises(ManifestError) as e:
            manifest.put_source(self.root, 'new-copy', kind=None, url='https://e.com')
        self.assertIn('save a copy with fetch-source.py', str(e.exception))
        with self.assertRaises(ManifestError) as e:
            manifest.put_source(self.root, 'alpha-doc', kind='link')
        self.assertIn('fetch-source.py --refresh', str(e.exception))
        manifest.put_source(self.root, 'gamma-link', url='https://e.com/g2')  # a link's fields can all change

    def test_drop_copy_turns_a_saved_copy_into_a_link_in_place(self):
        order = list(manifest.load(self.root, 'sources'))
        path = os.path.join(self.root, 'sllmwiki', 'sources', 'alpha-doc.md')
        self.assertTrue(os.path.exists(path))
        r = run(self.root, 'put-source', 'alpha-doc', '--kind', 'link', '--drop-copy', '--license', 'proprietary')
        self.assertEqual(r.out, 'made a link of source alpha-doc\n')
        sources = manifest.load(self.root, 'sources')
        self.assertEqual(list(sources), order)  # its place kept
        self.assertEqual((sources['alpha-doc']['kind'], sources['alpha-doc']['license']), ('link', 'proprietary'))
        self.assertNotIn('file', sources['alpha-doc'])
        self.assertIn('abstract', sources['alpha-doc'])
        self.assertFalse(os.path.exists(path))
        for argv, says in ((['gamma-link', '--kind', 'link', '--drop-copy'], "isn't a saved copy"),
                           (['beta-doc', '--drop-copy'], 'needs --kind link')):
            r = run(self.root, 'put-source', *argv)
            self.assertEqual(r.code, 1)
            self.assertIn(says, r.err)

    def test_set_abstract_clears_the_draft(self):
        manifest.put_source(self.root, 'alpha-doc', abstract_draft=True)
        manifest.set_abstract(self.root, 'alpha-doc', 'A real abstract.')
        entry = manifest.load(self.root, 'sources')['alpha-doc']
        self.assertEqual((entry['abstract'], 'abstract_draft' in entry), ('A real abstract.', False))
        with self.assertRaises(ManifestError):
            manifest.set_abstract(self.root, 'nope', 'x')

    def test_put_narrative_keeps_grades_and_adds_models(self):
        grades = {'alpha-doc': {'relevance': 'high', 'authority': 'A'}}
        manifest.put_narrative(self.root, 'what-is-alpha', 'technical_brief_overview', ['leaf-a'], [], ['alpha-doc'], grades, ('1.0', 'claude-opus-5-5'))
        manifest.put_narrative(self.root, 'what-is-alpha', 'technical_brief_overview', ['leaf-a'], [], ['alpha-doc'], None, ('1.1', 'claude-fable-5-1'))
        entry = manifest.load(self.root, 'narratives')['what-is-alpha']
        self.assertEqual((entry['grades'], entry['models']), (grades, {'1.0': 'claude-opus-5-5', '1.1': 'claude-fable-5-1'}))

    def test_put_narrative_checks_tags_file_and_sources(self):
        with self.assertRaises(ManifestError) as e:
            manifest.put_narrative(self.root, 'what-is-alpha', 't', ['nope'], [], [])
        self.assertIn('no such tag(s): nope', str(e.exception))
        with self.assertRaises(ManifestError) as e:
            manifest.put_narrative(self.root, 'not-written', 't', ['leaf-a'], [], [])
        self.assertIn('no narrative', str(e.exception))
        with self.assertRaises(ManifestError) as e:
            manifest.put_narrative(self.root, 'what-is-alpha', 't', ['leaf-a'], [], ['nope'])
        self.assertIn('no source nope', str(e.exception))

    def test_a_root_tag(self):
        manifest.add_tag(self.root, 'second-root', 'Another root')
        self.assertEqual(manifest.load(self.root, 'tags')['second-root'], {'description': 'Another root', 'parent': None})

    def test_tags(self):
        manifest.add_tag(self.root, 'leaf-c', 'Third', 'root-topic')
        manifest.put_tag(self.root, 'leaf-c', smes=['@bo: wrote it'])
        manifest.put_tag(self.root, 'leaf-c', description='Third leaf')
        self.assertEqual(manifest.load(self.root, 'tags')['leaf-c'], {'description': 'Third leaf', 'parent': 'root-topic', 'smes': ['@bo: wrote it']})
        manifest.put_tag(self.root, 'leaf-c', smes=[])
        self.assertNotIn('smes', manifest.load(self.root, 'tags')['leaf-c'])
        for call, msg in ((lambda: manifest.add_tag(self.root, 'leaf-a', 'x'), 'exists'),
                          (lambda: manifest.add_tag(self.root, 'x', 'x', 'nope'), 'no parent tag nope'),
                          (lambda: manifest.put_tag(self.root, 'nope'), 'no tag nope')):
            with self.assertRaises(ManifestError) as e:
                call()
            self.assertIn(msg, str(e.exception))

    def test_remove(self):
        manifest.remove(self.root, 'sources', 'gamma-link')
        self.assertNotIn('gamma-link', manifest.load(self.root, 'sources'))
        with self.assertRaises(ManifestError):
            manifest.remove(self.root, 'sources', 'gamma-link')


class Command(helpers.WikiTestCase):
    def test_commands(self):
        self.assertEqual(run(self.root, 'add-tag', 'leaf-c', '--description', 'Third', '--parent', 'root-topic').out, 'added tag leaf-c\n')
        self.assertEqual(run(self.root, 'put-tag', 'leaf-c', '--smes', '@a: x', '@b: y').code, 0)
        self.assertEqual(run(self.root, 'put-tag', 'leaf-c', '--no-smes').code, 0)
        r = run(self.root, 'put-source', 'delta', '--kind', 'link', '--url', 'https://e.com/d', '--license', 'unknown', '--tags', 'leaf-c, leaf-b',
                '--abstract', 'Delta.')
        self.assertEqual(r.out, 'recorded source delta\n')
        self.assertEqual(manifest.load(self.root, 'sources')['delta']['tags'], ['leaf-c', 'leaf-b'])
        self.assertEqual(run(self.root, 'put-source', 'delta', '--abstract', 'Delta again.').out, 'updated source delta\n')
        self.assertEqual(run(self.root, 'set-abstract', 'delta', '--abstract', 'Real.').code, 0)
        self.assertEqual(run(self.root, 'put-narrative', 'what-is-alpha', '--template', 'technical_brief_overview', '--primary', 'leaf-a',
                             '--read', 'alpha-doc').code, 0)
        self.assertEqual(run(self.root, 'remove', 'sources', 'delta').out, 'removed delta from sources\n')
        self.assertEqual(helpers.run('wiki-check.py', ['--root', self.root, '--visibility', 'private']).code, 0)  # pages kept current

    def test_refusals(self):
        r = run(self.root, 'add-tag', 'leaf-a', '--description', 'x')
        self.assertEqual((r.code, r.err), (1, 'manifest.py: tag leaf-a exists; change it with put-tag\n'))
        self.assertEqual(run(self.root, 'put-tag').code, 2)
        self.write('Config.toml', '[structural-llm-wiki-settings]\nmarkers = 1\n')
        r = run(self.root, 'add-tag', 'x', '--description', 'x')
        self.assertEqual(r.code, 1)
        self.assertIn('Config.toml is invalid', r.err)

    def test_not_a_wiki(self):
        r = run(self.tmp + '/sllmwiki', 'add-tag', 'x', '--description', 'x')
        self.assertEqual(r.code, 1)
        self.assertIn('is not a wiki', r.err)


if __name__ == '__main__':
    unittest.main()
