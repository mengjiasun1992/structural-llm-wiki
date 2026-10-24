"""Tests for lib/release.py and scripts/release.py: a release's version, checks, notes, and
the gh calls that make it, against a local bare origin and a fake gh that records its calls."""

import datetime
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import helpers
from lib import language, release

# A fake gh: answers from responses.json by the longest matching start of its arguments, logs each call.
FAKE_GH = '''import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
args = ' '.join(sys.argv[1:])
with open(os.path.join(here, 'gh.log'), 'a') as f:
    f.write(args + '\\n')
responses = json.load(open(os.path.join(here, 'responses.json')))
key = max((k for k in responses if args.startswith(k)), key=len, default=None)
if key is None:
    print('unexpected: ' + args, file=sys.stderr); sys.exit(1)
answer = responses[key]
if isinstance(answer, dict) and 'seq' in answer:  # one answer per call, the last repeated
    count = os.path.join(here, 'count-' + key.replace(' ', '_').replace('/', '_'))
    n = int(open(count).read()) if os.path.exists(count) else 0
    open(count, 'w').write(str(n + 1))
    answer = answer['seq'][min(n, len(answer['seq']) - 1)]
if isinstance(answer, dict) and 'fail' in answer:
    print(answer['fail'], file=sys.stderr); sys.exit(1)
print(answer if isinstance(answer, str) else json.dumps(answer))
'''
GIT_ENV = {'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@example.com', 'GIT_COMMITTER_NAME': 't',
           'GIT_COMMITTER_EMAIL': 't@example.com', 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}
REMOTE = 'git@github.com:o/wiki.git'
TODAY = 'v' + datetime.datetime.now(datetime.timezone.utc).date().strftime('%Y.%m.%d')
PASSING = {'check_runs': [{'name': 'wiki-checks', 'status': 'completed', 'conclusion': 'success'}]}


class Units(unittest.TestCase):
    def test_version(self):
        day = datetime.date(2026, 10, 24)
        self.assertEqual(release.version(set(), day), 'v2026.10.24')
        self.assertEqual(release.version({'v2026.10.24'}, day), 'v2026.10.24.2')
        self.assertEqual(release.version({'v2026.10.24', 'v2026.10.24.2'}, day), 'v2026.10.24.3')
        self.assertTrue(release.version(set()).startswith('v20'))

    def test_checks(self):
        self.assertEqual(release.checks([]), ('none', []))
        self.assertEqual(release.checks(PASSING['check_runs']), ('passing', []))
        runs = [{'name': 'a', 'status': 'completed', 'conclusion': 'failure'}, {'name': 'b', 'status': 'in_progress'},
                {'name': 'c', 'status': 'completed', 'conclusion': 'skipped'}]
        self.assertEqual(release.checks(runs), ('failing', ['a']))
        self.assertEqual(release.checks(runs[1:]), ('pending', ['b']))

    def test_notes(self):
        found = {'added': [('What is beta?', '1.0')], 'updated': [('What is alpha?', '1.0', '1.1')], 'removed': ['Old?'],
                 'sources': ['beta-doc'], 'narratives': 2, 'source_count': 3, 'open_questions': 1}
        text = release.notes(found, 'v2026.10.01', ['html'], failing=['wiki-checks'])
        self.assertEqual(text, '> [!WARNING]\n> Released while these checks failed: wiki-checks\n\n## Since v2026.10.01\n\n'
                               '**New narratives:**\n\n- What is beta? (1.0)\n\n**Updated narratives:**\n\n- What is alpha? (1.0 → 1.1)\n\n'
                               '**Removed narratives:**\n\n- Old?\n\n**New sources:** 1 (beta-doc)\n\n**Open questions:** 1 [?]\n\n**Book:** HTML\n')
        first = release.notes(dict(found, added=[('x', '1.0')], updated=[], removed=[]), None, [])
        self.assertTrue(first.startswith('## First release\n\n2 narratives, 3 sources.\n'), first)
        self.assertNotIn('New narratives', first)  # a first release doesn't list everything
        self.assertIn("**Book:** none: turn a format on in Config.toml's [structural-llm-wiki-release]", first)
        quiet = release.notes(dict(found, added=[], updated=[], removed=[], sources=[]), 'v1', ['html'])
        self.assertIn('Nothing in the wiki changed since the last release.', quiet)
        self.assertIn('## 首次发布', release.notes(found, None, [], language.pack('zh-Hans')))


