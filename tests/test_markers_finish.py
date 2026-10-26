"""Tests for lib/markers.py and scripts/finish-narrative.py."""

import json
import os
import unittest
from unittest import mock

import helpers
from lib import manifest, markers, metadata

NARRATIVE = 'sllmwiki/narratives/what-is-alpha.md'
R, G = '[→]', '[?]'
CITE = '[\\[1\\]](../sources/alpha-doc.md#details)'
DEFINED = f'| **{R}** | x |\n| **{G}** | y |\n'


def doc(body, terms=''):
    return f'# Q\n\n## 1. Terminology\n\n| Term | Definition |\n|---|---|\n{terms}\n## 2. Body\n\n{body}\n'


class Markers(unittest.TestCase):
    def codes(self, text, on=True):
        return [(c, n) for _, c, n, _ in markers.check(text, on)]

    def test_placement(self):
        for body in (f'Mine. {R}', f'Cited. {CITE} Mine. {R}', f'- In a list {R}', f'1. Unknown? {G}', f'| a | In a table {R} |',
                     f'> Quoted. {R}', f'Mine. {R} Then more.', f'## 3. Applying them {R}', 'A [?](not-a-marker.md) link.'):
            self.assertEqual(self.codes(doc(body, DEFINED)), [], body)
        for body in (f'{R} Before.', f'In the {R} middle.', f'Glued.{R}', f'- {G} Listed first.', f'| a | {R} cell |',
                     f'## 3. Marked {R} too early'):
            self.assertEqual(self.codes(doc(body, DEFINED)), [('MARKER_PLACEMENT', 12)], body)
        self.assertEqual(self.codes(doc(f'`{R}` in code and ${G}$ in math are fine.', DEFINED)), [])

    def test_marked_and_cited(self):
        self.assertEqual(self.codes(doc(f'Mine, cited. {CITE} {R}', DEFINED)), [('MARKER_AND_CITATION', 12)])
        self.assertEqual(self.codes(doc(f'Mine. {R} {CITE}', DEFINED)), [('MARKER_AND_CITATION', 12)])
        self.assertEqual(self.codes(doc(f'Cited. {CITE} Then mine. {R}', DEFINED)), [])
        self.assertEqual(self.codes(doc(f'| Window | None, by design {R} | 10 samples {CITE} |', DEFINED)), [])  # each cell is its own claim
        self.assertEqual(self.codes(doc(f'| Window | None {CITE} {R} | 10 |', DEFINED)), [('MARKER_AND_CITATION', 12)])

    def test_level(self):
        many = '\n'.join(f'Point {n}. {R}' for n in range(markers.LEVEL_HINT))
        self.assertEqual(self.codes(doc(many, DEFINED)), [('MARKER_LEVEL', 10)])
        self.assertEqual(self.codes(doc(many + f'\nCited. {CITE}', DEFINED)), [])

    def test_undefined_old_and_off(self):
        self.assertEqual(self.codes(doc(f'Unknown. {G}')), [('MARKER_UNDEFINED', 10)])
        self.assertEqual(self.codes(doc(f'Unknown. {G}'), on=False), [('MARKER_OFF', 10)])
        self.assertEqual(self.codes(doc('No markers.'), on=False), [])
        self.assertEqual(self.codes(doc('[sllmwiki_reasoning] Old.', DEFINED)), [('MARKER_OLD', 12)])
        self.assertEqual([markers.unmark('Applying them [->]'), markers.unmark('Applying them [→]')], ['Applying them'] * 2)
        self.assertEqual(self.codes(doc('Typed. [->]', DEFINED)), [('MARKER_OLD', 12)])

    def test_migrate(self):
        old = doc('[sllmwiki_reasoning] Mine here. Then cited. ' + CITE + '\n\n1. [sllmwiki_reasoning] What if it fails?\n'
                  '- [sllmwiki_gap] The sources don\'t say\n| a | [sllmwiki_reasoning] Cheap and conservative | c |\n'
                  '[sllmwiki_reasoning] One, `x.` then. Two.', '| **[sllmwiki_reasoning]** | old |\n| **[sllmwiki_gap]** | old |\n')
        text, n = markers.migrate(old)
        self.assertEqual(n, 7)
        for want in (f'Mine here. {R} Then cited.', f'1. What if it fails? {R}', f'- The sources don\'t say {G}',
                     f'| a | Cheap and conservative {R} | c |', f'One, `x.` then. {R} Two.'):
            self.assertIn(want, text)
        self.assertNotIn('sllmwiki_', text)
        text, _ = markers.add_rows(text)
        self.assertEqual(self.codes(text), [])
        self.assertEqual(markers.migrate(text), (text, 0))
        typed, n = markers.migrate(doc('Typed. [->] And `[->]` in code.', '| **[->]** | old |\n'))
        self.assertEqual(n, 2)
        self.assertIn('Typed. [→] And `[->]` in code.', typed)
        self.assertIn('| **[→]** |', typed)

    def test_add_rows(self):
        text, n = markers.add_rows(doc(f'Mine. {R} Unknown. {G}'))
        self.assertEqual(n, 2)
        self.assertIn(f'| **{R}** | {markers.MARKERS[R]} |\n| **{G}** |', text)
        self.assertEqual(markers.add_rows(text), (text, 0))
        bare = '# Q\n\n## 1. Terminology\n\n## 2. Body\n\n' + f'Mine. {R}\n'
        text, n = markers.add_rows(bare)
        self.assertEqual(n, 1)
        self.assertIn('## 1. Terminology\n\n| Term | Definition |\n|---|---|\n| **[→]**', text)
        self.assertEqual(markers.add_rows('# Q\n\nNo terminology. ' + R), ('# Q\n\nNo terminology. ' + R, 0))


