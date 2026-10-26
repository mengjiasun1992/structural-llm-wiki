"""Tests for lib/templates.py and the bundled narrative templates."""

import json
import os
import shutil
import unittest

import helpers
from lib import numbering, templates
from lib.templates import Section, TemplateError

PURPOSE = '**Takeaway:** the reader can run the task.\n\n**Aim:** exact, safe. Exact: every step a command. Safe: every risk named.\n\n'
GUIDE = '# Guide\n\n' + ''.join(f'## {s}\n\n{PURPOSE if s == "Audience and purpose" else ""}Text.\n\n' for s in templates.GUIDE_SECTIONS)
TEMPLATE = '---\ndescription: A runbook\nuse_when: an operational task\nmax_words: 800\nabstract_words: [100, 200]\n---\n\n## Steps\n\n<steps>\n'


class Bundled(helpers.WikiTestCase):
    def test_the_bundled_templates_load(self):
        found, problems = templates.available(self.root)
        self.assertEqual(problems, [])
        self.assertEqual(sorted(found), ['case_study', 'comparison', 'concept_brief_overview', 'survey', 'technical_brief_overview'])
        self.assertEqual([found[n].max_words for n in sorted(found)], [1500, 1500, 1200, 2200, 1800])
        t = found['technical_brief_overview']
        self.assertEqual((t.source, t.max_words, t.abstract_words), ('bundled', 1800, [80, 150]))
        self.assertTrue(t.use_when.startswith('A solution, an algorithm'))

    def test_the_skeleton_is_the_schema(self):
        t = templates.get(self.root, 'technical_brief_overview')
        skel = t.skeleton()
        self.assertEqual(numbering.check(skel), [])  # numbered in one sequence
        self.assertIn('- **Template:** technical_brief_overview', skel)
        self.assertNotIn(templates.BODY_MARK, skel)
        got = [(s.title, s.optional, s.diagram) for s in t.sections()]
        self.assertEqual(got, [('Abstract', False, False), ('Terminology', False, False), ('Background', False, False),
                               ('The core idea', False, True), ('How does it work?', False, False), ('Variants', True, False),
                               ('Design decisions and trade-offs', False, False), ('Limitations and failure modes', False, False),
                               ('Misconceptions', True, False), ('Where to go next', True, False), ('Appendix', True, False),
                               ('SMEs', True, False), ('References', False, False), ('Metadata', False, False)])

    def test_the_concept_template(self):
        titles = [s.title for s in templates.get(self.root, 'concept_brief_overview').sections()]
        self.assertEqual(titles[2:7], ['Overview', 'Definition', 'Key ideas', 'Boundaries', 'Where to go next'])

    def test_the_comparison_and_survey_templates(self):
        got = [(s.title, s.optional, s.diagram) for s in templates.get(self.root, 'comparison').sections()][2:9]
        self.assertEqual(got, [('The choices', False, False), ('When to choose which', False, True), ('At a glance', False, False),
                               ('Dimensions to think through', False, False), ('Pitfalls', True, False), ('Where to go next', True, False),
                               ('Appendix', True, False)])
        got = [(s.title, s.optional, s.diagram) for s in templates.get(self.root, 'survey').sections()][2:10]
        self.assertEqual(got, [('Overview', False, False), ('The map', False, True), ('The main items', False, False),
                               ('Tensions and trade-offs', True, False), ('Classic case studies', True, False), ('Applying them', True, False),
                               ('Where to go next', False, False), ('Appendix', True, False)])
        got = [(s.title, s.optional, s.diagram) for s in templates.get(self.root, 'case_study').sections()][2:11]
        self.assertEqual(got, [('Context', False, False), ('The problem', False, False), ('What happened', False, True), ('Why', False, False),
                               ('The ideas at work', False, False), ('Outcome', True, False), ('Lessons', False, False),
                               ('Where to go next', True, False), ('Appendix', True, False)])
        for name in ('case_study', 'comparison', 'survey'):
            skel = templates.get(self.root, name).skeleton()
            self.assertEqual(numbering.check(skel), [])
            self.assertIn(f'- **Template:** {name}', skel)


class SectionPatterns(unittest.TestCase):
    def test_placeholders_match_any_text(self):
        s = Section('What is <X>?', False, False)
        self.assertTrue(s.matches('What is a retry budget?'))
        self.assertTrue(s.matches('what is EWMA?'))
        self.assertFalse(s.matches('What is it'))
        self.assertTrue(Section('Background', False, False).matches(' background '))


