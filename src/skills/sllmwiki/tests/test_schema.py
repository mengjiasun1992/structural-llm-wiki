"""Tests for lib/schema.py: the fields of tags.yaml and the manifests."""

import copy
import unittest

import helpers
from lib import wikiyaml
from lib.schema import validate


def codes(findings):
    return [(f['entry'], f['field'], f['code']) for f in findings]


SOURCE = {'file': 'sources/a.md', 'kind': 'text', 'url': 'https://e.com/a', 'published': '2026-01-02', 'ingested': '2026-01-03',
          'license': 'CC-BY-4.0', 'license_url': 'https://e.com/l', 'tags': ['leaf-a'], 'abstract': 'About a.',
          'abstract_draft': True, 'upstream_changed': '2026-02-01'}
NARRATIVE = {'template': 'technical_brief_overview', 'tags': {'primary': ['leaf-a'], 'supporting': []},
             'read': {'a': 'fe7e08edc87d3fd71895ec611efdb04e'}}
TAG = {'description': 'A tag', 'parent': None, 'smes': ['@ann: wrote it']}


def with_(base, **changes):
    entry = copy.deepcopy(base)
    for k, v in changes.items():
        if v is ...:
            entry.pop(k, None)
        else:
            entry[k] = v
    return entry


class FixtureWiki(helpers.WikiTestCase):
    def test_is_valid(self):
        for kind, rel in (('tags', 'sllmwiki/tags/tags.yaml'), ('sources', 'sllmwiki/sources/manifest.yaml'),
                          ('narratives', 'sllmwiki/narratives/manifest.yaml')):
            self.assertEqual(validate(kind, wikiyaml.parse(self.read(rel)), rel), [], rel)


class Fields(unittest.TestCase):
    def test_complete_entries_pass(self):
        self.assertEqual(validate('sources', {'a': SOURCE}, 'm'), [])
        self.assertEqual(validate('narratives', {'q': NARRATIVE}, 'm'), [])
        self.assertEqual(validate('tags', {'t': TAG, 'u': with_(TAG, parent='t', smes=...)}, 't'), [])

    def test_each_kind_of_bad_value(self):
        cases = [
            ('sources', with_(SOURCE, kind='video'), ('a', 'kind', 'BAD_VALUE')),
            ('sources', with_(SOURCE, url='ftp://x'), ('a', 'url', 'BAD_VALUE')),
            ('sources', with_(SOURCE, published='2026-13-01'), ('a', 'published', 'BAD_VALUE')),
            ('sources', with_(SOURCE, ingested=20260103), ('a', 'ingested', 'BAD_TYPE')),
            ('sources', with_(SOURCE, license=''), ('a', 'license', 'BAD_VALUE')),
            ('sources', with_(SOURCE, tags=[]), ('a', 'tags', 'BAD_VALUE')),
            ('sources', with_(SOURCE, tags='leaf-a'), ('a', 'tags', 'BAD_TYPE')),
            ('sources', with_(SOURCE, tags=['Leaf A']), ('a', 'tags[0]', 'BAD_VALUE')),
            ('sources', with_(SOURCE, abstract_draft='yes'), ('a', 'abstract_draft', 'BAD_TYPE')),
            ('sources', with_(SOURCE, abstract=None), ('a', 'abstract', 'BAD_TYPE')),
            ('sources', with_(SOURCE, file='../x.md'), ('a', 'file', 'BAD_VALUE')),
            ('narratives', with_(NARRATIVE, template='Tech Brief'), ('q', 'template', 'BAD_VALUE')),
            ('narratives', with_(NARRATIVE, read={'a': 'xyz'}), ('q', 'read.a', 'BAD_VALUE')),
            ('narratives', with_(NARRATIVE, read={'Bad Key': 'fe7e08edc87d3fd71895ec611efdb04e'}), ('q', 'read', 'BAD_VALUE')),
            ('narratives', with_(NARRATIVE, read=['a']), ('q', 'read', 'BAD_TYPE')),
            ('narratives', with_(NARRATIVE, tags={'primary': [], 'supporting': []}), ('q', 'tags.primary', 'BAD_VALUE')),
            ('narratives', with_(NARRATIVE, tags={'primary': ['x']}), ('q', 'tags.supporting', 'MISSING_FIELD')),
            ('narratives', with_(NARRATIVE, tags={'primary': ['x'], 'supporting': [], 'other': []}), ('q', 'tags.other', 'UNKNOWN_FIELD')),
            ('tags', with_(TAG, parent='Root Topic'), ('t', 'parent', 'BAD_VALUE')),
            ('tags', with_(TAG, smes=[1]), ('t', 'smes[0]', 'BAD_TYPE')),
            ('tags', with_(TAG, description=...), ('t', 'description', 'MISSING_FIELD')),
        ]
        for kind, entry, want in cases:
            with self.subTest(want=want):
                key = want[0]
                self.assertEqual(codes(validate(kind, {key: entry}, 'f')), [want])

    def test_unknown_field_hint(self):
        found = validate('sources', {'a': with_(SOURCE, licence='x')}, 'f')
        self.assertEqual(codes(found), [('a', 'licence', 'UNKNOWN_FIELD')])
        self.assertIn('did you mean license?', found[0]['message'])
        found = validate('tags', {'t': with_(TAG, zzz=1)}, 'f')
        self.assertTrue(found[0]['message'].endswith('unknown field zzz'))

    def test_a_link_has_no_file_and_a_copy_needs_one(self):
        link = with_(SOURCE, kind='link', file=...)
        self.assertEqual(validate('sources', {'a': link}, 'f'), [])
        self.assertEqual(codes(validate('sources', {'a': with_(SOURCE, kind='link')}, 'f')), [('a', 'file', 'BAD_VALUE')])
        self.assertEqual(codes(validate('sources', {'a': with_(SOURCE, file=...)}, 'f')), [('a', 'file', 'MISSING_FIELD')])
        self.assertEqual(codes(validate('sources', {'a': with_(SOURCE, file='narratives/a.md')}, 'f')), [('a', 'file', 'BAD_VALUE')])

    def test_entries_and_files(self):
        self.assertEqual(codes(validate('tags', {'Bad Key': TAG}, 'f')), [('Bad Key', None, 'BAD_ENTRY')])
        self.assertEqual(codes(validate('tags', {'t': 'text'}, 'f')), [('t', None, 'BAD_ENTRY')])
        self.assertEqual(codes(validate('tags', ['x'], 'f')), [(None, None, 'BAD_TYPE')])
        found = validate('narratives', {'q': with_(NARRATIVE, template=...)}, 'narratives/manifest.yaml')
        self.assertEqual(found[0]['file'], 'narratives/manifest.yaml')
        self.assertEqual(found[0]['message'], 'q: template is required')


if __name__ == '__main__':
    unittest.main()
