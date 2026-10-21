"""Tests for lib/markers.py and scripts/finish-narrative.py."""

import json
import unittest

import helpers
from lib import manifest, markers, metadata

NARRATIVE = 'sllmwiki/narratives/what-is-alpha.md'
R, G = '[sllmwiki_reasoning]', '[sllmwiki_gap]'
CITE = '[\\[1\\]](../sources/alpha-doc.md#details)'


def doc(body, terms=''):
    return f'# Q\n\n## 1. Terminology\n\n| Term | Definition |\n|---|---|\n{terms}\n## 2. Body\n\n{body}\n'


class Markers(unittest.TestCase):
    def codes(self, text, on=True):
        return [(c, n) for _, c, n, _ in markers.check(text, on)]

    def test_placement(self):
        defined = f'| **{R}** | x |\n| **{G}** | y |\n'
        for body in (f'{R} Mine.', f'Cited. {CITE} {R} Mine.', f'- {R} In a list.', f'1. {G} Unknown.', f'| a | {R} In a table. |',
                     f'> {R} Quoted.', f'Two: {R} after a colon.'):
            self.assertEqual(self.codes(doc(body, defined)), [], body)
        self.assertEqual(self.codes(doc(f'In the {R} middle.', defined)), [('MARKER_PLACEMENT', 12)])
        self.assertEqual(self.codes(doc(f'`{R}` in code is fine.', defined)), [])

    def test_marked_and_cited(self):
        defined = f'| **{R}** | x |\n'
        self.assertEqual(self.codes(doc(f'{R} Mine, cited. {CITE}', defined)), [('MARKER_AND_CITATION', 11)])
        self.assertEqual(self.codes(doc(f'{R} Mine {CITE} inline.', defined)), [('MARKER_AND_CITATION', 11)])
        self.assertEqual(self.codes(doc(f'{R} Mine. Then cited. {CITE}', defined)), [])

    def test_undefined_and_off(self):
        self.assertEqual(self.codes(doc(f'{G} Unknown.')), [('MARKER_UNDEFINED', 10)])
        self.assertEqual(self.codes(doc(f'{G} Unknown.'), on=False), [('MARKER_OFF', 10)])
        self.assertEqual(self.codes(doc('No markers.'), on=False), [])

    def test_add_rows(self):
        text, n = markers.add_rows(doc(f'{R} Mine. {G} Unknown.'))
        self.assertEqual(n, 2)
        self.assertIn(f'| **{R}** | {markers.MARKERS[R]} |\n| **{G}** |', text)
        self.assertEqual(markers.add_rows(text), (text, 0))
        bare = '# Q\n\n## 1. Terminology\n\n## 2. Body\n\n' + f'{R} Mine.\n'
        text, n = markers.add_rows(bare)
        self.assertEqual(n, 1)
        self.assertIn('## 1. Terminology\n\n| Term | Definition |\n|---|---|\n| **[sllmwiki_reasoning]**', text)
        self.assertEqual(markers.add_rows('# Q\n\nNo terminology. ' + R), ('# Q\n\nNo terminology. ' + R, 0))


