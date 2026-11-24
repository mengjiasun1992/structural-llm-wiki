#!/usr/bin/env python3
"""bump-version: move every place that names the release version to a new one.

Usage: python3 src/tools/bump-version.py [--root DIR] NEW_VERSION

The plugin installs the package at exactly its own version, so a release writes the
version in several files, which must agree (tests check they do):

  - plugin/.claude-plugin/plugin.json      "version"
  - src/sllmwiki/__init__.py               __version__
  - plugin/skills/sllmwiki/SKILL.md        the version it installs and checks for
  - src/actions/*/action.yml               the @v<version> in each usage example

This reads the current version from __init__.py and replaces it, as a whole version
(not 11.4.0 for 1.4.0), in each of those files, leaving everything else as it was.
The new version is MAJOR.MINOR.PATCH and higher than the current one: a number
PyPI has seen can't be published again.

Exit code: 0 = bumped, 1 = a file that should name the current version doesn't
(nothing is written), 2 = usage error.
"""

import argparse
import glob
import os
import re
import sys

INIT = 'src/sllmwiki/__init__.py'
FILES = ('plugin/.claude-plugin/plugin.json', INIT, 'plugin/skills/sllmwiki/SKILL.md', 'src/actions/*/action.yml')
SEMVER = re.compile(r'(\d+)\.(\d+)\.(\d+)\Z')


def current(root):
    with open(os.path.join(root, INIT), encoding='utf-8') as f:
        return re.search(r"__version__ = '([^']+)'", f.read()).group(1)


def paths(root):
    """Every file that names the version, repository-relative, in FILES' order."""
    out = []
    for pattern in FILES:
        found = sorted(glob.glob(os.path.join(root, pattern)))
        out += [os.path.relpath(p, root).replace(os.sep, '/') for p in found] or [pattern]
    return out


def problem(old, new):
    """Why new can't follow old, or None."""
    if not SEMVER.match(new):
        return f'{new} isn\'t MAJOR.MINOR.PATCH'
    if tuple(map(int, SEMVER.match(new).groups())) <= tuple(map(int, SEMVER.match(old).groups())):
        return f'{new} isn\'t higher than the current {old}'
    return None


def bump(root, new):
    """{path: replacements} after moving every file from the current version to new; raises ValueError,
    writing nothing, when a file doesn't name the current version."""
    old = current(root)
    pattern = re.compile(r'(?:(?<=@v)|(?<![\w.]))' + re.escape(old) + r'(?!\w|\.\d)')  # a whole version, or a tag's, maybe ending a sentence
    texts, counts = {}, {}
    for rel in paths(root):
        path = os.path.join(root, rel)
        text = ''
        if os.path.isfile(path):
            with open(path, encoding='utf-8') as f:
                text = f.read()
        texts[rel], counts[rel] = pattern.subn(new, text)
        if not counts[rel]:
            raise ValueError(f'{rel} doesn\'t name the current version {old}: fix it by hand first')
    for rel, text in texts.items():
        with open(os.path.join(root, rel), 'w', encoding='utf-8', newline='') as f:
            f.write(text)
    return counts


def main(argv=None):
    p = argparse.ArgumentParser(prog='bump-version', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--root', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
    p.add_argument('version')
    args = p.parse_args(argv)
    old = current(args.root)
    if problem(old, args.version):
        print(f'bump-version: {problem(old, args.version)}', file=sys.stderr)
        return 2
    try:
        counts = bump(args.root, args.version)
    except ValueError as e:
        print(f'bump-version: {e}', file=sys.stderr)
        return 1
    for rel, n in counts.items():
        print(f'{rel}: {n}')
    print(f'{old} -> {args.version}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
