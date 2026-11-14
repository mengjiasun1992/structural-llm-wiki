"""Tests for src/tools/pypi-readme.py: a README's relative links and images, pointed at GitHub for PyPI's page (#168)."""

import os
import re
import tempfile
import unittest

import helpers

TOOL = os.path.join(helpers.REPO, 'src', 'tools', 'pypi-readme.py')
REPO, REF = 'owner/name', 'v9.9.9'
BLOB = f'https://github.com/{REPO}/blob/{REF}/'
TREE = f'https://github.com/{REPO}/tree/{REF}/'
RAW = f'https://raw.githubusercontent.com/{REPO}/{REF}/'


def rewrite(text):
    return helpers.load_script(TOOL).rewrite(text, REPO, REF)


class Rewrite(unittest.TestCase):
    def test_targets(self):
        cases = [  # (a line of the README, the line on PyPI)
            ('![Hero](docs/images/hero.svg)', f'![Hero]({RAW}docs/images/hero.svg)'),
            ('![A photo](./pics/a.PNG "a title")', f'![A photo]({RAW}pics/a.PNG "a title")'),
            ('[The manual](docs/manual.md)', f'[The manual]({BLOB}docs/manual.md)'),
            ('[§12](docs/manual.md#12-licenses)', f'[§12]({BLOB}docs/manual.md#12-licenses)'),
            ('[LICENSE](/LICENSE)', f'[LICENSE]({BLOB}LICENSE)'),
            ('[the docs](docs/)', f'[the docs]({TREE}docs)'),
            ('[the root](./)', f'[the root]({TREE})'),
            ('[a space](docs/my%20notes.md)', f'[a space]({BLOB}docs/my%20notes.md)'),
            ('[angle](<docs/a.md>)', f'[angle](<{BLOB}docs/a.md>)'),
            ('[![badge](https://img.shields.io/x.svg)](LICENSE)', f'[![badge](https://img.shields.io/x.svg)]({BLOB}LICENSE)'),
            ('[ref]: docs/design.md', f'[ref]: {BLOB}docs/design.md'),
            ('<img src="docs/images/a.svg" alt="a">', f'<img src="{RAW}docs/images/a.svg" alt="a">'),
            ('<a href=\'NOTICE\'>notice</a>', f'<a href=\'{BLOB}NOTICE\'>notice</a>'),
            ('[two](a.md) and [three](b.md)', f'[two]({BLOB}a.md) and [three]({BLOB}b.md)'),
        ]
        for line, want in cases:
            with self.subTest(line=line):
                self.assertEqual(rewrite(line), (want, []))

    def test_left_alone(self):
        for line in (
            '[PyPI](https://pypi.org/project/sllmwiki/)',
            '[mail](mailto:someone@example.com)',
            '[below](#install)',
            '[cdn](//cdn.example.com/a.js)',
            'Run `[x](docs/a.md)` to see it.',  # a code span
            'Plain text with (docs/a.md) in brackets.',
        ):
            with self.subTest(line=line):
                self.assertEqual(rewrite(line), (line, []))

    def test_fenced_code_is_left_alone(self):
        text = 'before [a](a.md)\n```markdown\n[b](b.md)\n~~~\n[c](c.md)\n```\nafter [d](d.md)\n~~~~\n[e](e.md)\n~~~~\n'
        out, _ = rewrite(text)
        self.assertEqual(re.findall(r'\]\(([^)]+)\)', out), [f'{BLOB}a.md', 'b.md', 'c.md', f'{BLOB}d.md', 'e.md'])

    def test_a_target_outside_the_repository(self):
        out, unresolved = rewrite('[up](../elsewhere.md) and [fine](a.md)')
        self.assertEqual(unresolved, ['../elsewhere.md'])
        self.assertIn('[up](../elsewhere.md)', out)

    def test_this_repositorys_readme(self):
        """Nothing relative is left on PyPI's page."""
        with open(os.path.join(helpers.REPO, 'README.md'), encoding='utf-8') as f:
            out, unresolved = rewrite(f.read())
        self.assertEqual(unresolved, [])
        relative = [t for t in re.findall(r'\]\(<?([^)\s>]+)', out) if not re.match(r'https?:|#|mailto:', t)]
        self.assertEqual(relative, [])
        self.assertIn(f'{RAW}docs/images/hero.svg', out)


class Command(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.readme = os.path.join(self.tmp.name, 'README.md')
        with open(self.readme, 'w', encoding='utf-8') as f:
            f.write('# Title\n\n![hero](docs/hero.svg)\n')

    def read(self):
        with open(self.readme, encoding='utf-8') as f:
            return f.read()

    def test_prints_or_writes(self):
        r = helpers.run(TOOL, ['--repo', REPO, '--ref', REF, self.readme])
        self.assertEqual(r.code, 0)
        self.assertEqual(r.out, f'# Title\n\n![hero]({RAW}docs/hero.svg)\n')
        self.assertIn('](docs/hero.svg)', self.read())  # printing leaves the file alone
        r = helpers.run(TOOL, ['--repo', REPO, '--ref', REF, '--write', self.readme])
        self.assertEqual((r.code, r.out), (0, ''))
        self.assertEqual(self.read(), f'# Title\n\n![hero]({RAW}docs/hero.svg)\n')

    def test_refuses_a_target_outside_the_repository(self):
        with open(self.readme, 'a', encoding='utf-8') as f:
            f.write('[up](../x.md)\n')
        r = helpers.run(TOOL, ['--repo', REPO, '--ref', REF, '--write', self.readme])
        self.assertEqual(r.code, 1)
        self.assertIn('../x.md', r.err)
        self.assertIn('](docs/hero.svg)', self.read())  # nothing written

    def test_usage(self):
        self.assertEqual(helpers.run(TOOL, ['--repo', 'not-a-repo', '--ref', REF, self.readme]).code, 2)
        self.assertEqual(helpers.run(TOOL, [self.readme]).code, 2)


if __name__ == '__main__':
    unittest.main()
