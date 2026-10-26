#!/usr/bin/env python3
"""init: make this repository a Structural LLM Wiki, or bring one up to date (design doc §3, §8).

  init.py [--name NAME] [--force] [--set KEY=VALUE ...] [--commit --prompt TEXT] [--json] [--root <dir>]
  init.py --ask [--json]

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

--ask writes nothing: it lists the settings to ask the owner about, each with
its value (the default, or what Config.toml has) and what it means. On a first
setup, every one in ASK; on a rerun, those Config.toml lacks, which the plugin
added since. --set KEY=VALUE writes an answer into Config.toml, typed as the
setting is: true/false, a number, text, or a comma-separated list.

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
from lib.util import dumps, placeholder, read_text, write_text  # noqa: E402

cli = Cli('init.py', 'usage: init.py [--name NAME] [--force] [--set KEY=VALUE ...] [--commit --prompt TEXT] | init.py --ask')
SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(SKILL, 'templates')
WIKI = os.path.join(TEMPLATES, 'wiki')
PLUGIN_JSON = os.path.normpath(os.path.join(SKILL, '..', '..', '.claude-plugin', 'plugin.json'))  # plugin/skills/sllmwiki -> plugin/
WORKFLOWS = ('wiki-checks.yml', 'review-checklist.yml', 'release-book.yml')
# What may already be in a folder that becomes a wiki: a new repository's files
EXPECTED = {'.git', 'README.md', 'LICENSE', 'LICENSE.md', '.gitignore', '.github', '.claude', 'CLAUDE.md', 'AGENTS.md', '.DS_Store',
            'Config.toml', 'SLLMWIKI_INDICES.md', 'sllmwiki', 'templates'}


# what init reports for a file it was refused, such as a sandbox's guarded .claude/settings.json
SKIPPED = "couldn't write (blocked); add the plugin to it by hand:"


def action_ref():
    """The ref the wiki's CI calls the actions at: this plugin's release tag, or mainline without a version."""
    try:
        with open(PLUGIN_JSON, encoding='utf-8') as f:
            version = json.load(f).get('version')
    except (OSError, ValueError):
        version = None
    return f'v{version}' if version else 'mainline'


# The settings init asks the owner about: the rest keep their defaults until edited
ASK = ('language', 'source_copies', 'pdf_book', 'epub_book', 'html_book', 'title', 'author', 'obsidian', 'markers', 'images', 'smes_exclude')


def settings_of(text):
    """{key: (table, line)} of each setting line in a Config.toml text."""
    out, table = {}, None
    for line in text.split('\n'):
        m = re.match(r'\[([^\]]+)\]', line)
        if m:
            table = m.group(1)
        elif table and re.match(r'[A-Za-z_]+ = ', line):
            out[line.split(' = ')[0]] = (table, line)
    return out


def questions(root):
    """The settings to ask about: [{key, table, value, about}], every one in ASK on a first setup, and on a
    rerun those Config.toml doesn't have yet."""
    template = read_text(os.path.join(WIKI, 'Config.toml'))
    path = layout.config_path(root)
    have = toml.loads(read_text(path)) if os.path.isfile(path) else None
    out = []
    for key, (table, line) in settings_of(template).items():
        if key not in ASK or (have is not None and key in have.get(table, {})):
            continue
        value, _, about = line.split(' = ', 1)[1].partition('#')
        out.append({'key': key, 'table': table, 'value': toml.loads(f'v = {value.strip()}')['v'], 'about': about.strip()})
    return out


def set_values(text, sets):
    """text with each {key: value} written in place on its line, the line's comment kept in its column."""
    lines = text.split('\n')
    for key, value in sets.items():
        i = next(i for i, line in enumerate(lines) if line.startswith(f'{key} = '))
        new = f'{key} = {toml_value(value)}'
        comment = re.search(r'\s{2,}(#.*)', lines[i])
        lines[i] = f'{new.ljust(comment.start(1) - 1)} {comment.group(1)}' if comment else new
    return '\n'.join(lines)


def toml_value(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, list):
        return '[' + ', '.join(toml_value(v) for v in value) + ']'
    if isinstance(value, int):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def parse_sets(pairs):
    """{key: value} of --set KEY=VALUE pairs, each typed as the template's setting; usage error on a bad one."""
    known = settings_of(read_text(os.path.join(WIKI, 'Config.toml')))
    out = {}
    for pair in pairs:
        key, eq, raw = pair.partition('=')
        if not eq or key not in known:
            cli.usage(f'--set {pair}: settings are {", ".join(sorted(known))}')
        default = toml.loads(f'v = {known[key][1].split(" = ", 1)[1].partition("#")[0].strip()}')['v']
        raw = raw.strip()
        if isinstance(default, bool):
            if raw.lower() not in ('true', 'false'):
                cli.usage(f'--set {key}: true or false')
            out[key] = raw.lower() == 'true'
        elif isinstance(default, int):
            if not raw.isdigit():
                cli.usage(f'--set {key}: a number')
            out[key] = int(raw)
        elif isinstance(default, list):
            out[key] = [v.strip() for v in raw.split(',') if v.strip()]
        else:
            out[key] = raw
    return out


