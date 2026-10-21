"""Tests for lib/wikiyaml.py: the YAML the skill writes, read back exactly, and
everything else refused with its line."""

import unittest

import helpers
from lib import wikiyaml as y
from lib.wikiyaml import YamlError

try:
    import yaml
except ImportError:
    yaml = None


class Read(unittest.TestCase):
    def test_the_subset(self):
        text = ('# a comment\n'
                '---\n'
                'entry-one:  # trailing comment\n'
                '  plain: hello world\n'
                '  url: https://example.com/a?b=1&c=%20  # a comment\n'
                '  quoted: "a: b # not a comment, \\"q\\" é"\n'
                "  single: 'it''s # here'\n"
                '  number: 42\n'
                '  negative: -3\n'
                '  flag: true\n'
                '  nothing: null\n'
                '  tilde: ~\n'
                '  empty-value:\n'
                '  flow: [a, "b, c", \'d\', 3, ]\n'
                '  empty-list: []\n'
                '  empty-map: {}\n'
                '  block:\n'
                '    - one\n'
                '    - "two: 2"\n'
                '  nested:\n'
                '    primary: [x]\n'
                '    deeper:\n'
                '      k: v\n'
                '\n'
                'entry-two:\n'
                '  a: b\n')
        self.assertEqual(y.parse(text), {
            'entry-one': {'plain': 'hello world', 'url': 'https://example.com/a?b=1&c=%20', 'quoted': 'a: b # not a comment, "q" é',
                          'single': "it's # here", 'number': 42, 'negative': -3, 'flag': True, 'nothing': None, 'tilde': None,
                          'empty-value': None, 'flow': ['a', 'b, c', 'd', 3], 'empty-list': [], 'empty-map': {},
                          'block': ['one', 'two: 2'], 'nested': {'primary': ['x'], 'deeper': {'k': 'v'}}},
            'entry-two': {'a': 'b'}})

    def test_empty_files(self):
        for text in ('', '# only comments\n\n', '{}\n', '---\n'):
            self.assertEqual(y.parse(text), {}, text)

    def test_crlf(self):
        self.assertEqual(y.parse('a:\r\n  b: c\r\n'), {'a': {'b': 'c'}})

    def test_refused_with_their_line(self):
        cases = [
            ('a:\n\tb: c\n', 2, 'tabs'),
            ('a: 1\n---\nb: 2\n', 2, 'one document per file'),
            ('a: 1\n...\n', 2, 'one document per file'),
            ('a: 1\n  b: 2\n', 2, 'unexpected indentation'),
            ('  a: 1\n', 1, 'unexpected indentation'),
            ('a:\n   b: 2\n', 2, 'two spaces'),
            ('a:\n  b: 1\n c: 2\n', 3, 'unexpected indentation'),
            ('- a\n', 1, 'needs a key above it'),
            ('a:\n  - x\n    - y\n', 3, 'unexpected indentation'),
            ('just text\n', 1, 'expected "key: value"'),
            ('a: 1\na: 2\n', 2, 'a is repeated'),
            ('a: |\n  text\n', 1, 'block scalars'),
            ('a: >\n', 1, 'block scalars'),
            ('a: &x 1\n', 1, 'anchors'),
            ('a: *x\n', 1, 'anchors'),
            ('a: !tag 1\n', 1, 'anchors'),
            ('a: {b: 1}\n', 1, 'flow mappings'),
            ('a: "open\n', 1, 'not one closed double-quoted string'),
            ('a: "x" y\n', 1, 'not one closed double-quoted string'),
            ("a: 'open\n", 1, 'single-quoted string must close'),
            ("a: 'x'y'\n", 1, 'single-quoted string must close'),
            ('a: [1, 2\n', 1, 'must close on its line'),
            ('a: [[1]]\n', 1, 'scalars only'),
            ('a: [{}]\n', 1, 'scalars only'),
            ('a: ["open]\n', 1, 'must close'),
            ('a: [x, , y]\n', 1, 'empty item'),
            ('a:\n  - k: v\n', 2, 'not mappings'),
            ('a:\n  - [x]\n', 2, 'scalars only'),
            ('a:\n  -\n', 2, 'an empty list item'),
            ('a: yes\n', 1, 'reads differently'),
            ('a: Off\n', 1, 'reads differently'),
            ('a: 1.5\n', 1, 'reads differently'),
            ('a: .inf\n', 1, 'reads differently'),
            ('a: 0x1F\n', 1, 'reads differently'),
            ('a: 2026-10-21\n', 1, 'reads differently'),
            ('a: 12:30\n', 1, 'reads differently'),
            ('a: 1\n---\n', 2, 'one document per file'),
            ('a: b: c\n', 1, 'quote this value'),
            ('a: @x\n', 1, 'quote this value'),
            ('a: x:\n', 1, 'quote this value'),
        ]
        for text, line, msg in cases:
            with self.subTest(text=text), self.assertRaises(YamlError) as e:
                y.parse(text)
            self.assertEqual(e.exception.line, line, text)
            self.assertIn(msg, str(e.exception))


