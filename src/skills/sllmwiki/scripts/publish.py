#!/usr/bin/env python3
"""publish: a run's branch, commits and one pull request (design doc §5.2-§5.3).

  publish.py start <slug> --title TEXT --prompt TEXT
      Checks the working tree is clean (Obsidian's settings aside), brings the
      default branch up to date and stops if it has diverged from the remote's,
      then starts the run's branch, sllmwiki/<slug>, from it.
  publish.py summary <step> --json '{"title": ..., "checklist": [...], "decisions": [...], "body": "..."}'
      Records a step's summary: its review checklist items, the decisions it
      leaves to the owner, and its report. (Or --file SUMMARY.json.)
  publish.py commit <action> --tags a,b --subject TEXT
      Commits everything the run changed with the message
      [sllmwiki][<action>][<tags>] <subject>, the step's report, and the
      request that started the run, verbatim, in a Prompt: block.
  publish.py pr
      Pushes the branch and opens its pull request, or updates it, with a
      description built from the summaries: the review checklist first, then
      the decisions, then each step's report. Without gh, prints the link to
      open it; without a remote, keeps the commits on the branch.
  publish.py resume <slug>     back to a run's branch
  publish.py status            the run, its summaries and its pull request

A run never merges its pull request: the owner does. Its state lives in
.git/sllmwiki/, never committed. Options: --root <wiki>.
Exit code: 0, 1 refused or failed (the reason is printed), 2 usage error.
"""

import argparse
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True

from lib.layout import Cli, entry  # noqa: E402
from lib.policy import github_repo  # noqa: E402
from lib.util import write_text  # noqa: E402

cli = Cli('publish.py', 'usage: publish.py start|summary|commit|pr|resume|status ...; see --help')
ACTIONS = ('init', 'tags', 'ingest', 'smes', 'narrative', 'lint')
STEP_ORDER = ('tags', 'ingest', 'smes', 'narrative', 'lint')
IGNORED = ('sllmwiki/.obsidian/',)  # Obsidian rewrites its settings whenever the graph moves


def git(root, *args, check=True):
    p = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True)
    if check and p.returncode:
        cli.fail(f'git {" ".join(args)}: {(p.stderr or p.stdout).strip()}')
    return p.stdout.strip()


def state_dir(root):
    return os.path.join(root, git(root, 'rev-parse', '--git-dir'), 'sllmwiki')


def load_state(root):
    path = os.path.join(state_dir(root), 'run.json')
    if not os.path.isfile(path):
        cli.fail('no run in progress here; start one with publish.py start')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save_state(root, state):
    os.makedirs(os.path.join(state_dir(root), 'summaries'), exist_ok=True)
    write_text(os.path.join(state_dir(root), 'run.json'), json.dumps(state, indent=2, ensure_ascii=False))


def has_remote(root):
    return 'origin' in git(root, 'remote').split()


def default_branch(root):
    if has_remote(root):
        head = git(root, 'symbolic-ref', '--quiet', 'refs/remotes/origin/HEAD', check=False)
        if head:
            return head.rsplit('/', 1)[1]
        for name in ('mainline', 'main', 'master'):
            if git(root, 'rev-parse', '--verify', '--quiet', f'refs/remotes/origin/{name}', check=False):
                return name
    return git(root, 'rev-parse', '--abbrev-ref', 'HEAD')


def dirty(root):
    lines = git(root, 'status', '--porcelain').split('\n')
    return [line for line in lines if line.strip() and not any(line[3:].startswith(p) for p in IGNORED)]


def gh_available():
    try:
        return subprocess.run(['gh', 'auth', 'status'], capture_output=True, text=True).returncode == 0
    except OSError:
        return False


