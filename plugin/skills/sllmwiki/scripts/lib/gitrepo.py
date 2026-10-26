"""The wiki's git repository: its remote and default branch, for the scripts that
publish (publish.py) and release (release.py)."""

import subprocess


def git(root, *args):
    """git's output in root, stripped; '' when it fails."""
    p = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else ''


def has_remote(root):
    return 'origin' in git(root, 'remote').split()


def default_branch(root):
    """origin's default branch (origin/HEAD, else mainline, main or master); without a remote, the current branch."""
    if has_remote(root):
        head = git(root, 'symbolic-ref', '--quiet', 'refs/remotes/origin/HEAD')
        if head:
            return head.rsplit('/', 1)[1]
        for name in ('mainline', 'main', 'master'):
            if git(root, 'rev-parse', '--verify', '--quiet', f'refs/remotes/origin/{name}'):
                return name
    return git(root, 'rev-parse', '--abbrev-ref', 'HEAD')
