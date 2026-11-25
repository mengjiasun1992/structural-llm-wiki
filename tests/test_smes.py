"""Tests for lib/smes.py: SMEs say who to ask, never who is best."""

import unittest

import helpers  # noqa: F401  (puts the package on the path)
from sllmwiki.lib import smes

RANKED = [  # (entry, what is reported)
    ('@ann: the best person for retries', '"best"'),
    ('@ann: strongest evidence of all', '"strongest"'),
    ('@eve: top contributor', '"top"'),
    ('@h: most knowledgeable about caching', '"most knowledgeable"'),
    ('@f: CODEOWNERS for /src/; ranked first', '"ranked"'),
    ('@cy: score 8.2, 12 commits', '"score"'),
    ('@cy: rated highly', '"rated"'),
    ('@dee: 9/10', '"9/10"'),
    ('@dee: knows it better than anyone', '"better than"'),
    ('@g: the #1 expert', '"#1"'),
    ('1. @bob: 3 commits', 'a numbered list'),
    ('- 2) @bob: 3 commits', 'a numbered list'),
]
FINE = [
    '@ann: wrote the alpha doc',
    '@g: 4 commits, the last on 2026-10-01; last changed 1,240 of 3,000 current lines',
    '@g: reviewed the change on 2026/10/01',
    '@eve: top-level owner; ask: what is the best retry limit?',  # the question may say best
    '@i: led the rewrite; question: which backoff is better than linear?',
    '@j: wrote `best_effort()`',  # code
    'Ann Lee: CODEOWNERS for /src/',
]


class Entries(unittest.TestCase):
    def test_ranked(self):
        for entry, what in RANKED:
            with self.subTest(entry=entry):
                self.assertEqual(smes.problem(entry), what)
                self.assertIn('never who is best', smes.check_entries([entry])[0][1])

    def test_fine(self):
        for entry in FINE:
            with self.subTest(entry=entry):
                self.assertIsNone(smes.problem(entry))
        self.assertEqual(smes.check_entries(FINE), [])


class Narrative(unittest.TestCase):
    def test_only_the_smes_section(self):
        text = ('# Q\n\n## Answer\n\nThe best retry limit is 3.\n\n1. First step.\n\n'
                '## SMEs\n\n- @ann: wrote the alpha doc; ask: why 3?\n- @bob: the top expert\n\n1. @cy: 2 commits\n\n'
                '### More\n\n- @dee: ranked second\n\n## References\n\n1. [a](a.md)\n')
        self.assertEqual([(f[1], f[2]) for f in smes.check(text)], [('SMES_RANKED', 12), ('SMES_RANKED', 14), ('SMES_RANKED', 18)])

    def test_numbered_heading(self):
        self.assertEqual(len(smes.check('# Q\n\n## 5. SMEs\n\n- @a: best\n')), 1)

    def test_none(self):
        self.assertEqual(smes.check('# Q\n\n## Answer\n\nThe best.\n'), [])


if __name__ == '__main__':
    unittest.main()
