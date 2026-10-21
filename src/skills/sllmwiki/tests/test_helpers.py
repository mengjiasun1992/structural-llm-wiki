"""Tests for helpers.py: the fixture wiki, file helpers, git and the local server."""

import os
import unittest
import urllib.error
import urllib.request

import helpers


class FixtureWikiTest(helpers.WikiTestCase):
    def test_layout(self):
        for rel in ('tags/tags.yaml', 'ingested/manifest.yaml', 'groomed/manifest.yaml',
                    'ingested/alpha-doc.md', 'ingested/beta-doc.md', 'groomed/what-is-alpha.md'):
            self.assertTrue(os.path.isfile(os.path.join(self.root, rel)), rel)

    def test_manifest_matches_the_sources(self):
        alpha = helpers.read_bytes(self.root, 'ingested/alpha-doc.md')
        manifest = self.read('ingested/manifest.yaml')
        self.assertIn(f'size_bytes: {len(alpha)}', manifest)
        self.assertIn(f'content_md5: {helpers.md5(alpha)}', manifest)

    def test_git_repository(self):
        log = helpers.git(self.root, 'log', '--format=%s').stdout
        self.assertEqual(log.strip(), 'init')
        self.assertEqual(helpers.git(self.root, 'status', '--porcelain').stdout, '')

    def test_write_read_and_reset(self):
        self.write('notes/a.md', 'hello\r\n')
        self.assertEqual(self.read('notes/a.md'), 'hello\r\n')
        self.reset()
        self.assertFalse(os.path.exists(os.path.join(self.root, 'notes/a.md')))


class NoGitTest(helpers.WikiTestCase):
    git = False

    def test_no_repository(self):
        self.assertFalse(os.path.exists(os.path.join(self.root, '.git')))


class NarrativeTextTest(unittest.TestCase):
    def test_draft_and_citations(self):
        text = helpers.narrative_text('Q?', version='0.1', status='draft', template='survey',
                                      sources=[('a', 'ingested/a.md')])
        self.assertIn('> **DRAFT**', text)
        self.assertIn('- **Status:** draft', text)
        self.assertIn('- **Template:** survey', text)
        self.assertIn('[\\[1\\]](../ingested/a.md)', text)
        self.assertIn('### 9.2 Citations', text)

    def test_plain(self):
        text = helpers.narrative_text('Q?')
        self.assertNotIn('DRAFT', text)
        self.assertNotIn('Citations', text)


class LocalServerTest(unittest.TestCase):
    def test_serves_routes_and_404(self):
        with helpers.LocalServer({'/a': (200, {'Content-Type': 'text/plain'}, b'body')}) as s:
            with urllib.request.urlopen(s.url('/a')) as r:
                self.assertEqual(r.read(), b'body')
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(s.url('/missing'))
            self.assertEqual(e.exception.code, 404)
            e.exception.close()


class ResultTest(unittest.TestCase):
    def test_repr(self):
        self.assertIn('code=1', repr(helpers.Result(1, 'out', 'err')))


if __name__ == '__main__':
    unittest.main()
