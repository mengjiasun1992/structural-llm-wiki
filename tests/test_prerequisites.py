"""Tests for prerequisites (issue #205): finish-narrative --prerequisite, the generated Before you read and
Where to go next (lib/prerequisites.py), the Read first pointer under the title, wiki-check's checks, and
sllmwiki prerequisites propose and migrate."""

import json
import unittest

import helpers
from sllmwiki.lib import language, manifest, metadata, prerequisites

ALPHA, BETA, GAMMA = 'what-is-alpha', 'how-does-beta-work', 'how-does-gamma-work'
TAKEAWAYS = '\n\n**Key takeaways:**\n\n- Alpha waits longer after each failure [\\[1\\]](../sources/alpha-doc.md#details) [→].\n- Second.\n'


def path(slug):
    return f'sllmwiki/narratives/{slug}.md'


class Base(helpers.WikiTestCase):
    def setUp(self):
        super().setUp()
        self.write(path(ALPHA), self.read(path(ALPHA)).replace('\n\n## 2. Terminology', TAKEAWAYS + '\n## 2. Terminology'))
        helpers.add_narrative(self.root, BETA, 'How does beta work?')
        helpers.add_narrative(self.root, GAMMA, 'How does gamma work?')

    def finish(self, slug, *argv):
        return helpers.run('finish-narrative.py', [slug, *argv, '--root', self.root])

    def check(self, *argv):
        r = helpers.run('wiki-check.py', ['--json', *argv, '--root', self.root])
        return json.loads(r.out)['findings']

    def codes(self, *argv):
        return [f['code'] for f in self.check(*argv)]

    def entry(self, slug):
        return manifest.load(self.root, 'narratives')[slug]


