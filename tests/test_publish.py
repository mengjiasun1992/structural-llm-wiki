"""Tests for scripts/publish.py and scripts/preflight.sh: a run's branch, commits and
pull request against a local bare origin, with a fake gh that records its calls."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

import helpers

FAKE_GH = '''#!/usr/bin/env bash
echo "$@" >> "{log}"
case "$1 $2" in
  "auth status") exit {auth} ;;
  "pr create") echo "https://github.com/o/r/pull/7" ;;
  "pr edit") exit {edit} ;;
  "pr view") cat "{view}" 2>/dev/null || exit 1 ;;
esac
'''
GIT_ENV = {'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@example.com', 'GIT_COMMITTER_NAME': 't',
           'GIT_COMMITTER_EMAIL': 't@example.com', 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}


class Publish(helpers.WikiTestCase):
    def setUp(self):
        super().setUp()
        self.outside = tempfile.mkdtemp(prefix='publish-')  # the remote and the fake gh live outside the wiki
        self.origin = os.path.join(self.outside, 'origin.git')
        helpers.git(self.outside, 'init', '-q', '--bare', '-b', 'mainline', self.origin)
        helpers.git(self.root, 'remote', 'add', 'origin', self.origin)
        helpers.git(self.root, 'push', '-q', '-u', 'origin', 'mainline')
        helpers.git(self.root, 'remote', 'set-head', 'origin', 'mainline')
        self.bin = os.path.join(self.outside, 'bin')
        self.log = os.path.join(self.outside, 'gh.log')
        self.fake_gh()
        self.env = mock.patch.dict(os.environ, dict(GIT_ENV, PATH=self.bin + os.pathsep + os.environ['PATH'],
                                                   CLAUDE_CODE_SESSION_ID='', CLAUDE_CONFIG_DIR=self.outside))
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.outside, ignore_errors=True)
        super().tearDown()

    def fake_gh(self, auth=0, edit=0):
        helpers.write(self.bin, 'gh', FAKE_GH.format(log=self.log, auth=auth, edit=edit, view=os.path.join(self.outside, 'view.json')))
        os.chmod(os.path.join(self.bin, 'gh'), 0o755)

    def pub(self, *argv):
        return helpers.run('publish.py', ['--root', self.root, *argv])

    def summary(self, step, **data):
        return self.pub('summary', step, '--json', json.dumps(data))

    def test_a_whole_run(self):
        r = self.pub('start', 'alpha-retries', '--title', 'How do alpha systems retry?', '--prompt', 'Build up alpha retries.\nKeep it short.')
        self.assertEqual(r.out, 'started sllmwiki/alpha-retries from origin/mainline\n')
        self.assertEqual(helpers.git(self.root, 'branch', '--show-current').stdout.strip(), 'sllmwiki/alpha-retries')
        self.write('sllmwiki/sources/new.md', '# New\n')
        self.write('sllmwiki/.obsidian/workspace.json', '{}')  # Obsidian's, never committed by a run
        self.assertEqual(self.summary('ingest', title='Sources', checklist=['Sources: new is one you\'d trust'],
                                      decisions=['Re-ingest beta-doc?'], body='Saved new.').code, 0)
        r = self.pub('commit', 'ingest', '--tags', 'leaf-a', '--subject', 'ingest new raw sources related to topic: alpha retries')
        self.assertEqual(r.code, 0, r.err)
        msg = helpers.git(self.root, 'log', '-1', '--format=%B').stdout
        self.assertEqual(msg, '[sllmwiki][ingest][leaf-a] ingest new raw sources related to topic: alpha retries\n\nSaved new.\n\n'
                              'Prompt:\n> Build up alpha retries.\n> Keep it short.\n\n')  # git log adds a newline
        committed = helpers.git(self.root, 'show', '--name-only', '--format=').stdout.split()
        self.assertEqual(committed, ['sllmwiki/sources/new.md'])
        self.write('sllmwiki/Config.toml', '[structural-llm-wiki-settings]\n')
        self.write('sllmwiki/.obsidian/graph.json', '{}')  # the add-on's, which init writes; .gitignore shares it
        self.write('.gitignore', 'sllmwiki/.obsidian/*\n!sllmwiki/.obsidian/graph.json\n')
        self.pub('commit', 'init', '--subject', 'Bring the wiki up to date')  # init has no tags
        committed = helpers.git(self.root, 'show', '--name-only', '--format=').stdout.split()
        self.assertIn('sllmwiki/.obsidian/graph.json', committed)
        self.assertNotIn('sllmwiki/.obsidian/workspace.json', committed)  # each person's own, ignored
        self.assertEqual(helpers.git(self.root, 'log', '-1', '--format=%s').stdout.strip(), '[sllmwiki][init] Bring the wiki up to date')
        r = self.pub('pr')
        self.assertEqual(r.out, 'opened https://github.com/o/r/pull/7\n')
        with open(self.log) as f:
            calls = f.read()
        self.assertIn('pr create --base mainline --head sllmwiki/alpha-retries --title How do alpha systems retry?', calls)
        body = self.read_state('pr.md')
        self.assertTrue(body.startswith('## Review checklist\n'))
        self.assertIn('- [ ] Sources: new is one you\'d trust\n', body)
        self.assertIn('## Decisions for you\n\n- Re-ingest beta-doc?\n', body)
        self.assertIn('## Sources\n\nSaved new.\n', body)
        self.assertIn('## Prompt\n\n> Build up alpha retries.\n> Keep it short.\n', body)
        self.assertIn('## Run\n\n- Time: 0 min since the run started\n- Turns and tokens: no session transcript', body)
        self.assertLess(body.index('## Run'), body.index('## Prompt'))
        self.assertIn('sllmwiki/alpha-retries', helpers.git(self.origin, 'branch').stdout)
        self.write('sllmwiki/narratives/a.md', '# A?\n')
        self.summary('narrative', title='Why A?', checklist=['A reads well'], body='Wrote A.')
        self.pub('commit', 'narrative', '--tags', 'leaf-a', '--subject', 'Why A?')
        self.write('sllmwiki/narratives/b.md', '# B?\n')
        self.summary('narrative', title='Why B?', checklist=['B reads well'], body='Wrote B.')
        self.pub('commit', 'narrative', '--tags', 'leaf-a', '--subject', 'Why B?')
        self.assertIn('\n\nWrote B.\n\nPrompt:', helpers.git(self.root, 'log', '-1', '--format=%B').stdout)  # each commit its own report
        self.summary('narrative', title='Why A?', checklist=['A reads well, reworked'], body='Rewrote A.')  # replaces A's
        r = self.pub('pr', '--cost', '1.5')
        self.assertEqual(r.out, 'updated https://github.com/o/r/pull/7\n')
        self.assertIn('- Cost: $1.50\n', self.read_state('pr.md'))
        self.pub('pr')
        self.assertIn('- Cost: $1.50\n', self.read_state('pr.md'))  # kept until a new figure
        self.assertIn('pr edit https://github.com/o/r/pull/7 --body-file', open(self.log).read())
        body = self.read_state('pr.md')
        self.assertLess(body.index('## Sources'), body.index('## Why B?'))  # steps in pipeline order
        self.assertLess(body.index('## Why B?'), body.index('## Why A?'))  # then as last recorded
        self.assertEqual((body.count('## Why A?'), body.count('Wrote A.')), (1, 0))
        self.assertIn('- [ ] A reads well, reworked\n', body)
        self.assertIn('summaries: ingest, narrative.why-b, narrative.why-a; pull request: https://github.com/o/r/pull/7', self.pub('status').out)
        self.summary('lint', title='Lint: A and B', checklist=['Lint: A and B'], body='Fixed two.')
        self.summary('lint', title='Lint: context first', checklist=['Lint: context first'], body='Fixed one.')
        body = self.pub('pr') and self.read_state('pr.md')
        self.assertTrue('## Lint: A and B' in body and '## Lint: context first' in body)  # a second lint keeps the first
        self.assertIn('- [ ] Lint: A and B\n- [ ] Lint: context first\n', body)
        helpers.git(self.root, 'switch', '-q', 'mainline')
        self.pub('start', 'beta-cache', '--title', 'Beta?', '--prompt', 'p')  # the next run starts clean
        self.assertIn('summaries: none; pull request: not opened yet', self.pub('status').out)
        self.assertFalse(os.path.exists(self.state_path('pr.md', 'beta-cache')))
        r = self.pub('resume', 'alpha-retries')  # back to the earlier run, its summaries kept
        self.assertEqual(r.out, 'on sllmwiki/alpha-retries; pull request: https://github.com/o/r/pull/7\n')
        self.assertIn('summaries: ingest, narrative.why-b, narrative.why-a, lint.lint-a-and-b, lint.lint-context-first', self.pub('status').out)
        state = json.loads(self.read_state('run.json'))
        self.assertNotIn('cost', state)  # a rework's own figures, not the first run's
        self.assertGreater(state['started'], '2026')

    def state_path(self, name, slug='alpha-retries'):
        return os.path.join(self.root, '.git', 'sllmwiki', 'runs', slug, name)

    def read_state(self, name, slug='alpha-retries'):
        with open(self.state_path(name, slug), encoding='utf-8') as f:
            return f.read()

    def test_start_refusals(self):
        self.write('sllmwiki/stray.md', 'x')
        r = self.pub('start', 'run', '--title', 't', '--prompt', 'p')
        self.assertEqual(r.code, 1)
        self.assertIn('the working tree has changes', r.err)
        os.remove(os.path.join(self.root, 'sllmwiki/stray.md'))
        self.assertEqual(self.pub('start', 'Bad Slug', '--title', 't', '--prompt', 'p').code, 2)
        self.assertEqual(self.pub('start', 'run', '--title', 't', '--prompt', 'p').code, 0)
        helpers.git(self.root, 'switch', '-q', 'mainline')
        self.assertIn('publish.py resume run', self.pub('start', 'run', '--title', 't', '--prompt', 'p').err)

    def test_a_changed_obsidian_graph_alone_doesnt_stop_a_run(self):
        # a tracked graph.json that Obsidian rewrote is the first (and only) line of git status, " M sllmwiki/..."
        self.write('sllmwiki/.obsidian/graph.json', '{}')
        helpers.git(self.root, 'add', '-f', 'sllmwiki/.obsidian/graph.json')
        helpers.git(self.root, 'commit', '-q', '-m', 'the graph')
        helpers.git(self.root, 'push', '-q', 'origin', 'mainline')
        self.write('sllmwiki/.obsidian/graph.json', '{"moved": true}')
        r = self.pub('start', 'run', '--title', 't', '--prompt', 'p')
        self.assertEqual(r.code, 0, r.err)
        # nor does an init rerun commit it: a tracked graph.json that changed is Obsidian's layout, not init's
        self.write('sllmwiki/Config.toml', '[structural-llm-wiki-settings]\n')
        self.summary('init', title='Init', checklist=['Config'], body='Refreshed.')
        self.assertEqual(self.pub('commit', 'init', '--subject', 'Bring the wiki up to date').code, 0)
        self.assertEqual(helpers.git(self.root, 'show', '--name-only', '--format=').stdout.split(), ['sllmwiki/Config.toml'])
        self.assertIn('sllmwiki/.obsidian/graph.json', helpers.git(self.root, 'status', '--porcelain').stdout)  # left as it is

    def test_a_sandboxs_placeholders_neither_stop_a_run_nor_are_committed(self):
        # on Linux, Claude Code's sandbox puts empty files and folders over the config files it guards
        self.write('.bashrc', '')
        self.write('.claude/settings.local.json', '')
        os.makedirs(os.path.join(self.root, '.idea'))
        r = self.pub('start', 'run', '--title', 't', '--prompt', 'p')
        self.assertEqual(r.code, 0, r.err)
        self.write('sllmwiki/narratives/new.md', '# New\n')
        self.summary('narrative', title='New', checklist=['New'], body='Written.')
        self.assertEqual(self.pub('commit', 'narrative', '--subject', 'New').code, 0)
        self.assertEqual(helpers.git(self.root, 'show', '--name-only', '--format=').stdout.split(), ['sllmwiki/narratives/new.md'])

    def test_a_run_never_writes_git_config(self):
        # Claude Code's sandbox guards .git/config: a lock that exists makes every write to it fail
        os.makedirs(os.path.join(self.root, '.git', 'config.lock'))
        self.assertEqual(self.pub('start', 'run', '--title', 't', '--prompt', 'p').code, 0)
        self.write('sllmwiki/narratives/new.md', '# New\n')
        self.summary('narrative', title='New', checklist=['New'], body='Written.')
        self.assertEqual(self.pub('commit', 'narrative', '--subject', 'New').code, 0)
        r = self.pub('pr')
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(helpers.git(self.root, 'rev-parse', 'origin/sllmwiki/run').stdout, helpers.git(self.root, 'rev-parse', 'HEAD').stdout)

    def test_a_diverged_default_branch_stops_the_run(self):
        helpers.git(self.root, 'commit', '-q', '--allow-empty', '-m', 'local only')
        r = self.pub('start', 'run', '--title', 't', '--prompt', 'p')
        self.assertEqual(r.code, 1)
        self.assertIn('has commits origin/mainline doesn\'t', r.err)

    def test_an_out_of_date_default_branch_is_brought_up_to_date(self):
        other = os.path.join(self.outside, 'other')
        helpers.git(self.outside, 'clone', '-q', self.origin, other)
        helpers.git(other, 'commit', '-q', '--allow-empty', '-m', 'from a teammate')
        helpers.git(other, 'push', '-q', 'origin', 'mainline')
        self.assertEqual(self.pub('start', 'run', '--title', 't', '--prompt', 'p').code, 0)
        self.assertEqual(helpers.git(self.root, 'log', '-1', '--format=%s').stdout.strip(), 'from a teammate')

    def test_commit_refusals(self):
        self.assertIn('no run in progress', self.pub('commit', 'lint', '--tags', 'a', '--subject', 's').err)
        self.pub('start', 'run', '--title', 't', '--prompt', 'p')
        self.assertIn('nothing to commit', self.pub('commit', 'lint', '--tags', 'a', '--subject', 's').err)
        helpers.git(self.root, 'switch', '-q', 'mainline')
        self.assertIn('not on the run\'s branch', self.pub('commit', 'lint', '--tags', 'a', '--subject', 's').err)
        self.assertIn('on sllmwiki/run; pull request: not opened yet', self.pub('resume', 'run').out)
        self.assertIn('no run branch', self.pub('resume', 'other').err)

    def test_summary_refusals(self):
        self.pub('start', 'run', '--title', 't', '--prompt', 'p')
        self.assertIn('at least a "title"', self.pub('summary', 'tags', '--json', '[]').err)
        self.assertIn('"checklist" is a list', self.summary('tags', title='t', checklist='x').err)
        self.assertIn('can\'t read the summary', self.pub('summary', 'tags', '--json', '{').err)
        self.assertIn('can\'t read the summary', self.pub('summary', 'tags', '--file', '/nope.json').err)
        path = helpers.write(self.outside, 's.json', json.dumps({'title': 'Tags'}))
        self.assertEqual(self.pub('summary', 'tags', '--file', path).code, 0)

    def test_without_gh_or_a_remote(self):
        self.pub('start', 'run', '--title', 't', '--prompt', 'p')
        self.fake_gh(auth=1)
        r = self.pub('pr')
        self.assertIn('pushed sllmwiki/run; open the pull request at', r.out)
        mod = helpers.load_script('publish.py')
        real = mod.subprocess.run

        def no_gh(cmd, *a, **k):
            if cmd[0] == 'gh':
                raise FileNotFoundError('gh')  # gh isn't installed
            return real(cmd, *a, **k)
        with mock.patch.object(mod.subprocess, 'run', side_effect=no_gh):
            self.assertIn('open the pull request at', self.pub('pr').out)
        helpers.git(self.root, 'remote', 'remove', 'origin')
        self.assertIn('no remote: the commits stay on sllmwiki/run', self.pub('pr').out)

    def test_a_github_compare_link(self):
        self.pub('start', 'run', '--title', 't', '--prompt', 'p')
        self.fake_gh(auth=1)
        helpers.git(self.root, 'remote', 'set-url', 'origin', 'git@github-work:o/r.git')  # an SSH host alias
        helpers.git(self.root, 'config', f'url.{self.origin}.insteadOf', 'git@github-work:o/r.git')  # so the push reaches the local origin
        r = self.pub('pr')
        self.assertIn('https://github.com/o/r/compare/mainline...sllmwiki/run?expand=1', r.out)

    def test_git_failing(self):
        self.pub('start', 'run', '--title', 't', '--prompt', 'p')
        helpers.git(self.root, 'remote', 'set-url', 'origin', os.path.join(self.outside, 'gone.git'))
        r = self.pub('pr')
        self.assertEqual(r.code, 1)
        self.assertIn('git push', r.err)
        hook = helpers.write(self.root, '.git/hooks/pre-commit', '#!/bin/sh\necho refused by a hook\nexit 1\n')
        os.chmod(hook, 0o755)
        self.write('sllmwiki/sources/new.md', '# New\n')
        r = self.pub('commit', 'ingest', '--tags', 'leaf-a', '--subject', 's')
        self.assertEqual(r.code, 1)
        self.assertIn('git commit: refused by a hook', r.err)

    def test_gh_failing(self):
        self.pub('start', 'run', '--title', 't', '--prompt', 'p')
        self.pub('pr')
        self.fake_gh(edit=1)
        self.assertIn('gh:', self.pub('pr').err)

    def test_not_a_repository_and_no_remote_start(self):
        plain = tempfile.mkdtemp(prefix='plain-')
        try:
            self.assertIn('isn\'t a git repository', helpers.run('publish.py', ['--root', plain, 'status']).err)
        finally:
            shutil.rmtree(plain)
        helpers.git(self.root, 'remote', 'remove', 'origin')
        self.assertEqual(self.pub('start', 'local', '--title', 't', '--prompt', 'p').out, 'started sllmwiki/local from mainline\n')

    def test_default_branch_without_origin_head(self):
        helpers.git(self.root, 'remote', 'set-head', 'origin', '-d')
        self.assertEqual(self.pub('start', 'run', '--title', 't', '--prompt', 'p').out, 'started sllmwiki/run from origin/mainline\n')

    def test_a_run_started_elsewhere_is_rebuilt_from_its_branch_and_pull_request(self):
        self.pub('start', 'alpha-retries', '--title', 'How do alpha systems retry?', '--prompt', 'Build alpha.\n\nShort.')
        self.write('sllmwiki/narratives/a.md', '# A?\n')
        self.summary('narrative', title='Why A?', checklist=['Why A?: answers it'], decisions=['Keep A?'], body='Wrote A.')
        self.pub('commit', 'narrative', '--tags', 'leaf-a', '--subject', 'Why A?')
        self.write('sllmwiki/narratives/b.md', '# B?\n')
        self.summary('narrative', title='Why B?', body='Wrote B.')
        self.pub('commit', 'narrative', '--tags', 'leaf-a', '--subject', 'Why B?')
        self.pub('pr')
        body = self.read_state('pr.md').replace('- [ ] Why A?', '- [x] Why A?')
        helpers.write(self.outside, 'view.json', json.dumps({'url': 'https://github.com/o/r/pull/7', 'title': 'Alpha retries',
                                                             'state': 'OPEN', 'body': body}))
        clone = os.path.join(self.outside, 'clone')  # another clone, with no state
        helpers.git(self.outside, 'clone', '-q', self.origin, clone)
        helpers.git(clone, 'remote', 'set-head', 'origin', 'mainline')
        r = helpers.run('publish.py', ['--root', clone, 'resume', 'alpha-retries'])
        self.assertEqual(r.out, 'on sllmwiki/alpha-retries (its state rebuilt from the branch and pull request); '
                                'pull request: https://github.com/o/r/pull/7\n')
        helpers.write(clone, 'sllmwiki/narratives/a.md', '# A, again?\n')
        helpers.run('publish.py', ['--root', clone, 'summary', 'narrative', '--json',
                                   json.dumps({'title': 'Why A?', 'checklist': ['A again'], 'body': 'Rewrote A.'})])
        helpers.run('publish.py', ['--root', clone, 'commit', 'narrative', '--tags', 'leaf-a', '--subject', 'Why A?'])
        self.assertIn('Prompt:\n> Build alpha.\n>\n> Short.\n', helpers.git(clone, 'log', '-1', '--format=%B').stdout)
        self.assertEqual(helpers.run('publish.py', ['--root', clone, 'pr']).out, 'updated https://github.com/o/r/pull/7\n')
        with open(os.path.join(clone, '.git', 'sllmwiki', 'runs', 'alpha-retries', 'pr.md'), encoding='utf-8') as f:
            rebuilt = f.read()
        self.assertEqual((rebuilt.count('## Why A?'), rebuilt.count('Wrote A.'), rebuilt.count('Rewrote A.'), rebuilt.count('Wrote B.')),
                         (1, 0, 1, 1))
        self.assertIn('- [ ] Why A?: answers it\n', rebuilt)  # unticked again, for the re-review
        self.assertIn('- [ ] A again\n', rebuilt)
        self.assertIn('## Decisions for you\n\n- Keep A?\n', rebuilt)
        self.assertIn('## Prompt\n\n> Build alpha.\n>\n> Short.\n', rebuilt)

    def test_a_rebuilt_run_without_a_pull_request(self):
        self.pub('start', 'alpha-retries', '--title', 't', '--prompt', 'p')
        self.write('sllmwiki/narratives/a.md', '# A?\n')
        self.summary('narrative', title='Why A?', body='Wrote A.')
        self.pub('commit', 'narrative', '--tags', 'leaf-a', '--subject', 'Why A?')
        shutil.rmtree(os.path.join(self.root, '.git', 'sllmwiki'))
        helpers.git(self.root, 'switch', '-q', 'mainline')
        self.assertIn('(its state rebuilt', self.pub('resume', 'alpha-retries').out)
        state = json.loads(self.read_state('run.json'))
        self.assertEqual((state['title'], state['prompt'], state['pr']), ('Why A?', 'p', None))
        helpers.write(self.outside, 'view.json', 'not json')
        shutil.rmtree(os.path.join(self.root, '.git', 'sllmwiki'))
        self.assertIn('(its state rebuilt', self.pub('resume', 'alpha-retries').out)
        self.assertIn('no run branch sllmwiki/nope', self.pub('resume', 'nope').err)

    def test_the_old_single_run_state_moves_into_runs(self):
        self.pub('start', 'alpha-retries', '--title', 't', '--prompt', 'p')
        base = os.path.join(self.root, '.git', 'sllmwiki')
        shutil.move(self.state_path('run.json'), os.path.join(base, 'run.json'))
        shutil.move(self.state_path('summaries'), os.path.join(base, 'summaries'))
        os.remove(os.path.join(base, 'current'))
        self.assertIn('run sllmwiki/alpha-retries', self.pub('status').out)
        self.assertTrue(os.path.isfile(self.state_path('run.json')))
        self.assertFalse(os.path.exists(os.path.join(base, 'summaries')))
        helpers.write(base, 'current', 'gone')
        self.assertIn('no run in progress here', self.pub('status').err)


class Preflight(unittest.TestCase):
    SCRIPT = os.path.join(helpers.SCRIPTS, 'preflight.sh')

    def run_with(self, tools):
        """Run preflight with only the named tools on PATH (bash and the basics stay)."""
        bin_dir = tempfile.mkdtemp(prefix='preflight-')
        try:
            for name in ('uname', 'awk', 'env', 'dirname', 'grep'):
                os.symlink(shutil.which(name), os.path.join(bin_dir, name))
            for name, body in tools.items():
                helpers.write(bin_dir, name, f'#!/bin/sh\n{body}\n')
                os.chmod(os.path.join(bin_dir, name), 0o755)
            return subprocess.run([shutil.which('bash'), self.SCRIPT], env={'PATH': bin_dir}, capture_output=True, text=True)
        finally:
            shutil.rmtree(bin_dir)

    def test_everything_present(self):
        p = self.run_with({'git': 'echo "git version 2.40.0"', 'python3': f'exec {shutil.which("python3")} "$@"', 'gh': 'exit 0'})
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn('ok       git 2.40.0', p.stdout)
        self.assertIn('ok       gh, signed in', p.stdout)

    def test_a_token_without_the_workflow_scope(self):
        python = f'exec {shutil.which("python3")} "$@"'
        git = 'case "$1" in remote) echo "{url}" ;; *) echo "git version 2.40.0" ;; esac'
        gh = 'echo "  - Token scopes: {scopes}"'
        warning = "warning  gh's token lacks the workflow scope"
        p = self.run_with({'git': git.format(url='https://github.com/o/r.git'), 'python3': python, 'gh': gh.format(scopes="'repo'")})
        self.assertEqual(p.returncode, 0)
        self.assertIn(warning + ', so a push can\'t add or change .github/workflows/: gh auth refresh -h github.com -s workflow', p.stdout)
        for url, scopes in (('https://github.com/o/r.git', "'repo', 'workflow'"),
                            ('git@github.com:o/r.git', "'repo'")):  # SSH pushes don't use gh's token
            p = self.run_with({'git': git.format(url=url), 'python3': python, 'gh': gh.format(scopes=scopes)})
            self.assertNotIn(warning, p.stdout)
        p = self.run_with({'git': git.format(url='https://github.com/o/r.git'), 'python3': python, 'gh': 'echo "  - Token: ghp_***"'})
        self.assertNotIn(warning, p.stdout)  # scopes not listed

    def test_missing_and_signed_out(self):
        p = self.run_with({'gh': 'exit 1'})
        self.assertEqual(p.returncode, 1)
        self.assertIn('missing  git (required)', p.stdout)
        self.assertIn('missing  Python 3.9 or later (required)', p.stdout)
        self.assertIn('warning  gh isn\'t signed in', p.stdout)
        p = self.run_with({'git': 'echo "xcrun: error" >&2; exit 1'})  # a stub that can't reach a real git
        self.assertIn('missing  git (required): `git --version` fails here', p.stdout)
        p = self.run_with({'python3': 'exit 1'})  # too old
        self.assertIn('missing  Python 3.9', p.stdout)
        self.assertIn('warning  gh (recommended', p.stdout)


if __name__ == '__main__':
    unittest.main()
