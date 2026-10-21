"""Tests for lib/cli.py and lib/paths.py: usage errors, failures, and finding the wiki."""

import contextlib
import io
import os
import unittest

import helpers
from lib import cli, paths


class CliTest(helpers.WikiTestCase):
    def call(self, fn, *args):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as e:
            fn(*args)
        return e.exception.code, err.getvalue()

    def test_usage_and_fail(self):
        c = cli.Cli('tool', 'usage: tool <x>')
        self.assertEqual(self.call(c.usage, 'missing x'), (2, 'tool: missing x\nusage: tool <x>\n'))
        self.assertEqual(self.call(c.fail, 'broken'), (1, 'tool: broken\n'))

    def test_wiki(self):
        c = cli.Cli('tool', '')
        root, layout = c.wiki(self.root)
        self.assertEqual((root, layout.tags), (os.path.abspath(self.root), 'tags/tags.yaml'))
        old = os.getcwd()
        try:
            os.chdir(os.path.join(self.root, 'groomed'))  # the git repository around the working directory
            self.assertEqual(os.path.realpath(c.wiki()[0]), os.path.realpath(self.root))
        finally:
            os.chdir(old)

    def test_not_a_wiki(self):
        os.remove(os.path.join(self.root, 'tags/tags.yaml'))
        code, err = self.call(cli.Cli('tool', '').wiki, self.root)
        self.assertEqual(code, 1)
        self.assertIn('is not a wiki (no tags/tags.yaml); run /sllmwiki:init first', err)

    def test_broken_config(self):
        self.write('Config.toml', '[structural-llm-wiki-paths]\ngroomed = "/abs"\n')
        code, err = self.call(cli.Cli('tool', '').wiki, self.root)
        self.assertEqual(code, 1)
        self.assertIn('Config.toml', err)

    def test_main_and_split_list(self):
        self.assertEqual(cli.Cli('tool', '').main(lambda argv: len(argv), ['a', 'b']), 2)
        self.assertEqual(cli.split_list('a, b,,c ,'), ['a', 'b', 'c'])


class PathsTest(helpers.WikiTestCase):
    def test_default_layout(self):
        self.assertEqual(paths.manifest_file(self.root, 'ingested'), 'ingested/manifest.yaml')
        self.assertEqual(paths.manifest_file(self.root, 'groomed'), 'groomed/manifest.yaml')
        self.assertEqual(paths.tags_file(self.root), 'tags/tags.yaml')
        self.assertTrue(paths.is_wiki(self.root))

    def test_configured_layout(self):
        self.write('Config.toml', '[structural-llm-wiki-paths]\ncontent = "kb"\ntags = "topics/tags.yaml"\n')
        self.assertEqual(paths.tags_file(self.root), 'kb/topics/tags.yaml')
        self.assertEqual(paths.manifest_file(self.root, 'groomed'), 'kb/groomed/manifest.yaml')
        self.assertFalse(paths.is_wiki(self.root))  # the files are still at the root


if __name__ == '__main__':
    unittest.main()
