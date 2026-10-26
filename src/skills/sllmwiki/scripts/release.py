#!/usr/bin/env python3
"""release: a release of the wiki, with its book attached (docs/book_design.md §2.2, §6.7).

  release.py plan [--anyway]
      Fetches, then checks the default branch on GitHub: its head commit is
      what gets released. Refuses when its checks failed or haven't finished
      (--anyway releases regardless, and the notes say what was failing), or
      when the release workflow isn't installed (rerun /sllmwiki:init). Picks
      the version, the date (vYYYY.MM.DD, then .2 for a second release that
      day), and drafts the notes from what changed since the last release:
      narratives added, updated and removed, new sources, open questions, and
      the book's formats (Config.toml's [structural-llm-wiki-release]), in the
      wiki's language. Writes the plan and the notes to .git/sllmwiki/release/
      (plan.json, notes.md): review the notes, and edit them if they need it.
  release.py create [--notes FILE]
      Makes the planned release on GitHub (gh release create) at the planned
      commit, with the notes (notes.md, or FILE). The release workflow then
      builds the book and attaches it. Prints the release's link.
  release.py wait [--timeout SECONDS]
      Follows the release workflow's run for the planned release, then
      reports the attached files with their sizes and links, and the release
      notes' Known issues, if any. --timeout defaults to 900.
  release.py preview [--timeout SECONDS]
      Builds the book from the current branch, as pushed, without a release:
      runs the release workflow on it (Run workflow), follows the run, and
      reports it and its artifact, which GitHub keeps for 90 days.

Needs gh, signed in. Options: --json, --root <wiki>.
Exit code: 0, 1 refused or failed (the reason is printed), 2 usage error.
"""

import argparse
import json
import os
import subprocess
import sys
import time

sys.dont_write_bytecode = True

from lib import config, language, release  # noqa: E402
from lib.gitrepo import default_branch, git, has_remote  # noqa: E402
from lib.layout import Cli, entry  # noqa: E402
from lib.policy import github_repo  # noqa: E402
from lib.util import dumps, write_text  # noqa: E402

cli = Cli('release.py', 'usage: release.py plan|create|wait|preview ...; see --help')


def gh(root, *args):
    """gh's output; fails with its message. $EVAL_SLLMWIKI_GH names a stand-in, from the wiki's
    root: the behavior evals' (evals/_fixture/release.sh), since an eval can set only EVAL_* variables."""
    stand_in = os.environ.get('EVAL_SLLMWIKI_GH')
    try:
        p = subprocess.run([os.path.join(root, stand_in) if stand_in else 'gh', *args], cwd=root, capture_output=True, text=True)
    except OSError:
        cli.fail('gh isn\'t installed: install the GitHub CLI and sign in (gh auth login)')
    if p.returncode:
        cli.fail(f'gh {" ".join(args[:2])}: {(p.stderr or p.stdout).strip()}')
    return p.stdout


def state(root):
    return os.path.join(git(root, 'rev-parse', '--absolute-git-dir') or os.path.join(root, '.git'), 'sllmwiki', 'release')