def start(root, slug, title, prompt):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
        cli.usage('the run\'s slug is kebab-case, such as gateway-routing')
    changes = dirty(root)
    if changes:
        cli.fail('the working tree has changes; commit or stash them first:\n' + '\n'.join(changes))
    base = default_branch(root)
    branch = f'sllmwiki/{slug}'
    if git(root, 'rev-parse', '--verify', '--quiet', f'refs/heads/{branch}', check=False):
        cli.fail(f'{branch} exists; continue it with publish.py resume {slug}, or pick another slug')
    if has_remote(root):
        git(root, 'fetch', '--quiet', 'origin', base)
        local = git(root, 'rev-parse', '--verify', '--quiet', f'refs/heads/{base}', check=False)
        behind = subprocess.run(['git', 'merge-base', '--is-ancestor', base, f'origin/{base}'], cwd=root).returncode == 0
        if local and not behind:
            cli.fail(f'your {base} has commits origin/{base} doesn\'t; sort that out first (a clone made before a rename?)')
        git(root, 'switch', '--quiet', '-C', base, f'origin/{base}')
    git(root, 'switch', '--quiet', '-c', branch, base)
    save_state(root, {'slug': slug, 'branch': branch, 'base': base, 'title': title, 'prompt': prompt, 'pr': None})
    print(f'started {branch} from {"origin/" if has_remote(root) else ""}{base}')


def record_summary(root, step, data):
    state = load_state(root)
    if not isinstance(data, dict) or not isinstance(data.get('title'), str):
        cli.fail('a summary is a JSON object with at least a "title"')
    for key in ('checklist', 'decisions'):
        if not isinstance(data.get(key, []), list):
            cli.fail(f'"{key}" is a list of strings')
    write_text(os.path.join(state_dir(root), 'summaries', f'{step}.json'), json.dumps(data, indent=2, ensure_ascii=False))
    print(f'recorded the {step} summary for {state["branch"]}')


def summaries(root):
    folder = os.path.join(state_dir(root), 'summaries')
    found = {}
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if name.endswith('.json'):
            with open(os.path.join(folder, name), encoding='utf-8') as f:
                found[name[:-5]] = json.load(f)
    order = {s: i for i, s in enumerate(STEP_ORDER)}
    return dict(sorted(found.items(), key=lambda kv: (order.get(kv[0], len(order)), kv[0])))


def quote(prompt):
    return '\n'.join('> ' + line if line else '>' for line in prompt.split('\n'))


def message(state, action, tags, subject, report):
    parts = [f'[sllmwiki][{action}][{",".join(tags)}] {subject}']
    if report:
        parts.append(report.strip())
    parts.append('Prompt:\n' + quote(state['prompt']))
    return '\n\n'.join(parts) + '\n'


def commit(root, action, tags, subject):
    state = load_state(root)
    if git(root, 'rev-parse', '--abbrev-ref', 'HEAD') != state['branch']:
        cli.fail(f'not on the run\'s branch {state["branch"]}; publish.py resume {state["slug"]}')
    git(root, 'add', '-A', '--', '.', *[f':(exclude){p}' for p in IGNORED])
    if not git(root, 'diff', '--cached', '--name-only'):
        cli.fail('nothing to commit')
    report = summaries(root).get(action, {}).get('body', '')
    msg = message(state, action, tags, subject, report)
    p = subprocess.run(['git', 'commit', '--quiet', '-F', '-'], cwd=root, input=msg, capture_output=True, text=True)
    if p.returncode:
        cli.fail(f'git commit: {(p.stderr or p.stdout).strip()}')
    print(f'committed {git(root, "rev-parse", "--short", "HEAD")} {msg.splitlines()[0]}')


def description(state, found):
    checklist = [item for s in found.values() for item in s.get('checklist', [])]
    decisions = [item for s in found.values() for item in s.get('decisions', [])]
    lines = ['## Review checklist', '', 'Tick each box as you check it; the "Review checklist" check turns green when all are ticked.', '']
    lines += [f'- [ ] {item}' for item in checklist] or ['- [ ] The changes in this pull request']
    if decisions:
        lines += ['', '## Decisions for you', ''] + [f'- {d}' for d in decisions]
    for s in found.values():
        lines += ['', f'## {s["title"]}', '', (s.get('body') or '').strip()]
    lines += ['', '## Prompt', '', quote(state['prompt']), '', 'This pull request was opened by a run; the owner merges it.']
    return '\n'.join(line for line in lines).rstrip() + '\n'


