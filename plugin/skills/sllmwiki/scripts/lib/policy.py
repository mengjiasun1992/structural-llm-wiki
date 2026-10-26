"""The checkable part of the source policy (design doc §4.7): who can see the
wiki, which licenses are open, and whether a copy may be saved.

Judging a source's license or terms is the agent's job; it records what it
found (--license). This module decides from that record and the setting
source_copies: with "links-only" nothing is copied; otherwise a private wiki
keeps reference copies and a public one only openly licensed sources, unless
the owner has given permission (--allow-restricted, which is recorded).
"""

import json
import re
import subprocess
import urllib.error
import urllib.request

# SPDX ids (and public-domain) whose terms let anyone share a copy
OPEN_LICENSES = {
    'cc0-1.0', 'cc-pdm-1.0', 'public-domain', 'unlicense',
    'cc-by-2.0', 'cc-by-2.5', 'cc-by-3.0', 'cc-by-4.0', 'cc-by-sa-2.0', 'cc-by-sa-2.5', 'cc-by-sa-3.0', 'cc-by-sa-4.0',
    'mit', 'apache-2.0', 'bsd-2-clause', 'bsd-3-clause', 'isc', 'mpl-2.0',
}


def is_open(license):
    return (license or '').strip().lower() in OPEN_LICENSES


GITHUB_URL = re.compile(r'github(?:\.com|-[\w.-]+)?[:/]([^/\s:]+)/([^/\s]+?)(?:\.git)?/?\s*\Z')  # github.com, or an SSH host alias like github-work


def github_repo(url):
    """(owner, repo) for a GitHub remote URL, an SSH host alias included; None for another host."""
    m = GITHUB_URL.search(url or '')
    return (m.group(1), m.group(2)) if m else None


def _github_repo(root):
    """(owner, repo) of the wiki's origin on GitHub, as configured (before any insteadOf), or None."""
    p = subprocess.run(['git', 'config', '--get', 'remote.origin.url'], cwd=root, capture_output=True, text=True, check=False)
    return github_repo(p.stdout.strip()) if p.returncode == 0 else None


def visibility(root):
    """'public', 'private' (also a wiki with no remote, which only its owner has), or
    'unknown' (a remote off GitHub, or GitHub can't be asked), which counts as public."""
    repo = _github_repo(root)
    if repo is None:
        has_remote = subprocess.run(['git', 'remote'], cwd=root, capture_output=True, text=True, check=False).stdout.strip()
        return 'unknown' if has_remote else 'private'
    try:
        p = subprocess.run(['gh', 'repo', 'view', f'{repo[0]}/{repo[1]}', '--json', 'visibility', '-q', '.visibility'],
                           capture_output=True, text=True, check=False, timeout=30)
        if p.returncode == 0 and p.stdout.strip():
            return 'public' if p.stdout.strip().upper() == 'PUBLIC' else 'private'
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:  # without gh: the public API sees only public repositories
        with urllib.request.urlopen(f'https://api.github.com/repos/{repo[0]}/{repo[1]}', timeout=15) as r:
            return 'private' if json.load(r).get('private') else 'public'
    except urllib.error.HTTPError as e:
        e.close()
        return 'private' if e.code == 404 else 'unknown'
    except (urllib.error.URLError, OSError, ValueError):
        return 'unknown'


def may_copy(source_copies, seen_by, license, permission=None):
    """(True, why) when a copy may be saved, else (False, what to do instead)."""
    if source_copies == 'links-only':
        return False, 'Config.toml sets source_copies = "links-only": record it as a link (manifest.py put-source --kind link)'
    if seen_by == 'private':
        return True, 'a private wiki keeps reference copies (unless the source\'s terms forbid sharing, which is yours to judge)'
    if is_open(license):
        return True, f'{license} is an open license'
    if permission:
        return True, f'the owner gave permission to keep this copy: {permission}'
    who = 'a public wiki' if seen_by == 'public' else 'a wiki whose visibility GitHub couldn\'t confirm'
    return False, (f'{who} keeps copies of openly licensed sources only, and {license or "an unknown license"} isn\'t one: record it as a '
                   'link (manifest.py put-source --kind link), or ask the owner for permission and rerun with --allow-restricted')
