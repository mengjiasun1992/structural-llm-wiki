import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

import helpers
from lib import config
from lib.toml import loads


class Config(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='llmwiki-config-')
        self.addCleanup(shutil.rmtree, self.root)

    def conf(self, text):
        helpers.write(self.root, config.FILE, text)

    def test_defaults_without_a_file(self):
        L = config.load_layout(self.root)
        self.assertEqual(L.paths, config.DEFAULTS)
        self.assertEqual((L.images, L.files, L.manifest('groomed')), ('ingested/images', 'ingested/files', 'groomed/manifest.yaml'))
        self.assertEqual(config.problems(self.root), [])

    def test_custom_paths(self):
        self.conf('[structural-llm-wiki-paths]\ningested = "sources/"\ningested_manifest = "sources/manifest.yaml"\ntags = "meta\\\\tags.yaml"\n')
        L = config.load_layout(self.root)
        self.assertEqual((L.ingested, L.images, L.tags, L.groomed), ('sources', 'sources/images', 'meta/tags.yaml', 'groomed'))
        self.conf('[other-tool]\nanything = 1\n[structural-llm-wiki-settings]\n[structural-llm-wiki-paths]\ngroomed = "notes"\n')  # other tools' tables are left alone
        self.assertEqual(config.load_layout(self.root).groomed, 'notes')

    def test_problems(self):
        for text, msg in [('[structural-llm-wiki-paths]\ningested = "/abs"\n', 'relative'), ('[structural-llm-wiki-paths]\ningested = "a/../b"\n', '".."'),
                          ('[structural-llm-wiki-paths]\ngroomed = ".github/x"\n', 'inside .github/'), ('[structural-llm-wiki-paths]\ntags = "tags.json"\n', 'must end with .yaml'),
                          ('[structural-llm-wiki-paths]\nindex = "INDEX.txt"\n', 'must end with .md'), ('[structural-llm-wiki-paths]\ningested = ""\n', 'non-empty'),
                          ('[structural-llm-wiki-paths]\ningested = 3\n', 'non-empty string'), ('[structural-llm-wiki-paths]\ngroomed = "ingested"\n', 'the same path'),
                          ('[structural-llm-wiki-paths]\ntags = "ingested/tags.yaml"\n', 'inside the ingested folder'),
                          ('[structural-llm-wiki-paths]\ngroomed_manifest = "ingested/g.yaml"\n', 'inside the ingested folder'),
                          ('[structural-llm-wiki-paths]\nindex = "C:/x.md"\n', 'relative'), ('[structural-llm-wiki-paths]\nnope = "x"\n', 'unknown path(s) structural-llm-wiki-paths.nope'),
                          ('structural-llm-wiki-paths = 1\n', 'must be a table'), ('structural-llm-wiki-settings = 1\n', 'must be a table'), ('[paths\n', 'line 1')]:
            self.conf(text)
            self.assertIn(msg, config.problems(self.root)[0], text)
            self.assertEqual(config.layout(self.root).paths, config.DEFAULTS)  # read-only scripts fall back to the defaults
        with open(os.path.join(self.root, config.FILE), 'wb') as f:
            f.write(b'\xff\xfe[structural-llm-wiki-paths]')
        self.assertIn('cannot read', config.problems(self.root)[0])

    def test_settings(self):
        self.assertEqual(config.load_settings(self.root), {'slice_large_sources': True, 'large_source_kb': 50, 'reasoning_marker': '[sllmwiki_reasoning]', 'gap_marker': '[sllmwiki_gap]', 'max_words': 0, 'abstract_words': [], 'max_quote_words': 50, 'addons': {'obsidian': {'enabled': False, 'show_sources': False, 'vault': 'content'}, 'sphinx': {'enabled': False, 'formats': ['html', 'epub', 'pdf']}, 'mdbook': {'enabled': False, 'formats': ['html', 'pdf']}}})  # the defaults, without a file
        self.conf('[structural-llm-wiki-settings]\nslice_large_sources = false\n')
        self.assertFalse(config.load_settings(self.root)['slice_large_sources'])
        self.conf('[structural-llm-wiki-settings]\n')
        self.assertTrue(config.load_settings(self.root)['slice_large_sources'])
        for text, msg in [('[structural-llm-wiki-settings]\nslice_large_sources = "no"\n', 'must be true or false'),
                          ('[structural-llm-wiki-settings]\nnope = 1\n', 'unknown setting(s) structural-llm-wiki-settings.nope')]:
            self.conf(text)
            self.assertIn(msg, config.problems(self.root)[0])
        from lib.toml import loads
        self.assertEqual(loads(config.render())['structural-llm-wiki-settings'], config.default_settings())  # the template writes every default

    def test_size_and_quote_limits(self):
        self.conf('[structural-llm-wiki-settings]\nlarge_source_kb = 200\nmax_quote_words = 25\n')
        s = config.load_settings(self.root)
        self.assertEqual((s['large_source_kb'], s['max_quote_words']), (200, 25))
        for key in ('large_source_kb', 'max_quote_words'):
            for value, msg in (('0', 'must be a positive whole number'), ('-5', 'must be a positive whole number'),
                               ('"50"', 'must be a whole number')):
                self.conf(f'[structural-llm-wiki-settings]\n{key} = {value}\n')
                problems = config.problems(self.root)
                self.assertTrue(problems and msg in problems[0], (key, value, problems))
                self.assertEqual(config.settings(self.root)[key], 50)  # read-only scripts fall back to the defaults

    def test_markers(self):
        self.conf('[structural-llm-wiki-settings]\nreasoning_marker = "*Inference:*"\ngap_marker = ""\n')
        s = config.load_settings(self.root)
        self.assertEqual((s['reasoning_marker'], s['gap_marker']), ('*Inference:*', ''))  # custom, and "" for no marker
        self.conf('[structural-llm-wiki-settings]\nreasoning_marker = ""\ngap_marker = ""\n')  # both off: they may be equal
        self.assertEqual(config.problems(self.root), [])
        for text, msg in [('[structural-llm-wiki-settings]\ngap_marker = 1\n', 'must be a string'),
                          ('[structural-llm-wiki-settings]\ngap_marker = " [gap]"\n', 'no leading or trailing spaces'),
                          ('[structural-llm-wiki-settings]\ngap_marker = "a\\nb"\n', 'one line'),
                          ('[structural-llm-wiki-settings]\nreasoning_marker = "[x]"\ngap_marker = "[x]"\n', 'must differ')]:
            self.conf(text)
            self.assertIn(msg, config.problems(self.root)[0], text)
            self.assertEqual(config.settings(self.root), config.default_settings())  # read-only scripts fall back to the defaults

    def test_lengths(self):
        self.conf('[structural-llm-wiki-settings]\nmax_words = 3000\nabstract_words = [150, 300]\n')
        s = config.load_settings(self.root)
        self.assertEqual((s['max_words'], s['abstract_words']), (3000, [150, 300]))
        for text, msg in [('max_words = -1', 'must be 0'), ('max_words = "big"', 'must be a whole number'), ('max_words = true', 'must be a whole number'),
                          ('abstract_words = [300, 150]', 'min <= max'), ('abstract_words = [150]', '[min, max]'), ('abstract_words = 200', 'must be a list'),
                          ('abstract_words = [0, 100]', 'two positive')]:
            self.conf(f'[structural-llm-wiki-settings]\n{text}\n')
            self.assertIn(msg, config.problems(self.root)[0], text)

    def test_obsidian(self):
        self.conf('[structural-llm-wiki-settings.addons.obsidian]\nenabled = true\n')
        self.assertEqual(config.load_settings(self.root)['addons']['obsidian'], {'enabled': True, 'show_sources': False, 'vault': 'content'})
        for text, msg in [('[structural-llm-wiki-settings.addons.obsidian]\nenabled = "yes"\n', 'addons.obsidian.enabled must be true or false'),
                          ('[structural-llm-wiki-settings.addons.obsidian]\ncolors = 1\n', 'unknown setting(s) structural-llm-wiki-settings.addons.obsidian.colors'),
                          ('[structural-llm-wiki-settings.addons.slides]\nenabled = true\n', 'unknown add-on(s) structural-llm-wiki-settings.addons.slides'),
                          ('[structural-llm-wiki-settings.addons.obsidian]\nvault = "sllmwiki"\n', "addons.obsidian.vault must be 'content' or 'root', not 'sllmwiki'"),
                          ('[structural-llm-wiki-settings.addons.obsidian]\nvault = 1\n', 'addons.obsidian.vault must be a string'),
                          ('[structural-llm-wiki-settings]\naddons = 1\n', 'holds a table per add-on'),
                          ('[structural-llm-wiki-settings]\nobsidian = true\n', 'unknown setting(s) structural-llm-wiki-settings.obsidian'),  # add-ons have their own tables
                          ('[structural-llm-wiki-settings.sphinx]\nenabled = false\n', 'unknown setting(s) structural-llm-wiki-settings.sphinx')]:
            self.conf(text)
            self.assertIn(msg, config.problems(self.root)[0], text)
        self.conf('[structural-llm-wiki-settings.addons.sphinx]\nformats = ["pdf"]\n')
        self.assertEqual(config.load_settings(self.root)['addons']['sphinx']['formats'], ['pdf'])
        self.conf('[structural-llm-wiki-settings\n')
        self.assertEqual(config.settings(self.root)['addons']['obsidian'], config.OBSIDIAN_DEFAULTS)

    def test_add_addon_tables(self):
        full = config.render()
        self.assertEqual(config.add_addon_tables(full), (full, []))  # current: left alone
        older = '[structural-llm-wiki-settings]\nmax_words = 0\n\n# Narrative templates: …\n[structural-llm-wiki-templates]\n'
        text, changes = config.add_addon_tables(older)
        self.assertEqual(changes, [('obsidian', 'added'), ('sphinx', 'added'), ('mdbook', 'added')])
        self.assertIn('[structural-llm-wiki-settings.addons.obsidian]\nenabled = false        # true turns the add-on on\n', text)
        data = loads(text)
        self.assertEqual(data['structural-llm-wiki-settings'], {'max_words': 0, 'addons': {
            'obsidian': {'enabled': False, 'show_sources': False, 'vault': 'content'},
            'sphinx': {'enabled': False, 'formats': ['html', 'epub', 'pdf']}, 'mdbook': {'enabled': False, 'formats': ['html', 'pdf']}}})
        self.assertLess(text.index('[structural-llm-wiki-settings.addons.obsidian]'), text.index('[structural-llm-wiki-settings.addons.sphinx]'))  # template order
        self.assertLess(text.index('[structural-llm-wiki-settings.addons.sphinx]'), text.index('[structural-llm-wiki-settings.addons.mdbook]'))
        self.assertLess(text.index('[structural-llm-wiki-settings.addons.mdbook]'), text.index('# Narrative templates'))  # before the next table's notes
        self.assertIn('# mdBook book add-on: the same book', text)  # each table with its own notes
        self.assertIn('# Sphinx book add-on: this wiki built as a book', text)  # with its notes
        self.assertIn('# Obsidian add-on, for reading this wiki', text)
        self.assertEqual(config.add_addon_tables(text), (text, []))
        start = full.index('[structural-llm-wiki-settings.addons.mdbook]')
        text, changes = config.add_addon_tables(full[:start] + full[full.index('formats', start):].split('\n', 1)[1])
        self.assertEqual(changes, [('mdbook', 'added')])  # a wiki from before the mdBook table
        self.assertEqual(loads(text)['structural-llm-wiki-settings']['addons']['mdbook'], config.MDBOOK_DEFAULTS)
        self.assertLess(text.index('[structural-llm-wiki-settings.addons.sphinx]'), text.index('[structural-llm-wiki-settings.addons.mdbook]'))  # after the last settings table
        text, changes = config.add_addon_tables('[structural-llm-wiki-settings.addons.obsidian]\nenabled = true\n')  # a key missing: added
        self.assertEqual(loads(text)['structural-llm-wiki-settings']['addons']['obsidian'], {'enabled': True, 'show_sources': False, 'vault': 'content'})
        self.assertEqual(changes, [('obsidian', 'completed'), ('sphinx', 'added'), ('mdbook', 'added')])  # the table was there: keys added
        text, changes = config.add_addon_tables('[structural-llm-wiki-settings.addons.sphinx]\nenabled = false\n\n# next\n[other]\nx = 1\n')  # an older table: its new keys come with their comments
        self.assertIn('[structural-llm-wiki-settings.addons.sphinx]\nenabled = false\nformats = ["html", "epub", "pdf"]   # any of html, epub, pdf\n', text)
        self.assertIn('\n\n# next\n[other]', text)
        self.assertEqual(loads(text)['other'], {'x': 1})
        self.assertEqual([c for c, _ in config.add_addon_tables('')[1]], ['obsidian', 'sphinx', 'mdbook'])
        self.assertEqual(config.add_addon_tables('[x\n'), ('[x\n', []))  # unparsable: unchanged

    def test_book_add_ons_stay_off_until_built(self):
        settings = config.load_settings(self.root)['addons']
        self.assertEqual((settings['sphinx'], settings['mdbook']), ({'enabled': False, 'formats': ['html', 'epub', 'pdf']}, {'enabled': False, 'formats': ['html', 'pdf']}))
        self.conf('[structural-llm-wiki-settings.addons.sphinx]\nenabled = false\n\n[structural-llm-wiki-settings.addons.mdbook]\nenabled = false\n')
        self.assertEqual(config.problems(self.root), [])
        for name, label in (('sphinx', 'Sphinx'), ('mdbook', 'mdBook')):
            self.conf(f'[structural-llm-wiki-settings.addons.{name}]\nenabled = true\n')
            problem = config.problems(self.root)[0]
            self.assertIn(f'structural-llm-wiki-settings.addons.{name}.enabled must be false for now: the {label} book add-on is planned', problem)
            self.assertEqual(config.settings(self.root)['addons'][name]['enabled'], False)  # read-only scripts fall back to the defaults
        self.conf('[structural-llm-wiki-settings.addons.sphinx]\nformats = ["pdf"]\n\n[structural-llm-wiki-settings.addons.mdbook]\nformats = ["html"]\n')
        settings = config.load_settings(self.root)['addons']
        self.assertEqual((settings['sphinx']['formats'], settings['mdbook']['formats']), (['pdf'], ['html']))
        for text, msg in [('[structural-llm-wiki-settings.addons.sphinx]\nformats = "pdf"\n', 'sphinx.formats must be a list'),
                          ('[structural-llm-wiki-settings.addons.sphinx]\nformats = []\n', 'sphinx.formats must list one or more of html, epub, pdf'),
                          ('[structural-llm-wiki-settings.addons.mdbook]\nformats = ["html", "epub"]\n', 'mdbook.formats must list one or more of html, pdf, each once (not epub)'),
                          ('[structural-llm-wiki-settings.addons.sphinx]\nformats = ["pdf", "pdf"]\n', 'each once'),
                          ('[structural-llm-wiki-settings.addons.sphinx]\nenabled = "yes"\n', 'sphinx.enabled must be true or false'),
                          ('[structural-llm-wiki-settings.addons.sphinx]\ntheme = 1\n', 'unknown setting(s) structural-llm-wiki-settings.addons.sphinx.theme')]:
            self.conf(text)
            self.assertIn(msg, config.problems(self.root)[0], text)

    def test_templates_config(self):
        empty = {'default': None, 'exclude': [], 'templates': {}}
        self.assertEqual((config.load_templates_config(self.root), config.templates_config(self.root)), (empty, empty))
        self.conf('[structural-llm-wiki-templates]\ndefault = "runbook"\nexclude = ["comparison"]\n\n'
                  '[structural-llm-wiki-templates.runbook]\ntemplate = "templates\\\\runbook/template.md"\nguide = "templates/runbook/guide.md/"\n'
                  'max_words = 800\n\n[structural-llm-wiki-templates.survey]\nabstract_words = [150, 300]\n')
        self.assertEqual(config.load_templates_config(self.root), {
            'default': 'runbook', 'exclude': ['comparison'],
            'templates': {'runbook': {'template': 'templates/runbook/template.md', 'guide': 'templates/runbook/guide.md', 'max_words': 800},
                          'survey': {'abstract_words': [150, 300]}}})
        T = '[structural-llm-wiki-templates]\n'
        for text, msg in [('[structural-llm-wiki-templates.survey]\nmax_words = 0\n', 'max_words must be a positive'),
                          ('[structural-llm-wiki-templates.survey]\nabstract_words = [9, 1]\n', 'min <= max'),
                          ('[structural-llm-wiki-templates.survey]\ncolour = 1\n', 'unknown key(s) colour'),
                          ('[structural-llm-wiki-templates.survey]\nguide = ""\n', 'must be a path'),
                          ('[structural-llm-wiki-templates.survey]\nguide = "C:/x.md"\n', 'inside the repository'),
                          ('[structural-llm-wiki-templates."Bad"]\n', 'not a valid template name'),
                          (T + 'survey = 3\n', 'must be a table'), (T + 'default = ""\n', 'default must be'),
                          (T + 'exclude = [1]\n', 'exclude must be'), ('structural-llm-wiki-templates = 3\n', 'must be a table')]:
            self.conf(text)
            self.assertIn(msg, config.problems(self.root)[0], text)
            self.assertEqual(config.templates_config(self.root), empty)

    def test_add_templates_notes(self):
        full = config.render({'templates': 'tmpl'})
        self.assertEqual(config.add_templates_notes(full), (full, False))  # a current file has the section
        text, added = config.add_templates_notes('[structural-llm-wiki-settings]\nx = 1\n', 'tmpl')
        self.assertTrue(added)
        self.assertTrue(text.endswith('#   guide = "tmpl/survey/guide.md"\n'))
        self.assertIn('\n[structural-llm-wiki-templates]\n# default = ', text)
        self.assertEqual(loads(text)['structural-llm-wiki-templates'], {})  # notes only, no values
        older = '[structural-llm-wiki-settings]\nx = 1\n\n# mine\n[structural-llm-wiki-templates.survey]\nmax_words = 3000\n'
        text, added = config.add_templates_notes(older)
        self.assertTrue(added)
        self.assertLess(text.index('[structural-llm-wiki-templates]\n'), text.index('# mine\n[structural-llm-wiki-templates.survey]'))  # before the tables, comment kept with its table
        self.assertEqual(loads(text)['structural-llm-wiki-templates'], {'survey': {'max_words': 3000}})
        self.assertFalse(config.add_templates_notes(text)[1])  # once

    def test_add_missing_settings(self):
        full = config.render()
        self.assertEqual(config.add_missing_settings(full), (full, []))  # a current file is left alone
        older = '[structural-llm-wiki-paths]\ngroomed = "notes"\n\n[structural-llm-wiki-settings]\nslice_large_sources = false   # mine\n\n[other-tool]\nx = 1\n'
        text, added = config.add_missing_settings(older)
        self.assertEqual(added, ['large_source_kb', 'reasoning_marker', 'gap_marker', 'max_words', 'abstract_words', 'max_quote_words'])
        self.assertIn('slice_large_sources = false   # mine\nlarge_source_kb = 50         # a source above this size is large', text)  # added inside the table, after the user's line, with the notes
        self.assertIn('gap_marker = "[sllmwiki_gap]"', text)
        self.assertIn('"" writes no marker', text)
        data = loads(text)
        self.assertEqual((data['structural-llm-wiki-settings']['slice_large_sources'], data['other-tool'], data['structural-llm-wiki-paths']), (False, {'x': 1}, {'groomed': 'notes'}))
        noted = '[structural-llm-wiki-settings]\nslice_large_sources = true\n\n# notes on the next table\n# more notes\n[structural-llm-wiki-templates]\n'
        text, _ = config.add_missing_settings(noted)  # the next table's notes stay with it
        self.assertLess(text.index('abstract_words = []'), text.index('\n\n# notes on the next table\n# more notes\n[structural-llm-wiki-templates]'))
        self.assertEqual(loads(text)['structural-llm-wiki-settings'], config.SETTING_DEFAULTS)
        text, added = config.add_missing_settings('[structural-llm-wiki-paths]\ngroomed = "notes"\n')  # no settings table: one is appended
        self.assertEqual(added, list(config.SETTING_DEFAULTS))
        self.assertEqual(loads(text)['structural-llm-wiki-settings'], config.SETTING_DEFAULTS)
        self.assertEqual(loads(config.add_missing_settings('')[0])['structural-llm-wiki-settings'], config.SETTING_DEFAULTS)
        self.assertEqual(config.add_missing_settings('[paths\n'), ('[paths\n', []))  # unparsable: unchanged
        self.assertEqual(config.add_missing_settings('structural-llm-wiki-settings = 1\n')[1], list(config.SETTING_DEFAULTS))

    def test_content_folder(self):
        L = config.Layout({'content': 'kb', 'tags': 'tags/tags.yaml'})
        self.assertEqual((L.content, L.ingested, L.groomed_manifest, L.tags, L.index, L.templates),
                         ('kb', 'kb/ingested', 'kb/groomed/manifest.yaml', 'kb/tags/tags.yaml', 'SLLMWIKI_INDICES.md', 'templates'))
        self.assertEqual(L.raw['ingested'], 'ingested')  # as Config.toml writes it
        self.assertEqual(config.Layout().ingested, 'ingested')  # no content folder: the repository root
        self.conf('[structural-llm-wiki-paths]\ncontent = "sllmwiki/"\n')
        self.assertEqual(config.load_layout(self.root).groomed, 'sllmwiki/groomed')
        for text, msg in [('content = "sllmwiki"\nindex = "sllmwiki/MAP.md"', 'index = "sllmwiki/MAP.md" must be outside the content folder'),
                          ('content = "sllmwiki"\ntemplates = "sllmwiki/templates"', 'templates = "sllmwiki/templates" must be outside the content folder'),
                          ('content = "sllmwiki"\ningested = "../sources"', 'must not contain empty, "." or ".." parts'),
                          ('content = "sllmwiki"\ngroomed = "/abs"', 'must be relative to the content folder'),
                          ('content = "../out"', 'must not contain'),
                          ('content = ".github/kb"', 'must not be inside .github/')]:
            self.conf(f'[structural-llm-wiki-paths]\n{text}\n')
            self.assertIn(msg, config.problems(self.root)[0], text)
        self.conf('[structural-llm-wiki-paths]\ncontent = "."\nindex = "MAP.md"\n')
        self.assertEqual(config.problems(self.root), [])

    def test_render_and_history(self):
        text = config.render({'groomed': 'narratives'})
        self.assertEqual(loads(text)['structural-llm-wiki-paths'], {**config.DEFAULTS, 'content': 'sllmwiki', 'groomed': 'narratives'})  # a new wiki's content folder
        self.assertEqual(config.history(self.root), [])  # not a git repository
        env = {**os.environ, 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@t'}

        def commit(text):
            self.conf(text)
            subprocess.run(['git', '-C', self.root, 'add', '-A'], check=True, env=env)
            subprocess.run(['git', '-C', self.root, 'commit', '-qm', 'c'], check=True, env=env)
        subprocess.run(['git', '-C', self.root, 'init', '-q'], check=True)
        commit('[structural-llm-wiki-paths]\ngroomed = "first"\n')
        commit('[paths\n')  # a broken version is skipped
        commit('[structural-llm-wiki-paths]\ngroomed = "second"\nnope = "x"\n')
        commit('[structural-llm-wiki-paths]\ncontent = "kb"\ngroomed = "third"\nindex = "MAP.md"\n')  # resolved through that commit's content folder
        self.assertEqual(config.history(self.root), [{'content': 'kb', 'groomed': 'kb/third', 'index': 'MAP.md'},
                                                     {'content': '.', 'groomed': 'second'}, {'content': '.', 'groomed': 'first'}])
        with mock.patch.object(config, 'TEMPLATE', os.path.join(self.root, 'missing')), self.assertRaises(OSError):
            config.render()


if __name__ == '__main__':
    unittest.main()
