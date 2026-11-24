"""Tests for citations.renumber, narrative-format --fix-citations and finish-narrative's renumbering: citations
numbered by first use, the Citations list rebuilt to match (issue #190)."""

import unittest

import helpers
from sllmwiki.lib import citations

A, B, C = '../sources/alpha-doc.md#details', '../sources/beta-doc.md#x', '../sources/gamma-doc.md#y'


def cite(n, target):
    return f'[\\[{n}\\]]({target})'


def narrative(body, listing):
    return (f'# Q\n\n## 1. Body\n\n{body}\n\n```text\nkept {cite(9, A)}\n```\n\n## 2. References\n\n### 2.1 Citations\n\n'
            + '\n'.join(listing) + '\n\n## 3. Metadata\n\n- **Version:** 1.0\n')


def problems(text):
    return [f[1] for f in citations.check(text) if f[1].startswith('CITATION')]


class Renumber(unittest.TestCase):
    def test_in_order_of_first_use(self):
        text = narrative(f'Waits double {cite(2, B)}. Alpha {cite(1, A)}, again {cite(2, B)}.',
                         [f'1. [Alpha, details]({A})', f'2. [Beta, x]({B})'])
        self.assertIn('CITATION_ORDER', problems(text))
        fixed, changed, dropped = citations.renumber(text)
        self.assertIn(f'Waits double {cite(1, B)}. Alpha {cite(2, A)}, again {cite(1, B)}.', fixed)
        self.assertIn(f'1. [Beta, x]({B})\n2. [Alpha, details]({A})\n\n## 3. Metadata', fixed)  # labels kept
        self.assertIn(f'kept {cite(9, A)}', fixed)  # code is never touched
        self.assertEqual((changed, dropped), (5, 0))
        self.assertEqual(problems(fixed), [])
        self.assertEqual(citations.renumber(fixed), (fixed, 0, 0))  # a second run changes nothing

    def test_the_body_decides(self):
        # one target under two numbers, a target the list lacks, and an entry no longer cited
        text = narrative(f'One {cite(1, A)}. Same {cite(3, A)}. New {cite(2, C)}.', [f'1. [Alpha]({A})', f'2. [Beta]({B})'])
        fixed, _, dropped = citations.renumber(text)
        self.assertIn(f'One {cite(1, A)}. Same {cite(1, A)}. New {cite(2, C)}.', fixed)
        self.assertIn(f'1. [Alpha]({A})\n2. [gamma-doc: y]({C})\n', fixed)
        self.assertNotIn(B, fixed)
        self.assertEqual(dropped, 1)
        self.assertEqual(problems(fixed), [])

    def test_an_empty_list_and_no_list(self):
        fixed = citations.renumber(narrative(f'Only {cite(4, A)}.', []))[0]
        self.assertIn(f'### 2.1 Citations\n\n1. [alpha-doc: details]({A})\n', fixed)
        self.assertEqual(problems(fixed), [])
        bare = f'# Q\n\nOnly {cite(4, A)}.\n'
        self.assertEqual(citations.renumber(bare), (f'# Q\n\nOnly {cite(1, A)}.\n', 1, 0))
        other = '# Q\n\n## Citations\n\n1. [x](https://example.com/x)\n'
        self.assertEqual(citations.renumber(other)[2], 1)
        self.assertEqual(citations._label('https://example.com/x'), '[https://example.com/x](https://example.com/x)')
        self.assertEqual(citations._label('../sources/alpha-doc.md'), '[alpha-doc](../sources/alpha-doc.md)')


class Commands(helpers.WikiTestCase):
    def setUp(self):
        super().setUp()
        text = helpers.narrative_text(cites=(('alpha-doc', 'details'), ('beta-doc', 'beta')))
        self.swapped = text.replace('[\\[1\\]](../sources/alpha-doc.md', '[\\[9\\]](../sources/alpha-doc.md', 1)
        self.write('sllmwiki/narratives/what-is-alpha.md', self.swapped)

    def test_narrative_format_fix_citations(self):
        path = f'{self.root}/sllmwiki/narratives/what-is-alpha.md'
        r = helpers.run('narrative-format.py', ['--root', self.root, path])
        self.assertIn('CITATION', r.out)
        r = helpers.run('narrative-format.py', ['--root', self.root, '--fix-citations', path])
        self.assertIn('renumbered', r.out)
        self.assertNotIn('CITATION', r.out)
        self.assertNotEqual(helpers.read(self.root, 'sllmwiki/narratives/what-is-alpha.md'), self.swapped)

    def test_finish_narrative_renumbers(self):
        r = helpers.run('finish-narrative.py', ['--root', self.root, 'what-is-alpha'])
        self.assertIn('renumbered', r.out)
        self.assertNotIn('CITATION', r.out)


if __name__ == '__main__':
    unittest.main()