class WikiTemplates(helpers.WikiTestCase):
    def add(self, name, template=TEMPLATE, guide=GUIDE):
        helpers.write(self.root, f'sllmwiki/.templates/{name}/template.md', template)
        if guide is not None:
            helpers.write(self.root, f'sllmwiki/.templates/{name}/guide.md', guide)

    def test_a_wiki_template_is_offered(self):
        self.add('runbook')
        t = templates.get(self.root, 'runbook')
        self.assertEqual((t.source, t.max_words, [s.title for s in t.sections()][2]), ('wiki', 800, 'Steps'))

    def test_a_wiki_template_replaces_a_bundled_one(self):
        self.add('concept_brief_overview')
        self.assertEqual(templates.get(self.root, 'concept_brief_overview').source, 'wiki')

    def test_config_budgets_win_over_the_header(self):
        self.write('sllmwiki/Config.toml', '[structural-llm-wiki-templates.technical_brief_overview]\nmax_words = 3000\n\n'
                                  '[structural-llm-wiki-templates.concept_brief_overview]\nabstract_words = [100, 300]\n')
        found, problems = templates.available(self.root)
        self.assertEqual(problems, [])
        self.assertEqual((found['technical_brief_overview'].max_words, found['technical_brief_overview'].abstract_words), (3000, [80, 150]))
        self.assertEqual(found['concept_brief_overview'].abstract_words, [100, 300])

    def test_problems(self):
        cases = [
            ('no-header', '## Steps\n', GUIDE, 'must start with a --- header ---'),
            ('bad-yaml', '---\ndescription: a: b\n---\n', GUIDE, 'its header: line 1'),
            ('missing-key', '---\ndescription: x\nuse_when: when needed\nmax_words: 5\n---\n', GUIDE, 'missing abstract_words'),
            ('extra-key', TEMPLATE.replace('max_words: 800', 'max_words: 800\ncolor: red'), GUIDE, 'unknown color'),
            ('bad-budget', TEMPLATE.replace('max_words: 800', 'max_words: 0'), GUIDE, 'max_words must be a positive whole number'),
            ('bad-range', TEMPLATE.replace('[100, 200]', '[300, 200]'), GUIDE, 'abstract_words [min, max]'),
            ('no-guide', TEMPLATE, None, 'no guide.md'),
            ('thin-guide', TEMPLATE, '# G\n\n## Audience and purpose\n', 'missing Voice and tone'),
        ]
        for name, template, guide, msg in cases:
            with self.subTest(name=name):
                self.add(name, template, guide)
                found, problems = templates.available(self.root)
                self.assertNotIn(name, found)
                self.assertTrue(any(name in p and msg in p for p in problems), problems)
                shutil.rmtree(os.path.join(self.root, 'sllmwiki', '.templates', name))

    def test_budgets_for_a_template_that_doesnt_exist(self):
        self.write('sllmwiki/Config.toml', '[structural-llm-wiki-templates.runbook]\nmax_words = 500\n')
        self.assertIn('there\'s no template runbook', templates.available(self.root)[1][0])

    def test_get_an_unknown_template(self):
        with self.assertRaises(TemplateError) as e:
            templates.get(self.root, 'nope')
        self.assertIn('there are case_study, comparison, concept_brief_overview, survey, technical_brief_overview', str(e.exception))

    def test_folders_without_a_template_are_ignored(self):
        os.makedirs(os.path.join(self.root, 'sllmwiki', '.templates', 'notes'))
        self.assertEqual(templates.available(self.root)[1], [])



class NewTemplate(helpers.WikiTestCase):
    git = False

    def test_start_one_from_a_bundled_template(self):
        folder = templates.create(self.root, 'postmortem', 'case_study')
        self.assertEqual(folder, os.path.join(self.root, 'sllmwiki', '.templates', 'postmortem'))
        for f in ('template.md', 'guide.md'):
            self.assertEqual(helpers.read(folder, f), helpers.read(os.path.join(templates.BUNDLED, 'case_study'), f))
        offered, problems = templates.available(self.root)
        self.assertEqual((offered['postmortem'].source, problems), ('wiki', []))
        self.assertEqual(offered['case_study'].source, 'bundled')  # the one it came from is still there

    def test_replace_a_bundled_template_and_start_from_the_wikis_own(self):
        templates.create(self.root, 'survey', 'survey')  # a copy that replaces the bundled survey here
        self.assertEqual(templates.get(self.root, 'survey').source, 'wiki')
        templates.create(self.root, 'field-survey', 'survey')  # from the wiki's own
        self.assertEqual(helpers.read(self.root, 'sllmwiki/.templates/field-survey/template.md'), helpers.read(self.root, 'sllmwiki/.templates/survey/template.md'))

    def test_refusals(self):
        for name, base, says in [('Bad Name', 'survey', 'lowercase letters'), ('x', 'nope', 'no template nope')]:
            with self.assertRaises(TemplateError) as e:
                templates.create(self.root, name, base)
            self.assertIn(says, str(e.exception))
        templates.create(self.root, 'x', 'survey')
        with self.assertRaises(TemplateError) as e:
            templates.create(self.root, 'x', 'survey')
        self.assertIn('sllmwiki/.templates/x already exists', str(e.exception))

    def test_the_command(self):
        r = helpers.run('narrative-format.py', ['--new-template', 'postmortem', '--from', 'case_study'], cwd=self.root)
        self.assertEqual(r.code, 0, r.err)
        self.assertIn('started sllmwiki/.templates/postmortem/ from case_study', r.out)
        self.assertIn('postmortem (wiki,', helpers.run('narrative-format.py', ['--templates'], cwd=self.root).out)
        self.assertEqual(helpers.run('narrative-format.py', ['--new-template', 'postmortem', '--from', 'case_study'], cwd=self.root).code, 1)
        r = helpers.run('narrative-format.py', ['--new-template', 'other'], cwd=self.root)
        self.assertEqual((r.code, '--new-template needs --from BASE' in r.err), (2, True))



