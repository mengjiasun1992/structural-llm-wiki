import unittest

import helpers  # noqa: F401
from lib import toml

try:
    import tomllib
except ImportError:  # Python 3.9 and 3.10
    tomllib = None

SAMPLE = '''# comment
title = "wiki"   # trailing comment
'quoted key' = 'literal \\n stays'
"basic key" = "tab\\there \\"quoted\\" \\u00e9"
count = 1_000
negative = -3
on = true
off = false
list = [
  "a",   # first
  'b',
]
empty = []
inline = { a = 1, "b c" = "d" }
nested = { x = { y = 2 } }

[paths]
ingested = "sources"
dotted.key = "v"

[templates.custom.one]
template = "one/template.md"
'''


class Parse(unittest.TestCase):
    def test_sample(self):
        data = toml.loads(SAMPLE)
        self.assertEqual(data['title'], 'wiki')
        self.assertEqual(data['quoted key'], 'literal \\n stays')
        self.assertEqual(data['basic key'], 'tab\there "quoted" é')
        self.assertEqual((data['count'], data['negative'], data['on'], data['off']), (1000, -3, True, False))
        self.assertEqual((data['list'], data['empty']), (['a', 'b'], []))
        self.assertEqual(data['inline'], {'a': 1, 'b c': 'd'})
        self.assertEqual(data['nested'], {'x': {'y': 2}})
        self.assertEqual(data['paths'], {'ingested': 'sources', 'dotted': {'key': 'v'}})
        self.assertEqual(data['templates']['custom']['one']['template'], 'one/template.md')
        self.assertEqual(toml.loads(''), {})
        self.assertEqual(toml.loads('a = {}\nb = "\\U0001F600"\n'), {'a': {}, 'b': '\U0001F600'})

    @unittest.skipIf(tomllib is None, 'tomllib needs Python 3.11+')
    def test_matches_tomllib(self):
        self.assertEqual(toml.loads(SAMPLE), tomllib.loads(SAMPLE))

    def test_errors(self):
        for text, msg in [('a = "x', 'unterminated'), ('a = """x"""', 'multi-line'), ('a = 1.5', 'expected a string'),
                          ('a = 1979-05-27', 'expected a string'), ('[[t]]\n', 'arrays of tables'), ('a = 1\na = 2', 'duplicate key'),
                          ('[t]\n[t]\n', 'defined twice'), ('a = 1\n[a]\n', 'already a value'), ('a = 1\na.b = 2', 'already a value'),
                          ('a = [1 2]', 'in an array'), ('a = {b = 1 c = 2}', 'inline table'), ('a = {b 1}', 'expected "="'),
                          ('a 1', 'expected "="'), ('= 1', 'expected a key'), ('a = 1 b', 'after the value'), ('[t\n', 'expected "]"'),
                          ('[t] x\n', 'after the value'), ('a = "\\q"', 'unknown escape'), ('a = "\\u12"', 'bad \\u escape'),
                          ('a = nope', 'expected a string')]:
            with self.assertRaises(toml.TomlError, msg=text) as ctx:
                toml.loads(text)
            self.assertIn(msg, str(ctx.exception), text)
        with self.assertRaises(toml.TomlError) as ctx:
            toml.loads('a = 1\n\nb = "x')
        self.assertIn('line 3', str(ctx.exception))


class Write(unittest.TestCase):
    def test_dumps_value(self):
        self.assertEqual(toml.dumps_value('a "b" \\ c\nd'), '"a \\"b\\" \\\\ c\\nd"')
        self.assertEqual([toml.dumps_value(v) for v in (True, False, 3, ['x', 1])], ['true', 'false', '3', '["x", 1]'])
        with self.assertRaises(TypeError):
            toml.dumps_value(1.5)

    def test_set_value(self):
        text = '# top\n[paths]\ningested = "ingested"   # sources\ngroomed = "groomed"\n\n[other]\nx = 1\n'
        out = toml.set_value(text, 'paths', 'ingested', 'sources')
        self.assertIn('ingested = "sources"    # sources\n', out)  # the comment is kept, in its column
        self.assertIn('x = "a much longer value"  # c', toml.set_value('[t]\nx = "v"  # c\n', 't', 'x', 'a much longer value'))
        self.assertEqual(toml.loads(out)['paths'], {'ingested': 'sources', 'groomed': 'groomed'})
        out = toml.set_value(text, 'paths', 'tags', 'meta/tags.yaml')  # added at the end of the table
        self.assertIn('groomed = "groomed"\ntags = "meta/tags.yaml"\n\n[other]', out)
        out = toml.set_value(text, 'new', 'k', 'v')  # a new table at the end
        self.assertTrue(out.endswith('x = 1\n\n[new]\nk = "v"\n'))
        self.assertEqual(toml.set_value('', 'paths', 'k', 'v'), '[paths]\nk = "v"\n')
        self.assertEqual(toml.loads(toml.set_value('[paths]\nk = [1, 2]\n', 'paths', 'k', 'v'))['paths']['k'], 'v')
        self.assertEqual(toml.set_value('[paths]\nk = broken\n', 'paths', 'k', 'v'), '[paths]\nk = "v"\n')


if __name__ == '__main__':
    unittest.main()