class Finish(Base):
    def test_recorded_and_written_both_ways(self):
        r = self.finish(BETA, '--prerequisite', ALPHA)
        self.assertEqual(r.code, 0, r.out + r.err)
        alpha, beta = self.read(path(ALPHA)), self.read(path(BETA))
        self.assertEqual(self.entry(BETA)['prerequisites'], {ALPHA: manifest.narrative_hash(alpha)})
        # beta's Appendix, made before its References, and its Read first line under the title
        self.assertIn('## 8. Appendix\n\n' + prerequisites.START + '\n\n### 8.1 Before you read\n\n'
                      '- [What is alpha?](what-is-alpha.md) (about 1 min): Alpha waits longer after each failure.\n\n'
                      + prerequisites.END + '\n\n## 9. References', beta)
        self.assertIn('# How does beta work?\n\n*Read first: [What is alpha?](what-is-alpha.md) ([Before you read](#81-before-you-read)).*\n\n## 1.', beta)
        # alpha lists beta as where to go next, and wiki-check finds both current
        self.assertIn('### 8.1 Where to go next\n\n- [How does beta work?](how-does-beta-work.md) (about 1 min)\n\n' + prerequisites.END, alpha)
        self.assertIn(f'rewrote Before you read and Where to go next in 1 narrative(s): {path(ALPHA)}', r.out)
        codes = self.codes()
        for code in ('READING_ORDER_OUTDATED', 'PREREQUISITE_CHANGED', 'NARRATIVE_BASE_CHANGED', 'LINK_ANCHOR', 'PREREQUISITE_UNKNOWN'):
            self.assertNotIn(code, codes)
        # finishing again changes nothing; a later run without --prerequisite keeps them
        self.assertEqual(self.finish(BETA).code, 0)
        self.assertEqual(self.read(path(BETA)), beta)
        self.assertEqual(list(self.entry(BETA)['prerequisites']), [ALPHA])

    def test_the_marker_from_before_214_is_rewritten(self):
        # issue #214: the marker held "--fix", which XML forbids in a comment; a narrative with it is outdated, and fixed
        self.assertEqual(self.finish(BETA, '--prerequisite', ALPHA).code, 0)
        old = metadata.REGION_START + ': written by sllmwiki finish-narrative and wiki-check --fix; your own next reads go after its end -->'
        self.write(path(BETA), self.read(path(BETA)).replace(prerequisites.START, old))
        self.assertIn('READING_ORDER_OUTDATED', self.codes())
        self.assertEqual(helpers.run('wiki-check.py', ['--fix', '--root', self.root]).code, 0)
        beta = self.read(path(BETA))
        self.assertEqual((beta.count(prerequisites.START), old in beta), (1, False))

    def test_a_reading_time_line_gets_the_pointer_beside_it(self):
        self.write(path(BETA), self.read(path(BETA)).replace('# How does beta work?\n', '# How does beta work?\n\n*About 9 min read.*\n'))
        self.assertEqual(self.finish(BETA, '--prerequisite', ALPHA).code, 0)
        beta = self.read(path(BETA))
        self.assertIn('\n*About 1 min read. Read first: [What is alpha?](what-is-alpha.md) ([Before you read](#81-before-you-read)).*\n', beta)
        self.assertEqual(metadata.with_reading_line(beta), beta)
        self.assertEqual(self.finish(BETA, '--no-prerequisites').code, 0)
        beta = self.read(path(BETA))
        self.assertIn('\n*About 1 min read.*\n', beta)
        self.assertNotIn('Appendix', beta)  # the Appendix it made goes with the region
        self.assertNotIn('prerequisites', self.entry(BETA))
        self.assertNotIn(prerequisites.START, self.read(path(ALPHA)))

    def test_generated_parts_are_neither_words_nor_a_change(self):
        before = self.read(path(ALPHA))
        words, pin = metadata.reading(before), manifest.narrative_hash(before)
        self.assertEqual(self.finish(BETA, '--prerequisite', ALPHA).code, 0)
        self.assertEqual(self.finish(GAMMA, '--prerequisite', ALPHA).code, 0)
        after = self.read(path(ALPHA))
        self.assertIn('- [How does beta work?](how-does-beta-work.md)', after)
        self.assertIn('- [How does gamma work?](how-does-gamma-work.md)', after)
        self.assertEqual((metadata.reading(after), manifest.narrative_hash(after)), (words, pin))
        self.write(path(ALPHA), after.replace('Requests fail, and', 'Requests often fail, and'))
        found = [f for f in self.check() if f['code'] == 'PREREQUISITE_CHANGED']
        self.assertEqual(sorted(f['file'] for f in found), [path(BETA), path(GAMMA)])

    def test_refused(self):
        r = self.finish(BETA, '--prerequisite', 'what-is-nothing')
        self.assertEqual(r.code, 1)
        self.assertIn('no sllmwiki/narratives/what-is-nothing.md', r.err)
        r = self.finish(BETA, '--prerequisite', BETA)
        self.assertIn('would be its own prerequisite, through itself', r.err)
        self.assertEqual(self.finish(BETA, '--prerequisite', ALPHA).code, 0)
        r = self.finish(ALPHA, '--prerequisite', BETA)
        self.assertEqual(r.code, 1)
        self.assertIn(f'through {BETA}', r.err)
        r = self.finish(BETA, '--prerequisite', ALPHA, '--no-prerequisites')
        self.assertEqual(r.code, 2)
        with self.assertRaises(manifest.ManifestError):
            manifest.put_narrative(self.root, BETA, 'technical_brief_overview', ['leaf-a'], [], [], prerequisites=[BETA])
        with self.assertRaises(manifest.ManifestError):
            manifest.put_narrative(self.root, BETA, 'technical_brief_overview', ['leaf-a'], [], [], prerequisites=['nope'])

    def test_indirect(self):
        self.assertEqual(self.finish(BETA, '--prerequisite', ALPHA).code, 0)
        r = self.finish(GAMMA, '--prerequisite', BETA, '--prerequisite', ALPHA, '--json')
        found = [f for f in json.loads(r.out)['findings'] if f['code'] == 'PREREQUISITE_INDIRECT']
        self.assertEqual(found[0]['message'], f'{ALPHA} is already a prerequisite of {BETA}: leave it out of --prerequisite')
        self.assertIn('PREREQUISITE_INDIRECT', self.codes())
        gamma = self.read(path(GAMMA))
        self.assertIn('Read first: [How does beta work?](how-does-beta-work.md), [What is alpha?](what-is-alpha.md)', gamma)


