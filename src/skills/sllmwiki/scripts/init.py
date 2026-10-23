#!/usr/bin/env python3
"""init: make this repository a Structural LLM Wiki, or bring one up to date (design doc §3, §8).

  init.py [--name NAME] [--force] [--commit --prompt TEXT] [--json] [--root <dir>]

Lays out the wiki: sllmwiki/tags/tags.yaml, the sources and narratives
manifests, the generated index and tag pages, README.md, AGENTS.md, CLAUDE.md,
.gitignore, .claude/settings.json (offering the plugin to teammates),
Config.toml, the CI workflows, and with the Obsidian add-on,
sllmwiki/.obsidian/graph.json. Run again after a plugin update, it refreshes
what it owns (the CI workflows and the ref they call this repository at,
CLAUDE.md, the plugin settings, .gitignore lines, Config.toml's missing
settings) and keeps the wiki's own: README.md and AGENTS.md once written,
Config.toml's values, every source, narrative and tag. GitHub's one-line
starter README is replaced.

It stops when the folder holds files that aren't a wiki's (code, documents),
unless --force says the owner agreed. --commit commits what it wrote, and nothing
else, with the request that started it (--prompt) in the message: for the
first setup. It never pushes; a rerun on a wiki is published as a pull request.

Exit code: 0 done, 1 refused (the reason is printed), 2 usage error.
"""

import argparse
import json
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True

from lib import config, layout, manifest, toml, wikiindex  # noqa: E402
from lib.layout import Cli, entry  # noqa: E402
from lib.util import dumps, read_text, write_text  # noqa: E402

cli = Cli('init.py', 'usage: init.py [--name NAME] [--force] [--commit --prompt TEXT]')
SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(SKILL, 'templates')
WIKI = os.path.join(TEMPLATES, 'wiki')
PLUGIN_JSON = os.path.normpath(os.path.join(SKILL, '..', '..', '..', '.claude-plugin', 'plugin.json'))
WORKFLOWS = ('wiki-checks.yml', 'review-checklist.yml')
# What may already be in a folder that becomes a wiki: a new repository's files
EXPECTED = {'.git', 'README.md', 'LICENSE', 'LICENSE.md', '.gitignore', '.github', '.claude', 'CLAUDE.md', 'AGENTS.md', '.DS_Store',
            'Config.toml', 'SLLMWIKI_INDICES.md', 'sllmwiki', 'templates'}


def action_ref():
    """The ref the wiki's CI calls the actions at: this plugin's release tag, or mainline without a version."""
    try:
        with open(PLUGIN_JSON, encoding='utf-8') as f:
            version = json.load(f).get('version')
    except (OSError, ValueError):
        version = None
    return f'v{version}' if version else 'mainline'


GRAPH_LINES = ('# with the Obsidian add-on, the graph\'s settings are shared', '!sllmwiki/.obsidian/graph.json')
OLD_GITIGNORE = {'# Obsidian: share only the graph settings, not each person\'s workspace': '# Obsidian: each person\'s settings are their own'}


