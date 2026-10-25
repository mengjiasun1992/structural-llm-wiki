"""Tests for scripts/wiki-check.py and the generated pages (lib/wikiindex.py, lib/tagpages.py)."""

import json
import os
import unittest
from unittest import mock

import helpers
from lib import compat, manifest, policy, tagpages, wikiindex


class Pages(helpers.WikiTestCase):
    def test_the_index(self):
        text = self.read('SLLMWIKI_INDICES.md')
        self.assertIn('    t0 --> t1\n', text)
        self.assertIn('    click t1 "sllmwiki/tags/leaf-a.md"\n', text)
        self.assertIn('  - [leaf-a](sllmwiki/tags/leaf-a.md): First leaf, about alpha systems (1 narrative)\n', text)
        self.assertEqual(compat.check(text), [])

    def test_a_tag_page(self):
        text = self.read('sllmwiki/tags/leaf-a.md')
        for want in ('# leaf-a\n', '**Path:** [root-topic](root-topic.md) / leaf-a', '- [What is alpha?](../narratives/what-is-alpha.md) · 1 min\n',
                     '- [alpha-doc](../sources/alpha-doc.md): Alpha systems and how they retry failed requests.\n',
                     '- [gamma-link](<https://example.com/gamma>): A pointer', '## Who to ask\n\n- @ann: wrote the alpha doc\n'):
            self.assertIn(want, text)
        root_page = self.read('sllmwiki/tags/root-topic.md')
        self.assertIn('## Subtopics\n\n- [leaf-a](leaf-a.md): First leaf', root_page)
        for rel in ('sllmwiki/tags/leaf-a.md', 'sllmwiki/tags/root-topic.md'):
            page = self.read(rel)
            self.assertEqual(compat.check(page) + compat.check_links(page, os.path.join(self.root, 'sllmwiki/tags'), self.root), [], rel)

    def test_supporting_drafts_and_long_abstracts(self):
        manifest.put_narrative(self.root, 'what-is-alpha', 'technical_brief_overview', ['leaf-a'], ['leaf-b'], ['alpha-doc'])
        manifest.put_source(self.root, 'beta-doc', abstract=' '.join(['long'] * 40), abstract_draft=True)
        wikiindex.sync(self.root, write=True)
        text = self.read('sllmwiki/tags/leaf-b.md')
        self.assertIn('- [What is alpha?](../narratives/what-is-alpha.md) · 1 min (supporting)', text)
        self.assertIn('(abstract not written yet): ' + ' '.join(['long'] * 30) + '…', text)

    def test_an_empty_wiki(self):
        from lib.tagtree import Tree
        self.assertIn('No topics yet.', wikiindex.render(Tree({}, {}, {}), {}))


