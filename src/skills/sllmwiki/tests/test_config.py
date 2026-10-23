"""Tests for lib/config.py: Config.toml's settings, template budgets and add-ons."""

import unittest

import helpers
from lib import config
from lib.config import ConfigError, parse


def problems(text):
    with unittest.TestCase().assertRaises(ConfigError) as e:
        parse(text)
    return e.exception.problems


class Defaults(helpers.WikiTestCase):
    def test_no_file_means_the_defaults(self):
        c = config.load(self.root)
        self.assertEqual(c.settings, {'source_copies': 'allow', 'max_quote_words': 50, 'smes_exclude': [], 'markers': True, 'images': True})
        self.assertEqual((c.templates, c.addons), ({}, {'obsidian': False}))
        self.assertEqual(config.problems(self.root), [])

    def test_a_file_overrides_what_it_sets(self):
        self.write('Config.toml', '[structural-llm-wiki-settings]\nmarkers = false\n\n[structural-llm-wiki-addons]\nobsidian = true\n')
        c = config.load(self.root)
        self.assertEqual((c.settings['markers'], c.settings['max_quote_words'], c.addons['obsidian']), (False, 50, True))

    def test_get_falls_back_to_the_defaults(self):
        self.write('Config.toml', '[structural-llm-wiki-settings]\nmarkers = "no"\n')
        self.assertEqual(config.problems(self.root), ['Config.toml: structural-llm-wiki-settings.markers must be true or false'])
        self.assertTrue(config.get(self.root).settings['markers'])
        with self.assertRaises(ConfigError):
            config.load(self.root)


class Settings(unittest.TestCase):
    def test_every_setting(self):
        c = parse('[structural-llm-wiki-settings]\nsource_copies = "links-only"\nmax_quote_words = 25\n'
                  'smes_exclude = ["@owner", "dependabot"]\nmarkers = false\n')
        self.assertEqual(c.settings, {'source_copies': 'links-only', 'max_quote_words': 25,
                                      'smes_exclude': ['@owner', 'dependabot'], 'markers': False, 'images': True})

    def test_bad_values(self):
        cases = [
            ('source_copies = "none"', 'source_copies must be "allow" or "links-only"'),
            ('source_copies = true', 'source_copies must be a string'),
            ('max_quote_words = 0', 'max_quote_words must be a positive whole number'),
            ('max_quote_words = "50"', 'max_quote_words must be a whole number'),
            ('max_quote_words = true', 'max_quote_words must be a whole number'),
            ('smes_exclude = "@a"', 'smes_exclude must be a list'),
            ('smes_exclude = ["@a", ""]', 'smes_exclude must list names'),
            ('smes_exclude = [1]', 'smes_exclude must list names'),
            ('markers = 1', 'markers must be true or false'),
            ('marker = true', 'unknown setting structural-llm-wiki-settings.marker (did you mean markers?)'),
            ('zzz = true', 'unknown setting structural-llm-wiki-settings.zzz (known: source_copies, max_quote_words'),
        ]
        for line, msg in cases:
            with self.subTest(line=line):
                found = problems(f'[structural-llm-wiki-settings]\n{line}\n')
                self.assertEqual(len(found), 1, found)
                self.assertIn(msg, found[0])
                self.assertTrue(found[0].startswith('Config.toml: '))


class Templates(unittest.TestCase):
    def test_budgets(self):
        c = parse('[structural-llm-wiki-templates.technical_brief_overview]\nmax_words = 3000\nabstract_words = [150, 300]\n\n'
                  '[structural-llm-wiki-templates.runbook]\nmax_words = 800\n')
        self.assertEqual(c.templates, {'technical_brief_overview': {'max_words': 3000, 'abstract_words': [150, 300]},
                                       'runbook': {'max_words': 800}})

    def test_bad_tables(self):
        cases = [
            ('[structural-llm-wiki-templates.x]\nmax_words = 0\n', 'max_words must be a positive whole number'),
            ('[structural-llm-wiki-templates.x]\nmax_words = "3000"\n', 'max_words must be a positive whole number'),
            ('[structural-llm-wiki-templates.x]\nabstract_words = [300, 150]\n', 'abstract_words must be [min, max]'),
            ('[structural-llm-wiki-templates.x]\nabstract_words = [150]\n', 'abstract_words must be [min, max]'),
            ('[structural-llm-wiki-templates.x]\nabstract_words = [0, 10]\n', 'abstract_words must be [min, max]'),
            ('[structural-llm-wiki-templates.x]\nmax_word = 1\n', 'unknown key max_word in [structural-llm-wiki-templates.x] (did you mean max_words?)'),
            ('[structural-llm-wiki-templates.Bad]\nmax_words = 1\n', 'a template name is lowercase'),
            ('[structural-llm-wiki-templates]\ndefault = "x"\n', 'structural-llm-wiki-templates.default must be a table'),
        ]
        for text, msg in cases:
            with self.subTest(text=text):
                found = problems(text)
                self.assertEqual(len(found), 1, found)
                self.assertIn(msg, found[0])


class Addons(unittest.TestCase):
    def test_bad_addons(self):
        self.assertIn('unknown add-on structural-llm-wiki-addons.mdbook (known: obsidian)',
                      problems('[structural-llm-wiki-addons]\nmdbook = true\n')[0])
        self.assertIn('did you mean obsidian?', problems('[structural-llm-wiki-addons]\nobsidan = true\n')[0])
        self.assertIn('obsidian must be true or false', problems('[structural-llm-wiki-addons]\nobsidian = "yes"\n')[0])


class Tables(unittest.TestCase):
    def test_other_tools_tables_are_left_alone(self):
        c = parse('[tool.ruff]\nline-length = 200\n\n[structural-llm-wiki-addons]\nobsidian = true\n')
        self.assertTrue(c.addons['obsidian'])

    def test_unknown_or_retired_tables(self):
        found = problems('[structural-llm-wiki-paths]\ncontent = "kb"\n')
        self.assertIn('[structural-llm-wiki-paths] isn\'t a table this version reads', found[0])
        self.assertIn('the layout is fixed', found[0])
        self.assertIn('did you mean structural-llm-wiki-settings?', problems('[structural-llm-wiki-setting]\nmarkers = true\n')[0])
        self.assertIn('must be a table', problems('structural-llm-wiki-settings = 1\n')[0])

    def test_every_problem_is_listed(self):
        found = problems('[structural-llm-wiki-settings]\nmarkers = 1\nmax_quote_words = 0\n\n[structural-llm-wiki-addons]\nx = true\n')
        self.assertEqual(len(found), 3)

    def test_a_toml_error(self):
        self.assertEqual(problems('[structural-llm-wiki-settings]\nmax_quote_words = 1.5\n'),
                         ['Config.toml: line 2: expected a string, a whole number, true or false, or an array (Config.toml uses no other values)'])


if __name__ == '__main__':
    unittest.main()