class Init:
    def __init__(self, root, name):
        self.root, self.name, self.done = root, name, []

    def path(self, rel):
        return os.path.join(self.root, rel)

    def exists(self, rel):
        return os.path.exists(self.path(rel))

    def put(self, rel, text, verb):
        write_text(self.path(rel), text)
        self.done.append((verb, rel))

    def create(self, rel, text):
        """Write rel unless it exists."""
        if self.exists(rel):
            self.done.append(('kept', rel))
        else:
            self.put(rel, text, 'created')

    def refresh(self, rel, text):
        """Write rel unless it already says this."""
        if not self.exists(rel):
            self.put(rel, text, 'created')
        elif read_text(self.path(rel)) != text:
            self.put(rel, text, 'updated')
        else:
            self.done.append(('kept', rel))

    def layout(self):
        for kind in ('tags', 'sources', 'narratives'):
            self.create(manifest.FILES[kind], manifest.HEADERS[kind])

    def readme(self):
        text = read_text(os.path.join(WIKI, 'README.md')).replace('{{name}}', self.name)
        rel = 'README.md'
        if self.exists(rel) and len([line for line in read_text(self.path(rel)).splitlines() if line.strip()]) <= 2:
            self.put(rel, text, 'replaced GitHub\'s starter')  # a heading and maybe one line: a new repository's
        else:
            self.create(rel, text)

    def agents(self):
        self.create('AGENTS.md', read_text(os.path.join(WIKI, 'AGENTS.md')))
        self.refresh('CLAUDE.md', read_text(os.path.join(WIKI, 'CLAUDE.md')))

    def gitignore(self):
        """Add the template's lines the file lacks. The add-on's lines (sharing graph.json) are there only while
        the Obsidian add-on is on: a rerun with it off takes them out, so a person's own graph is never committed."""
        on = config.load(self.root).addons['obsidian']
        want = [line for line in read_text(os.path.join(WIKI, 'gitignore')).splitlines() if line.strip() and (on or line not in GRAPH_LINES)]
        rel = '.gitignore'
        have = read_text(self.path(rel)) if self.exists(rel) else ''
        lines = [OLD_GITIGNORE.get(line, line) for line in have.splitlines()]
        if not on:
            lines = [line for line in lines if line not in GRAPH_LINES]
        elif GRAPH_LINES[1] in lines and GRAPH_LINES[0] not in lines:
            lines.insert(lines.index(GRAPH_LINES[1]), GRAPH_LINES[0])
        missing = [line for line in want if line not in lines]
        body = '\n'.join(lines).rstrip('\n')
        text = (body + '\n\n' if body and missing else body + '\n' if body else '') + ('\n'.join(missing) + '\n' if missing else '')
        if text == have:
            self.done.append(('kept', rel))
        else:
            self.put(rel, text, 'updated' if have else 'created')

    def settings(self):
        rel = '.claude/settings.json'
        with open(os.path.join(WIKI, '.claude', 'settings.json'), encoding='utf-8') as f:
            want = json.load(f)
        have = {}
        if self.exists(rel):
            try:
                have = json.loads(read_text(self.path(rel)))
            except ValueError:
                cli.fail(f'{rel} isn\'t valid JSON; fix it, then rerun init')
        merged = dict(have)
        for key in ('extraKnownMarketplaces', 'enabledPlugins'):
            merged[key] = {**have.get(key, {}), **want[key]}
        self.refresh(rel, json.dumps(merged, indent=2) + '\n')

    def config(self):
        template = read_text(os.path.join(WIKI, 'Config.toml'))
        rel = layout.CONFIG
        if not self.exists(rel):
            self.put(rel, template, 'created')
            return
        text = read_text(self.path(rel))
        try:
            config.parse(text)
        except config.ConfigError as e:
            cli.fail('Config.toml has problems; fix them, then rerun init: ' + '; '.join(e.problems))
        added = add_missing_settings(text, template)
        if added != text:
            self.put(rel, added, 'added settings to')
        else:
            self.done.append(('kept', rel))

    def workflows(self):
        ref = action_ref()
        for name in WORKFLOWS:
            self.refresh(f'.github/workflows/{name}', read_text(os.path.join(TEMPLATES, name)).replace('{{ref}}', ref))

    def obsidian(self):
        if config.load(self.root).addons['obsidian']:
            self.create(layout.OBSIDIAN_GRAPH, read_text(os.path.join(WIKI, 'sllmwiki', '.obsidian', 'graph.json')))

    def pages(self):
        _, changed = wikiindex.sync(self.root, write=True)
        for rel in changed:
            self.done.append(('generated', rel))


