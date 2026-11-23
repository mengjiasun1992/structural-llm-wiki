"""markdownlint, as a wiki's CI runs it (src/actions/wiki-checks), for sllmwiki wiki-check: the same
markdownlint-cli2, at the same version, with the same settings (templates/markdownlint/ in this
package), so a problem CI would fail on shows up locally first (issue #182).

It needs Node's npx, which fetches markdownlint-cli2 from npm the first time. Without npx, or when the
run fails (offline, say), wiki-check says so in a warning and CI still runs it. SLLMWIKI_MARKDOWNLINT=off
skips it: for the CI step that runs it on its own, and for tests and sandboxes with no network.
"""

import os
import re
import shutil
import subprocess

from .. import TEMPLATES

VERSION = '0.13.0'  # the version the wiki-checks action runs; a test keeps them equal
SETTINGS = os.path.join(TEMPLATES, 'markdownlint', '.markdownlint-cli2.jsonc')
FINDING = re.compile(r'(?P<file>[^\s:][^:]*):(?P<line>[0-9]+)(?::[0-9]+)? (?P<rule>MD[0-9]{3})/\S+ (?P<message>.*)\Z')
TIMEOUT = 300  # seconds: the first run downloads markdownlint-cli2


def files(root):
    """The markdown files CI would lint: what git tracks plus new files it doesn't ignore, so a nested checkout (an
    agent's worktree under .claude/) or other local clutter isn't linted; ['**/*.md'] outside a git repository."""
    try:
        p = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard', '--', '*.md'],
                           cwd=root, capture_output=True, text=True)
    except OSError:
        p = None
    if not p or p.returncode:
        return ['**/*.md']
    return sorted({f for f in p.stdout.split('\0') if f and os.path.isfile(os.path.join(root, f))})


def run(root):
    """[(severity, code, where, message)]: each markdownlint finding as an error named by its rule (MD038), or one
    MARKDOWNLINT_SKIPPED warning when it couldn't run; [] when it is off or finds nothing."""
    if os.environ.get('SLLMWIKI_MARKDOWNLINT', '').lower() in ('off', '0', 'false', 'no'):
        return []
    npx = shutil.which('npx')
    if not npx:
        return [('warning', 'MARKDOWNLINT_SKIPPED', '.', 'Node isn\'t installed, so markdownlint didn\'t run here; '
                 'the wiki\'s CI runs it (install Node to check before pushing)')]
    found = files(root)
    if not found:
        return []
    try:
        p = subprocess.run([npx, '--yes', f'markdownlint-cli2@{VERSION}', '--config', SETTINGS, *found], cwd=root,
                           capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as e:
        return [('warning', 'MARKDOWNLINT_SKIPPED', '.', f'markdownlint couldn\'t run ({e}); the wiki\'s CI runs it')]
    out = []
    for line in (p.stdout + '\n' + p.stderr).splitlines():
        m = FINDING.match(line.strip())
        if m:
            out.append(('error', m.group('rule'), f'{m.group("file")}:{m.group("line")}', f'markdownlint: {m.group("message")}'))
    if p.returncode not in (0, 1) or (p.returncode == 1 and not out):
        tail = (p.stderr or p.stdout).strip().splitlines()[-1:] or ['no output']
        return [('warning', 'MARKDOWNLINT_SKIPPED', '.', f'markdownlint couldn\'t run ({tail[0]}); the wiki\'s CI runs it')]
    return out
