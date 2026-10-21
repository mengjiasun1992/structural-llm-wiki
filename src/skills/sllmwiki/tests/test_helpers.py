"""Tests for helpers.py: the fixture wiki, in-process scripts, git and the local server."""

import os
import shutil
import tempfile
import unittest
import urllib.error
import urllib.request

import helpers


class FixtureWiki(helpers.WikiTestCase):
    def test_fixed_layout(self):
        for rel in ('sllmwiki/tags/tags.yaml', 'sllmwiki/sources/manifest.yaml', 'sllmwiki/narratives/manifest.yaml',
                    'sllmwiki/sources/alpha-doc.md', 'sllmwiki/sources/beta-doc.md', 'sllmwiki/narratives/what-is-alpha.md'):
            self.assertTrue(os.path.isfile(os.path.join(self.root, rel)), rel)

    def test_pin_is_the_source_without_its_footer(self):
        saved = self.read('sllmwiki/sources/alpha-doc.md')
        self.assertTrue(saved.startswith(helpers.ALPHA))
        self.assertIn('<!-- sllmwiki:original-source -->', saved)
        self.assertIn(f'alpha-doc: {helpers.md5(helpers.ALPHA.encode())}', self.read('sllmwiki/narratives/manifest.yaml'))

    def test_narrative_cites_saved_sections(self):
        text = self.read('sllmwiki/narratives/what-is-alpha.md')
        self.assertTrue(text.startswith('# What is alpha?\n'))
        self.assertIn('[\\[1\\]](../sources/alpha-doc.md#details)', text)

    def test_a_committed_git_repository(self):
        self.assertEqual(helpers.git(self.root, 'log', '--format=%s').stdout.strip(), 'init')
        self.assertEqual(helpers.git(self.root, 'branch', '--show-current').stdout.strip(), 'mainline')
        self.assertEqual(helpers.git(self.root, 'status', '--porcelain').stdout, '')

    def test_write_keeps_text_byte_for_byte_and_takes_bytes(self):
        self.write('a.md', 'x\r\ny\n')
        self.assertEqual(self.read('a.md'), 'x\r\ny\n')
        self.write('b/c.bin', b'\x00\x01')
        with open(os.path.join(self.root, 'b/c.bin'), 'rb') as f:
            self.assertEqual(f.read(), b'\x00\x01')


class NoGit(helpers.WikiTestCase):
    git = False

    def test_no_repository(self):
        self.assertFalse(os.path.exists(os.path.join(self.root, '.git')))


class InProcessScripts(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='helpers-')
        self.script = helpers.write(self.dir, 'tool-x.py', (
            'import os, sys\n'
            'def main(argv):\n'
            '    if argv == ["exit"]:\n'
            '        sys.exit(3)\n'
            '    if argv == ["exit-none"]:\n'
            '        sys.exit()\n'
            '    if argv == ["exit-text"]:\n'
            '        sys.exit("bad")\n'
            '    print(os.path.basename(os.getcwd())); print("e", file=sys.stderr)\n'
            '    return None if argv == ["none"] else 5\n'))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_output_exit_codes_and_cwd(self):
        sub = os.path.join(self.dir, 'sub')
        os.makedirs(sub)
        r = helpers.run(self.script, [], cwd=sub)
        self.assertEqual((r.code, r.out, r.err), (5, 'sub\n', 'e\n'))
        self.assertNotEqual(os.getcwd(), sub)  # the working directory is restored
        self.assertEqual(helpers.run(self.script, ['none']).code, 0)
        self.assertEqual(helpers.run(self.script, ['exit']).code, 3)
        self.assertEqual(helpers.run(self.script, ['exit-none']).code, 0)
        self.assertEqual(helpers.run(self.script, ['exit-text']).code, 1)
        self.assertIn('code=5', repr(r))


class Server(unittest.TestCase):
    def test_routes_and_404(self):
        with helpers.LocalServer({'/a': (200, {'Content-Type': 'text/plain'}, b'body')}) as s:
            with urllib.request.urlopen(s.url('/a')) as r:
                self.assertEqual(r.read(), b'body')
            with self.assertRaises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(s.url('/missing'))
            self.assertEqual(e.exception.code, 404)
            e.exception.close()


if __name__ == '__main__':
    unittest.main()