def add_missing_settings(text, template):
    """text with each setting and add-on the template has and text lacks, added
    (with the template's own line, comment included) at the end of its table."""
    have = toml.loads(text)
    wanted, table = {}, None
    for line in template.split('\n'):
        m = re.match(r'\[([^\]]+)\]', line)
        if m:
            table = m.group(1)
        elif table and re.match(r'[A-Za-z_]+ = ', line):
            wanted.setdefault(table, []).append(line)
    lines = text.rstrip('\n').split('\n')
    for table, entries in wanted.items():
        missing = [line for line in entries if line.split(' = ')[0] not in have.get(table, {})]
        if not missing:
            continue
        at = next((i for i, line in enumerate(lines) if line.strip() == f'[{table}]'), None)
        if at is None:
            lines += ['', f'[{table}]'] + missing
            continue
        end = next((i for i in range(at + 1, len(lines)) if lines[i].startswith('[')), len(lines))
        # back over blank lines, and over the comments that introduce the next table
        while end > at + 1 and (not lines[end - 1].strip() or (end < len(lines) and lines[end - 1].lstrip().startswith('#'))):
            end -= 1
        lines[end:end] = missing
    return '\n'.join(lines) + '\n'


def unrelated(root):
    """What in root isn't a new repository's or a wiki's."""
    return sorted(n for n in os.listdir(root) if n not in EXPECTED)


def main(argv):
    p = argparse.ArgumentParser(prog='init.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--name')
    p.add_argument('--force', action='store_true')
    p.add_argument('--commit', action='store_true')
    p.add_argument('--prompt')
    p.add_argument('--json', action='store_true')
    p.add_argument('--root')
    args = p.parse_args(argv)
    if args.commit and not args.prompt:
        cli.usage('--commit needs --prompt, the request that started this')
    root = os.path.abspath(args.root or layout.find_root())
    if not os.path.isdir(root):
        cli.fail(f'no such folder: {root}')
    others = unrelated(root)
    if others and not layout.is_wiki(root) and not args.force:
        cli.fail(f'{root} holds files that aren\'t a wiki\'s ({", ".join(others[:8])}{", …" if len(others) > 8 else ""}); '
                 'a wiki is a repository of its own. Ask the owner, and pass --force to set it up here anyway')
    if subprocess.run(['git', 'rev-parse', '--git-dir'], cwd=root, capture_output=True).returncode:
        subprocess.run(['git', 'init', '-q', '-b', 'mainline'], cwd=root, check=True)
        new_repo = True
    else:
        new_repo = False
    name = args.name or os.path.basename(root)
    run = Init(root, name)
    run.layout()
    run.config()
    run.readme()
    run.agents()
    run.gitignore()
    run.settings()
    run.workflows()
    run.obsidian()
    run.pages()
    if args.commit:
        written = sorted({rel for verb, rel in run.done if verb != 'kept'})
        if written:  # only what init wrote: the owner's other untracked files stay theirs
            subprocess.run(['git', 'add', '--', *written], cwd=root, check=True)
        msg = '[sllmwiki][init] Set up the wiki\n\nPrompt:\n' + '\n'.join('> ' + line if line else '>' for line in args.prompt.split('\n')) + '\n'
        c = subprocess.run(['git', 'commit', '-q', '-F', '-'], cwd=root, input=msg, capture_output=True, text=True)
        if c.returncode and 'nothing to commit' not in c.stdout + c.stderr:
            cli.fail(f'git commit: {(c.stderr or c.stdout).strip()}')
        run.done.append(('committed', 'the wiki' if not c.returncode else 'nothing new'))
    if args.json:
        print(dumps({'root': root, 'new_repository': new_repo, 'ref': action_ref(), 'done': [{'what': v, 'file': f} for v, f in run.done]}))
    else:
        if new_repo:
            print(f'initialized a git repository in {root} on mainline')
        for verb, rel in run.done:
            if verb != 'kept':
                print(f'{verb} {rel}')
        print(f'init: a wiki at {root}; its CI calls the skill\'s actions at {action_ref()}')
    return 0


if __name__ == '__main__':  # pragma: no cover
    entry(main)
