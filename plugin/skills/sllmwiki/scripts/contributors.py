#!/usr/bin/env python3
"""contributors: the people behind some code or docs, ranked with their evidence
(design doc §5.1, the smes step).

  contributors.py <path> [<path> ...] [--repo DIR] [--limit N] [--json] [--root <wiki>]

<path>s are files or folders in the repository at --repo (default: the wiki's
own). Each person is ranked by:
  - commits touching the paths, recent ones counting more (a year halves a commit's weight);
  - the lines of those files they last changed (git blame), as a share;
  - CODEOWNERS rules that cover the paths;
  - Reviewed-by and Co-authored-by trailers on those commits;
  - author, authors or owner in a markdown file's front matter.
Never listed: anyone in the wiki's smes_exclude, bots, and commits a wiki run
made ([sllmwiki] subjects), so no one becomes an SME for writing the wiki.

Exit code: 0, 1 when a path or the repository isn't found, 2 on a usage error.
"""

import argparse
import datetime
import fnmatch
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True

from lib import config, runstats  # noqa: E402
from lib.layout import Cli, entry  # noqa: E402
from lib.util import dumps, read_text  # noqa: E402

cli = Cli('contributors.py', 'usage: contributors.py <path> [<path> ...] [--repo DIR] [--limit N] [--json]')
HALF_LIFE_DAYS = 365
MAX_BLAME_FILES = 200
BOT = re.compile(r'\[bot\]|(?:^|[-_.])bot(?:$|[-_.@])|dependabot|renovate|github-actions|^noreply@', re.I)  # tools, not people
TRAILER = re.compile(r'^(Reviewed-by|Co-authored-by):\s*(.+?)\s*<([^>]+)>\s*$', re.I | re.M)
WEIGHTS = {'commits': 1.0, 'lines': 10.0, 'owner': 3.0, 'reviews': 1.0, 'author': 3.0}


def git(repo, *args):
    try:
        p = subprocess.run(['git', '-C', repo, *args], capture_output=True, text=True)
    except OSError:
        return ''
    return p.stdout if p.returncode == 0 else ''


class Person:
    def __init__(self, name, email):
        self.name, self.email = name, email
        self.commits, self.weight, self.last, self.lines, self.reviews = 0, 0.0, '', 0, 0
        self.owner, self.author = [], []

    def score(self, total_lines):
        return (WEIGHTS['commits'] * self.weight + WEIGHTS['lines'] * (self.lines / total_lines if total_lines else 0)
                + WEIGHTS['owner'] * bool(self.owner) + WEIGHTS['reviews'] * self.reviews + WEIGHTS['author'] * bool(self.author))

    def evidence(self, total_lines):
        parts = []
        if self.commits:
            parts.append(f'{self.commits} commit{"s" * (self.commits != 1)}, the last on {self.last}')
        if self.lines:
            parts.append(f'last changed {self.lines:,} of {total_lines:,} current lines')
        if self.owner:
            parts.append('CODEOWNERS for ' + ', '.join(self.owner))
        if self.reviews:
            parts.append(f'reviewed or co-wrote {self.reviews}')
        if self.author:
            parts.append('named author of ' + ', '.join(self.author))
        return '; '.join(parts)


def excluded(name, email, exclude):
    """A bot or a tool, or someone in smes_exclude, by name, email or handle (an email's
    local part stands for the same person's handle)."""
    who = {name.lower(), email.lower(), '@' + email.split('@')[0].lower(), '@' + name.lower().lstrip('@')}
    names = {x.lower() for x in exclude} | {'@' + x.lower().split('@')[0] for x in exclude if '@' in x[1:]}
    return bool(BOT.search(name) or BOT.search(email) or who & names or name.lower() in {x.lstrip('@') for x in names})


def owners(repo, paths):
    """{owner: [patterns]} from the repository's CODEOWNERS rules that cover any of the paths."""
    for where in ('.github/CODEOWNERS', 'CODEOWNERS', 'docs/CODEOWNERS'):
        full = os.path.join(repo, where)
        if os.path.isfile(full):
            break
    else:
        return {}
    out = {}
    for line in read_text(full).split('\n'):
        fields = line.split('#', 1)[0].split()
        if len(fields) < 2:
            continue
        pattern = fields[0].strip('/')
        if any(fnmatch.fnmatch(p, pattern) or fnmatch.fnmatch(p, pattern + '/*') or p.startswith(pattern + '/') or p == pattern
               or pattern in ('*', '**') for p in paths):
            for owner in fields[1:]:
                out.setdefault(owner, []).append(fields[0])
    return out


