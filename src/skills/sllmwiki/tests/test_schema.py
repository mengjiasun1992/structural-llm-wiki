import unittest

import helpers  # noqa: F401
from lib.schema import validate

MD5 = 'a' * 32


def source(**over):
    e = {'file': 'ingested/a.md', 'type': 'raw_content', 'size_bytes': 10, 'original_url': 'https://x', 'content_modified': '2026-01-01',
         'content_ingested': '2026-01-02T00:00:00Z', 'content_md5': MD5, 'tags': ['t'], 'abstract': 'An abstract.'}
    e.update(over)
    return e


def codes(findings):
    return sorted(f[1] for f in findings)


class Sources(unittest.TestCase):
    def test_valid_entry(self):
        self.assertEqual(validate('ingested', {'a': source()}, 'm'), [])
        self.assertEqual(validate('ingested', {'a': source(fetch={'start': 's', 'exclude_class': ['x']})}, 'm'), [])

    def test_type_errors_and_values(self):
        f = validate('ingested', {'a': source(size_bytes='10', content_md5='xyz', content_modified='last week', type='weblink',
                                               tags='t', original_url='')}, 'm')
        self.assertEqual(codes(f), ['BAD_TYPE', 'BAD_TYPE', 'BAD_TYPE', 'BAD_TYPE', 'BAD_TYPE', 'BAD_VALUE'])
        f = validate('ingested', {'a': source(tags=['ok', 'Not Ok', 'ok'])}, 'm')
        self.assertEqual(codes(f), ['BAD_TYPE', 'BAD_VALUE'])

    def test_missing_unknown_and_nested(self):
        e = source(orignal_url='x', fetch={'start': 's', 'exclude_klass': []}, zzz=1)
        del e['original_url']
        msgs = [f[3] for f in validate('ingested', {'a': e}, 'm')]
        self.assertTrue(any('missing field "original_url"' in m for m in msgs))
        self.assertTrue(any('did you mean "original_url"' in m for m in msgs))
        self.assertTrue(any('did you mean "fetch.exclude_class"' in m for m in msgs))
        self.assertTrue(any('unknown field "zzz"; allowed:' in m for m in msgs))
        self.assertEqual(codes(validate('ingested', {'a': source(fetch='x')}, 'm')), ['BAD_TYPE'])
        self.assertEqual(codes(validate('ingested', {'a': source(tags=None)}, 'm')), ['BAD_TYPE'])

    def test_cross_field_rules_and_entry_shape(self):
        self.assertEqual(codes(validate('ingested', {'a': source(file=None)}, 'm')), ['BAD_TYPE', 'BAD_VALUE'])
        link = source(type='link', size_bytes=None, content_md5=None)
        self.assertEqual(codes(validate('ingested', {'a': link}, 'm')), ['BAD_VALUE'])
        del link['file']
        self.assertEqual(validate('ingested', {'a': link}, 'm'), [])
        self.assertEqual(codes(validate('ingested', {'Bad Key': 'x'}, 'm')), ['BAD_ENTRY', 'BAD_TYPE'])


class NarrativesAndTags(unittest.TestCase):
    def test_narrative_entry(self):
        n = {'file': 'groomed/q.md', 'question': 'Q?', 'size_bytes': 1, 'version': '1.0', 'created': '2026-01-01',
             'last_modified': '2026-01-01', 'tags': {'primary': ['t'], 'supporting': []}, 'sources_read_full': {'s': MD5},
             'sources_abstract_only': [], 'status': 'draft'}
        self.assertEqual(validate('groomed', {'q': n}, 'g'), [])
        n2 = dict(n, version=1.1, sources_read_full=['s', 'Bad Slug'], status='final')
        self.assertEqual(codes(validate('groomed', {'q': n2}, 'g')), ['BAD_TYPE', 'BAD_TYPE', 'BAD_VALUE'])
        n3 = dict(n, version='one', sources_read_full={'s': 'nope'}, tags={'primary': ['t']})
        self.assertEqual(codes(validate('groomed', {'q': n3}, 'g')), ['BAD_TYPE', 'BAD_TYPE', 'MISSING_FIELD'])
        self.assertEqual(codes(validate('groomed', {'q': dict(n, sources_read_full='x', size_bytes=-1)}, 'g')), ['BAD_TYPE', 'BAD_TYPE'])
        self.assertEqual(codes(validate('groomed', {'q': dict(n, file='/abs/path')}, 'g')), ['BAD_TYPE'])

    def test_tag_entry(self):
        t = {'description': 'd', 'parent': None, 'sub_tags': [], 'ingested': [], 'groomed': [], 'smes': []}
        self.assertEqual(validate('tags', {'t': t}, 'tags.yaml'), [])
        self.assertEqual(codes(validate('tags', {'t': dict(t, abstract_inputs=MD5)}, 'tags.yaml')), ['BAD_VALUE'])
        self.assertEqual(codes(validate('tags', {'Bad_Tag': dict(t, parent='Not Kebab')}, 'tags.yaml')), ['BAD_TYPE', 'BAD_TYPE'])
        self.assertEqual(validate('tags', None, 'tags.yaml'), [])


if __name__ == '__main__':
    unittest.main()
