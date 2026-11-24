"""Tests for lib/mermaid.py and narrative-format --render-mermaid: each diagram rendered with mermaid-cli
through npx, here a fake npx on PATH, since tests never use the network (issue #190)."""

import os
import stat
import tempfile
import unittest
from unittest import mock

import helpers
from sllmwiki.lib import mermaid

FAKE_NPX = '''#!/bin/sh
while [ $# -gt 0 ]; do
  case "$1" in -i) in="$2"; shift ;; -o) out="$2"; shift ;; esac
  shift
done
if grep -q BAD "$in"; then echo "Error: Parse error on line 2:" >&2; exit 1; fi
if grep -q CRASH "$in"; then echo "Failed to launch the browser process" >&2; exit 1; fi
echo '<svg/>' > "$out"
'''
GOOD = '```mermaid\nflowchart LR\n  A --> B\n```\n\n*Figure 1-1: A sends to B.*\n'


def doc(*diagrams):
    return '# Q\n\nText.\n\n' + '\n'.join(diagrams)


class Render(unittest.TestCase):
    def setUp(self):
        self.bin = tempfile.mkdtemp()
        with open(os.path.join(self.bin, 'npx'), 'w') as f:
            f.write(FAKE_NPX)
        os.chmod(os.path.join(self.bin, 'npx'), stat.S_IRWXU)
        self.env = mock.patch.dict(os.environ, {'PATH': self.bin + os.pathsep + os.environ['PATH'], 'SLLMWIKI_MERMAID': ''})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_renders(self):
        self.assertEqual(mermaid.render(doc(GOOD)), [])
        self.assertEqual(mermaid.render('# Q\n\nNo diagram.\n'), [])
        bad = doc(GOOD, GOOD.replace('A --> B', 'A --> BAD'))
        self.assertEqual(mermaid.render(bad), [('error', 'MERMAID_SYNTAX', 12, 'this diagram doesn\'t render: Error: Parse error on line 2:')])
        self.assertEqual(mermaid.blocks(doc(GOOD)), [(4, 'flowchart LR\n  A --> B')])

    def test_unchecked(self):
        crash = mermaid.render(doc(GOOD.replace('A --> B', 'A --> CRASH')))
        self.assertEqual([c for _, c, _, _ in crash], ['MERMAID_UNCHECKED'])
        self.assertIn('Failed to launch', crash[0][3])
        with mock.patch.dict(os.environ, {'PATH': tempfile.mkdtemp()}):
            self.assertEqual([c for _, c, _, _ in mermaid.render(doc(GOOD))], ['MERMAID_UNCHECKED'])
        with mock.patch('subprocess.run', side_effect=OSError('no exec')):
            self.assertIn('no exec', mermaid.render(doc(GOOD))[0][3])
        with mock.patch.dict(os.environ, {'SLLMWIKI_MERMAID': 'off'}):
            self.assertEqual(mermaid.render(doc(GOOD.replace('A --> B', 'A --> BAD'))), [])


class Command(helpers.WikiTestCase):
    def test_render_mermaid_flag(self):
        bin_dir = tempfile.mkdtemp(dir=self.root)
        with open(os.path.join(bin_dir, 'npx'), 'w') as f:
            f.write(FAKE_NPX)
        os.chmod(os.path.join(bin_dir, 'npx'), stat.S_IRWXU)
        rel = 'sllmwiki/narratives/what-is-alpha.md'
        text = helpers.read(self.root, rel)
        self.write(rel, text.replace('graph LR\n', 'graph LR\n    BAD\n', 1))
        path = os.path.join(self.root, rel)
        with mock.patch.dict(os.environ, {'PATH': bin_dir + os.pathsep + os.environ['PATH'], 'SLLMWIKI_MERMAID': ''}):
            plain = helpers.run('narrative-format.py', ['--root', self.root, path])
            rendered = helpers.run('narrative-format.py', ['--root', self.root, '--render-mermaid', path])
        self.assertNotIn('MERMAID', plain.out)  # only when asked
        self.assertIn('MERMAID_SYNTAX', rendered.out)
        self.assertEqual(rendered.code, 1)


if __name__ == '__main__':
    unittest.main()
