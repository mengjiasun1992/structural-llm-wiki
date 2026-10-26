"""Tests for run.py, the parallel test runner."""

import contextlib
import io
import os
import unittest

import run


def call(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = run.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class Run(unittest.TestCase):
    def test_repo_root_is_the_checkout(self):
        self.assertTrue(os.path.isfile(os.path.join(run.repo_root(), 'pyproject.toml')))

    def test_help(self):
        code, out, _ = call('--help')
        self.assertEqual(code, 0)
        self.assertIn('Usage: python3 run.py', out)

    def test_usage_errors(self):
        for argv, msg in ((['--bogus'], 'unknown option --bogus'), (['-j'], '-j needs a positive number'),
                          (['-j', '0'], '-j needs a positive number'), (['-j', '2', 'no_such_module'], 'no test modules matched')):
            code, _, err = call(*argv)
            self.assertEqual(code, 2, argv)
            self.assertIn(msg, err)

    def test_parse(self):
        self.assertEqual(run.parse(['--coverage', '-j', '3', 'a', 'b']), (True, 3, ['a', 'b']))

    def test_runs_a_module_in_its_own_process(self):
        r = run.run_module('test_helpers', False, run.repo_root())
        self.assertTrue(r['ok'], r['output'])
        self.assertGreater(r['tests'], 0)

    def test_runs_only_matching_modules(self):
        code, out, _ = call('-j', '1', 'helpers')
        self.assertEqual(code, 0, out)
        self.assertIn('test_helpers', out)
        self.assertNotIn('test_run ', out)
        self.assertIn('1 module(s)', out)


if __name__ == '__main__':
    unittest.main()
