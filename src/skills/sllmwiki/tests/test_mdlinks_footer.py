"""Tests for lib/mdlinks.py and lib/footer.py."""

import os
import time
import unittest

import helpers
from lib import footer, mdlinks
from lib.util import source_hash


class Links(helpers.WikiTestCase):
    NARRATIVE = 'sllmwiki/narratives/what-is-alpha.md'

    def test_split_and_resolve(self):
        self.assertEqual(mdlinks.split('../sources/a%20b.md?x=1#sec-1'), ('../sources/a b.md', 'sec-1'))
        self.assertEqual(mdlinks.split('#only'), ('', 'only'))
        self.assertEqual(mdlinks.resolve(self.NARRATIVE, '../sources/a.md'), 'sllmwiki/sources/a.md')
        self.assertIsNone(mdlinks.resolve('a.md', '../../outside.md'))
        self.assertIsNone(mdlinks.resolve('a.md', '..'))

    def test_problems(self):
        self.assertIsNone(mdlinks.problem(self.root, self.NARRATIVE, '../sources/alpha-doc.md#details'))
        self.assertIsNone(mdlinks.problem(self.root, self.NARRATIVE, '#1-abstract'))
        self.assertIn('no such file', mdlinks.problem(self.root, self.NARRATIVE, '../sources/missing.md'))
        self.assertIn('has no section #nope', mdlinks.problem(self.root, self.NARRATIVE, '../sources/alpha-doc.md#nope'))
        self.assertIn('no such file', mdlinks.problem(self.root, self.NARRATIVE, '../../../../outside.md'))

    def test_anchors_follow_edits(self):
        path = 'sllmwiki/sources/alpha-doc.md'
        self.assertIn('details', mdlinks.anchors_of(self.root, path))
        time.sleep(0.01)
        self.write(path, '# Alpha\n\n## Renamed\n')
        os.utime(os.path.join(self.root, path), (time.time() + 5, time.time() + 5))
        self.assertIn('renamed', mdlinks.anchors_of(self.root, path))


class Footer(unittest.TestCase):
    BODY = b'# Doc\n\nText.\n'

    def test_add_read_and_hash(self):
        data = footer.add(self.BODY, 'https://e.com/a', 'CC-BY-4.0', 'https://creativecommons.org/licenses/by/4.0/')
        self.assertTrue(data.startswith(self.BODY))
        self.assertEqual(footer.read(data), {'url': 'https://e.com/a', 'license': 'CC-BY-4.0'})
        self.assertEqual(source_hash(data), source_hash(self.BODY))  # the footer never changes the hash
        again = footer.add(data, 'https://e.com/b', 'unknown')
        self.assertEqual(again.count(b'Original source'), 1)  # replaced, not added twice
        self.assertEqual(footer.read(again), {'url': 'https://e.com/b', 'license': 'unknown'})

    def test_no_footer(self):
        self.assertIsNone(footer.read(self.BODY))

    def test_the_fixture_footer(self):
        self.assertEqual(footer.read((helpers.ALPHA + helpers.FOOTER.format(url='https://x', license='MIT')).encode()),
                         {'url': 'https://x', 'license': 'MIT'})


if __name__ == '__main__':
    unittest.main()
