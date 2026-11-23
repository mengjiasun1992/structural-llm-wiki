"""Tests for lib/markdownlint.py: wiki-check runs markdownlint as the wiki's CI does (issue #182). No test runs npx:
a stand-in answers, and helpers turns it off for every other test."""

import os
import re
import subprocess
import unittest
from unittest import mock

import helpers
from sllmwiki.lib import markdownlint

ACTION = os.path.join(helpers.REPO, 'src', 'actions', 'wiki-checks', 'action.yml')


def done(code, out='', err=''):
    return subprocess.CompletedProcess([], code, out, err)


class Run(helpers.WikiTestCase):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.dict(os.environ, {'SLLMWIKI_MARKDOWNLINT': ''})
        patcher.start()
        self.addCleanup(patcher.stop)

    def lint(self, result, npx='/usr/bin/npx'):
        listed = markdownlint.files(self.root)
        with mock.patch.object(markdownlint.shutil, 'which', return_value=npx), mock.patch.object(markdownlint, 'files', return_value=listed), \
                mock.patch.object(markdownlint.subprocess, 'run', side_effect=[result] if not isinstance(result, list) else result) as run:
            return markdownlint.run(self.root), run

    def test_findings(self):
        err = ('markdownlint-cli2 v0.13.0 (markdownlint v0.34.0)\n'
               'sllmwiki/narratives/x.md:12:5 MD038/no-space-in-code Spaces inside code span elements [Context: "` Paris`"]\n'
               'README.md:3 MD051/link-fragments Link fragments should be valid [Context: "[a](#b)"]\n')
        found, run = self.lint(done(1, 'Summary: 2 error(s)\n', err))
        self.assertEqual(found, [
            ('error', 'MD038', 'sllmwiki/narratives/x.md:12', 'markdownlint: Spaces inside code span elements [Context: "` Paris`"]'),
            ('error', 'MD051', 'README.md:3', 'markdownlint: Link fragments should be valid [Context: "[a](#b)"]')])
        argv, kw = run.call_args
        self.assertEqual(argv[0][:5], ['/usr/bin/npx', '--yes', f'markdownlint-cli2@{markdownlint.VERSION}', '--config', markdownlint.SETTINGS])
        self.assertEqual(argv[0][5:], markdownlint.files(self.root))
        self.assertIn('sllmwiki/narratives/what-is-alpha.md', argv[0][5:])
        self.assertEqual(kw['cwd'], self.root)

    def test_the_files_ci_would_see(self):
        self.write('notes/new.md', '# New\n')  # new, not yet committed: CI would see it once pushed
        self.write('.gitignore', 'scratch/\n')
        self.write('scratch/ignored.md', '# Ignored\n')
        self.write('sllmwiki/narratives/gone.md', '# Gone\n')
        subprocess.run(['git', 'add', 'sllmwiki/narratives/gone.md'], cwd=self.root, check=True, capture_output=True)
        os.remove(os.path.join(self.root, 'sllmwiki/narratives/gone.md'))  # staged, then deleted: nothing to lint
        nested = os.path.join(self.root, '.claude', 'worktrees', 'agent')  # an agent's checkout of the wiki
        os.makedirs(nested)
        subprocess.run(['git', 'init', '-q', nested], check=True)
        helpers.write(nested, 'copy.md', '# A copy\n')
        found = markdownlint.files(self.root)
        self.assertIn('notes/new.md', found)
        self.assertIn('sllmwiki/narratives/what-is-alpha.md', found)
        for left_out in ('scratch/ignored.md', 'sllmwiki/narratives/gone.md', '.claude/worktrees/agent/copy.md'):
            self.assertNotIn(left_out, found)
        self.assertEqual(found, sorted(found))

    def test_outside_git_and_with_nothing_to_lint(self):
        with mock.patch.object(markdownlint.subprocess, 'run', side_effect=OSError('no git')):
            self.assertEqual(markdownlint.files(self.root), ['**/*.md'])
        with mock.patch.object(markdownlint.subprocess, 'run', return_value=done(128, '', 'not a git repository')):
            self.assertEqual(markdownlint.files(self.root), ['**/*.md'])
        with mock.patch.object(markdownlint.shutil, 'which', return_value='/usr/bin/npx'), \
                mock.patch.object(markdownlint, 'files', return_value=[]), mock.patch.object(markdownlint.subprocess, 'run') as run:
            self.assertEqual(markdownlint.run(self.root), [])
            run.assert_not_called()

    def test_clean(self):
        self.assertEqual(self.lint(done(0, 'Summary: 0 error(s)\n'))[0], [])

    def test_when_it_cannot_run(self):
        cases = [
            (None, 'Node isn\'t installed'),  # no npx
            (OSError('boom'), 'boom'),
            (subprocess.TimeoutExpired('npx', 300), 'timed out'),
            (done(2, '', 'npm error network request failed\n'), 'network request failed'),
            (done(1, '', 'something odd\n'), 'something odd'),  # a failure with no finding isn't a pass
        ]
        for result, says in cases:
            with self.subTest(says=says):
                if result is None:
                    found, _ = self.lint(done(0), npx=None)
                else:
                    with mock.patch.object(markdownlint.shutil, 'which', return_value='/usr/bin/npx'), \
                            mock.patch.object(markdownlint, 'files', return_value=['README.md']), \
                            mock.patch.object(markdownlint.subprocess, 'run', side_effect=result if isinstance(result, Exception) else [result]):
                        found = markdownlint.run(self.root)
                self.assertEqual([(f[0], f[1]) for f in found], [('warning', 'MARKDOWNLINT_SKIPPED')])
                self.assertIn(says, found[0][3])
                self.assertIn('CI', found[0][3])

    def test_off(self):
        for value in ('off', 'OFF', '0', 'false', 'no'):
            with self.subTest(value=value), mock.patch.dict(os.environ, {'SLLMWIKI_MARKDOWNLINT': value}), \
                    mock.patch.object(markdownlint.subprocess, 'run') as run:
                self.assertEqual(markdownlint.run(self.root), [])
                run.assert_not_called()

    def test_wiki_check_reports_them(self):
        err = 'sllmwiki/narratives/what-is-alpha.md:4:1 MD038/no-space-in-code Spaces inside code span elements\n'
        with mock.patch.object(markdownlint.shutil, 'which', return_value='/usr/bin/npx'), \
                mock.patch.object(markdownlint, 'files', return_value=['sllmwiki/narratives/what-is-alpha.md']), \
                mock.patch.object(markdownlint.subprocess, 'run', return_value=done(1, '', err)):
            r = helpers.run('wiki-check.py', ['--root', self.root, '--visibility', 'private'])
        self.assertEqual(r.code, 1)
        self.assertIn('MD038', r.out)
        self.assertIn('sllmwiki/narratives/what-is-alpha.md:4', r.out)