def front_matter_authors(repo, files):
    """{name: [file]} from markdown front matter: author, authors or owner."""
    out = {}
    for f in files:
        if not f.endswith('.md'):
            continue
        text = read_text(os.path.join(repo, f)) if os.path.isfile(os.path.join(repo, f)) else ''
        m = re.match(r'---\n(.*?)\n---', text, re.S)
        for line in (m.group(1).split('\n') if m else []):
            k, _, v = line.partition(':')
            if k.strip().lower() in ('author', 'authors', 'owner'):
                for name in re.split(r'[,;]|\band\b', v.strip(' []"\'')):
                    if name.strip(' "\''):
                        out.setdefault(name.strip(' "\''), []).append(f)
    return out


def rank(repo, paths, exclude, now=None):
    """(people, total current lines), people sorted by score."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    people = {}

    def person(name, email):
        key = email.lower() or name.lower()
        return people.setdefault(key, Person(name, email))
    log = git(repo, 'log', '--no-merges', '--format=%x1e%an%x1f%ae%x1f%aI%x1f%s%x1f%b', '--', *paths)
    for record in log.split('\x1e')[1:]:
        name, email, when, subject, body = (record.split('\x1f') + [''] * 5)[:5]
        if subject.startswith('[sllmwiki]'):
            continue
        for _, tname, temail in TRAILER.findall(body):
            if not excluded(tname, temail, exclude):
                person(tname, temail).reviews += 1
        if excluded(name, email, exclude):
            continue
        p = person(name, email)
        age = (now - runstats.parse_time(when.strip())).days
        p.commits += 1
        p.weight += 0.5 ** (max(age, 0) / HALF_LIFE_DAYS)
        p.last = max(p.last, when.strip()[:10])
    files = [f for f in git(repo, 'ls-files', '--', *paths).split('\n') if f][:MAX_BLAME_FILES]
    total = 0
    for f in files:
        name = email = None
        for line in git(repo, 'blame', '--line-porcelain', '--', f).split('\n'):
            if line.startswith('author '):
                name = line[7:]
            elif line.startswith('author-mail '):
                email = line[12:].strip('<>')
            elif line.startswith('\t'):
                total += 1
                if name is not None and not excluded(name, email or '', exclude) and name != 'Not Committed Yet':
                    person(name, email or '').lines += 1
    for owner, patterns in owners(repo, paths).items():
        if not excluded(owner, owner if '@' in owner and not owner.startswith('@') else '', exclude):
            match = next((p for p in people.values() if owner.lstrip('@').lower() in (p.email.split('@')[0].lower(), p.name.lower())
                          or owner.lower() == p.email.lower()), None)
            (match or person(owner, owner if '@' in owner[1:] else '')).owner += patterns
    for name, found in front_matter_authors(repo, files).items():
        if not excluded(name, '', exclude):
            match = next((p for p in people.values() if p.name.lower() == name.lower()), None)
            (match or person(name, '')).author += found
    ranked = sorted(people.values(), key=lambda p: (-p.score(total), p.name))
    return [p for p in ranked if p.score(total) > 0], total


def main(argv):
    p = argparse.ArgumentParser(prog='contributors.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('paths', nargs='+')
    p.add_argument('--repo')
    p.add_argument('--limit', type=int, default=10)
    p.add_argument('--json', action='store_true')
    p.add_argument('--root')
    args = p.parse_args(argv)
    root = cli.wiki(args.root)
    repo = os.path.abspath(args.repo or root)
    if not git(repo, '--version'):
        cli.fail('git doesn\'t run here (preflight.sh says why), so there is no history to rank people from')
    if not git(repo, 'rev-parse', '--git-dir'):
        cli.fail(f'{repo} isn\'t a git repository')
    missing = [x for x in args.paths if not os.path.exists(os.path.join(repo, x))]
    if missing:
        cli.fail(f'not in {repo}: {", ".join(missing)}')
    try:
        exclude = config.load(root).settings['smes_exclude']
    except config.ConfigError as e:
        cli.fail('Config.toml is invalid, fix it first: ' + '; '.join(e.problems))
    people, total = rank(repo, [x.rstrip('/') or '.' for x in args.paths], exclude)
    rows = [{'name': x.name, 'email': x.email, 'score': round(x.score(total), 2), 'evidence': x.evidence(total)} for x in people[:args.limit]]
    if args.json:
        print(dumps({'repo': repo, 'paths': args.paths, 'people': rows}))
        return 0
    for i, r in enumerate(rows, 1):
        print(f'{i}. {r["name"]}' + (f' <{r["email"]}>' if r['email'] else '') + f' ({r["score"]}): {r["evidence"]}')
    if not rows:
        print('no one found: no commits, blame, CODEOWNERS or named authors for these paths')
    return 0


if __name__ == '__main__':  # pragma: no cover
    entry(main)
