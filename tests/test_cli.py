"""Tests for the sllmwiki command (src/sllmwiki/cli.py): one subcommand per script."""

import contextlib
import io
import os
import tempfile
import unittest

import helpers
import sllmwiki
from sllmwiki import cli


def call(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class Cli(unittest.TestCase):
    def test_version_and_help(self):
        self.assertEqual(call('--version'), (0, f'sllmwiki {sllmwiki.__version__}\n', ''))
        code, out, _ = call('--help')
        self.assertEqual(code, 0)
        self.assertIn('wiki-check', out)
        self.assertEqual(call()[0], 2)  # no command

    def test_an_unknown_command(self):
        code, _, err = call('wiki-check.py')
        self.assertEqual(code, 2)
        self.assertIn("no command 'wiki-check.py'", err)

    def test_every_command_is_a_module_with_main(self):
        for name in cli.COMMANDS:
            with self.subTest(command=name):
                self.assertTrue(callable(helpers.load_script(name).main))
        modules = {f[:-3].replace('_', '-') for f in os.listdir(os.path.join(helpers.PACKAGE, 'commands')) if f.endswith('.py') and f != '__init__.py'}
        self.assertEqual(modules, set(cli.COMMANDS))

    def test_a_command_runs_with_its_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = helpers.write(tmp, 'body.md', '## Review checklist\n\n- [x] tags\n- [ ] sources\n')
            code, out, _ = call('review-checklist', '--file', path)
        self.assertEqual(code, 1)
        self.assertIn('sources', out)


if __name__ == '__main__':
    unittest.main()