class Check(Base):
    def test_outdated_and_fixed(self):
        self.assertEqual(self.finish(BETA, '--prerequisite', ALPHA).code, 0)
        alpha = self.read(path(ALPHA))
        self.write(path(ALPHA), alpha.replace('(about 1 min)', '(about 7 min)'))
        found = [f for f in self.check() if f['code'] == 'READING_ORDER_OUTDATED']
        self.assertEqual([f['file'] for f in found], [path(ALPHA)])
        self.assertNotIn('READING_ORDER_OUTDATED', self.codes('--fix'))
        self.assertEqual(self.read(path(ALPHA)), alpha)

    def test_a_region_left_without_prerequisites_goes(self):
        self.assertEqual(self.finish(BETA, '--prerequisite', ALPHA).code, 0)
        text = self.read('sllmwiki/narratives/manifest.yaml')
        start = text.index('  prerequisites:', text.index(f'{BETA}:'))
        self.write('sllmwiki/narratives/manifest.yaml', text[:start] + text[start:].split('\n', 2)[2])
        self.assertIn('READING_ORDER_OUTDATED', self.codes())
        self.assertNotIn('READING_ORDER_OUTDATED', self.codes('--fix'))
        self.assertNotIn('Appendix', self.read(path(BETA)))
        self.assertNotIn('Read first', self.read(path(BETA)))
        self.assertNotIn('Appendix', self.read(path(ALPHA)))

    def test_unknown_and_cycle(self):
        self.assertEqual(self.finish(BETA, '--prerequisite', ALPHA).code, 0)
        text = self.read('sllmwiki/narratives/manifest.yaml')
        pin = self.entry(BETA)['prerequisites'][ALPHA]
        at = text.index(f'\n{GAMMA}:')
        self.write('sllmwiki/narratives/manifest.yaml', text.replace(f'{ALPHA}:\n  template', f'{ALPHA}:\n  prerequisites:\n    {BETA}: {pin}\n  template', 1)
                   [:at + 40] + text[at:].replace('  read:', f'  prerequisites:\n    what-is-nothing: {pin}\n  read:', 1))
        found = {f['code']: f['message'] for f in self.check()}
        self.assertIn(f'{BETA}, {ALPHA} are each other', found['PREREQUISITE_CYCLE'].replace(f'{ALPHA}, {BETA}', f'{BETA}, {ALPHA}'))
        self.assertIn(f'{GAMMA}: its prerequisite what-is-nothing is no narrative', found['PREREQUISITE_UNKNOWN'])

    def test_legacy_pins_still_match(self):
        alpha = self.read(path(ALPHA))
        self.assertNotEqual(manifest.legacy_hash(alpha), manifest.narrative_hash(alpha))
        self.assertTrue(manifest.pin_matches(alpha, manifest.legacy_hash(alpha)))
        self.assertFalse(manifest.pin_matches(alpha, '0' * 32))


class Render(unittest.TestCase):
    def setUp(self):
        self.infos = {'a': type('I', (), {'title': 'What is [a]?', 'minutes': 3, 'takeaway': 'It costs $5 a day.'})(),
                      'c': type('I', (), {'title': 'How does c work?', 'minutes': 8, 'takeaway': ''})()}
        self.text = helpers.narrative_text('How does b work?', ()).replace(
            '## 8. References', '## 8. Appendix\n\n### 8.1 Where to go next\n\n- [How does c work?](c.md): next.\n- Siblings: d.\n\n'
                                '### 8.2 Glossary\n\n| Term | Definition |\n|---|---|\n| **X** | Y. |\n\n## 9. References')

    def test_own_next_reads_kept_and_deduplicated(self):
        out = prerequisites.render(self.text, ['a'], ['c'], self.infos, language.ENGLISH)
        self.assertIn('## 8. Appendix\n\n' + prerequisites.START + '\n\n### 8.1 Before you read\n\n'
                      '- [What is \\[a\\]?](a.md) (about 3 min): It costs \\$5 a day.\n\n### 8.2 Where to go next\n\n'
                      '- [How does c work?](c.md) (about 8 min)\n\n' + prerequisites.END + '\n\n- Siblings: d.\n\n### 8.3 Glossary', out)
        self.assertEqual(prerequisites.render(out, ['a'], ['c'], self.infos, language.ENGLISH), out)
        # without prerequisites or dependents, the writer's own next reads stay, under their heading
        bare = prerequisites.render(out, [], [], self.infos, language.ENGLISH)
        self.assertIn('### 8.1 Where to go next\n\n' + prerequisites.END + '\n\n- Siblings: d.\n\n### 8.2 Glossary', bare)
        self.assertNotIn('Read first', bare)

    def test_nothing_to_write_changes_nothing(self):
        text = helpers.narrative_text('Q?', ()).replace('## 2. Terminology', '## 5. Terminology')  # misnumbered: left as it is
        self.assertEqual(prerequisites.render(text, [], [], self.infos, language.ENGLISH), text)

    def test_in_the_narratives_language(self):
        out = prerequisites.render(helpers.ZH_NARRATIVE, ['c'], [], self.infos, language.pack('zh-Hans'))
        self.assertIn('## 4. 附录\n\n' + prerequisites.START + '\n\n### 4.1 阅读之前\n\n- [How does c work?](c.md) (约 8 分钟)', out)
        self.assertIn('*请先读：[How does c work?](c.md)（[阅读之前](#41-阅读之前)）。*', out)
        self.assertEqual(metadata.read_first(out), '请先读：[How does c work?](c.md)（[阅读之前](#41-阅读之前)）。')

    def test_takeaway(self):
        self.assertEqual(prerequisites.takeaway('# Q\n\n## 1. Abstract\n\nText.\n' + TAKEAWAYS), 'Alpha waits longer after each failure.')
        self.assertEqual(prerequisites.takeaway('# Q\n\n## 1. Abstract\n\nText.\n'), '')

    def test_graph(self):
        g = {'a': ['b', 'c'], 'b': ['c'], 'c': [], 'd': ['e'], 'e': ['d']}
        self.assertEqual(prerequisites.reach(g, 'a'), {'b', 'c'})
        self.assertEqual(prerequisites.cycles(g), [['d', 'e']])
        self.assertEqual(prerequisites.indirect(g), [('a', 'c', 'b')])
        self.assertEqual(prerequisites.dependents(g, 'c'), ['a', 'b'])


