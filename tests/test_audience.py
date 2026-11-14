"""Tests for lib/audience.py: the wiki's audience profile, at the path Config.toml's audience names, before the
skill and every guide, in at most 800 words; init's empty starter; and how narrative-format and wiki-check use it."""

import json
import os

import helpers
from sllmwiki.lib import audience, layout

PROFILE = '# Who reads this wiki\n\nProduct managers on the payments team: no code, plain words, the decision first.\n'
HEADER = f'<!-- {layout.AUDIENCE}: who this wiki is written for; it comes before the skill and the guides below -->\n'


class Profile(helpers.WikiTestCase):
    def nf(self, *argv):
        return helpers.run('narrative-format.py', ['--root', self.root, *argv])

    def codes(self):
        r = helpers.run('wiki-check.py', ['--root', self.root, '--visibility', 'private', '--json'])
        return [f['code'] for f in json.loads(r.out)['findings']]

    def config(self, line):
        self.write(layout.CONFIG, f'[structural-llm-wiki-settings]\n{line}\n')

    def test_none(self):
        self.assertEqual(audience.path(self.root), layout.AUDIENCE)  # the default
        self.assertIsNone(audience.read(self.root))  # no file
        self.assertEqual(audience.problems(self.root), [])
        r = self.nf('--audience')
        self.assertEqual(r.code, 0)
        self.assertIn('no audience profile', r.out)
        self.assertTrue(self.nf('--guide', 'comparison').out.startswith('<!-- comparison/guide.md (bundled) -->\n'))
        for empty in ('  \n\n', audience.STARTER, '# Readers\n\n## Who\n<!-- later -->\n'):  # says nothing: none
            self.write(layout.AUDIENCE, empty)
            self.assertIsNone(audience.read(self.root), empty)
        self.write(layout.AUDIENCE, PROFILE)
        self.config('audience = ""')  # none, whatever the file says
        self.assertIsNone(audience.path(self.root))
        self.assertIsNone(audience.read(self.root))

    def test_the_profile_comes_first(self):
        self.write(layout.AUDIENCE, PROFILE + '\n<!-- a note to the owner, not part of the profile -->\n')
        self.assertEqual(audience.read(self.root), PROFILE.strip())
        r = self.nf('--audience')
        self.assertEqual((r.code, r.out, r.err), (0, PROFILE.strip() + '\n', ''))
        out = self.nf('--guide', 'comparison').out
        self.assertTrue(out.startswith(HEADER + '# Who reads this wiki\n'), out[:300])
        self.assertLess(out.index('Product managers'), out.index('<!-- comparison/guide.md (bundled) -->'))
        self.assertLess(out.index('<!-- comparison/guide.md'), out.index('<!-- shared.md -->'))
        self.assertNotIn('AUDIENCE_TOO_LONG', self.codes())
        skill = helpers.read(helpers.SKILL_DIR, 'SKILL.md')
        rules = skill[skill.index('## Rules every run follows'):]
        self.assertIn('narrative-format --audience', rules.split('\n- ')[1])  # the first rule every run follows

    def test_a_path_of_the_owners(self):
        self.config('audience = "docs/readers.md"')
        self.write('docs/readers.md', PROFILE)
        self.assertEqual(audience.path(self.root), 'docs/readers.md')
        self.assertEqual(audience.read(self.root), PROFILE.strip())
        self.assertTrue(self.nf('--guide', 'comparison').out.startswith('<!-- docs/readers.md: who this wiki'))
        self.write('docs/readers.md', ' '.join(['word'] * 801))
        r = json.loads(helpers.run('wiki-check.py', ['--root', self.root, '--visibility', 'private', '--json']).out)
        self.assertEqual([f['file'] for f in r['findings'] if f['code'] == 'AUDIENCE_TOO_LONG'], ['docs/readers.md'])

    def test_at_most_800_words(self):
        self.write(layout.AUDIENCE, ' '.join(['word'] * audience.MAX_WORDS))
        self.assertEqual(audience.problems(self.root), [])
        self.write(layout.AUDIENCE, ' '.join(['word'] * (audience.MAX_WORDS + 1)) + '\n<!-- ' + 'not counted ' * 50 + '-->\n')
        self.assertIn('801 words, over its 800', audience.problems(self.root)[0])
        self.assertIn('AUDIENCE_TOO_LONG', self.codes())
        r = self.nf('--audience')  # still printed, with the problem on stderr: the run goes on, the wiki's CI fails
        self.assertEqual(r.code, 0)
        self.assertIn('over its 800', r.err)
        self.assertTrue(r.out.startswith('word word'))
        self.assertIn('over its 800', self.nf('--guide', 'comparison').err)

    def test_chinese_counts_by_characters(self):
        self.write(layout.AUDIENCE, '读' * 1280)  # 1280 characters at 1.6 to a word: 800 words
        self.assertEqual(audience.problems(self.root), [])
        self.write(layout.AUDIENCE, '读' * 1290)
        self.assertEqual(len(audience.problems(self.root)), 1)

    def test_not_a_template(self):
        self.write(layout.AUDIENCE, PROFILE)
        r = self.nf('--templates', '--json')
        self.assertEqual(r.code, 0)
        self.assertNotIn('audience', [t['name'] for t in json.loads(r.out)['templates']])


class Init(helpers.WikiTestCase):
    def init(self, *argv):
        return helpers.run('init.py', ['--root', self.root, '--name', 'w', '--force', *argv])

    def test_init_writes_an_empty_profile(self):
        r = self.init()
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(helpers.read(self.root, layout.AUDIENCE), audience.STARTER)
        self.assertIsNone(audience.read(self.root))  # empty until the owner fills it in
        self.assertIn('audience = "sllmwiki/.templates/audience.md"', helpers.read(self.root, layout.CONFIG))
        self.write(layout.AUDIENCE, PROFILE)
        self.assertEqual(self.init().code, 0)
        self.assertEqual(helpers.read(self.root, layout.AUDIENCE), PROFILE)  # a rerun keeps the owner's

    def test_at_the_owners_path_or_none(self):
        self.assertEqual(self.init('--set', 'audience=docs/readers.md').code, 0)
        self.assertEqual(helpers.read(self.root, 'docs/readers.md'), audience.STARTER)
        self.assertFalse(os.path.exists(os.path.join(self.root, layout.AUDIENCE)))

    def test_none(self):
        self.write(layout.CONFIG, '[structural-llm-wiki-settings]\naudience = ""\n')
        self.assertEqual(self.init().code, 0)
        self.assertFalse(os.path.exists(os.path.join(self.root, layout.AUDIENCE)))
