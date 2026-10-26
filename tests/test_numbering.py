"""Tests for lib/numbering.py: heading numbers, anchors and sections."""

import unittest

import helpers  # noqa: F401  (puts the scripts on the path)
from lib import numbering as nb

DOC = '''# What is X?

## 1. Abstract

Text.

## 2. Terminology

### 2.1 Terms

#### 2.1.1 Detail

## 3. How does it work?

```text
## Not a heading
```

### 3.1 Flow

## 4. Metadata
'''


class Numbers(unittest.TestCase):
    def test_a_numbered_document_passes(self):
        self.assertEqual(nb.check(DOC), [])
        self.assertEqual(nb.renumber(DOC), (DOC, 0))

    def test_missing_and_wrong_numbers(self):
        text = '# T\n\n## Abstract\n\n## 3. Terms\n\n### 2.5 Sub\n\n##### Deep, not numbered\n'
        self.assertEqual([(c, n) for _, c, n, _ in nb.check(text)], [('HEADING_UNNUMBERED', 3), ('HEADING_NUMBER', 5), ('HEADING_NUMBER', 7)])
        fixed, changed = nb.renumber(text)
        self.assertEqual(changed, 3)
        self.assertEqual(fixed, '# T\n\n## 1. Abstract\n\n## 2. Terms\n\n### 2.1 Sub\n\n##### Deep, not numbered\n')
        self.assertEqual(nb.check(fixed), [])

    def test_counters_reset_under_a_new_parent(self):
        text = '## A\n### B\n#### C\n#### D\n### E\n## F\n#### G\n'
        fixed, _ = nb.renumber(text)
        self.assertEqual(fixed, '## 1. A\n### 1.1 B\n#### 1.1.1 C\n#### 1.1.2 D\n### 1.2 E\n## 2. F\n#### 2.0.1 G\n')

    def test_split_number(self):
        self.assertEqual(nb.split_number('5.1 Why'), ('5.1', 'Why'))
        self.assertEqual(nb.split_number('1. Abstract'), ('1', 'Abstract'))
        self.assertEqual(nb.split_number('2026 in review'), ('2026', 'in review'))  # a number is a number
        self.assertEqual(nb.split_number('Why'), (None, 'Why'))

    def test_headings_skip_code_and_closing_hashes(self):
        heads = nb.headings('## Title ##\n\n```\n## code\n```\n\n#\n')
        self.assertEqual([(h.level, h.title) for h in heads], [(2, 'Title'), (1, '')])


class Anchors(unittest.TestCase):
    def test_github_anchors(self):
        cases = {
            '1. Abstract': '1-abstract',
            '5.1 North star overview': '51-north-star-overview',
            'How does it work?': 'how-does-it-work',
            'The `fetch` step and [links](x.md)': 'the-fetch-step-and-links',
            '**Bold** and _emphasis_ but snake_case': 'bold-and-emphasis-but-snake_case',
            'Sets {a, b\\}': 'sets-a-b',
            'Ünïcode — dash': 'ünïcode--dash',
            'Page 3': 'page-3',
        }
        for text, want in cases.items():
            self.assertEqual(nb.anchor(text), want, text)

    def test_repeated_anchors(self):
        self.assertEqual(list(nb.anchors('## Notes\n## Notes\n## Notes\n')), ['notes', 'notes-1', 'notes-2'])


class Sections(unittest.TestCase):
    def test_by_anchor_or_title(self):
        lines = DOC.split('\n')
        start, end = nb.section(DOC, '2-terminology')
        self.assertEqual((lines[start], lines[end]), ('## 2. Terminology', '## 3. How does it work?'))
        self.assertEqual(nb.section(DOC, 'terms'), nb.section(DOC, '21-terms'))
        start, end = nb.section(DOC, 'Metadata')
        self.assertEqual((lines[start], end), ('## 4. Metadata', len(lines)))
        self.assertIsNone(nb.section(DOC, 'nothing'))


if __name__ == '__main__':
    unittest.main()
