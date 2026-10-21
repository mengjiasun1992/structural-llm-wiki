"""Tests for lib/citations.py."""

import unittest

import helpers
from lib import citations


def codes(text):
    return [(c, n) for _, c, n, _ in citations.check(text)]


def doc(body, listing):
    return f'# Q?\n\n## 1. Body\n\n{body}\n\n## 2. References\n\n### 2.1 Citations\n\n{listing}\n'


A = '../sources/a.md#x'
B = '../sources/b-doc.md#y'


class Check(unittest.TestCase):
    def test_the_fixture_narrative(self):
        self.assertEqual(citations.check(helpers.narrative_text()), [])

    def test_matching_citations_pass(self):
        text = doc(f'One. [\\[1\\]]({A}) Two. [\\[2\\]]({B}) Again. [\\[1\\]]({A})\n\n[\\[2\\]]({B}) at a line start.',
                   f'1. [a]({A})\n2. [b]({B})')
        self.assertEqual(codes(text), [])
        self.assertEqual([(c.n, c.slug) for c in citations.cites(text)], [(1, 'a'), (2, 'b-doc'), (1, 'a'), (2, 'b-doc')])

    def test_problems(self):
        self.assertEqual(codes(doc(f'No space.[\\[1\\]]({A})', f'1. [a]({A})')), [('CITATION_SPACE', 5)])
        self.assertEqual(codes(doc('Web. [\\[1\\]](https://e.com)', '1. [e](https://e.com)')), [('CITATION_TARGET', 5)])
        self.assertEqual(codes(doc(f'One. [\\[1\\]]({A})', '')), [('CITATION_UNLISTED', 5)])
        self.assertEqual(codes(doc(f'One. [\\[1\\]]({A})', f'1. [b]({B})')), [('CITATION_MISMATCH', 5)])
        self.assertEqual(codes(doc(f'Two first. [\\[2\\]]({B}) then [\\[1\\]]({A})', f'1. [a]({A})\n2. [b]({B})')), [('CITATION_ORDER', 5)])
        self.assertEqual(codes(doc(f'Skips. [\\[2\\]]({B})', f'2. [b]({B})')), [('CITATION_ORDER', 5)])
        self.assertEqual(codes(doc(f'One. [\\[1\\]]({A})', f'1. [a]({A})\n2. [b]({B})')), [('CITATION_UNUSED', 12)])

    def test_code_and_the_list_itself_are_not_citations(self):
        text = doc(f'```text\n[\\[1\\]]({A})\n```', f'1. [a]({A}) [\\[1\\]]({A})')
        self.assertEqual(citations.cites(text), [])
        self.assertEqual(codes(text), [('CITATION_UNUSED', 13)])

    def test_no_citations_list(self):
        self.assertEqual(citations.listed('# Q\n\nText.\n'), {})
        self.assertEqual(codes(f'# Q\n\nOne. [\\[1\\]]({A})\n'), [('CITATION_UNLISTED', 3)])
        self.assertIsNone(citations.Cite(0, 1, 'https://e.com', True).slug)


if __name__ == '__main__':
    unittest.main()
