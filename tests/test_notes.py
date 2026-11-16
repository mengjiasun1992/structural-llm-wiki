"""Tests for lib/notes.py, the owner's notes (design doc §4.10.1), and how the scripts handle them."""

import json
import os
import unittest
from unittest import mock

import helpers
from sllmwiki.lib import book, config, narrativecheck, notes

ROW = f'| **{notes.TERM}** | x |\n'
CITE = '[\\[1\\]](../sources/alpha-doc.md#details)'
NOTE = '> [\\*mengjiasun1992 2026-11-16] It reads like if-blocks.'
OLDER = '> [\\*alice 2026-10-01] An older view.'


def doc(body, terms=ROW, after='## 3. Next\n\nMore.\n'):
    return (f'# Q\n\n## 1. Terminology\n\n| Term | Definition |\n|---|---|\n{terms}\n'
            f'## 2. Body\n\n{body}\n\n{after}\n## 4. References\n\n### 4.1 Citations\n\n## 5. Metadata\n')


class Check(unittest.TestCase):
    def codes(self, text, on=True):
        return [(c, n) for _, c, n, _ in notes.check(text, on)]

    def test_a_note_at_a_sections_end(self):
        self.assertEqual(self.codes(doc(f'Text. {CITE}\n\n{NOTE}')), [])
        self.assertEqual(self.codes(doc(f'Text.\n\n{NOTE}\n> It goes on here.\n\n{OLDER}')), [])  # newest first, a block of several lines
        self.assertEqual(self.codes(doc(f'Text.\n\n{NOTE}', after='### 2.1 Part\n\nMore.\n')), [])  # before the first subsection
        found = notes.notes(doc(f'Text.\n\n{NOTE}\n> It goes on here.\n\n{OLDER}'))
        self.assertEqual([(n.user, n.date, n.last - n.line) for n in found], [('mengjiasun1992', '2026-11-16', 1), ('alice', '2026-10-01', 0)])

    def test_off_by_default(self):
        self.assertEqual(self.codes(doc(f'Text.\n\n{NOTE}'), on=False), [('NOTE_OFF', 13)])
        self.assertEqual(self.codes(doc('Text, [**bold**], [*] and [*sic*] are no notes.'), on=False), [])
        self.assertEqual(self.codes(doc('Text, [**bold**], [*] and [*sic*] are no notes.')), [])
        self.assertFalse(config.Config().settings['owner_notes'])

    def test_format_and_inline(self):
        self.assertEqual(self.codes(doc('Text.\n\n> [\\*mengjia sun 2026-11-16] Two words.')), [('NOTE_FORMAT', 13)])
        self.assertEqual(self.codes(doc('Text.\n\n> [\\*alice 2026-13-40] No such day.')), [('NOTE_FORMAT', 13)])
        self.assertEqual(self.codes(doc('Text, as [\\*alice 2026-11-16] said.')), [('NOTE_INLINE', 11)])
        self.assertEqual(self.codes(doc('Text.\n\n> Quoted first, [\\*alice 2026-11-16] then.')), [('NOTE_INLINE', 13)])
        self.assertEqual(self.codes(doc('Text.\n\n> [*alice 2026-11-16] Typed plain.')), [('NOTE_ESCAPE', 13)])
        self.assertEqual(self.codes(doc('`[*alice 2026-11-16]` in code is fine.')), [])

    def test_placement_order_and_mixing(self):
        self.assertEqual(self.codes(doc(f'{NOTE}\n\nText after it.')), [('NOTE_PLACEMENT', 11)])
        self.assertEqual(self.codes(doc(f'Text.\n\n{OLDER}\n\n{NOTE}')), [('NOTE_ORDER', 15)])
        self.assertEqual(self.codes(doc(f'Text.\n\n{NOTE} Cited {CITE}.')), [('NOTE_MIXED', 13)])
        self.assertEqual(self.codes(doc('Text.\n\n> [\\*alice 2026-11-16] Mine. [→]')), [('NOTE_MIXED', 13)])
        text = doc('Text.').replace('## 5. Metadata\n', f'## 5. Metadata\n\n{NOTE}\n')
        self.assertEqual(self.codes(text), [('NOTE_PLACEMENT', 23)])

    def test_defined(self):
        self.assertEqual(self.codes(doc(f'Text.\n\n{NOTE}', terms='')), [('NOTE_UNDEFINED', 12)])
        added, n = notes.add_row(doc(f'Text.\n\n{NOTE}', terms=''))
        self.assertEqual(n, 1)
        self.assertEqual(self.codes(added), [])
        self.assertEqual(notes.add_row(added), (added, 0))
        self.assertEqual(notes.add_row(doc('No notes.', terms='')), (doc('No notes.', terms=''), 0))

    def test_escape_and_budget(self):
        typed, n = notes.escape(doc('Text.\n\n> [*alice 2026-11-16] Typed plain.'))
        self.assertEqual(n, 1)
        self.assertIn('> [\\*alice 2026-11-16] Typed plain.', typed)
        self.assertEqual(notes.escape(typed), (typed, 0))
        text = doc(f'Text.\n\n{NOTE}\n> ' + 'word ' * 50)
        self.assertEqual(narrativecheck.words(notes.without(text).split('\n')), narrativecheck.words(doc('Text.').split('\n')))

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

    def test_finish_escapes_and_defines_when_on(self):
        self.write('sllmwiki/Config.toml', '[structural-llm-wiki-settings]\nowner_notes = true\n')
        self.write(self.NARRATIVE, helpers.narrative_text(extra='\n> [*alice 2026-11-16] Like a backoff timer.\n'))
        r = helpers.run('finish-narrative.py', ['what-is-alpha', '--json', '--root', self.root])
        self.assertEqual(r.code, 0, r.out)
        done = json.loads(r.out)['done']
        self.assertIn('wrote 1 note marker(s) [*… as [\\*…', done)
        self.assertIn('defined the owner\'s notes in Terminology', done)
        out = self.read(self.NARRATIVE)
        self.assertIn('> [\\*alice 2026-11-16] Like a backoff timer.', out)
        self.assertIn(f'| **{notes.TERM}** |', out)

    def test_a_note_is_refused_when_off(self):
        self.write(self.NARRATIVE, helpers.narrative_text(extra='\n> [\\*alice 2026-11-16] Like a backoff timer.\n'))
        r = helpers.run('narrative-format.py', [self.NARRATIVE, '--json'], cwd=self.root)
        self.assertIn('NOTE_OFF', r.out)


if __name__ == '__main__':
    unittest.main()