class ReadFirstLine(unittest.TestCase):
    def test_added_kept_and_removed(self):
        text = '# Q?\n\n## 1. Abstract\n\nText.\n'
        added = metadata.with_read_first(text, 'Read first: [A](a.md) ([B](#b)).')
        self.assertEqual(added, '# Q?\n\n*Read first: [A](a.md) ([B](#b)).*\n\n## 1. Abstract\n\nText.\n')
        self.assertEqual(metadata.with_read_first(added, ''), text)
        self.assertEqual(metadata.without_generated(added), '# Q?\n\n\n## 1. Abstract\n\nText.\n')
        self.assertEqual(metadata.with_read_first('No title.\n', 'Read first: x (y).'), 'No title.\n')
        self.assertEqual(metadata.with_reading_line(added), added)  # no minutes to keep
        self.assertEqual(metadata.without_reading_line(added), text)
        self.assertEqual(metadata.read_first('# Q?\n\n*Not a pointer.*\n'), '')


class Command(Base):
    def run_cmd(self, *argv):
        return helpers.run('prerequisites.py', [*argv, '--root', self.root])

    def test_propose(self):
        beta = self.read(path(BETA))
        self.write(path(BETA), beta.replace('Waiting longer each time spares a struggling server.',
                                            'A retry, as [alpha](what-is-alpha.md#3-background) says, spares a struggling server.'))
        self.write(path(GAMMA), self.read(path(GAMMA)).replace('| **Retry** |', '| **Backoff** |'))
        r = self.run_cmd('propose', GAMMA, '--json')
        found = json.loads(r.out)['narratives'][GAMMA]['candidates']
        self.assertEqual(found[BETA], {'built_on': False, 'links': 0, 'terms': ['retry'], 'cycle': False, 'indirect': False})
        r = self.run_cmd('propose', BETA)
        self.assertIn(f'{BETA} (prerequisites: none)\n  {ALPHA}: links to it 1 time(s)', r.out)
        self.assertEqual(self.finish(BETA, '--prerequisite', GAMMA).code, 0)
        r = self.run_cmd('propose', BETA)
        self.assertIn(f'unused? {GAMMA}: no link to it and none of its terms', r.out)
        r = self.run_cmd('propose', GAMMA, '--json')
        self.assertTrue(json.loads(r.out)['narratives'][GAMMA]['candidates'][BETA]['cycle'])
        self.assertEqual(self.run_cmd('propose', 'what-is-nothing').code, 2)
        self.assertEqual(self.run_cmd('migrate', BETA).code, 2)

    def test_migrate(self):
        alpha = self.read(path(ALPHA)).replace('## 8. References', '## 8. Where to go next\n\n- [How does gamma work?](how-does-gamma-work.md)\n'
                                                                   '- How does delta work?\n\n### 8.1 Deeper\n\nMore.\n\n## 9. References')
        self.write(path(ALPHA), alpha)
        text = self.read('sllmwiki/narratives/manifest.yaml')
        pin = manifest.legacy_hash(alpha)  # an old pin, as finish-narrative wrote it before
        self.write('sllmwiki/narratives/manifest.yaml', text.rstrip('\n') + f'\n  built_on:\n    {ALPHA}: {pin}\n')
        self.assertNotIn('NARRATIVE_BASE_CHANGED', self.codes())
        r = self.run_cmd('migrate')
        self.assertEqual(r.code, 0, r.err)
        self.assertIn(f'moved Where to go next into the Appendix in 1 narrative(s): {ALPHA}', r.out)
        self.assertIn('proposed prerequisites, for the narratives that record none:', r.out)
        moved = self.read(path(ALPHA))
        self.assertIn('## 8. Appendix\n\n' + prerequisites.START + '\n\n### 8.1 Where to go next\n\n' + prerequisites.END +
                      '\n\n- [How does gamma work?](how-does-gamma-work.md)\n- How does delta work?\n\n#### 8.1.1 Deeper\n\nMore.\n\n## 9. References', moved)
        self.assertEqual(self.entry(GAMMA)['built_on'][ALPHA], manifest.narrative_hash(moved))  # re-pinned: nothing a reader reads changed
        codes = self.codes()
        self.assertNotIn('NARRATIVE_BASE_CHANGED', codes)
        self.assertNotIn('READING_ORDER_OUTDATED', codes)
        r = self.run_cmd('migrate', '--json')
        self.assertEqual(json.loads(r.out)['moved'], [])
        self.assertEqual(self.read(path(ALPHA)), moved)


if __name__ == '__main__':
    unittest.main()