class SameAsCI(unittest.TestCase):
    def test_the_action_runs_the_same_version_and_settings(self):
        action = helpers.read(os.path.dirname(ACTION), 'action.yml')
        self.assertEqual(re.findall(r'markdownlint-cli2@([0-9.]+)', action), [markdownlint.VERSION])
        self.assertIn('sllmwiki/templates/markdownlint/.markdownlint-cli2.jsonc', action)
        self.assertIn('SLLMWIKI_MARKDOWNLINT: "off"', action)  # its wiki-check step leaves it to its own step
        self.assertTrue(os.path.isfile(markdownlint.SETTINGS))
        settings = helpers.read(os.path.dirname(markdownlint.SETTINGS), '.markdownlint-cli2.jsonc')
        for ignored in ('sllmwiki/sources/**', 'sllmwiki/.templates/**', '.git/**'):
            self.assertIn(f'"{ignored}"', settings)
        self.assertIn('"extends": "./.markdownlint.jsonc"', settings)
        self.assertTrue(os.path.isfile(os.path.join(os.path.dirname(markdownlint.SETTINGS), '.markdownlint.jsonc')))

    def test_this_repository_uses_the_same_rules(self):
        self.assertIn('src/sllmwiki/templates/markdownlint/.markdownlint.jsonc', helpers.read(helpers.REPO, '.markdownlint.jsonc'))


if __name__ == '__main__':
    unittest.main()
