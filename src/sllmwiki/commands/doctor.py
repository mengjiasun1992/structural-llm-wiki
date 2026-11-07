"""doctor: are the tools a run needs here?

  sllmwiki doctor [--updates]

git is required; gh, signed in, is recommended (without it, a run prints the
link to open its pull request). Python 3.9 or later is running this. Prints
what's missing with the command that installs it on this machine, from its
package manager; a command starting with sudo, the owner runs.
--updates also asks PyPI for the latest sllmwiki release, the plugin's too,
and prints the command that upgrades to it when it's newer than this one.
Exit code: 0 ready, 1 something required is missing, 2 usage error.
"""

import argparse
import json
import os
import platform
import re
import shutil
import subprocess

from sllmwiki import __version__
from sllmwiki.lib import fetch
from sllmwiki.lib.layout import Cli

cli = Cli('sllmwiki doctor', 'usage: sllmwiki doctor [--updates]')
PYPI = 'https://pypi.org/pypi/sllmwiki/json'  # the latest release: the package and the plugin share its version
UPGRADE = 'claude plugin marketplace update structural-llm-wiki && claude plugin update sllmwiki@structural-llm-wiki'
DOWNLOADS = {'git': 'https://git-scm.com/downloads', 'gh': 'https://cli.github.com'}
WINGET = {'git': 'Git.Git', 'gh': 'GitHub.cli'}
LINUX = ('apt-get', 'dnf', 'yum', 'pacman', 'zypper', 'apk')  # the package managers looked for, in order


def _run(*cmd):
    """(exit code, output) of a command, or (None, '') when it can't start."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None, ''
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def install_hint(tool):
    """The command that installs git or gh here, with this machine's package manager, or where to get it."""
    system = platform.system()
    if system == 'Darwin':
        if shutil.which('brew'):
            return f'brew install {tool}'
        if tool == 'git':
            return "xcode-select --install (Apple's command line tools: git)"
        return f'install Homebrew (https://brew.sh), then: brew install {tool}'
    if system == 'Linux':
        pm = next((m for m in LINUX if shutil.which(m)), None)
        if not pm:
            return DOWNLOADS[tool]
        pkg = 'github-cli' if tool == 'gh' and pm in ('pacman', 'apk') else tool
        sudo = '' if hasattr(os, 'geteuid') and os.geteuid() == 0 else 'sudo '
        return {'apt-get': f'{sudo}apt-get install -y {pkg}', 'pacman': f'{sudo}pacman -S --noconfirm {pkg}',
                'apk': f'{sudo}apk add {pkg}'}.get(pm, f'{sudo}{pm} install -y {pkg}')
    if system == 'Windows' or system.startswith(('MINGW', 'MSYS', 'CYGWIN')):
        return f'winget install -e --id {WINGET[tool]}'
    return DOWNLOADS[tool]


def checks():
    """[(status, line)]: status is 'ok', 'missing' (required) or 'warning'."""
    out = [('ok', f'python {platform.python_version()}')]
    # Run git, not just find it: macOS's /usr/bin/git is a stub that fails when it
    # can't reach the real one (in a sandbox, or without the developer tools).
    code, text = _run('git', '--version')
    if code == 0:
        out.append(('ok', f'git {text.split()[2] if len(text.split()) > 2 else text.strip()}'))
    elif code is not None:
        out.append(('missing', f'git (required): `git --version` fails here; install a working git ({install_hint("git")}) '
                               'or allow the sandbox to run it'))
    else:
        out.append(('missing', f'git (required): {install_hint("git")}'))
    code, text = _run('gh', 'auth', 'status')
    if code is None:
        out.append(('warning', f'gh (recommended, to open pull requests): {install_hint("gh")}'))
    elif code != 0:
        out.append(('warning', "gh isn't signed in (recommended): gh auth login"))
    else:
        out.append(('ok', 'gh, signed in'))
        # Over HTTPS, gh's token can't push .github/workflows/ (init's CI) without the
        # workflow scope. Tokens that don't list their scopes aren't judged.
        _, remote = _run('git', 'remote', 'get-url', 'origin')
        if remote.startswith('https://github.com/') and 'Token scopes:' in text and "'workflow'" not in text:
            out.append(('warning', "gh's token lacks the workflow scope, so a push can't add or change .github/workflows/: "
                                   'gh auth refresh -h github.com -s workflow'))
    return out


def _release(version):
    return tuple(int(n) for n in re.findall(r'\d+', version))


def update():
    """(status, line): 'update' with the command when PyPI has a newer release than this one, 'ok' when not,
    'warning' when PyPI can't be asked (offline, a proxy, a sandbox)."""
    try:
        latest = json.loads(fetch.fetch(PYPI, timeout=10).data)['info']['version']
    except (fetch.FetchError, ValueError, KeyError, TypeError) as e:
        return 'warning', f"couldn't ask PyPI for a newer sllmwiki ({e}); this is {__version__}"
    if _release(latest) <= _release(__version__):
        return 'ok', f'sllmwiki {__version__}, the latest release'
    return 'update', (f'sllmwiki {latest} is out; this is {__version__}. In Claude Code: {UPGRADE}, then restart it. '
                      f'Another agent: npx skills update, then pipx install sllmwiki=={latest}')


def main(argv):
    p = argparse.ArgumentParser(prog='sllmwiki doctor', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--updates', action='store_true')
    args = p.parse_args(argv)
    found = checks() + ([update()] if args.updates else [])
    for status, line in found:
        print(f'{status:<8} {line}')
    return 1 if any(s == 'missing' for s, _ in found) else 0
