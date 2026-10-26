"""Tests for lib/xrefs.py: links from a narrative to a section of another, and their repair."""

import os
import unittest

import helpers
from lib import manifest, xrefs

BETA = 'sllmwiki/narratives/how-does-beta-work.md'


def beta(body):
    return helpers.narrative_text('How does beta work?', extra=f'\n{body}\n')


class Xrefs(helpers.WikiTestCase):
    def setUp(self):
        super().setUp()
        self.write(BETA, beta('Retries, as [alpha explains](what-is-alpha.md#5-how-does-it-work), wait.'))
        manifest.put_narrative(self.root, 'how-does-beta-work', 'technical_brief_overview', ['leaf-a'], [], ['alpha-doc'])

    def test_check(self):
        self.assertEqual(xrefs.check(self.root, BETA, helpers.read(self.root, BETA)), [])
        text = beta('See [alpha](what-is-alpha.md#9-how-does-it-work), [nothing](what-is-alpha.md#9-nope), [gone](gone.md#x), '
                    '[a source](../sources/alpha-doc.md#details) and [itself](how-does-beta-work.md#9-nope).\n\n```text\n[x](what-is-alpha.md#9-nope)\n```')
        found = xrefs.check(self.root, BETA, text)
        self.assertEqual([f[1] for f in found], ['NARRATIVE_ANCHOR', 'NARRATIVE_ANCHOR'])
        self.assertIn('it is #5-how-does-it-work now', found[0][3])
        self.assertNotIn('now', found[1][3])

    def test_repair(self):
        text, n = xrefs.repair(self.root, BETA, beta('See [alpha](what-is-alpha.md#9-how-does-it-work), [here](what-is-alpha.md#9-nope).'))
        self.assertEqual(n, 1)
        self.assertIn('[alpha](what-is-alpha.md#5-how-does-it-work), [here](what-is-alpha.md#9-nope)', text)
        self.assertEqual(xrefs.repair(self.root, BETA, text)[1], 0)

    def test_check_all_and_tools(self):
        self.assertEqual(xrefs.check_all(self.root), [])
        self.write(BETA, beta('See [alpha](what-is-alpha.md#9-how-does-it-work).'))
        self.assertEqual([f[1] for f in xrefs.check_all(self.root)], ['NARRATIVE_ANCHOR'])
        self.assertIn('NARRATIVE_ANCHOR', helpers.run('wiki-check.py', ['--root', self.root]).out)
        self.assertEqual(xrefs.check_all(self.root, fix=True), [])
        self.assertIn('#5-how-does-it-work', helpers.read(self.root, BETA))
        self.write(BETA, beta('See [alpha](what-is-alpha.md#9-how-does-it-work).'))
        self.assertIn('repaired 1 link(s)', helpers.run('finish-narrative.py', ['how-does-beta-work', '--root', self.root]).out)
        os.remove(os.path.join(self.root, BETA))
        self.assertEqual(xrefs.check_all(self.root), [])  # a recorded narrative whose file is gone is wiki-check's NARRATIVE_MISSING


if __name__ == '__main__':
    unittest.main()
