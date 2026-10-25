"""Tests for lib/metadata.py."""

import unittest

import helpers
from lib import metadata

DOC = '''# What is X?

## 1. Abstract

First paragraph
on two lines.

Second.

## 2. Metadata

- **Version:** 1.1
- **Template:** concept_brief_overview
- **Created:** 2026-10-01
- **Last modified:** 2026-10-02
- **History:**
  - 1.1 (2026-10-02): Wider scope.
  - 1.0 (2026-10-01): First version.

A note someone left.
'''


class Read(unittest.TestCase):
    def test_title_abstract_and_fields(self):
        self.assertEqual(metadata.title(DOC), 'What is X?')
        self.assertEqual(metadata.abstract(DOC), 'First paragraph on two lines.\n\nSecond.')
        self.assertEqual(metadata.read(DOC), {'version': '1.1', 'template': 'concept_brief_overview', 'language': None, 'model': None, 'created': '2026-10-01',
                                              'last_modified': '2026-10-02', 'words': None,
                                              'history': [('1.1', '2026-10-02', 'Wider scope.'), ('1.0', '2026-10-01', 'First version.')],
                                              'plan': []})

    def test_reading_time(self):
        prose = ' '.join(['word'] * 460)
        doc = (f'---\ntags: [a]\n---\n# Q\n\n## 1. Abstract\n\n{prose}\n\n```mermaid\n{prose}\n```\n\n'
               f'## 2. References\n\n{prose}\n\n## 3. Metadata\n\n- **Version:** 1.0\n- **Words:** stale\n')
        n, minutes = metadata.reading(doc)
        self.assertEqual((n, minutes), (463, 2))  # the title, '1. Abstract' and the prose; not code, References or Metadata
        self.assertEqual(metadata.reading_label(doc), '463 (about 2 min)')
        self.assertEqual(metadata.reading('# Q\n\nShort.\n'), (2, 1))  # at least a minute
        self.assertEqual(metadata.reading('# 问\n\n' + '字' * 736 + '\n')[1], 2)  # CJK at 1.6 characters a word
        self.assertEqual(metadata.read(doc)['words'], 'stale')

    def test_missing_parts(self):
        self.assertIsNone(metadata.title('No title\n'))
        self.assertEqual(metadata.abstract('# T\n'), '')
        self.assertEqual(metadata.read('# T\n')['version'], None)
        self.assertEqual(metadata.read('# T\n\n## 1. Metadata\n\n- **Version:**\n- **Other:** x\n')['version'], None)


class Write(unittest.TestCase):
    def test_bump(self):
        self.assertEqual((metadata.bump(None, 'minor'), metadata.bump('1.1', 'minor'), metadata.bump('1.9', 'minor'), metadata.bump('1.4', 'major')),
                         ('1.0', '1.2', '1.10', '2.0'))

    def test_set_fields_and_add_history_keeping_other_lines(self):
        out = metadata.write(DOC, {'version': '1.2', 'last_modified': '2026-10-21'}, ('1.2', '2026-10-21', 'Added retries.'))
        meta = metadata.read(out)
        self.assertEqual((meta['version'], meta['last_modified'], meta['created']), ('1.2', '2026-10-21', '2026-10-01'))
        self.assertEqual(meta['history'][0], ('1.2', '2026-10-21', 'Added retries.'))
        self.assertEqual(len(meta['history']), 3)
        self.assertIn('A note someone left.', out)
        self.assertTrue(out.endswith('A note someone left.\n'))
        self.assertEqual(metadata.write(out, {}), out)  # writing what's there changes nothing

    def test_model_and_reading_plan(self):
        out = metadata.write(DOC, {'model': 'claude-opus-5-5'}, plan=['`a`, in full: high relevance, authority A, 2026-01-01', '`b`, not read: a link'])
        self.assertIn('- **Template:** concept_brief_overview\n- **Model:** claude-opus-5-5\n- **Created:**', out)
        self.assertIn('  - 1.0 (2026-10-01): First version.\n- **Reading plan:**\n  1. `a`, in full: high relevance, authority A, 2026-01-01\n'
                      '  2. `b`, not read: a link\n\nA note someone left.\n', out)
        meta = metadata.read(out)
        self.assertEqual((meta['model'], len(meta['plan']), len(meta['history'])), ('claude-opus-5-5', 2, 2))
        self.assertEqual(metadata.write(out, {}), out)  # the plan is kept unless given
        self.assertEqual(metadata.read(metadata.write(out, {}, plan=['`c`, abstract only: low relevance']))['plan'], ['`c`, abstract only: low relevance'])

    def test_a_section_after_metadata_is_kept(self):
        text = '# T\n\n## 1. Metadata\n\n- **Version:** 1.0\n\n## 2. After\n\nKept.\n'
        out = metadata.write(text, {'template': 'survey'})
        self.assertEqual(out, '# T\n\n## 1. Metadata\n\n- **Version:** 1.0\n- **Template:** survey\n\n## 2. After\n\nKept.\n')

    def test_the_fixture_narrative(self):
        out = metadata.write(helpers.narrative_text(), {'version': '1.1'}, ('1.1', '2026-10-21', 'x'))
        self.assertEqual(metadata.read(out)['version'], '1.1')

    def test_no_metadata_section(self):
        with self.assertRaises(ValueError):
            metadata.write('# T\n', {'version': '1.0'})


if __name__ == '__main__':
    unittest.main()
