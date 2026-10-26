"""Tests for scripts/init.py, the wiki templates, and scripts/review-checklist.py."""

import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import helpers
from lib import config, layout

GIT_ENV = {'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@example.com', 'GIT_COMMITTER_NAME': 't',
           'GIT_COMMITTER_EMAIL': 't@example.com', 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}


class Init(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='init-')
        self.env = mock.patch.dict(os.environ, GIT_ENV)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.root, ignore_errors=True)

    def init(self, *argv):
        return helpers.run('init.py', ['--root', self.root, *argv])

    def read(self, rel):
        return helpers.read(self.root, rel)

    def test_a_new_wiki(self):
        r = self.init('--name', 'demo-wiki', '--commit', '--prompt', 'Set up a wiki.\nFor the team.', '--json')
        self.assertEqual(r.code, 0, r.err)
        done = {d['file']: d['what'] for d in json.loads(r.out)['done']}
        for rel in ('sllmwiki/tags/tags.yaml', 'sllmwiki/sources/manifest.yaml', 'sllmwiki/narratives/manifest.yaml', 'Config.toml',
                    'README.md', 'AGENTS.md', 'CLAUDE.md', '.gitignore', '.claude/settings.json',
                    '.github/workflows/wiki-checks.yml', '.github/workflows/review-checklist.yml', '.github/workflows/release-book.yml'):
            self.assertEqual(done[rel], 'created', rel)
        self.assertEqual(done['SLLMWIKI_INDICES.md'], 'generated')
        self.assertTrue(self.read('README.md').startswith('# demo-wiki\n'))
        self.assertEqual(self.read('CLAUDE.md'), '@AGENTS.md\n')
        self.assertIn('src/actions/wiki-checks@mainline', self.read('.github/workflows/wiki-checks.yml'))
        book = self.read('.github/workflows/release-book.yml')
        self.assertIn('src/actions/release-book@mainline', book)
        self.assertIn('types: [published]', book)
        self.assertIn('[structural-llm-wiki-release]\npdf_book = true', self.read('Config.toml'))
        self.assertEqual(json.loads(self.read('.claude/settings.json'))['enabledPlugins'], {'sllmwiki@structural-llm-wiki': True})
        self.assertEqual(helpers.git(self.root, 'log', '--format=%B').stdout,
                         '[sllmwiki][init] Set up the wiki\n\nPrompt:\n> Set up a wiki.\n> For the team.\n\n')
        self.assertEqual(helpers.git(self.root, 'branch', '--show-current').stdout.strip(), 'mainline')
        self.assertEqual(helpers.run('wiki-check.py', ['--root', self.root, '--visibility', 'private']).code, 0)
        self.assertEqual(config.load(self.root).settings, config.DEFAULTS)  # the template writes every default
        self.assertFalse(os.path.exists(os.path.join(self.root, layout.OBSIDIAN_GRAPH)))  # the add-on is off

    def test_it_commits_only_what_it_wrote(self):
        helpers.write(self.root, 'sllmwiki/Untitled.canvas', '{}')  # the owner's, made in Obsidian
        self.assertEqual(self.init('--commit', '--prompt', 'p').code, 0)
        tracked = helpers.git(self.root, 'ls-files').stdout.split()
        self.assertIn('Config.toml', tracked)
        self.assertNotIn('sllmwiki/Untitled.canvas', tracked)
        self.assertTrue(os.path.isfile(os.path.join(self.root, 'sllmwiki', 'Untitled.canvas')))

    def test_commit_after_a_run_without_it(self):
        # the workflow lays the wiki out, then commits it in a second run, which writes nothing new
        self.assertEqual(self.init('--name', 'demo-wiki').code, 0)
        self.assertEqual(self.init('--commit', '--prompt', 'p').code, 0)
        tracked = helpers.git(self.root, 'ls-files').stdout.split()
        self.assertTrue({'Config.toml', 'sllmwiki/tags/tags.yaml', '.claude/settings.json'} <= set(tracked), tracked)

    def test_a_rerun_changes_nothing_and_commits_nothing(self):
        self.init('--commit', '--prompt', 'p')
        r = self.init('--commit', '--prompt', 'again', '--json')
        self.assertEqual({d['what'] for d in json.loads(r.out)['done']}, {'kept', 'committed'})
        self.assertIn({'what': 'committed', 'file': 'nothing new'}, json.loads(r.out)['done'])
        self.assertEqual(len(helpers.git(self.root, 'log', '--format=%s').stdout.strip().split('\n')), 1)

    def test_a_rerun_keeps_the_wikis_own_and_refreshes_its_own(self):
        self.init()
        helpers.write(self.root, 'README.md', '# Ours\n\nAbout this wiki.\nMore.\n')
        helpers.write(self.root, 'AGENTS.md', '# Our rules\n')
        helpers.write(self.root, '.github/workflows/wiki-checks.yml', 'old\n')
        helpers.write(self.root, 'CLAUDE.md', 'old\n')
        helpers.write(self.root, 'Config.toml', '[structural-llm-wiki-settings]\nmarkers = false\n\n# notes on the next table\n[other-tool]\nx = 1\n')
        helpers.write(self.root, '.claude/settings.json', json.dumps({'permissions': {'allow': ['Bash(ls)']}, 'enabledPlugins': {'other@x': True}}))
        helpers.write(self.root, '.gitignore', 'node_modules/\n')
        r = self.init('--json')
        done = {d['file']: d['what'] for d in json.loads(r.out)['done']}
        self.assertEqual((done['README.md'], done['AGENTS.md']), ('kept', 'kept'))
        self.assertEqual((done['.github/workflows/wiki-checks.yml'], done['CLAUDE.md'], done['Config.toml']), ('updated', 'updated', 'added settings to'))
        self.assertEqual(self.read('README.md'), '# Ours\n\nAbout this wiki.\nMore.\n')
        cfg = self.read('Config.toml')
        self.assertIn('markers = false\nsource_copies = "allow"     # the source policy', cfg)  # added after the wiki's own line, its value kept
        self.assertIn('\n\n# notes on the next table\n[other-tool]\nx = 1\n', cfg)
        self.assertIn('[structural-llm-wiki-addons]\nobsidian = false', cfg)
        self.assertEqual(config.load(self.root).settings['markers'], False)
        settings = json.loads(self.read('.claude/settings.json'))
        self.assertEqual((settings['permissions'], settings['enabledPlugins']), ({'allow': ['Bash(ls)']}, {'other@x': True, 'sllmwiki@structural-llm-wiki': True}))
        self.assertTrue(self.read('.gitignore').startswith('node_modules/\n\n# Obsidian'))

    def test_githubs_starter_readme_is_replaced(self):
        helpers.write(self.root, 'README.md', '# demo-wiki\nA new repository.\n')
        r = self.init('--name', 'demo-wiki')
        self.assertIn('replaced GitHub\'s starter README.md', r.out)
        self.assertIn('/sllmwiki:query', self.read('README.md'))

    def test_a_guarded_settings_file_is_reported_not_fatal(self):
        # a sandbox guards .claude/settings.json from scripts: init reports it, and writes the rest
        import init
        guarded, real = os.path.join(self.root, '.claude', 'settings.json'), open

        def refuse(path, *a, **k):
            if str(path) == guarded:
                raise PermissionError(13, 'Permission denied', path)
            return real(path, *a, **k)
        for existing in (False, True):
            if existing:
                helpers.write(self.root, '.claude/settings.json', '{}')
            run = init.Init(self.root, 'demo-wiki')
            with mock.patch('builtins.open', refuse):
                run.settings()
            self.assertEqual(run.done, [(init.SKIPPED, '.claude/settings.json')])

    def test_empty_placeholders_arent_unrelated(self):
        # the eval sandbox on Linux puts empty files and folders over the config files it guards
        helpers.write(self.root, '.bashrc', '')
        helpers.write(self.root, '.mcp.json', '')
        os.makedirs(os.path.join(self.root, '.idea'))
        self.assertEqual(self.init('--name', 'demo-wiki').code, 0)

    def test_unrelated_files(self):
        helpers.write(self.root, 'src/app.py', 'print()\n')
        helpers.write(self.root, 'package.json', '{}')
        r = self.init()
        self.assertEqual(r.code, 1)
        self.assertIn('holds files that aren\'t a wiki\'s (package.json, src)', r.err)
        self.assertEqual(self.init('--force').code, 0)
        self.assertEqual(self.init().code, 0)  # a wiki now, so it isn't asked again
        for i in range(10):
            helpers.write(self.root, f'more/f{i}', '')
        other = tempfile.mkdtemp(prefix='init-many-')
        try:
            for i in range(10):
                helpers.write(other, f'f{i}.txt', 'notes\n')
            self.assertIn(', …)', helpers.run('init.py', ['--root', other]).err)
        finally:
            shutil.rmtree(other)

    def test_obsidian_add_on(self):
        self.init()
        helpers.write(self.root, 'Config.toml', self.read('Config.toml').replace('obsidian = false', 'obsidian = true'))
        r = self.init('--json')
        self.assertIn({'what': 'created', 'file': layout.OBSIDIAN_GRAPH}, json.loads(r.out)['done'])
        graph = json.loads(self.read(layout.OBSIDIAN_GRAPH))
        self.assertEqual(graph['search'], '-path:sources')
        helpers.write(self.root, layout.OBSIDIAN_GRAPH, '{"mine": true}')
        self.init()
        self.assertEqual(self.read(layout.OBSIDIAN_GRAPH), '{"mine": true}')  # the wiki's from then on

    def test_the_graph_is_shared_only_with_the_add_on(self):
        self.init()
        off = self.read('.gitignore')
        self.assertIn('sllmwiki/.obsidian/*\n', off)
        self.assertNotIn('graph.json', off)  # off: a person's own graph is never committed
        on = self.read('Config.toml').replace('obsidian = false', 'obsidian = true')
        helpers.write(self.root, 'Config.toml', on)
        self.init()
        self.assertIn("# with the Obsidian add-on, the graph's settings are shared\n!sllmwiki/.obsidian/graph.json\n", self.read('.gitignore'))
        helpers.write(self.root, 'Config.toml', on.replace('obsidian = true', 'obsidian = false'))
        self.init()
        self.assertEqual(self.read('.gitignore'), off)

    def test_an_earlier_gitignore_is_brought_up_to_date(self):
        earlier = ("node_modules/\n\n# Obsidian: share only the graph settings, not each person's workspace\n"
                   'sllmwiki/.obsidian/*\n!sllmwiki/.obsidian/graph.json\n.DS_Store\n')
        helpers.write(self.root, '.gitignore', earlier)
        self.init()
        self.assertEqual(self.read('.gitignore'), "node_modules/\n\n# Obsidian: each person's settings are their own\nsllmwiki/.obsidian/*\n.DS_Store\n")
        helpers.write(self.root, '.gitignore', earlier)
        helpers.write(self.root, 'Config.toml', self.read('Config.toml').replace('obsidian = false', 'obsidian = true'))
        self.init()
        self.assertEqual(self.read('.gitignore'), "node_modules/\n\n# Obsidian: each person's settings are their own\nsllmwiki/.obsidian/*\n"
                                                  "# with the Obsidian add-on, the graph's settings are shared\n!sllmwiki/.obsidian/graph.json\n.DS_Store\n")

    def test_the_action_ref_follows_the_plugin_version(self):
        mod = helpers.load_script('init.py')
        plugin = helpers.write(self.root, 'plugin.json', json.dumps({'name': 'sllmwiki', 'version': '1.2.0'}))
        with mock.patch.object(mod, 'PLUGIN_JSON', plugin):
            self.assertEqual(mod.action_ref(), 'v1.2.0')
            helpers.write(self.root, 'plugin.json', '{')
            self.assertEqual(mod.action_ref(), 'mainline')
        with mock.patch.object(mod, 'PLUGIN_JSON', '/nope.json'):
            self.assertEqual(mod.action_ref(), 'mainline')

    def test_refusals(self):
        self.assertEqual(self.init('--commit').code, 2)
        self.assertIn('no such folder', helpers.run('init.py', ['--root', '/nope/nowhere']).err)
        self.init()
        helpers.write(self.root, 'Config.toml', '[structural-llm-wiki-settings]\nmarkers = 1\n')
        self.assertIn('Config.toml has problems', self.init().err)
        helpers.write(self.root, 'Config.toml', '')
        helpers.write(self.root, '.claude/settings.json', '{')
        self.assertIn('isn\'t valid JSON', self.init().err)

    def test_a_failing_commit(self):
        self.init()
        hook = helpers.write(self.root, '.git/hooks/pre-commit', '#!/bin/sh\necho no\nexit 1\n')
        os.chmod(hook, 0o755)
        r = self.init('--commit', '--prompt', 'p')
        self.assertEqual(r.code, 1)
        self.assertIn('git commit: no', r.err)

    def test_a_rerun_adds_the_release_table(self):
        mod = helpers.load_script('init.py')
        template = helpers.read(mod.WIKI, 'Config.toml')
        out = mod.add_missing_settings('[structural-llm-wiki-settings]\nmarkers = true\n', template)
        self.assertIn('\n[structural-llm-wiki-release]\npdf_book = true', out)
        self.assertEqual(mod.add_missing_settings(out, template), out)

    def test_ask_and_set(self):
        r = self.init('--ask', '--json')
        data = json.loads(r.out)
        self.assertTrue(data['first_setup'])
        keys = [q['key'] for q in data['ask']]
        self.assertEqual(sorted(keys), sorted(helpers.load_script('init.py').ASK))
        self.assertNotIn('max_quote_words', keys)  # kept at its default unless edited
        q = next(q for q in data['ask'] if q['key'] == 'pdf_book')
        self.assertEqual((q['table'], q['value'], q['about']), ('structural-llm-wiki-release', True, 'a PDF: share, print, read anywhere'))
        self.assertTrue(all(q['about'] for q in data['ask']))
        self.assertFalse(os.path.exists(os.path.join(self.root, 'Config.toml')))  # --ask writes nothing
        r = self.init('--name', 'w', '--set', 'language=zh-Hans', '--set', 'epub_book=TRUE', '--set', 'title=我的 "笔记"',
                      '--set', 'smes_exclude=@me, dependabot', '--set', 'max_quote_words=30', '--set', 'obsidian=true')
        self.assertEqual(r.code, 0, r.err)
        cfg = self.read('Config.toml')
        for line in ('language = "zh-Hans"        # narratives', 'epub_book = true            # an EPUB',
                     'smes_exclude = ["@me", "dependabot"] # never', 'max_quote_words = 30        # the longest'):
            self.assertIn(line, cfg)
        self.assertEqual(config.load(self.root).release['title'], '我的 "笔记"')
        self.assertTrue(os.path.isfile(os.path.join(self.root, 'sllmwiki', '.obsidian', 'graph.json')))  # the answer took effect in the same run
        self.assertIn('nothing new to ask about', self.init('--ask').out)
        # a rerun asks only about settings the plugin added since; --set changes one in place
        helpers.write(self.root, 'Config.toml', cfg.replace('author = ""                 # its author; empty: the title\n', ''))
        self.assertEqual([q['key'] for q in json.loads(self.init('--ask', '--json').out)['ask']], ['author'])
        self.assertEqual(self.init('--ask').out, 'author = "": its author; empty: the title\ninit: 1 setting(s) to ask about\n')
        r = self.init('--set', 'author=Ann', '--set', 'markers=false')
        self.assertEqual(r.code, 0, r.err)
        self.assertIn('author = "Ann"', self.read('Config.toml'))
        self.assertIn('markers = false             # false', self.read('Config.toml'))

    def test_set_refusals(self):
        for pair, says in (('markers=maybe', 'true or false'), ('max_quote_words=lots', 'a number'), ('colour=red', 'settings are author'),
                           ('nokey', 'settings are'), ('source_copies=some', 'must be "allow" or "links-only"')):
            r = self.init('--name', 'w', '--set', pair)
            self.assertEqual((r.code, says in r.err), (2, True), (pair, r.err))
        self.assertFalse(os.path.exists(os.path.join(self.root, 'Config.toml')))

    def test_settings_for_a_missing_table(self):
        mod = helpers.load_script('init.py')
        out = mod.add_missing_settings('[structural-llm-wiki-settings]\nmarkers = true\n', '[structural-llm-wiki-addons]\nobsidian = false\n')
        self.assertEqual(out, '[structural-llm-wiki-settings]\nmarkers = true\n\n[structural-llm-wiki-addons]\nobsidian = false\n')


