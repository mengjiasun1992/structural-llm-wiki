import unittest

import helpers  # noqa: F401
from lib import wikiyaml as y
from lib.wikiyaml import YamlError, parse_yaml


class Parse(unittest.TestCase):
    def test_supported_subset(self):
        text = '''# comment
a: 1
b: 2.5
c: 3.0
d: "q # not a comment"
e: 'it''s'
f: [x, "y", 'z', 4]
g: []
h: {}
i: ~
j: null
k: true
l: false
m:
  - one
  - "two"
n:
- three
o:
  p: plain value  # trailing comment
"quoted key": v
q:
'''
        d = parse_yaml(text)
        self.assertEqual(d['a'], 1)
        self.assertEqual(d['b'], 2.5)
        self.assertEqual(d['c'], 3)
        self.assertEqual(d['d'], 'q # not a comment')
        self.assertEqual(d['e'], "it's")
        self.assertEqual(d['f'], ['x', 'y', 'z', 4])
        self.assertEqual((d['g'], d['h']), ([], {}))
        self.assertIsNone(d['i'])
        self.assertIsNone(d['j'])
        self.assertEqual((d['k'], d['l']), (True, False))
        self.assertEqual(d['m'], ['one', 'two'])
        self.assertEqual(d['n'], ['three'])
        self.assertEqual(d['o'], {'p': 'plain value'})
        self.assertEqual(d['quoted key'], 'v')
        self.assertIsNone(d['q'])

    def test_empty_files_and_placeholders(self):
        self.assertIsNone(parse_yaml('# only comments\n\n---\n'))
        self.assertEqual(parse_yaml('{}\n'), {})
        self.assertEqual(parse_yaml('[]\n'), [])
        self.assertEqual(parse_yaml('- a\n- b\n'), ['a', 'b'])
        self.assertEqual(parse_yaml('a: "x \\\\ y"\n')['a'], 'x \\ y')
        self.assertEqual(parse_yaml('a: ["x\\"y", b]\n')['a'], ['x"y', 'b'])
        self.assertEqual(parse_yaml('a: 1.5e3\n')['a'], 1500)
        self.assertEqual(parse_yaml('a: 1e3\n')['a'], '1e3')  # a float needs a decimal point

    def test_refusals(self):
        bad = {
            'a: "unterminated\n': 'unterminated double',
            "a: 'unterminated\n": 'unterminated single',
            'a: "bad \\q"\n': 'invalid double',
            'a: {b: 1}\n': 'non-empty flow',
            'a: [x, [y]]\n': 'nested flow',
            'a: [x\n': 'unterminated flow',
            'a: ["x]\n': 'unterminated string in flow',
            'a: [x, , y]\n': 'empty item',
            'a: &anchor\n': 'unsupported YAML',
            '\ta: 1\n': 'tabs',
            '{}\na: 1\n': 'placeholder',
            'a:\n  - b: 1\n': 'only scalar sequence',
            'a:\n  - x\n    - y\n': 'unexpected indentation inside a sequence',
            'a: 1\n- b\n': 'sequence item where a mapping',
            'a: 1\nnot a mapping\n': 'expected "key: value"',
            'a: 1\na: 2\n': 'duplicate key',
            'a:\n  b: 1\n    c: 2\n': 'unexpected indentation',
            '"open: 1\n': 'unterminated quoted key',
            '  a: 1\nb: 2\n': 'unexpected content',
        }
        for text, why in bad.items():
            with self.assertRaises(YamlError, msg=why) as ctx:
                parse_yaml(text)
            self.assertIn('line', str(ctx.exception), why)
        self.assertEqual(str(YamlError('plain')), 'plain')

    def test_quoted_key_without_colon_is_not_a_key(self):
        with self.assertRaises(YamlError):
            parse_yaml('"key" value\n')


