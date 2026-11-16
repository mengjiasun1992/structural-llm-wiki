"""Tests for lib/annotations.py, readers' annotations (design doc §4.10.1), and how the scripts handle them."""

import json
import os
import unittest
from unittest import mock

import helpers
from sllmwiki.lib import annotations, book, config, narrativecheck

ROW = f'| **{annotations.TERM}** | x |\n'
CITE = '[\\[1\\]](../sources/alpha-doc.md#details)'
NEW = '> [* 2026-11-16 mengjiasun1992] It reads like if-blocks.'
OLD = '> [* 2026-10-01 alice] An older view.'


def doc(body, terms=ROW, after='## 3. Next\n\nMore.\n'):
    """Terminology's rows end on line 7 with ROW (6 without); the body starts on line 11 (10 without)."""
    return (f'# Q\n\n## 1. Terminology\n\n| Term | Definition |\n|---|---|\n{terms}\n'
            f'## 2. Body\n\n{body}\n\n{after}\n## 4. References\n\n### 4.1 Citations\n\n## 5. Metadata\n')


class Check(unittest.TestCase):
    def codes(self, text, on=True):
        return [(c, n) for _, c, n, _ in annotations.check(text, on)]

    def test_at_a_sections_end(self):
        self.assertEqual(self.codes(doc(f'Text. {CITE}\n\n{NEW}')), [])
        self.assertEqual(self.codes(doc(f'Text.\n\n{NEW}\n> It goes on here.\n\n{OLD}')), [])  # newest first, a block of several lines
        self.assertEqual(self.codes(doc(f'Text.\n\n{NEW}', after='### 2.1 Part\n\nMore.\n')), [])  # before the first subsection
        found = annotations.annotations(doc(f'Text.\n\n{NEW}\n> It goes on here.\n\n{OLD}'))
        self.assertEqual([(a.date, a.user, a.last - a.line) for a in found], [('2026-11-16', 'mengjiasun1992', 1), ('2026-10-01', 'alice', 0)])

    def test_off_by_default(self):
        self.assertEqual(self.codes(doc(f'Text.\n\n{NEW}'), on=False), [('ANNOTATION_OFF', 13)])
        self.assertEqual(self.codes(doc('Text, [**bold**], [*] and [*sic*] are no annotations.'), on=False), [])
        self.assertEqual(self.codes(doc('Text, [**bold**], [*] and [*sic*] are no annotations.')), [])
        self.assertFalse(config.Config().settings['reader_annotations'])

    def test_format_and_inline(self):
        self.assertEqual(self.codes(doc('Text.\n\n> [* 2026-11-16 mengjia sun] Two words.')), [('ANNOTATION_FORMAT', 13)])
        self.assertEqual(self.codes(doc('Text.\n\n> [* 2026-13-40 alice] No such day.')), [('ANNOTATION_FORMAT', 13)])
        self.assertEqual(self.codes(doc('Text.\n\n> [*2026-11-16 alice] No space.')), [('ANNOTATION_FORMAT', 13)])
        self.assertEqual(self.codes(doc('Text.\n\n> [*alice 2026-11-16] The old order.')), [('ANNOTATION_FORMAT', 13)])
        self.assertEqual(self.codes(doc('Text, as [* 2026-11-16 alice] said.')), [('ANNOTATION_INLINE', 11)])
        self.assertEqual(self.codes(doc('Text.\n\n> Quoted first, [* 2026-11-16 alice] then.')), [('ANNOTATION_INLINE', 13)])
        self.assertEqual(self.codes(doc('`[* 2026-11-16 alice]` in code is fine.')), [])

    def test_placement_order_and_mixing(self):
        self.assertEqual(self.codes(doc(f'{NEW}\n\nText after it.')), [('ANNOTATION_PLACEMENT', 11)])
        self.assertEqual(self.codes(doc(f'Text.\n\n{OLD}\n\n{NEW}')), [('ANNOTATION_ORDER', 15)])
        self.assertEqual(self.codes(doc(f'Text.\n\n{NEW} Cited {CITE}.')), [('ANNOTATION_MIXED', 13)])
        self.assertEqual(self.codes(doc('Text.\n\n> [* 2026-11-16 alice] Mine. [→]')), [('ANNOTATION_MIXED', 13)])
        text = doc('Text.').replace('## 5. Metadata\n', f'## 5. Metadata\n\n{NEW}\n')
        self.assertEqual(self.codes(text), [('ANNOTATION_PLACEMENT', 23)])

    def test_defined(self):
        self.assertEqual(self.codes(doc(f'Text.\n\n{NEW}', terms='')), [('ANNOTATION_UNDEFINED', 12)])
        added, n = annotations.add_row(doc(f'Text.\n\n{NEW}', terms=''))
        self.assertEqual(n, 1)
        self.assertEqual(self.codes(added), [])
        self.assertEqual(annotations.add_row(added), (added, 0))
        self.assertEqual(annotations.add_row(doc('None.', terms='')), (doc('None.', terms=''), 0))

    def test_the_budget_leaves_them_out(self):
        text = doc(f'Text.\n\n{NEW}\n> ' + 'word ' * 50)
        self.assertEqual(narrativecheck.words(annotations.without(text).split('\n')), narrativecheck.words(doc('Text.').split('\n')))

    def test_the_books_glossary_leaves_the_row_out(self):
        text = doc('Text.', terms=f'| **Retry** | Sending again. |\n{ROW}')
        self.assertEqual(book.terms(text), [('**Retry**', 'Sending again.')])


class Scripts(helpers.WikiTestCase):
    NARRATIVE = 'sllmwiki/narratives/what-is-alpha.md'

    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ, {'CLAUDE_CODE_SESSION_ID': ''})
        env.start()
        self.addCleanup(env.stop)

    def test_finish_defines_them_when_on(self):
        self.write('sllmwiki/Config.toml', '[structural-llm-wiki-settings]\nreader_annotations = true\n')
        self.write(self.NARRATIVE, helpers.narrative_text(extra='\n> [* 2026-11-16 alice] Like a backoff timer.\n'))
        r = helpers.run('finish-narrative.py', ['what-is-alpha', '--json', '--root', self.root])
        self.assertEqual(r.code, 0, r.out)
        self.assertIn('defined readers\' annotations in Terminology', json.loads(r.out)['done'])
        out = self.read(self.NARRATIVE)
        self.assertIn('> [* 2026-11-16 alice] Like a backoff timer.', out)
        self.assertIn(f'| **{annotations.TERM}** |', out)

    def test_refused_when_off(self):
        self.write(self.NARRATIVE, helpers.narrative_text(extra='\n> [* 2026-11-16 alice] Like a backoff timer.\n'))
        r = helpers.run('narrative-format.py', [self.NARRATIVE, '--json'], cwd=self.root)
        self.assertIn('ANNOTATION_OFF', r.out)


if __name__ == '__main__':
    unittest.main()