class Finish(helpers.WikiTestCase):
    def finish(self, *argv):
        return helpers.run('finish-narrative.py', [*argv, '--root', self.root])

    def test_a_new_narrative(self):
        text = helpers.narrative_text('How does beta caching work?', cites=(('beta-doc', 'beta'),),
                                      extra=f'\n{R} Caching suits read-heavy loads.\n')
        text = text.replace('## 3. Background', '## Background').replace('- **Version:** 1.0\n', '').replace(
            '- **Created:** 2026-10-01\n', '').replace('- **History:**\n  - 1.0 (2026-10-01): First version.\n', '')
        self.write('sllmwiki/narratives/beta-caching.md', text)
        r = self.finish('beta-caching')
        self.assertEqual(r.code, 1)
        self.assertIn('is new: pass --primary', r.err)
        r = self.finish('beta-caching', '--primary', 'leaf-b', '--supporting', 'leaf-a', '--read', 'beta-doc', '--json')
        self.assertEqual(r.code, 0, r.out)
        done = json.loads(r.out)['done']
        self.assertTrue(any(d.startswith('numbered') for d in done))
        self.assertIn('defined 1 marker(s) in Terminology', done)
        out = self.read('sllmwiki/narratives/beta-caching.md')
        meta = metadata.read(out)
        self.assertEqual((meta['version'], meta['history'][0][2]), ('1.0', 'First version.'))
        self.assertIn('## 3. Background', out)
        entry = manifest.load(self.root, 'narratives')['beta-caching']
        self.assertEqual((entry['tags'], list(entry['read'])), ({'primary': ['leaf-b'], 'supporting': ['leaf-a']}, ['beta-doc']))

    def test_rerun_and_bump(self):
        r = self.finish('what-is-alpha')
        self.assertEqual(r.code, 0, r.out)
        self.assertIn('finish-narrative: done, no errors', r.out)
        self.assertEqual(metadata.read(self.read(NARRATIVE))['version'], '1.0')
        r = self.finish('what-is-alpha', '--bump', 'minor', '--note', 'Added the jitter.')
        self.assertEqual(r.code, 0, r.out)
        meta = metadata.read(self.read(NARRATIVE))
        self.assertEqual((meta['version'], meta['history'][0][1:], len(meta['history'])), ('1.1', (meta['last_modified'], 'Added the jitter.'), 2))

    def test_a_narrative_without_history_gets_its_first_entry(self):
        self.write(NARRATIVE, helpers.narrative_text().replace('- **History:**\n  - 1.0 (2026-10-01): First version.\n', ''))
        self.assertEqual(self.finish('what-is-alpha').code, 0)
        self.assertEqual(metadata.read(self.read(NARRATIVE))['history'], [('1.0', '2026-10-01', 'First version.')])

    def test_errors_left_are_reported(self):
        self.write(NARRATIVE, helpers.narrative_text().replace('Requests fail', '<The problem X solves> Requests fail'))
        r = self.finish('what-is-alpha')
        self.assertEqual(r.code, 1)
        self.assertIn('PLACEHOLDER', r.out)
        self.assertIn('1 error(s) left', r.out)

    def test_refusals(self):
        self.assertIn('--bump needs --note', self.finish('what-is-alpha', '--bump', 'minor').err)
        self.assertIn('no narrative', self.finish('nope').err)
        self.write(NARRATIVE, helpers.narrative_text().replace('technical_brief_overview', 'runbook'))
        self.assertIn('Metadata names no template', self.finish('what-is-alpha').err)
        self.write(NARRATIVE, helpers.narrative_text().replace('- **Template:** technical_brief_overview\n', '')
                   .replace('## 8. Metadata', '## 8. Notes').replace('## 7. References', '## 7. References'))
        self.assertIn('Metadata names no template', self.finish('what-is-alpha').err)
        self.write(NARRATIVE, helpers.narrative_text())
        r = self.finish('what-is-alpha', '--primary', 'no-such-tag')
        self.assertIn('no such tag(s): no-such-tag', r.err)
        self.write('Config.toml', '[structural-llm-wiki-settings]\nmarkers = 1\n')
        self.assertIn('Config.toml is invalid', self.finish('what-is-alpha').err)

    def test_markers_off_adds_no_rows(self):
        self.write('Config.toml', '[structural-llm-wiki-settings]\nmarkers = false\n')
        self.write(NARRATIVE, helpers.narrative_text(extra=f'\n{R} Mine.\n'))
        r = self.finish('what-is-alpha')
        self.assertEqual(r.code, 1)
        self.assertIn('MARKER_OFF', r.out)
        self.assertNotIn(markers.MARKERS[R], self.read(NARRATIVE))



if __name__ == '__main__':
    unittest.main()