class Release(helpers.WikiTestCase):
    def setUp(self):
        super().setUp()
        self.outside = tempfile.mkdtemp(prefix='release-')
        self.origin = os.path.join(self.outside, 'origin.git')
        helpers.git(self.outside, 'init', '-q', '--bare', '-b', 'mainline', self.origin)
        helpers.git(self.root, 'remote', 'add', 'origin', REMOTE)
        helpers.git(self.root, 'config', f'url.{self.origin}.insteadOf', REMOTE)  # a GitHub remote, served locally
        self.write('.github/workflows/release-book.yml', 'name: Book\n')
        self.commit('install the release workflow')
        helpers.git(self.root, 'remote', 'set-head', 'origin', 'mainline')
        self.bin = os.path.join(self.outside, 'bin')
        helpers.write(self.bin, 'gh', f'#!{sys.executable}\n{FAKE_GH}')
        os.chmod(os.path.join(self.bin, 'gh'), 0o755)
        self.respond()
        self.env = mock.patch.dict(os.environ, dict(GIT_ENV, PATH=self.bin + os.pathsep + os.environ['PATH']))
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.outside, ignore_errors=True)
        super().tearDown()

    def commit(self, message):
        helpers.git(self.root, 'add', '-A')
        helpers.git(self.root, 'commit', '-q', '-m', message)
        helpers.git(self.root, 'push', '-q', 'origin', 'mainline', '--tags')

    def respond(self, **changes):
        responses = {'api repos/o/wiki/commits/': PASSING, 'release list': [], 'release create': 'https://github.com/o/wiki/releases/tag/x',
                     'run list': [{'databaseId': 1, 'status': 'completed', 'conclusion': 'success', 'headBranch': TODAY, 'url': 'https://run/1'}],
                     'release view': {'url': 'https://github.com/o/wiki/releases/tag/' + TODAY, 'body': 'notes',
                                      'assets': [{'name': f'wiki-{TODAY}.html', 'size': 84546, 'url': 'https://dl/wiki.html'}]}}
        responses.update(changes)
        helpers.write(self.bin, 'responses.json', json.dumps(responses))
        for name in os.listdir(self.bin):  # each sequence starts again
            if name.startswith('count-'):
                os.remove(os.path.join(self.bin, name))

    def rel(self, *argv):
        return helpers.run('release.py', list(argv), cwd=self.root)

    def calls(self):
        return helpers.read(self.bin, 'gh.log').split('\n')[:-1]

    def plan_file(self, name):
        return helpers.read(self.root, f'.git/sllmwiki/release/{name}')

    def test_a_first_release(self):
        r = self.rel('plan')
        self.assertEqual(r.code, 0, r.err)
        commit = helpers.git(self.root, 'rev-parse', 'HEAD').stdout.strip()
        self.assertIn(f'Releasing {TODAY} from mainline ({commit[:7]}); checks: passing', r.out)
        notes = self.plan_file('notes.md')
        self.assertTrue(notes.startswith('## First release\n\n1 narratives, 3 sources.\n'), notes)
        self.assertIn("**Book:** none", notes)
        plan = json.loads(self.plan_file('plan.json'))
        self.assertEqual((plan['version'], plan['commit'], plan['previous'], plan['formats']), (TODAY, commit, None, []))
        self.assertIn(f'api repos/o/wiki/commits/{commit}/check-runs?per_page=100', self.calls())
        r = self.rel('create')
        self.assertEqual((r.code, r.out), (0, 'Release: https://github.com/o/wiki/releases/tag/x\n'))
        created = [c for c in self.calls() if c.startswith('release create')]
        self.assertEqual(len(created), 1)
        self.assertTrue(created[0].startswith(f'release create {TODAY} -R o/wiki --target {commit} --title wiki {TODAY} --notes-file '))
        self.assertTrue(created[0].endswith('/.git/sllmwiki/release/notes.md'))
        r = self.rel('wait', '--interval', '0')
        self.assertEqual(r.code, 0, r.err)
        self.assertIn(f'wiki-{TODAY}.html: 84,546 bytes, https://dl/wiki.html', r.out)
        self.assertIn('Build: success (https://run/1)', r.out)

    def test_changes_since_the_last_release(self):
        helpers.git(self.root, 'tag', 'v2026.10.01')
        helpers.git(self.root, 'push', '-q', 'origin', '--tags')
        helpers.add_narrative(self.root, 'what-is-beta', 'What is beta?', primary=('leaf-b',))
        alpha = self.read('sllmwiki/narratives/what-is-alpha.md').replace('- **Version:** 1.0', '- **Version:** 1.1')
        self.write('sllmwiki/narratives/what-is-alpha.md', alpha.replace('## 6. Design', 'Unknown [?].\n\n## 6. Design'))
        self.write('sllmwiki/sources/manifest.yaml', self.read('sllmwiki/sources/manifest.yaml')
                   + '\ndelta-link:\n  kind: link\n  url: https://example.com/d\n  ingested: "2026-10-02"\n  license: unknown\n  tags: [leaf-b]\n'
                     '  abstract: Delta.\n')
        self.commit('more')
        self.respond(**{'release list': [{'tagName': 'v2026.10.01', 'publishedAt': '2026-10-01T00:00:00Z', 'isDraft': False},
                                         {'tagName': 'v2099.01.01', 'publishedAt': '2099-01-01T00:00:00Z', 'isDraft': True}]})
        helpers.write(self.root, 'Config.toml', '[structural-llm-wiki-release]\nhtml_book = true\n')
        r = self.rel('plan', '--json')
        self.assertEqual(r.code, 0, r.err)
        out = json.loads(r.out)
        self.assertEqual((out['previous'], out['formats'], out['changes']['sources']), ('v2026.10.01', ['html'], ['delta-link']))
        notes = self.plan_file('notes.md')
        for says in ('## Since v2026.10.01', '- What is beta? (1.0)', '- What is alpha? (1.0 → 1.1)', '**New sources:** 1 (delta-link)',
                     '**Open questions:** 1 [?]', '**Book:** HTML'):
            self.assertIn(says, notes)

    def test_checks_that_fail_or_are_pending(self):
        self.respond(**{'api repos/o/wiki/commits/': {'check_runs': [{'name': 'wiki-checks', 'status': 'completed', 'conclusion': 'failure'}]}})
        r = self.rel('plan')
        self.assertEqual(r.code, 1)
        self.assertIn("mainline's checks failed: wiki-checks. Fix them (or wait), or release anyway with --anyway", r.err)
        r = self.rel('plan', '--anyway')
        self.assertEqual(r.code, 0, r.err)
        self.assertTrue(self.plan_file('notes.md').startswith('> [!WARNING]\n> Released while these checks failed: wiki-checks\n'))
        self.respond(**{'api repos/o/wiki/commits/': {'check_runs': [{'name': 'book', 'status': 'queued'}]}})
        self.assertIn("checks haven't finished: book", self.rel('plan').err)

    def test_refusals(self):
        self.assertIn('no release is planned', self.rel('create').err)
        self.assertIn('no release is planned', self.rel('wait').err)
        helpers.git(self.root, 'rm', '-q', '.github/workflows/release-book.yml')
        self.commit('drop the workflow')
        r = self.rel('plan')
        self.assertEqual(r.code, 1)
        self.assertIn('rerun /sllmwiki:init', r.err)
        self.respond(**{'api repos/o/wiki/commits/': {'fail': 'HTTP 401: Bad credentials'}})
        self.write('.github/workflows/release-book.yml', 'name: Book\n')
        self.commit('the workflow again')
        self.assertIn('gh api repos/o/wiki/commits/', self.rel('plan').err)
        self.assertIn('HTTP 401', self.rel('plan').err)

    def test_notes_from_a_file_and_a_build_that_fails(self):
        self.rel('plan')
        helpers.write(self.outside, 'mine.md', 'My notes.\n')
        self.rel('create', '--notes', os.path.join(self.outside, 'mine.md'))
        self.assertTrue(any(c.endswith('--notes-file ' + os.path.join(self.outside, 'mine.md')) for c in self.calls()))
        self.assertIn('no notes at', self.rel('create', '--notes', os.path.join(self.outside, 'none.md')).err)
        self.respond(**{'run list': {'seq': [[], [{'databaseId': 1, 'status': 'in_progress', 'headBranch': TODAY, 'url': 'https://run/1'}],
                                             [{'databaseId': 1, 'status': 'completed', 'conclusion': 'failure', 'headBranch': TODAY, 'url': 'https://run/1'}]]},
                        'release view': {'url': 'u', 'body': 'Notes.\n\n### Known issues\n\n- html: Sphinx failed\n', 'assets': []}})
        r = self.rel('wait', '--interval', '0', '--json')
        self.assertEqual(r.code, 1)
        out = json.loads(r.out)
        self.assertEqual((out['conclusion'], out['files'], out['issues']), ('failure', [], '- html: Sphinx failed'))
        r = self.rel('wait', '--interval', '0')
        self.assertIn('No files: no book format is on', r.out)
        self.assertIn('Known issues:\n- html: Sphinx failed', r.out)

    def test_waiting_runs_out(self):
        self.rel('plan')
        self.respond(**{'run list': []})
        r = self.rel('wait', '--timeout', '0', '--interval', '0')
        self.assertEqual(r.code, 1)
        self.assertIn('no release workflow run started', r.err)
        self.respond(**{'run list': [{'databaseId': 1, 'status': 'queued', 'headBranch': TODAY, 'url': 'https://run/1'}]})
        self.assertIn('follow it at https://run/1', self.rel('wait', '--timeout', '0', '--interval', '0').err)

    def test_a_preview(self):
        helpers.git(self.root, 'checkout', '-q', '-b', 'draft')
        self.assertIn("draft isn't on GitHub: push it first", self.rel('preview').err)
        helpers.git(self.root, 'push', '-q', 'origin', 'draft')
        run = {'databaseId': 7, 'headBranch': 'draft', 'url': 'https://run/7'}
        self.respond(**{'run list': {'seq': [[{'databaseId': 3, 'status': 'completed', 'headBranch': 'draft', 'url': 'old'}],
                                             [dict(run, status='in_progress')], [dict(run, status='completed', conclusion='success')]]},
                        'workflow run': '', 'api repos/o/wiki/actions/runs/7/artifacts': {'artifacts': [{'name': 'book-preview', 'size_in_bytes': 90000}]}})
        r = self.rel('preview', '--interval', '0', '--timeout', '5')
        self.assertEqual(r.code, 0, r.err)
        self.assertEqual(r.out, 'Preview of draft: success (https://run/7)\nbook-preview: 90,000 bytes, on the run\'s page\n')
        self.assertIn('workflow run release-book.yml -R o/wiki --ref draft', self.calls())
        self.respond(**{'run list': [], 'workflow run': ''})
        r = self.rel('preview', '--timeout', '0', '--interval', '0', '--json')
        self.assertEqual((r.code, "the preview of draft isn't built after 0 s" in r.err), (1, True))
        self.respond(**{'run list': {'seq': [[], [dict(run, status='completed', conclusion='failure')]]}, 'workflow run': '',
                        'api repos/o/wiki/actions/runs/7/artifacts': {'artifacts': [{'name': 'book-preview'}]}})
        r = self.rel('preview', '--interval', '0', '--timeout', '5', '--json')
        self.assertEqual((r.code, json.loads(r.out)['artifacts']), (1, [{'name': 'book-preview', 'bytes': None}]))
        self.respond(**{'run list': {'seq': [[], [dict(run, status='completed', conclusion='failure')]]}, 'workflow run': '',
                        'api repos/o/wiki/actions/runs/7/artifacts': {'artifacts': [{'name': 'book-preview'}]}})
        self.assertIn("book-preview: on the run's page", self.rel('preview', '--interval', '0', '--timeout', '5').out)
        helpers.git(self.root, 'rm', '-q', '.github/workflows/release-book.yml')
        self.commit_on('draft', 'no workflow')
        self.assertIn('rerun /sllmwiki:init', self.rel('preview').err)

    def commit_on(self, branch, message):
        helpers.git(self.root, 'commit', '-q', '-am', message)
        helpers.git(self.root, 'push', '-q', 'origin', branch)

    def test_a_broken_manifest_and_nothing_pushed(self):
        with mock.patch.object(release.wikiyaml, 'parse', side_effect=release.wikiyaml.YamlError(1, 'bad')):
            self.assertEqual(release.changes(self.root, None, 'HEAD')['source_count'], 0)  # an old release's broken manifest counts nothing
        empty = os.path.join(self.outside, 'empty.git')
        helpers.git(self.outside, 'init', '-q', '--bare', '-b', 'mainline', empty)
        helpers.git(self.root, 'config', '--unset', f'url.{self.origin}.insteadOf')
        helpers.git(self.root, 'config', f'url.{empty}.insteadOf', REMOTE)
        helpers.git(self.root, 'update-ref', '-d', 'refs/remotes/origin/mainline')
        helpers.git(self.root, 'remote', 'set-head', 'origin', '-d')
        self.assertIn("origin/mainline isn't there to release", self.rel('plan').err)

    def test_a_stand_in_gh_for_the_evals(self):
        helpers.write(self.root, '.eval/gh', f'#!{sys.executable}\nimport sys\nprint("stand-in", file=sys.stderr)\nsys.exit(1)\n')
        os.chmod(os.path.join(self.root, '.eval/gh'), 0o755)
        with mock.patch.dict(os.environ, {'EVAL_SLLMWIKI_GH': '.eval/gh'}):
            self.assertIn('stand-in', self.rel('plan').err)

    def test_without_github_or_gh(self):
        helpers.git(self.root, 'remote', 'set-url', 'origin', self.origin)
        self.assertIn('no GitHub remote', self.rel('plan').err)
        helpers.git(self.root, 'remote', 'set-url', 'origin', REMOTE)
        only_git = os.path.join(self.outside, 'only-git')  # a PATH with git and no gh (on CI they share /usr/bin)
        os.makedirs(only_git)
        os.symlink(shutil.which('git'), os.path.join(only_git, 'git'))
        with mock.patch.dict(os.environ, {'PATH': only_git}):
            r = self.rel('plan')
        self.assertIn("gh isn't installed", r.err)


if __name__ == '__main__':
    unittest.main()
