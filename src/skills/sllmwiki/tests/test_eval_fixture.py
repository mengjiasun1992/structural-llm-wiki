"""Tests for evals/_fixture/wiki.sh, which builds the eval fixture wiki."""

import glob
import os
import re
import shutil
import subprocess
import tempfile
import unittest

import helpers

SCRIPT = os.path.join(helpers.REPO, 'evals', '_fixture', 'wiki.sh')


class EvalFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='eval-fixture-')
        self.run_dir = os.path.join(self.tmp, 'run')
        os.makedirs(self.run_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_the_unit_tests_wiki_committed_with_a_local_origin(self):
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
        subprocess.run(['bash', SCRIPT], cwd=self.run_dir, env=env, check=True, capture_output=True, text=True)
        for rel in ('sllmwiki/tags/tags.yaml', 'sllmwiki/sources/manifest.yaml', 'sllmwiki/narratives/what-is-alpha.md'):
            self.assertTrue(os.path.isfile(os.path.join(self.run_dir, rel)), rel)
        self.assertEqual(helpers.git(self.run_dir, 'log', '--format=%s|%an').stdout.strip(), 'fixture wiki|Eval Agent')
        self.assertEqual(helpers.git(self.run_dir, 'branch', '--show-current').stdout.strip(), 'mainline')
        self.assertEqual(helpers.git(self.run_dir, 'status', '--porcelain').stdout, '')
        origin = helpers.git(self.run_dir, 'remote', 'get-url', 'origin').stdout.strip()
        self.assertEqual(os.path.realpath(origin), os.path.realpath(os.path.join(self.tmp, 'origin.git')))
        self.assertEqual(helpers.git(self.run_dir, 'rev-parse', 'origin/mainline').stdout, helpers.git(self.run_dir, 'rev-parse', 'HEAD').stdout)


class Graders(unittest.TestCase):
    def test_no_inline_regex_flags(self):
        # claude plugin eval compiles graders' patterns as JavaScript regexes, which refuse (?i);
        # a regex grader takes flags: i instead
        for path in glob.glob(os.path.join(helpers.REPO, 'evals', '*', 'graders', '*.md')):
            with open(path, encoding='utf-8') as f:
                self.assertNotRegex(f.read(), r'(input_match|pattern): .*\(\?[a-z]', path)


if __name__ == '__main__':
    unittest.main()
