"""Tests for the narratives a narrative builds on: their pins, and wiki-check's NARRATIVE_BASE_CHANGED."""

import json
import os
import unittest

import helpers
from lib import manifest

BETA = 'sllmwiki/narratives/how-does-beta-work.md'


class BuiltOn(helpers.WikiTestCase):
    def setUp(self):
        super().setUp()
        self.write(BETA, helpers.narrative_text('How does beta work?'))
        self.grades = helpers.write(self.tmp, 'grades.json', json.dumps({'alpha-doc': {'relevance': 'high', 'authority': 'A'},
                                                                         'beta-doc': {'relevance': 'low', 'authority': 'C'},
                                                                         'what-is-alpha': {'relevance': 'high'}}))

    def finish(self, *argv):
        return helpers.run('finish-narrative.py', ['how-does-beta-work', *argv, '--root', self.root])

    def codes(self):
        r = helpers.run('wiki-check.py', ['--json', '--root', self.root])
        return [f['code'] for f in json.loads(r.out)['findings']]

    def test_pinned_and_checked(self):
        r = self.finish('--primary', 'leaf-a', '--read', 'alpha-doc', '--grades', self.grades)
        self.assertEqual(r.code, 0, r.out + r.err)
        entry = manifest.load(self.root, 'narratives')['how-does-beta-work']
        alpha = helpers.read(self.root, 'sllmwiki/narratives/what-is-alpha.md')
        self.assertEqual(entry['built_on'], {'what-is-alpha': manifest.narrative_hash(alpha)})
        self.assertNotIn('NARRATIVE_BASE_CHANGED', self.codes())
        self.write('sllmwiki/narratives/what-is-alpha.md', alpha.replace('- **Last modified:** 2026-10-02', '- **Last modified:** 2026-11-01'))
        self.assertNotIn('NARRATIVE_BASE_CHANGED', self.codes())  # new dates alone aren't a change
        self.write('sllmwiki/narratives/what-is-alpha.md', alpha.replace('Requests fail, and', 'Requests often fail, and'))
        self.assertIn('NARRATIVE_BASE_CHANGED', self.codes())
        self.assertEqual(self.finish().code, 0)  # finishing again re-pins what it builds on
        self.assertNotIn('NARRATIVE_BASE_CHANGED', self.codes())
        os.remove(os.path.join(self.root, 'sllmwiki/narratives/what-is-alpha.md'))
        self.assertIn('NARRATIVE_BASE_CHANGED', self.codes())
        self.assertEqual(manifest.narrative_pins(self.root, ['what-is-alpha']), {})

    def test_nothing_built_on(self):
        self.assertEqual(self.finish('--primary', 'leaf-a', '--read', 'alpha-doc').code, 0)
        self.assertNotIn('built_on', manifest.load(self.root, 'narratives')['how-does-beta-work'])
        self.assertEqual(manifest.narrative_hash('# Q\n\nNo metadata.\n'), manifest.narrative_hash('# Q\n\nNo metadata.\n'))


if __name__ == '__main__':
    unittest.main()