class Write(unittest.TestCase):
    def test_format_scalar_reads_back(self):
        values = [None, True, False, 0, -7, 'plain', 'https://e.com/x?a=1&b=%2F', 'two words', 'yes', 'No', '1.5', '123',
                  '0x1F', 'a: b', 'a #b', 'ends:', '#tag', '@ann', '- item', ': x', '[x]', '"q"', "it's", 'trailing ',
                  'é', 'line\nbreak', '', 'CC-BY-4.0', 'sources/a-b.md', '2026-10-21', '2026-10-21T10:00:00Z', '12:30', 'fe7e08edc87d3fd71895ec611efdb04e']
        for v in values:
            with self.subTest(v=v):
                self.assertEqual(y.parse(f'k: {y.format_scalar(v)}\n')['k'], v)
                if yaml is not None and isinstance(v, str):
                    self.assertEqual(yaml.safe_load(f'k: {y.format_scalar(v)}\n')['k'], v)  # PyYAML agrees
        self.assertEqual(y.format_scalar('plain'), 'plain')
        self.assertEqual(y.format_scalar('123'), '"123"')
        with self.assertRaises(TypeError):
            y.format_scalar(1.5)

    def test_render_entry(self):
        fields = {'template': 'technical_brief_overview', 'tags': {'primary': ['leaf-a'], 'supporting': []},
                  'read': {'alpha-doc': 'fe7e08edc87d3fd71895ec611efdb04e'}, 'empty': {}, 'long': ['word ' * 10] * 3}
        text = y.render_entry('what-is-alpha', fields)
        self.assertTrue(text.startswith('what-is-alpha:\n  template: technical_brief_overview\n  tags:\n    primary: [leaf-a]\n    supporting: []\n'))
        self.assertIn('  empty: {}\n', text)
        self.assertIn('  long:\n    - "word word', text)  # too long for one line: a block list
        self.assertIn('  sentences:\n    - one two\n', y.render_entry('e', {'sentences': ['one two']}))  # sentences: one per line
        self.assertEqual(y.parse(text), {'what-is-alpha': fields})

    def test_upsert_replaces_in_place_and_keeps_the_rest(self):
        text = '# Header comment.\n\nalpha:\n  a: 1\n  # inner\n  b: 2\n\n# about beta\nbeta:\n  c: 3\n'
        out = y.upsert_entry(text, 'alpha', {'a': 9})
        self.assertEqual(out, '# Header comment.\n\nalpha:\n  a: 9\n\n# about beta\nbeta:\n  c: 3\n')
        out = y.upsert_entry(out, 'gamma', {'d': 'x'})
        self.assertTrue(out.endswith('beta:\n  c: 3\n\ngamma:\n  d: x\n'))
        self.assertEqual(y.upsert_entry('', 'a', {'b': 1}), 'a:\n  b: 1\n')
        self.assertEqual(y.upsert_entry('# only a comment\n', 'a', {'b': 1}), '# only a comment\n\na:\n  b: 1\n')
        self.assertEqual(y.parse(y.upsert_entry(text, 'beta', {'c': 4}))['beta'], {'c': 4})

    def test_a_key_that_starts_another_does_not_match(self):
        text = 'alpha-doc:\n  a: 1\n\nalpha:\n  b: 2\n'
        self.assertEqual(y.parse(y.upsert_entry(text, 'alpha', {'b': 3})), {'alpha-doc': {'a': 1}, 'alpha': {'b': 3}})

    def test_remove_entry(self):
        text = 'a:\n  x: 1\n\nb:\n  y: 2\n\nc:\n  z: 3\n'
        self.assertEqual(y.remove_entry(text, 'b'), 'a:\n  x: 1\n\nc:\n  z: 3\n')
        self.assertEqual(y.remove_entry(text, 'c'), 'a:\n  x: 1\n\nb:\n  y: 2\n\n')
        self.assertEqual(y.remove_entry(text, 'missing'), text)


class FixtureFiles(helpers.WikiTestCase):
    def test_read_and_rewrite_unchanged(self):
        for rel in ('sllmwiki/tags/tags.yaml', 'sllmwiki/sources/manifest.yaml', 'sllmwiki/narratives/manifest.yaml'):
            text = self.read(rel)
            data = y.parse(text)
            rewritten = text
            for key, fields in data.items():
                rewritten = y.upsert_entry(rewritten, key, fields)
            self.assertEqual(rewritten, text, rel)  # the writer writes what the fixture holds
            if yaml is not None:
                self.assertEqual(yaml.safe_load(text), data, rel)


if __name__ == '__main__':
    unittest.main()