class ReviewChecklist(unittest.TestCase):
    def check(self, body, *argv):
        with mock.patch.dict(os.environ, {'PR_BODY': body}):
            return helpers.run('review-checklist.py', list(argv))

    def test_ticked_and_not(self):
        body = '## Review checklist\n\n- [x] Tags\n- [ ] Sources\n* [X] Narrative\n\n## Sources\n\n- [ ] not a review box\n'
        r = self.check(body)
        self.assertEqual((r.code, r.out), (1, 'not ticked: Sources\nreview-checklist: 2 of 3 ticked\n'))
        self.assertEqual(self.check(body.replace('- [ ] Sources', '- [x] Sources')).code, 0)
        self.assertEqual(self.check(body.replace('\n', '\r\n').replace('- [ ] Sources', '- [x] Sources')).code, 0)

    def test_not_a_runs_pull_request(self):
        r = self.check('Fixes a typo.\n\n- [ ] something\n')
        self.assertEqual(r.code, 0)
        self.assertIn('nothing to check', r.out)

    def test_from_a_file_and_usage(self):
        tmp = tempfile.mkdtemp()
        try:
            path = helpers.write(tmp, 'body.md', '# Review checklist\n- [ ] One\n')
            self.assertEqual(helpers.run('review-checklist.py', ['--file', path]).code, 1)
        finally:
            shutil.rmtree(tmp)
        self.assertEqual(helpers.run('review-checklist.py', ['--bogus']).code, 2)


class Templates(unittest.TestCase):
    def test_the_wiki_config_template_is_valid_and_complete(self):
        text = helpers.read(os.path.join(helpers.SKILL_DIR, 'templates', 'wiki'), 'Config.toml')
        c = config.parse(text)
        self.assertEqual((c.settings, c.addons), (config.DEFAULTS, config.ADDON_DEFAULTS))
        for key in list(config.DEFAULTS) + list(config.ADDON_DEFAULTS):
            self.assertIn(f'\n{key} = ', text)


if __name__ == '__main__':
    unittest.main()