class Finish(helpers.WikiTestCase):
    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ, {'CLAUDE_CODE_SESSION_ID': ''})  # never this test session's model
        env.start()
        self.addCleanup(env.stop)

    def finish(self, *argv):
        return helpers.run('finish-narrative.py', [*argv, '--root', self.root])

    def grades(self, data):
        return helpers.write(self.tmp, 'grades.json', json.dumps(data))

    def test_the_reading_plan_and_the_model_are_recorded_and_shown(self):
        g = self.grades({'alpha-doc': {'relevance': 'high', 'authority': 'A'}, 'beta-doc': {'relevance': 'medium', 'authority': 'C'},
                         'elsewhere': {'relevance': 'low', 'authority': 'B'}})
        r = self.finish('what-is-alpha', '--primary', 'leaf-a', '--supporting', 'leaf-b', '--grades', g, '--model', 'claude-opus-5-5',
                        '--bump', 'minor', '--note', 'Read beta too.')
        self.assertEqual(r.code, 0, r.out)
        meta = metadata.read(self.read(NARRATIVE))
        self.assertEqual(meta['model'], 'claude-opus-5-5')
        self.assertEqual(meta['plan'], ['`beta-doc`, in full: medium relevance, authority C, undated',  # the narrative itself isn't background
                                        '`alpha-doc`, in full: high relevance, authority A, 2026-09-01',
                                        '`gamma-link`, not read: a link, no saved copy'])
        entry = manifest.load(self.root, 'narratives')['what-is-alpha']
        self.assertEqual(entry['grades'], {'alpha-doc': {'relevance': 'high', 'authority': 'A'}, 'beta-doc': {'relevance': 'medium', 'authority': 'C'}})
        self.assertEqual(entry['models'], {'1.1': 'claude-opus-5-5'})
        r = self.finish('what-is-alpha')  # a rerun keeps both
        self.assertEqual(r.code, 0, r.out)
        self.assertEqual(manifest.load(self.root, 'narratives')['what-is-alpha'], entry)
        self.assertEqual(len(metadata.read(self.read(NARRATIVE))['plan']), 3)

    def test_the_plan_keeps_the_narratives_read_then(self):
        g = self.grades({'alpha-doc': {'relevance': 'high', 'authority': 'A'}})
        r = helpers.run('reading-plan.py', ['order', '--primary', 'leaf-a', '--grades', g, '--root', self.root])
        self.assertEqual(r.code, 0, r.err)
        self.write('sllmwiki/narratives/later.md', helpers.narrative_text('Later?'))  # written after the plan was made
        self.assertEqual(self.finish('later', '--primary', 'leaf-a', '--read', 'alpha-doc').code, 0)
        self.assertEqual(self.finish('what-is-alpha', '--primary', 'leaf-a', '--grades', g).code, 0)
        self.assertNotIn('`later`', '\n'.join(metadata.read(self.read(NARRATIVE))['plan']))
        os.remove(g + '.plan.json')  # no saved plan: every narrative on the tags, as before
        self.assertEqual(self.finish('what-is-alpha', '--grades', g).code, 0)
        self.assertIn('`later`, in full: existing narrative, background', metadata.read(self.read(NARRATIVE))['plan'])

    def test_the_model_comes_from_the_session(self):
        session = helpers.write(self.tmp, 'claude/projects/-w/s-1.jsonl',
                                json.dumps({'type': 'assistant', 'message': {'model': 'claude-fable-5-1'}}) + '\n')
        self.assertTrue(session)
        with mock.patch.dict(os.environ, {'CLAUDE_CODE_SESSION_ID': 's-1', 'CLAUDE_CONFIG_DIR': os.path.join(self.tmp, 'claude')}):
            self.assertEqual(self.finish('what-is-alpha').code, 0)  # no new version: no model recorded
            self.assertIsNone(metadata.read(self.read(NARRATIVE))['model'])
            self.assertEqual(self.finish('what-is-alpha', '--bump', 'major', '--note', 'Rewritten.').code, 0)
        self.assertEqual(metadata.read(self.read(NARRATIVE))['model'], 'claude-fable-5-1')
        self.assertEqual(manifest.load(self.root, 'narratives')['what-is-alpha']['models'], {'2.0': 'claude-fable-5-1'})

    def test_bad_grades_are_refused(self):
        self.assertIn('can\'t read the grades', self.finish('what-is-alpha', '--grades', '/nope.json').err)
        r = self.finish('what-is-alpha', '--grades', self.grades({'alpha-doc': {'relevance': 'high'}}))
        self.assertEqual(r.code, 1)
        self.assertIn('grade every saved source first: alpha-doc: needs', r.err)

    def test_a_new_narrative(self):
        text = helpers.narrative_text('How does beta caching work?', cites=(('beta-doc', 'beta'),),
                                      extra=f'\nCaching suits read-heavy loads. {R}\n')
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
        from lib import metadata as meta
        self.assertIn(f'- **Words:** {meta.reading_label(out)}\n', out)  # its reading time, which narrative-format keeps an eye on
        stale = out.replace(f'- **Words:** {meta.reading_label(out)}', '- **Words:** 9 (about 1 min)')
        self.write('sllmwiki/narratives/beta-caching.md', stale)
        r = helpers.run('narrative-format.py', ['sllmwiki/narratives/beta-caching.md', '--json'], cwd=self.root)
        self.assertIn('WORDS_OUTDATED', r.out)
        self.write('sllmwiki/narratives/beta-caching.md', out)
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
                   .replace('## 9. Metadata', '## 9. Notes'))
        self.assertIn('Metadata names no template', self.finish('what-is-alpha').err)
        self.write(NARRATIVE, helpers.narrative_text())
        r = self.finish('what-is-alpha', '--primary', 'no-such-tag')
        self.assertIn('no such tag(s): no-such-tag', r.err)
        self.write('sllmwiki/Config.toml', '[structural-llm-wiki-settings]\nmarkers = 1\n')
        self.assertIn('Config.toml is invalid', self.finish('what-is-alpha').err)

    def test_markers_off_adds_no_rows(self):
        self.write('sllmwiki/Config.toml', '[structural-llm-wiki-settings]\nmarkers = false\n')
        self.write(NARRATIVE, helpers.narrative_text(extra=f'\nMine. {R}\n'))
        r = self.finish('what-is-alpha')
        self.assertEqual(r.code, 1)
        self.assertIn('MARKER_OFF', r.out)
        self.assertNotIn(markers.MARKERS[R], self.read(NARRATIVE))

    def test_the_old_format_is_converted(self):
        old = helpers.narrative_text(extra='\n[sllmwiki_reasoning] Mine here. Then more.\n').replace(
            f'twice as long {CITE}.', f'twice as long. {CITE}')
        self.write(NARRATIVE, old)
        r = self.finish('what-is-alpha')
        self.assertEqual(r.code, 0, r.out + r.err)
        self.assertIn('moved 2 reference(s) inside their sentence', r.out)
        text = self.read(NARRATIVE)
        self.assertIn(f'twice as long {CITE}.', text)
        self.assertIn(f'Mine here {R}. Then more.', text)




class Statement(unittest.TestCase):
    def test_the_statement_a_marker_covers(self):
        def said(line):
            return markers.statement(line, line.index('[?]'))
        self.assertEqual(said('It works. Nobody says why [?].'), 'Nobody says why')
        self.assertEqual(said('Why? Waldo et al. argue it, but it was not read [?].'), 'Waldo et al. argue it, but it was not read')
        self.assertEqual(said('- **Open:** how it scales [?].'), '**Open:** how it scales')
        self.assertEqual(said('**It is. Unclear how [?]**.'), 'Unclear how')
        self.assertEqual(said('| Weights | not covered [?] |'), 'not covered')
        self.assertEqual(said('它很快。原因未知 [?]。'), '原因未知')
        self.assertEqual(said('1. Unknown [?]'), 'Unknown')


if __name__ == '__main__':
    unittest.main()
