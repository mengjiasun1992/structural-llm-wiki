"""Tests for lib/layout.py: the fixed layout and the command-line plumbing."""

import contextlib
import io
import os
import unittest
from unittest import mock

import helpers
from lib import layout


class Layout(unittest.TestCase):
    def test_the_fixed_paths(self):
        self.assertEqual(
            (layout.TAGS, layout.SOURCES, layout.SOURCES_MANIFEST, layout.NARRATIVES, layout.NARRATIVES_MANIFEST,
             layout.OBSIDIAN_GRAPH, layout.INDEX, layout.TEMPLATES, layout.CONFIG),
            ('sllmwiki/tags/tags.yaml', 'sllmwiki/sources', 'sllmwiki/sources/manifest.yaml', 'sllmwiki/narratives',
             'sllmwiki/narratives/manifest.yaml', 'sllmwiki/.obsidian/graph.json', 'SLLMWIKI_INDICES.md', 'sllmwiki/templates', 'Config.toml'))
        self.assertEqual(layout.in_content('sources/a.md'), 'sllmwiki/sources/a.md')


class Cli(helpers.WikiTestCase):
    def call(self, fn, *args):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as e:
            fn(*args)
        return e.exception.code, err.getvalue()

    def test_usage_and_fail(self):
        c = layout.Cli('tool', 'usage: tool <x>')
        self.assertEqual(self.call(c.usage, 'missing x'), (2, 'tool: missing x\nusage: tool <x>\n'))
        self.assertEqual(self.call(c.fail, 'broken'), (1, 'tool: broken\n'))

    def test_wiki_from_root_or_working_directory(self):
        c = layout.Cli('tool', '')
        self.assertEqual(c.wiki(self.root), os.path.abspath(self.root))
        old = os.getcwd()
        try:
            os.chdir(os.path.join(self.root, 'sllmwiki', 'narratives'))  # inside the repository: its root
            self.assertEqual(os.path.realpath(c.wiki()), os.path.realpath(self.root))
        finally:
            os.chdir(old)
        self.assertTrue(layout.is_wiki(self.root))

    def test_not_a_wiki(self):
        os.remove(os.path.join(self.root, layout.TAGS))
        code, err = self.call(layout.Cli('tool', '').wiki, self.root)
        self.assertEqual(code, 1)
        self.assertIn('is not a wiki (no sllmwiki/tags/tags.yaml): run /sllmwiki:init first', err)

    def test_find_root_outside_git(self):
        plain = os.path.join(self.tmp, 'plain')
        os.makedirs(plain)
        with mock.patch.object(layout, 'git_root', return_value=None):
            self.assertEqual(layout.find_root(plain), os.path.abspath(plain))

    def test_take_root(self):
        c = layout.Cli('tool', 'usage')
        self.assertEqual(c.take_root(['a', '--root', '/w', 'b']), ('/w', ['a', 'b']))
        self.assertEqual(c.take_root(['a']), (None, ['a']))
        for argv in (['--root'], ['--root', '--json']):
            self.assertEqual(self.call(c.take_root, argv)[0], 2)

    def test_entry(self):
        with mock.patch('sys.argv', ['tool', 'x']), self.assertRaises(SystemExit) as e:
            layout.entry(lambda argv: len(argv) + 4)
        self.assertEqual(e.exception.code, 5)


if __name__ == '__main__':
    unittest.main()
