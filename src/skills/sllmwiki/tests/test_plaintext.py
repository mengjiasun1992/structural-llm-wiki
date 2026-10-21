"""Tests for lib/plaintext.py, and line ranges in links and section reads."""

import unittest

import helpers
from lib import mdlinks, plaintext, search

RFC = '''Network Working Group                                         A. Author
Request for Comments: 9999                                     June 2026


                        A Small Standard

Status of This Memo

   This is a test.

1.  Introduction

   Retries need a budget.
   ``` backticks in the text ```



Author                       Standards Track                    [Page 1]
\f
RFC 9999                   A Small Standard                   June 2026


2.  The Algorithm

   (2.1) Count requests.

2.1.  Details

   Not a section: 3 widgets
   10 Gbps links

Appendix A.  Rationale

   Because.
'''


class Standard(unittest.TestCase):
    def test_numbered_sections_become_headings(self):
        out = plaintext.standard(RFC)
        self.assertEqual([line for line in out.split('\n') if line.startswith('#')],
                         ['## 1. Introduction', '## 2. The Algorithm', '### 2.1. Details', '## Appendix A. Rationale'])
        self.assertTrue(out.startswith('```text\nNetwork Working Group'))
        self.assertIn('## 1. Introduction\n\n````text\n   Retries need a budget.\n   ``` backticks in the text ```\n````', out)
        self.assertNotIn('[Page 1]', out)
        self.assertNotIn('RFC 9999                   A Small Standard', out)
        self.assertIn('   (2.1) Count requests.', out)

    def test_text_without_numbered_sections_is_left_alone(self):
        self.assertIsNone(plaintext.standard('Notes\n\n1.  Only one\n\n2.  Or two\n'))


class Code(unittest.TestCase):
    TEXT = 'def ewma(prev, x, a):\n    return a * x + (1 - a) * prev\n\n# done\n'

    def test_code_keeps_its_lines(self):
        out = plaintext.code(self.TEXT, 'https://e.com/ewma.py?raw=1')
        self.assertTrue(out.startswith('```python\ndef ewma'))
        self.assertEqual(plaintext.code('x = "```"', 'a.unknown'), '````\nx = "```"\n````\n')
        saved = out + '\n<!-- sllmwiki:original-source -->\n## Original source\n'
        self.assertEqual(plaintext.lines(saved, 'L2'), ['    return a * x + (1 - a) * prev'])
        self.assertEqual(plaintext.lines(saved, 'L1-L2'), ['def ewma(prev, x, a):', '    return a * x + (1 - a) * prev'])
        for bad in ('L5', 'L2-L1', 'L0', 'section', None):
            self.assertIsNone(plaintext.lines(saved, bad), bad)
        self.assertIsNone(plaintext.lines('# A page\n\n```\ncode\n```\n', 'L1'))  # not a code source


class Links(helpers.WikiTestCase):
    def test_line_ranges_in_links_and_section_reads(self):
        self.write('sllmwiki/sources/alpha-code.md', plaintext.code(Code.TEXT, 'ewma.py'))
        rel = 'sllmwiki/narratives/x.md'
        self.assertIsNone(mdlinks.problem(self.root, rel, '../sources/alpha-code.md#L1-L2'))
        self.assertIn('has no code lines #L9', mdlinks.problem(self.root, rel, '../sources/alpha-code.md#L9'))
        self.assertIn('has no section #nope', mdlinks.problem(self.root, rel, '../sources/alpha-code.md#nope'))
        text = self.read('sllmwiki/sources/alpha-code.md')
        self.assertEqual(search.section(text, 'L2-L4'), '2:     return a * x + (1 - a) * prev\n3: \n4: # done\n')


if __name__ == '__main__':
    unittest.main()