class Writers(unittest.TestCase):
    SRC = '''# header
alpha:
  size: 1  # keep me
  tags: [a]
  items:
    - one
  empty: []

beta:
  size: 2
'''

    def test_format_scalar(self):
        self.assertEqual(y.format_scalar(None), 'null')
        self.assertEqual(y.format_scalar(True), 'true')
        self.assertEqual(y.format_scalar(3), '3')
        self.assertEqual(y.format_scalar('plain'), 'plain')
        self.assertEqual(y.format_scalar('yes'), '"yes"')
        self.assertEqual(y.format_scalar('1.0'), '"1.0"')
        self.assertEqual(y.format_scalar('a: b'), '"a: b"')
        self.assertEqual(y.format_scalar('plain', quote=True), '"plain"')
        self.assertEqual(y.format_scalar('trailing '), '"trailing "')

    def test_set_field_keeps_comments(self):
        out = y.set_field(self.SRC, 'alpha', 'size', 9)
        self.assertIn('  size: 9  # keep me', out)
        self.assertIn('  size: 2', out)
        self.assertIsNone(y.set_field(self.SRC, 'gamma', 'size', 1))
        self.assertIsNone(y.set_field(self.SRC, 'alpha', 'missing', 1))
        self.assertEqual(parse_yaml(y.set_field('"q":\n  size: 1\n', 'q', 'size', 5))['q']['size'], 5)

    def test_entry_and_field_blocks(self):
        out = y.replace_field_block(self.SRC, 'alpha', 'items', ['  items:', '    - two', '    - three'])
        self.assertEqual(parse_yaml(out)['alpha']['items'], ['two', 'three'])
        out = y.replace_field_block(self.SRC, 'beta', 'new', ['  new: x'])
        self.assertEqual(parse_yaml(out)['beta']['new'], 'x')
        self.assertIsNone(y.replace_field_block(self.SRC, 'gamma', 'x', ['  x: 1']))

    def test_append_entry(self):
        out = y.append_entry('{}\n', 'n', [('a', '1'), ('b', ['    - x'])])
        self.assertEqual(parse_yaml(out), {'n': {'a': 1, 'b': ['x']}})
        out = y.append_entry('a: 1', 'n', [('k', 'v')])
        self.assertEqual(parse_yaml(out)['n'], {'k': 'v'})

    def test_add_and_remove_list_items(self):
        src = self.SRC
        out = y.add_list_item(src, 'alpha', 'tags', 'b')
        self.assertEqual(parse_yaml(out)['alpha']['tags'], ['a', 'b'])
        self.assertEqual(y.add_list_item(out, 'alpha', 'tags', 'b'), out)
        out = y.add_list_item(src, 'alpha', 'items', 'two')
        self.assertEqual(parse_yaml(out)['alpha']['items'], ['one', 'two'])
        self.assertEqual(y.add_list_item(out, 'alpha', 'items', 'two'), out)
        out = y.add_list_item(src, 'alpha', 'empty', 'z')
        self.assertEqual(parse_yaml(out)['alpha']['empty'], ['z'])
        out = y.add_list_item(src, 'beta', 'brand_new', 'n')
        self.assertEqual(parse_yaml(out)['beta']['brand_new'], ['n'])
        self.assertIsNone(y.add_list_item(src, 'gamma', 'x', 'y'))
        with self.assertRaises(YamlError):
            y.add_list_item(src, 'alpha', 'size', 'x')

        out = y.remove_list_item(src, 'alpha', 'tags', 'a')
        self.assertEqual(parse_yaml(out)['alpha']['tags'], [])
        self.assertEqual(y.remove_list_item(src, 'alpha', 'tags', 'zz'), src)
        out = y.remove_list_item(src, 'alpha', 'items', 'one')
        self.assertEqual(parse_yaml(out)['alpha']['items'], [])
        two = y.add_list_item(src, 'alpha', 'items', 'two')
        self.assertEqual(parse_yaml(y.remove_list_item(two, 'alpha', 'items', 'one'))['alpha']['items'], ['two'])
        self.assertEqual(y.remove_list_item(src, 'alpha', 'items', 'zz'), src)
        self.assertEqual(y.remove_list_item(src, 'alpha', 'missing', 'x'), src)
        self.assertIsNone(y.remove_list_item(src, 'gamma', 'x', 'y'))
        with self.assertRaises(YamlError):
            y.remove_list_item(src, 'alpha', 'size', 'x')

    def test_remove_entry(self):
        from lib.wikiyaml import remove_entry
        text = '# c\na:\n  x: 1\n\nb:\n  y: 2\n'
        self.assertEqual(remove_entry(text, 'a'), '# c\nb:\n  y: 2\n')
        self.assertEqual(remove_entry(text, 'b'), '# c\na:\n  x: 1\n')
        self.assertEqual(remove_entry(text, 'zz'), text)


if __name__ == '__main__':
    unittest.main()
