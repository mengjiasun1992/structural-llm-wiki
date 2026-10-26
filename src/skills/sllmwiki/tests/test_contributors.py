"""Tests for scripts/contributors.py, over a repository the test commits to."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

import helpers

PEOPLE = {'ann': ('Ann Lee', 'ann@example.com'), 'bob': ('Bob Roy', 'bob@example.com'), 'cy': ('Cy Wu', 'cy@example.com'),
          'bot': ('dependabot[bot]', 'bot@example.com'), 'owner': ('Wiki Owner', 'owner@example.com')}


class Contributors(helpers.WikiTestCase):
    def setUp(self):
        super().setUp()
        self.repo = tempfile.mkdtemp(prefix='code-')
        helpers.git(self.repo, 'init', '-q', '-b', 'main')
        self.commit('ann', 'src/retry.py', 'def retry():\n    pass\n', 'Add retries', date='2020-01-01T00:00:00+00:00')
        self.commit('bob', 'src/retry.py', 'def retry():\n    return backoff()\n', 'Back off\n\nReviewed-by: Cy Wu <cy@example.com>\n'
                    'Co-authored-by: Claude <noreply@anthropic.com>')
        self.commit('bot', 'src/retry.py', 'def retry():\n    return backoff()\n# bumped\n', 'Bump')
        self.commit('owner', 'src/retry.py', 'def retry():\n    return backoff()\n# bumped\n# noted\n', '[sllmwiki][narrative][x] A run')
        self.commit('ann', 'docs/design.md', '---\nauthor: Dee Fox and Ann Lee\nowner: "Eve"\n---\n# Design\n', 'Design notes')
        helpers.write(self.repo, '.github/CODEOWNERS', '# owners\n/src/ @bob @team-x  # the code\n*.md @ann\nbad-line\n')

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)
        super().tearDown()

    def commit(self, who, path, text, message, date='2026-10-01T00:00:00+00:00'):
        name, email = PEOPLE[who]
        helpers.write(self.repo, path, text)
        env = dict(os.environ, GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email, GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=email,
                   GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
        for args in (['add', '-A'], ['commit', '-q', '-m', message]):
            subprocess.run(['git', *args], cwd=self.repo, env=env, check=True, capture_output=True)

    def run_it(self, *argv):
        return helpers.run('contributors.py', [*argv, '--repo', self.repo, '--root', self.root])

    def test_ranked_with_evidence(self):
        r = self.run_it('src', 'docs/design.md', '--json')
        self.assertEqual(r.code, 0, r.err)
        people = {p['name']: p for p in json.loads(r.out)['people']}
        self.assertNotIn('dependabot[bot]', people)  # a bot
        self.assertNotIn('Claude', people)  # a tool's noreply address
        self.assertIn('Wiki Owner', people)  # only blame: the run's commit doesn't count, the lines it wrote do
        self.assertNotIn('commit', people['Wiki Owner']['evidence'])
        self.assertIn('1 commit, the last on 2026-10-01', people['Bob Roy']['evidence'])
        self.assertIn('CODEOWNERS for /src/', people['Bob Roy']['evidence'])
        self.assertIn('reviewed or co-wrote 1', people['Cy Wu']['evidence'])
        self.assertIn('named author of docs/design.md', people['Ann Lee']['evidence'])
        self.assertIn('named author of docs/design.md', people['Dee Fox']['evidence'])
        self.assertIn('CODEOWNERS for /src/', people['@team-x']['evidence'])
        names = list(people)
        self.assertLess(names.index('Bob Roy'), names.index('Cy Wu'))

    def test_excluded_and_text(self):
        self.write('sllmwiki/Config.toml', '[structural-llm-wiki-settings]\nsmes_exclude = ["@ann", "Wiki Owner", "bob@example.com", "@team-x"]\n')
        out = self.run_it('src', '--limit', '5').out
        for gone in ('Ann Lee', 'Wiki Owner', 'Bob Roy', 'team-x'):
            self.assertNotIn(gone, out)
        self.assertIn('Cy Wu <cy@example.com>', out)
        self.assertTrue(out.startswith('1. '))

    def test_refusals_and_nothing_found(self):
        self.assertIn('not in', self.run_it('nope').err)
        with mock.patch.dict(os.environ, {'PATH': self.tmp}):  # no git on the PATH
            self.assertIn('git doesn\'t run here', self.run_it('src').err)
        empty = tempfile.mkdtemp(prefix='empty-')
        self.addCleanup(shutil.rmtree, empty)
        self.assertIn('isn\'t a git repository', helpers.run('contributors.py', ['x', '--repo', empty, '--root', self.root]).err)
        shutil.rmtree(os.path.join(self.repo, '.github'))
        self.write('sllmwiki/Config.toml', '[structural-llm-wiki-settings]\nsmes_exclude = ["Ann Lee", "Bob Roy", "Cy Wu", "Wiki Owner", "Dee Fox", "Eve"]\n')
        self.assertIn('no one found', self.run_it('src').out)
        self.write('sllmwiki/Config.toml', '[structural-llm-wiki-settings]\nsmes_exclude = 1\n')
        self.assertIn('Config.toml is invalid', self.run_it('src').err)


if __name__ == '__main__':
    unittest.main()