def pr(root):
    state = load_state(root)
    body = description(state, summaries(root))
    body_path = os.path.join(state_dir(root), 'pr.md')
    write_text(body_path, body)
    if not has_remote(root):
        print(f'no remote: the commits stay on {state["branch"]}; the description is in {body_path}')
        return
    git(root, 'push', '--quiet', '-u', 'origin', state['branch'])
    if not gh_available():
        remote = git(root, 'config', '--get', 'remote.origin.url')
        repo = github_repo(remote)
        link = f'https://github.com/{repo[0]}/{repo[1]}/compare/{state["base"]}...{state["branch"]}?expand=1' if repo else remote
        print(f'pushed {state["branch"]}; open the pull request at {link} with the description in {body_path}')
        return
    if state.get('pr'):
        p = subprocess.run(['gh', 'pr', 'edit', state['pr'], '--body-file', body_path], cwd=root, capture_output=True, text=True)
        verb = 'updated'
    else:
        p = subprocess.run(['gh', 'pr', 'create', '--base', state['base'], '--head', state['branch'], '--title', state['title'],
                            '--body-file', body_path], cwd=root, capture_output=True, text=True)
        verb = 'opened'
    if p.returncode:
        cli.fail(f'gh: {(p.stderr or p.stdout).strip()}')
    if verb == 'opened':
        state['pr'] = p.stdout.strip().splitlines()[-1]
        save_state(root, state)
    print(f'{verb} {state["pr"]}')


def resume(root, slug):
    branch = f'sllmwiki/{slug}'
    if not git(root, 'rev-parse', '--verify', '--quiet', f'refs/heads/{branch}', check=False):
        cli.fail(f'no run branch {branch}')
    git(root, 'switch', '--quiet', branch)
    state = load_state(root)
    if state['branch'] != branch:
        cli.fail(f'the recorded run is {state["branch"]}; start a new run for {slug}')
    print(f'on {branch}; pull request: {state.get("pr") or "not opened yet"}')


def main(argv):
    p = argparse.ArgumentParser(prog='publish.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--root')
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('start')
    s.add_argument('slug')
    s.add_argument('--title', required=True)
    s.add_argument('--prompt', required=True)
    m = sub.add_parser('summary')
    m.add_argument('step', choices=ACTIONS)
    g = m.add_mutually_exclusive_group(required=True)
    g.add_argument('--json')
    g.add_argument('--file')
    c = sub.add_parser('commit')
    c.add_argument('action', choices=ACTIONS)
    c.add_argument('--tags', required=True, type=lambda v: [t.strip() for t in v.split(',') if t.strip()])
    c.add_argument('--subject', required=True)
    sub.add_parser('pr')
    r = sub.add_parser('resume')
    r.add_argument('slug')
    sub.add_parser('status')
    args = p.parse_args(argv)
    root = os.path.abspath(args.root or '.')
    if subprocess.run(['git', 'rev-parse', '--git-dir'], cwd=root, capture_output=True).returncode:
        cli.fail(f'{root} isn\'t a git repository')

    if args.command == 'start':
        start(root, args.slug, args.title, args.prompt)
    elif args.command == 'summary':
        try:
            if args.json:
                data = json.loads(args.json)
            else:
                with open(args.file, encoding='utf-8') as f:
                    data = json.load(f)
        except (OSError, ValueError) as e:
            cli.fail(f'can\'t read the summary: {e}')
        record_summary(root, args.step, data)
    elif args.command == 'commit':
        commit(root, args.action, args.tags, args.subject)
    elif args.command == 'pr':
        pr(root)
    elif args.command == 'resume':
        resume(root, args.slug)
    else:
        state = load_state(root)
        print(f'run {state["branch"]} from {state["base"]}: {state["title"]}')
        print(f'summaries: {", ".join(summaries(root)) or "none"}; pull request: {state.get("pr") or "not opened yet"}')
    return 0


if __name__ == '__main__':  # pragma: no cover
    entry(main)
