"""Tests for sllmwiki doctor: the tools a run needs, and the command that installs each on this machine."""

import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

import helpers

doctor = helpers.load_script('doctor.py')


class Doctor(unittest.TestCase):
    def run_with(self, tools, system=None, uid=1000):
        """doctor with only the named fake tools on PATH ({name: shell body}), on system (uname's name) as uid."""
        bin_dir = tempfile.mkdtemp(prefix='doctor-')
        self.addCleanup(shutil.rmtree, bin_dir)
        for name, body in tools.items():
            helpers.write(bin_dir, name, f'#!/bin/sh\n{body}\n')
            os.chmod(os.path.join(bin_dir, name), 0o755)
        patches = [mock.patch.dict(os.environ, {'PATH': bin_dir}), mock.patch.object(doctor.os, 'geteuid', return_value=uid, create=True)]
        if system:
            patches.append(mock.patch.object(doctor.platform, 'system', return_value=system))
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        return helpers.run('doctor.py', [])

    def test_everything_present(self):
        r = self.run_with({'git': 'echo "git version 2.40.0"', 'gh': 'exit 0'})
        self.assertEqual(r.code, 0, r.out)
        self.assertIn(f'ok       python {sys.version.split()[0]}', r.out)
        self.assertIn('ok       git 2.40.0', r.out)
        self.assertIn('ok       gh, signed in', r.out)

    def test_a_token_without_the_workflow_scope(self):
        git = 'case "$1" in remote) echo "{url}" ;; *) echo "git version 2.40.0" ;; esac'
        gh = 'echo "  - Token scopes: {scopes}"'
        warning = "warning  gh's token lacks the workflow scope"
        r = self.run_with({'git': git.format(url='https://github.com/o/r.git'), 'gh': gh.format(scopes="'repo'")})
        self.assertEqual(r.code, 0)
        self.assertIn(warning + ", so a push can't add or change .github/workflows/: gh auth refresh -h github.com -s workflow", r.out)
        for url, scopes in (('https://github.com/o/r.git', "'repo', 'workflow'"),
                            ('git@github.com:o/r.git', "'repo'")):  # SSH pushes don't use gh's token
            self.assertNotIn(warning, self.run_with({'git': git.format(url=url), 'gh': gh.format(scopes=scopes)}).out)
        r = self.run_with({'git': git.format(url='https://github.com/o/r.git'), 'gh': 'echo "  - Token: ghp_***"'})
        self.assertNotIn(warning, r.out)  # scopes not listed

    def test_missing_and_signed_out(self):
        r = self.run_with({'gh': 'exit 1'})
        self.assertEqual(r.code, 1)
        self.assertIn('missing  git (required)', r.out)
        self.assertIn("warning  gh isn't signed in", r.out)
        r = self.run_with({'git': 'echo "xcrun: error" >&2; exit 1'})  # a stub that can't reach a real git
        self.assertIn('missing  git (required): `git --version` fails here', r.out)
        self.assertIn('warning  gh (recommended', r.out)

    def test_the_install_command_fits_the_machine(self):
        def hints(system, *managers, uid=1000):
            return self.run_with({m: 'exit 0' for m in managers}, system=system, uid=uid).out
        out = hints('Linux', 'apt-get')
        self.assertIn('missing  git (required): sudo apt-get install -y git', out)
        self.assertIn('warning  gh (recommended, to open pull requests): sudo apt-get install -y gh', out)
        self.assertIn(': dnf install -y git', hints('Linux', 'dnf', uid=0))  # root needs no sudo
        self.assertIn('sudo pacman -S --noconfirm github-cli', hints('Linux', 'pacman'))
        self.assertIn('sudo apk add github-cli', hints('Linux', 'apk'))
        self.assertIn('git (required): https://git-scm.com/downloads', hints('Linux'))
        self.assertIn('git (required): brew install git', hints('Darwin', 'brew'))
        out = hints('Darwin')
        self.assertIn('git (required): xcode-select --install', out)
        self.assertIn('install Homebrew (https://brew.sh), then: brew install gh', out)
        out = hints('Windows')
        self.assertIn('git (required): winget install -e --id Git.Git', out)
        self.assertIn('gh (recommended, to open pull requests): winget install -e --id GitHub.cli', out)
        self.assertIn('winget install -e --id Git.Git', hints('MINGW64_NT-10.0'))
        self.assertIn('git (required): https://git-scm.com/downloads', hints('Plan9'))

    def test_usage(self):
        self.assertEqual(helpers.run('doctor.py', ['--bogus']).code, 2)


if __name__ == '__main__':
    unittest.main()