class Schema(helpers.WikiTestCase):
    """What every template must have, a wiki's own as much as a bundled one."""
    git = False

    def test_every_bundled_template_has_its_aim(self):
        found = {n: t.aim for n, t in templates.available(self.root)[0].items()}
        self.assertEqual(found, {'case_study': ['faithful', 'causal', 'transferable', 'deep on one case'],
                                 'comparison': ['precise', 'breadth and depth in balance'],
                                 'concept_brief_overview': ['concise', 'precise', 'rigorous'],
                                 'survey': ['concise', 'thorough', 'breadth over depth'],
                                 'technical_brief_overview': ['concise', 'authoritative', 'depth over breadth']})
        self.assertTrue(all(t.takeaway for t in templates.available(self.root)[0].values()))

    def problem(self, template=TEMPLATE, guide=GUIDE):
        helpers.write(self.root, 'sllmwiki/.templates/runbook/template.md', template)
        helpers.write(self.root, 'sllmwiki/.templates/runbook/guide.md', guide)
        found = templates.available(self.root)[1]
        return found[0] if found else None

    def test_a_good_wiki_template(self):
        self.assertIsNone(self.problem())
        t = templates.get(self.root, 'runbook')
        self.assertEqual((t.takeaway, t.aim), ('the reader can run the task.', ['exact', 'safe']))

    def test_the_guide_needs_a_takeaway_and_an_aim(self):
        for drop in ('**Takeaway:**', '**Aim:**'):
            guide = '\n'.join(line for line in GUIDE.split('\n') if not line.startswith(drop))
            self.assertIn('needs a **Takeaway:** line', self.problem(guide=guide))

    def test_the_body(self):
        head = TEMPLATE.split('## Steps')[0]
        self.assertIn('needs at least one ## section', self.problem(head + 'Just text.\n'))
        self.assertIn('needs at least one ## section', self.problem(head + '### Steps\n\n<steps>\n'))
        self.assertIn('repeats "Abstract", which every narrative already has', self.problem(head + '## Abstract\n\n<a>\n\n## Steps\n\n<s>\n'))
        self.assertIn('repeats "References"', self.problem(head + '## Steps\n\n<s>\n\n## References (optional)\n\n<r>\n'))
        self.assertIn('repeats "参考资料"', self.problem(head + '## 参考资料\n\n<r>\n'))  # in a language pack's words too
        self.assertIn('section "Steps" needs a <...> line', self.problem(head + '## Steps\n\nFree text.\n\n## Risks\n\n<r>\n'))
        self.assertIsNone(self.problem(head + '## Steps\n\n```mermaid\n%% <a flowchart of the steps>\n```\n'))

    def test_headings_a_language_pack_doesnt_translate(self):
        self.problem()
        r = helpers.run('narrative-format.py', ['--templates', '--json'], cwd=self.root)
        self.assertEqual((r.code, json.loads(r.out)['warnings']), (0, []))  # English needs no translation
        helpers.write(self.root, 'sllmwiki/Config.toml', '[structural-llm-wiki-settings]\nlanguage = "zh-Hans"\n')
        r = helpers.run('narrative-format.py', ['--templates'], cwd=self.root)
        self.assertEqual(r.code, 0)  # a warning, not a problem
        self.assertIn('warning: template runbook: zh-Hans keeps "Steps" in English: translate it in sllmwiki/.templates/languages/zh-Hans.md', r.out)
        self.assertIn('aim: exact, safe', r.out)
        self.assertEqual(templates.untranslated(templates.get(self.root, 'survey'), templates.language.pack('zh-Hans')), [])


if __name__ == '__main__':
    unittest.main()