GRAPH_LINES = ('# with the Obsidian add-on, the graph\'s settings are shared', '!sllmwiki/.obsidian/graph.json')
OLD_GITIGNORE = {'# Obsidian: share only the graph settings, not each person\'s workspace': '# Obsidian: each person\'s settings are their own'}


class Init:
    def __init__(self, root, name, sets=None):
        self.sets = sets or {}
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
        self.move_old()

    def move_old(self):
        """Before 1.0, the settings, the templates and the index were at the root: move them into sllmwiki/."""
        for old, new in ((layout.OLD_CONFIG, layout.CONFIG), *((t, layout.TEMPLATES) for t in layout.OLD_TEMPLATES)):
            if os.path.exists(self.path(old)) and not os.path.exists(self.path(new)):
                os.rename(self.path(old), self.path(new))
                self.done.append((f'moved {old} to', new))
        readme = read_text(self.path('README.md')) if self.exists('README.md') else ''
        for old in layout.OLD_INDEX:
            if os.path.isfile(self.path(old)) and wikiindex.GENERATED in read_text(self.path(old)):  # pages() writes it in its new place
                os.remove(self.path(old))
                self.done.append(('removed the old', old))
            readme = readme.replace(f']({old})', f']({layout.INDEX})')  # the README init wrote links to it; only that link changes
        if self.exists('README.md') and readme != read_text(self.path('README.md')):
            self.put('README.md', readme, 'pointed the index link in')

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
        try:
            if self.exists(rel):
                try:
                    have = json.loads(read_text(self.path(rel)))
                except ValueError:
                    cli.fail(f'{rel} isn\'t valid JSON; fix it, then rerun init')
            merged = dict(have)
            for key in ('extraKnownMarketplaces', 'enabledPlugins'):
                merged[key] = {**have.get(key, {}), **want[key]}
            self.refresh(rel, json.dumps(merged, indent=2) + '\n')
        except OSError:  # a sandbox guards Claude Code's settings from scripts
            self.done.append((SKIPPED, rel))

    def config(self):
        template = read_text(os.path.join(WIKI, 'Config.toml'))
        rel = layout.CONFIG
        if not self.exists(rel):
            text = set_values(template, self.sets)
            self.check(text)
            self.put(rel, text, 'created')
            return
        text = read_text(self.path(rel))
        try:
            config.parse(text)
        except config.ConfigError as e:
            cli.fail('Config.toml has problems; fix them, then rerun init: ' + '; '.join(e.problems))
        added = set_values(add_missing_settings(text, template), self.sets)
        self.check(added)
        if added != text:
            self.put(rel, added, 'added settings to')
        else:
            self.done.append(('kept', rel))

    @staticmethod
    def check(text):
        try:
            config.parse(text)
        except config.ConfigError as e:
            cli.usage('--set gives Config.toml problems: ' + '; '.join(e.problems))

    def workflows(self):
        ref = action_ref()
        for name in WORKFLOWS:
            self.refresh(f'.github/workflows/{name}', read_text(os.path.join(TEMPLATES, name)).replace('{{ref}}', ref))

    def obsidian(self):
        if config.load(self.root).addons['obsidian']:
            self.create(layout.OBSIDIAN_GRAPH, read_text(os.path.join(WIKI, 'sllmwiki', '.obsidian', 'graph.json')))

    def pages(self):
        """The index and tag pages: every one is init's, so --commit stages it even when a run without
        --commit already wrote it."""
        _, changed = wikiindex.sync(self.root, write=True)
        for rel in changed:
            self.done.append(('generated', rel))
        for rel in wikiindex.pages(self.root):
            if rel not in changed:
                self.done.append(('kept', rel))


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
    return sorted(n for n in os.listdir(root) if n not in EXPECTED and not placeholder(os.path.join(root, n)))


def main(argv):
    p = argparse.ArgumentParser(prog='init.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--name')
    p.add_argument('--force', action='store_true')
    p.add_argument('--commit', action='store_true')
    p.add_argument('--prompt')
    p.add_argument('--ask', action='store_true')
    p.add_argument('--set', action='append', default=[], metavar='KEY=VALUE')
    p.add_argument('--json', action='store_true')
    p.add_argument('--root')
    args = p.parse_args(argv)
    sets = parse_sets(args.set)
    if args.commit and not args.prompt:
        cli.usage('--commit needs --prompt, the request that started this')
    root = os.path.abspath(args.root or layout.find_root())
    if not os.path.isdir(root):
        cli.fail(f'no such folder: {root}')
    if args.ask:
        found = questions(root)
        if args.json:
            print(dumps({'first_setup': not os.path.isfile(layout.config_path(root)), 'ask': found}))
        else:
            for q in found:
                print(f'{q["key"]} = {toml_value(q["value"])}: {q["about"]}')
            print(f'init: {len(found)} setting(s) to ask about' if found else 'init: nothing new to ask about')
        return 0
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
    run = Init(root, name, sets)
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
        # init's own files, written now or by a run without --commit; the owner's other files stay theirs
        written = sorted({rel for verb, rel in run.done if verb != SKIPPED and os.path.exists(run.path(rel))})
        if written:
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
