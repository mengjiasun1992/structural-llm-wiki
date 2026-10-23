"""Tests for lib/quotes.py: quotations found in the section they cite, and not too long."""

import unittest

import helpers
from lib import quotes

CITE = '[\\[1\\]](../sources/alpha-doc.md#details)'


class Quotes(helpers.WikiTestCase):
    def setUp(self):
        super().setUp()
        self.write('sllmwiki/sources/alpha-paper.md', '# Paper\n\n## Page 2\n\nThe architecture must pre-\nvent cascading ‘‘failures’’ — always, with $\\\\alpha$ small, $\\\\frac12$.\n')

    def codes(self, body, max_words=50):
        text = helpers.narrative_text(extra='\n' + body + '\n')
        return [(code, line) for _, code, line, _ in quotes.check(self.root, 'sllmwiki/narratives/what-is-alpha.md', text, max_words)]

    def test_found_word_for_word_or_cut(self):
        for body in (f'They say "each retry waits twice as long as the last." {CITE}',
                     f'They say “Each **retry** waits … as the last”. {CITE}',
                     '"The architecture must prevent cascading \'failures\' - always, with $\\alpha$ small, $\\frac12$" [\\[2\\]](../sources/alpha-paper.md#page-2)',
                     f'A "named term" here, and "each retry waits" there. {CITE}',
                     f'It "waits twice" ({CITE}).',
                     'A link that\'s gone: "no such words anywhere" [\\[3\\]](../sources/gone.md#x)',
                     'A whole file: "alpha systems retry failed requests" [\\[4\\]](../sources/alpha-doc.md)'):
            self.assertEqual(self.codes(body), [], body)

    def test_not_found(self):
        self.assertEqual(self.codes(f'They say "each retry waits three times as long." {CITE}'), [('QUOTE_NOT_FOUND', 32)])
        self.assertEqual(self.codes(f'In order: "as the last … each retry waits" {CITE}'), [('QUOTE_NOT_FOUND', 32)])
        self.assertEqual(self.codes(f'Wrong section: "alpha systems retry failed requests" {CITE}'), [('QUOTE_NOT_FOUND', 32)])

    def test_too_long_even_uncited(self):
        long = ' '.join(['word'] * 12)
        self.assertEqual(self.codes(f'"{long}"', max_words=10), [('QUOTE_TOO_LONG', 32)])
        self.assertEqual(self.codes(f'`"{long}"` in code is not a quotation', max_words=10), [])


if __name__ == '__main__':
    unittest.main()