class Check(helpers.WikiTestCase):
    def wc(self, *argv):
        return helpers.run('wiki-check.py', ['--root', self.root, '--visibility', 'private', *argv])

    def codes(self, *argv):
        return [f['code'] for f in json.loads(self.wc('--json', *argv).out)['findings']]

    def test_a_consistent_wiki(self):
        r = self.wc()
        self.assertEqual((r.code, r.out), (0, 'wiki-check: 0 error(s), 0 warning(s)\n'))

    def test_every_page_renders_alike(self):
        self.write('sllmwiki/notes/meeting.md', '# Notes\n\nSee [[what-is-alpha]] and ==this==, and [gone](missing.md).\n')
        self.write('sllmwiki/sources/raw-note.md', 'A source keeps its [[wikilink]].\n')  # verbatim, never checked here
        self.write('sllmwiki/.obsidian/x.md', '[[ignored]]\n')
        self.write('sllmwiki/narratives/what-is-alpha.md', helpers.narrative_text().replace('Requests fail', 'Costs $5. Requests fail'))
        out = self.wc('--json').out
        found = {(f['code'], f['file']) for f in json.loads(out)['findings']}
        self.assertTrue({('WIKILINK', 'sllmwiki/notes/meeting.md:3'), ('HIGHLIGHT', 'sllmwiki/notes/meeting.md:3'),
                         ('LINK_PATH', 'sllmwiki/notes/meeting.md:3')} <= found, found)
        self.assertIn(('DOLLAR_SIGN', 'sllmwiki/narratives/what-is-alpha.md:15'), {(c, f) for c, f in found if c == 'DOLLAR_SIGN'})
        self.assertFalse([f for f in found if ('sources/raw-note' in f[1] or '.obsidian' in f[1]) and f[0] != 'SOURCE_UNRECORDED'])

    def test_config_and_yaml(self):
        self.write('Config.toml', '[structural-llm-wiki-settings]\nmarkers = 1\n')
        self.assertIn('CONFIG_INVALID', self.codes())
        self.write('sllmwiki/sources/manifest.yaml', 'a: [unclosed\n')
        r = self.wc()
        self.assertEqual(r.code, 1)
        self.assertIn('YAML_INVALID', r.out)

    def test_the_wikis_own_templates(self):
        self.write('templates/postmortem/template.md', '---\ndescription: x\n---\n\n## Timeline\n\n<what happened>\n')
        self.write('Config.toml', '[structural-llm-wiki-templates.runbook]\nmax_words = 900\n')
        found = {(f['code'], f['file']): f['message'] for f in json.loads(self.wc('--json').out)['findings']}
        self.assertIn('header needs exactly', found[('TEMPLATE_INVALID', 'templates/postmortem')])
        self.assertIn('no template runbook', found[('TEMPLATE_INVALID', 'Config.toml')])
        self.assertEqual(self.wc().code, 1)

    def test_schema_and_tree(self):
        text = self.read('sllmwiki/tags/tags.yaml')
        self.write('sllmwiki/tags/tags.yaml', text.replace('parent: root-topic\n  smes', 'parent: gone\n  smes').replace('description: Second leaf', 'descripton: Second leaf'))
        codes = self.codes()
        self.assertIn('UNKNOWN_PARENT', codes)
        self.assertIn('UNKNOWN_FIELD', codes)

    def test_files_and_entries(self):
        self.write('sllmwiki/sources/stray.md', '# Stray\n')
        self.write('sllmwiki/narratives/stray-question.md', '# Stray?\n')
        os.remove(os.path.join(self.root, 'sllmwiki/sources/beta-doc.md'))
        manifest.save(self.root, 'narratives', 'gone', {'template': 't', 'tags': {'primary': ['leaf-a'], 'supporting': []}, 'read': {'gamma-link': 'f' * 32}})
        manifest.put_source(self.root, 'gamma-link', url='https://example.com/gamma')
        codes = self.codes()
        for code in ('SOURCE_UNRECORDED', 'SOURCE_MISSING', 'NARRATIVE_UNRECORDED', 'NARRATIVE_MISSING', 'PIN_UNKNOWN'):
            self.assertIn(code, codes)

    def test_file_name_and_attribution(self):
        text = self.read('sllmwiki/sources/manifest.yaml').replace('file: sources/beta-doc.md', 'file: sources/beta.md')
        self.write('sllmwiki/sources/manifest.yaml', text)
        os.rename(os.path.join(self.root, 'sllmwiki/sources/beta-doc.md'), os.path.join(self.root, 'sllmwiki/sources/beta.md'))
        self.write('sllmwiki/sources/alpha-doc.md', helpers.ALPHA)  # no footer
        codes = self.codes()
        self.assertIn('FILE_NAME', codes)
        self.assertIn('SOURCE_ATTRIBUTION', codes)

    def test_pins_upstream_and_drafts(self):
        self.write('sllmwiki/sources/alpha-doc.md', helpers.ALPHA + 'A new line.\n' + helpers.FOOTER.format(url='https://example.com/alpha', license='CC-BY-4.0'))
        manifest.put_source(self.root, 'beta-doc', upstream_changed='2026-10-20', abstract_draft=True)
        wikiindex.sync(self.root, write=True)  # as manifest.py does after writing
        r = self.wc()
        self.assertEqual(r.code, 0)  # warnings only
        for code in ('NARRATIVE_SOURCE_CHANGED', 'SOURCE_UPSTREAM_CHANGED', 'ABSTRACT_DRAFT'):
            self.assertIn(code, r.out)

    def test_source_policy(self):
        manifest.put_source(self.root, 'alpha-doc', license='proprietary')
        self.assertNotIn('SOURCE_POLICY', self.codes())
        r = helpers.run('wiki-check.py', ['--root', self.root, '--visibility', 'public', '--json'])
        findings = json.loads(r.out)['findings']
        self.assertEqual([f['file'] for f in findings if f['code'] == 'SOURCE_POLICY'], ['sllmwiki/sources/alpha-doc.md'])
        manifest.put_source(self.root, 'alpha-doc', permission='Jane Doe, 2026-10-21')
        self.assertNotIn('SOURCE_POLICY', [f['code'] for f in json.loads(helpers.run('wiki-check.py', ['--root', self.root, '--visibility', 'public', '--json']).out)['findings']])
        self.write('Config.toml', '[structural-llm-wiki-settings]\nsource_copies = "links-only"\n')
        self.assertEqual(self.codes().count('SOURCE_POLICY'), 2)

    def test_visibility_is_asked_only_with_saved_copies(self):
        with mock.patch.object(policy, 'visibility', return_value='private') as asked:
            self.assertEqual(helpers.run('wiki-check.py', ['--root', self.root]).code, 0)
            self.assertEqual(asked.call_count, 1)
            manifest.remove(self.root, 'sources', 'alpha-doc')
            manifest.remove(self.root, 'sources', 'beta-doc')
            manifest.save(self.root, 'narratives', 'what-is-alpha', {'template': 'technical_brief_overview',
                                                                    'tags': {'primary': ['leaf-a'], 'supporting': []}, 'read': {}})
            helpers.run('wiki-check.py', ['--root', self.root, '--fix'])
            self.assertEqual(asked.call_count, 1)

    def test_generated_pages(self):
        manifest.add_tag(self.root, 'leaf-c', 'Third leaf', 'root-topic')
        os.remove(os.path.join(self.root, 'sllmwiki/tags/leaf-b.md'))
        self.write('sllmwiki/tags/old-tag.md', f'# old-tag\n\n{tagpages.GENERATED}\n')
        self.write('sllmwiki/tags/notes.md', '# My notes\n')
        codes = self.codes()
        self.assertEqual(sorted(c for c in codes if c.endswith(('OUTDATED', 'ORPHAN'))),
                         ['INDEX_OUTDATED', 'TAG_PAGE_ORPHAN', 'TAG_PAGE_OUTDATED', 'TAG_PAGE_OUTDATED', 'TAG_PAGE_OUTDATED'])
        r = self.wc('--fix')
        self.assertEqual(r.code, 0, r.out)
        self.assertTrue(os.path.isfile(os.path.join(self.root, 'sllmwiki/tags/leaf-c.md')))
        self.assertFalse(os.path.exists(os.path.join(self.root, 'sllmwiki/tags/old-tag.md')))
        self.assertEqual(self.read('sllmwiki/tags/notes.md'), '# My notes\n')  # someone's own page
        self.write('sllmwiki/tags/leaf-a.md', '# leaf-a\n\nMy own page.\n')
        r = self.wc('--fix')
        self.assertIn('PAGE_HANDWRITTEN', r.out)
        self.assertEqual(self.read('sllmwiki/tags/leaf-a.md'), '# leaf-a\n\nMy own page.\n')


    def test_what_the_book_cannot_show(self):
        helpers.add_narrative(self.root, 'x', 'X?', built_on=('y',))
        helpers.add_narrative(self.root, 'y', 'Y?', built_on=('x',))
        links = ('See [nothing](#nope), [the metadata](what-is-alpha.md#9-metadata), [a ghost](ghost.md), '
                 '[no source](../sources/nope.md) and ![gone](figures/y/gone.png).\n\n## 6.')
        self.write('sllmwiki/narratives/y.md', self.read('sllmwiki/narratives/y.md').replace('## 6.', links))
        found = json.loads(self.wc('--json').out)['findings']
        book = [(f['code'], f['message']) for f in found if f['code'].startswith('BOOK_')]
        self.assertEqual(book, [('BOOK_CYCLE', 'narratives built on each other in a cycle: x, y'),
                                ('BOOK_LINK', '#nope: this narrative has no section #nope, in the book'),
                                ('BOOK_LINK', 'what-is-alpha.md#9-metadata: what-is-alpha has no section #9-metadata, in the book')])
        self.assertEqual([f['file'] for f in found if f['code'] == 'BOOK_LINK'], ['sllmwiki/narratives/y.md:34'] * 2)
        # the ghost, the missing source and the missing figure are the wiki's own checks' to report
        self.assertEqual(sum(f['code'] == 'LINK_PATH' for f in found), 3)


class FinishRegenerates(helpers.WikiTestCase):
    def test_finish_narrative_rewrites_the_pages(self):
        manifest.add_tag(self.root, 'leaf-c', 'Third leaf', 'root-topic')
        r = helpers.run('finish-narrative.py', ['what-is-alpha', '--primary', 'leaf-c', '--root', self.root])
        self.assertEqual(r.code, 0, r.out)
        self.assertIn('regenerated', r.out)
        self.assertIn('[What is alpha?](../narratives/what-is-alpha.md)', self.read('sllmwiki/tags/leaf-c.md'))
        self.assertEqual(helpers.run('wiki-check.py', ['--root', self.root, '--visibility', 'private']).code, 0)


if __name__ == '__main__':
    unittest.main()
