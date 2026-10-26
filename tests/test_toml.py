"""Tests for lib/toml.py: the subset Config.toml uses, and everything else refused."""

import unittest

import helpers  # noqa: F401  (puts the scripts on the path)
from lib.toml import TomlError, dumps_value, loads


class Subset(unittest.TestCase):
    def test_tables_values_and_comments(self):
        text = ('# a comment\n'
                'top = 1\n\n'
                '[structural-llm-wiki-settings]   # trailing comment\n'
                'source_copies = "links-only"  # why\n'
                'max_quote_words = -0\n'
                'markers = false\n'
                "literal = 'C:\\path'\n"
                'escaped = "a\\"b\\\\c\\n\\t\\r\\u00e9"\n'
                'smes_exclude = ["@a", \'b\', ]\n'
                'nested = [[1, 2], []]\n'
                'multi = [\n  "x",  # first\n  "y"\n]\n\n'
                '[ a . b ]\n'
                'ok = true\n')
        self.assertEqual(loads(text), {
            'top': 1,
            'structural-llm-wiki-settings': {'source_copies': 'links-only', 'max_quote_words': 0, 'markers': False,
                                             'literal': 'C:\\path', 'escaped': 'a"b\\c\n\t\ré', 'smes_exclude': ['@a', 'b'],
                                             'nested': [[1, 2], []], 'multi': ['x', 'y']},
            'a': {'b': {'ok': True}}})

    def test_empty_and_crlf(self):
        self.assertEqual(loads(''), {})
        self.assertEqual(loads('# only\n\n'), {})
        self.assertEqual(loads('k = 1\n  # no newline at the end'), {'k': 1})
        self.assertEqual(loads('[t]\r\nk = 1\r\n'), {'t': {'k': 1}})

    def test_refused_with_their_line(self):
        cases = [
            ('k = 1.5\n', 1, 'expected a string'),
            ('k = 1979-05-27\n', 1, 'expected a string'),
            ('k = { a = 1 }\n', 1, 'expected a string'),
            ('k = """x"""\n', 1, 'expected the end of the line'),
            ('a.b = 1\n', 1, 'expected key = value'),
            ('"q" = 1\n', 1, 'expected key = value'),
            ('[[t]]\n', 1, 'arrays of tables'),
            ('[t\n', 1, 'not a table header'),
            ('[t]\n[t]\n', 2, 'defined twice'),
            ('k = 1\nk = 2\n', 2, 'set twice'),
            ('a = 1\n[a.b]\n', 2, 'clashes with the value a'),
            ('k = "open\n', 1, 'must close on its line'),
            ("k = 'open\n", 1, 'must close on its line'),
            ('k = "\\q"\n', 1, 'unknown escape'),
            ('k = [1 2]\n', 1, 'expected , or ]'),
            ('k = [1,\n2\n', 3, 'an array must close'),
            ('k = [', 1, 'an array must close'),
            ('k = 1 x\n', 1, 'expected the end of the line'),
            ('k = truex\n', 1, 'expected a string'),
            ('k = 12ab\n', 1, 'expected a string'),
            ('\n\nk\n', 3, 'expected key = value'),
        ]
        for text, line, msg in cases:
            with self.subTest(text=text), self.assertRaises(TomlError) as e:
                loads(text)
            self.assertEqual(e.exception.line, line, text)
            self.assertIn(msg, str(e.exception))


class Dumps(unittest.TestCase):
    def test_values_round_trip(self):
        for value in (True, False, 0, 3000, 'links-only', 'é "q"', ['@a', 'b'], [150, 300], []):
            self.assertEqual(loads(f'k = {dumps_value(value)}\n')['k'], value)

    def test_other_types_refused(self):
        with self.assertRaises(TypeError):
            dumps_value(1.5)


if __name__ == '__main__':
    unittest.main()
