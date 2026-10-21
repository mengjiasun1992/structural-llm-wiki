"""Tests for run.py, the parallel test runner."""

import contextlib
import io
import os
import unittest

import run


class RunTest(unittest.TestCase):
    def main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = run.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_repo_root_is_the_checkout(self):
        root = run.repo_root()
        self.assertTrue(os.path.isfile(os.path.join(root, 'pyproject.toml')))

    def test_help(self):
        code, out, _ = self.main('-h')
        self.assertEqual(code, 0)
        self.assertIn('Usage: python3 run.py', out)

    def test_unknown_option(self):
        code, _, err = self.main('--bogus')
        self.assertEqual(code, 2)
        self.assertIn('unknown option --bogus', err)

    def test_no_module_matches(self):
        code, _, err = self.main('-j', '2', 'no_such_module_name')
        self.assertEqual(code, 2)
        self.assertIn('no test modules matched', err)

    def test_runs_a_module(self):
        r = run.run_module('test_helpers', False, run.repo_root())
        self.assertTrue(r['ok'], r['output'])
        self.assertGreater(r['tests'], 0)


if __name__ == '__main__':
    unittest.main()