def load_plan(root):
    path = os.path.join(state(root), 'plan.json')
    if not os.path.isfile(path):
        cli.fail('no release is planned: run release.py plan first')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def plan(root, repo, anyway):
    branch = default_branch(root)
    git(root, 'fetch', '--quiet', '--tags', 'origin')
    commit = git(root, 'rev-parse', f'origin/{branch}')
    if not commit:
        cli.fail(f'origin/{branch} isn\'t there to release: push the default branch first')
    if subprocess.run(['git', 'cat-file', '-e', f'{commit}:{release.WORKFLOW}'], cwd=root, capture_output=True).returncode:
        cli.fail(f'{release.WORKFLOW} isn\'t on {branch}: rerun /sllmwiki:init and merge its pull request, so a release builds the book')
    runs = json.loads(gh(root, 'api', f'repos/{repo}/commits/{commit}/check-runs?per_page=100')).get('check_runs', [])
    checks, names = release.checks(runs)
    if checks in ('failing', 'pending') and not anyway:
        why = 'failed' if checks == 'failing' else 'haven\'t finished'
        cli.fail(f'{branch}\'s checks {why}: {", ".join(names)}. Fix them (or wait), or release anyway with --anyway')
    published = json.loads(gh(root, 'release', 'list', '-R', repo, '--limit', '100', '--json', 'tagName,publishedAt,isDraft'))
    published = [r for r in published if not r.get('isDraft')]
    previous = max(published, key=lambda r: r['publishedAt'])['tagName'] if published else None
    taken = {r['tagName'] for r in published} | set(git(root, 'tag', '--list').split())
    cfg = config.get(root)
    found = release.changes(root, previous, commit)
    pack = language.pack(cfg.settings['language']) or language.ENGLISH
    out = {'version': release.version(taken), 'commit': commit, 'branch': branch, 'repo': repo, 'previous': previous,
           'checks': checks, 'failing': names if checks == 'failing' else [], 'formats': cfg.book_formats(),
           'changes': found}
    text = release.notes(found, previous, out['formats'], pack, out['failing'])
    write_text(os.path.join(state(root), 'plan.json'), json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    write_text(os.path.join(state(root), 'notes.md'), text)
    out['notes'] = os.path.join(state(root), 'notes.md')
    return out, text


def create(root, notes_file):
    p = load_plan(root)
    notes = notes_file or os.path.join(state(root), 'notes.md')
    if not os.path.isfile(notes):
        cli.fail(f'no notes at {notes}')
    name = config.get(root).release['title'] or os.path.basename(p['repo'])  # the book's title, as on its cover
    url = gh(root, 'release', 'create', p['version'], '-R', p['repo'], '--target', p['commit'],
             '--title', f'{name} {p["version"]}', '--notes-file', notes).strip()
    p['url'] = url
    write_text(os.path.join(state(root), 'plan.json'), json.dumps(p, indent=2, ensure_ascii=False) + '\n')
    return p


def wait(root, timeout, interval):
    p = load_plan(root)
    deadline, run = time.time() + timeout, None
    while True:
        runs = _runs(root, p['repo'], 'release')
        # the planned commit's run: a release made again under the same name leaves the earlier one's run in the list
        run = next((r for r in runs if r.get('headBranch') == p['version'] and r.get('headSha', p['commit']) == p['commit']), None)
        if run and run.get('status') == 'completed':
            break
        if time.time() >= deadline:
            cli.fail(f'the book for {p["version"]} isn\'t built after {timeout} s' + (f': follow it at {run["url"]}' if run else
                     ': no release workflow run started; check the repository\'s Actions'))
        time.sleep(interval)
    view = json.loads(gh(root, 'release', 'view', p['version'], '-R', p['repo'], '--json', 'url,assets,body'))
    body = view.get('body') or ''
    heading = '### ' + (language.pack(config.get(root).settings['language']) or language.ENGLISH).t('Known issues')
    issues = body[body.rfind(heading) + len(heading):].strip() if heading in body else ''
    return {'version': p['version'], 'release': view.get('url'), 'run': run['url'], 'conclusion': run.get('conclusion'),
            'files': [{'name': a['name'], 'bytes': a.get('size'), 'url': a.get('url')} for a in view.get('assets', [])],
            'issues': issues}


def _runs(root, repo, event, branch=None):
    return json.loads(gh(root, 'run', 'list', '-R', repo, '--workflow', os.path.basename(release.WORKFLOW), '--event', event,
                         *(['--branch', branch] if branch else []), '--limit', '20', '--json', 'databaseId,status,conclusion,headBranch,headSha,url'))


def preview(root, repo, timeout, interval):
    ref = git(root, 'rev-parse', '--abbrev-ref', 'HEAD')
    git(root, 'fetch', '--quiet', 'origin')
    if not git(root, 'rev-parse', '--verify', '--quiet', f'refs/remotes/origin/{ref}'):
        cli.fail(f'{ref} isn\'t on GitHub: push it first, and the preview builds it as pushed')
    if subprocess.run(['git', 'cat-file', '-e', f'origin/{ref}:{release.WORKFLOW}'], cwd=root, capture_output=True).returncode:
        cli.fail(f'{release.WORKFLOW} isn\'t on {ref}: rerun /sllmwiki:init and merge its pull request')
    before = {r['databaseId'] for r in _runs(root, repo, 'workflow_dispatch', ref)}
    gh(root, 'workflow', 'run', os.path.basename(release.WORKFLOW), '-R', repo, '--ref', ref)
    deadline, run = time.time() + timeout, None
    while True:
        run = next((r for r in _runs(root, repo, 'workflow_dispatch', ref) if r['databaseId'] not in before), None)
        if run and run.get('status') == 'completed':
            break
        if time.time() >= deadline:
            cli.fail(f'the preview of {ref} isn\'t built after {timeout} s' + (f': follow it at {run["url"]}' if run else ''))
        time.sleep(interval)
    found = json.loads(gh(root, 'api', f'repos/{repo}/actions/runs/{run["databaseId"]}/artifacts')).get('artifacts', [])
    return {'branch': ref, 'run': run['url'], 'conclusion': run.get('conclusion'),
            'artifacts': [{'name': a['name'], 'bytes': a.get('size_in_bytes')} for a in found]}


def main(argv):
    p = argparse.ArgumentParser(prog='release.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('command', choices=['plan', 'create', 'wait', 'preview'])
    p.add_argument('--anyway', action='store_true')
    p.add_argument('--notes')
    p.add_argument('--timeout', type=int, default=900)
    p.add_argument('--interval', type=float, default=10.0)  # between looks at the run, while waiting
    p.add_argument('--json', action='store_true')
    p.add_argument('--root')
    args = p.parse_args(argv)
    root = cli.wiki(args.root)
    repo = github_repo(git(root, 'config', '--get', 'remote.origin.url')) if has_remote(root) else None
    if not repo:
        cli.fail('the wiki has no GitHub remote (origin): a release lives on GitHub')
    repo = '/'.join(repo)
    if args.command == 'plan':
        out, text = plan(root, repo, args.anyway)
        if args.json:
            print(dumps(out))
        else:
            print(f'Releasing {out["version"]} from {out["branch"]} ({out["commit"][:7]}); checks: {out["checks"]}'
                  + (f' (failing: {", ".join(out["failing"])})' if out['failing'] else ''))
            print(f'Notes, to review: {out["notes"]}\n\n{text}')
        return 0
    if args.command == 'create':
        out = create(root, args.notes)
        print(dumps(out) if args.json else f'Release: {out["url"]}')
        return 0
    if args.command == 'preview':
        out = preview(root, repo, args.timeout, args.interval)
        if args.json:
            print(dumps(out))
        else:
            print(f'Preview of {out["branch"]}: {out["conclusion"]} ({out["run"]})')
            for a in out['artifacts']:
                print(f'{a["name"]}: {a["bytes"]:,} bytes, on the run\'s page' if a['bytes'] is not None else f'{a["name"]}: on the run\'s page')
        return 0 if out['conclusion'] == 'success' else 1
    out = wait(root, args.timeout, args.interval)
    if args.json:
        print(dumps(out))
    else:
        print(f'Release: {out["release"]}\nBuild: {out["conclusion"]} ({out["run"]})')
        for f in out['files']:
            print(f'{f["name"]}: {f["bytes"]:,} bytes, {f["url"]}' if f['bytes'] is not None else f'{f["name"]}: {f["url"]}')
        if not out['files']:
            print('No files: no book format is on (Config.toml\'s [structural-llm-wiki-release]), or the build failed.')
        if out['issues']:
            print(f'Known issues:\n{out["issues"]}')
    return 0 if out['conclusion'] == 'success' else 1


if __name__ == '__main__':  # pragma: no cover
    entry(main)
