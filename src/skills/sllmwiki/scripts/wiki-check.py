#!/usr/bin/env python3
"""wiki-check: is the wiki consistent? (design doc §4, §7.2)

  wiki-check.py [--fix] [--json] [--visibility public|private] [--root <wiki>]

Errors:
  CONFIG_INVALID            Config.toml has a problem
  LANGUAGE_PACK_INVALID     a language pack in templates/languages/ can't be read
  LANGUAGE_PACK             Config.toml's language has no pack, so headings stay English (warning)
  YAML_INVALID              tags.yaml or a manifest can't be read
  MISSING_FIELD, UNKNOWN_FIELD, BAD_TYPE, BAD_VALUE, BAD_ENTRY
                            an entry doesn't match the schema (lib/schema.py)
  UNKNOWN_PARENT, TAG_CYCLE, UNKNOWN_TAG
                            the tag tree is broken, or a manifest names a tag that isn't one
  SOURCE_UNRECORDED, SOURCE_MISSING, NARRATIVE_UNRECORDED, NARRATIVE_MISSING, FILE_NAME
                            a file and its manifest entry don't match
  PIN_UNKNOWN               a narrative is pinned to a source that isn't recorded or has no copy
  SOURCE_ATTRIBUTION        a saved source lacks its footer, or the footer's URL isn't its recorded URL
  SOURCE_POLICY             a saved copy the source policy doesn't allow (design doc §4.7)
  INDEX_OUTDATED, TAG_PAGE_OUTDATED, TAG_PAGE_ORPHAN
                            a generated page is out of date (--fix rewrites it)
  NARRATIVE_ANCHOR          a link to a section of another narrative that isn't there
                            (--fix repairs one whose section was only renumbered)
  WIKILINK, HIGHLIGHT, CALLOUT, DOLLAR_MATH, LINK_PATH, ...
                            on any page under sllmwiki/ but the sources, markdown a
                            renderer would show wrong: GitHub, Obsidian or a book
                            (lib/compat.py; their warnings are warnings here too)
Warnings:
  NARRATIVE_SOURCE_CHANGED  a narrative was built on an older version of a source: recheck it
  NARRATIVE_BASE_CHANGED    a narrative it builds on changed since, or is gone: recheck the wording it reuses
  SOURCE_UPSTREAM_CHANGED   check-upstream found the original changed: re-ingest it
  ABSTRACT_DRAFT            a source still has its starter abstract
  PAGE_HANDWRITTEN          a page where a generated one would go, left alone
  FIGURE_UNUSED             a figure in narratives/figures/ that no narrative shows

--visibility skips asking GitHub who can see the wiki. Exit code: 0 with no
errors, 1 with errors, 2 on a usage error.
"""

import argparse
import os
import sys

sys.dont_write_bytecode = True

from lib import compat, config, figures, footer, language, layout, manifest, policy, schema, tagtree, wikiindex, wikiyaml, xrefs  # noqa: E402
from lib.layout import Cli, entry  # noqa: E402
from lib.util import dumps, read_bytes, read_text, source_hash  # noqa: E402

cli = Cli('wiki-check.py', 'usage: wiki-check.py [--fix] [--json] [--visibility public|private]')


def check(root, fix=False, seen_by=None):
    """[(severity, code, file, message)] for the whole wiki; with fix, the generated pages are rewritten first."""
    out = []
    add = out.append
    for p in config.problems(root):
        add(('error', 'CONFIG_INVALID', layout.CONFIG, p))
    settings = config.get(root).settings
    for p in language.use(root):
        add(('error', 'LANGUAGE_PACK_INVALID', f'{layout.TEMPLATES}/{language.FOLDER}', p))
    if not language.pack(settings['language']):
        add(('warning', 'LANGUAGE_PACK', layout.CONFIG, f'no language pack for {settings["language"]}: narratives\' headings stay English; '
                                                       f'add {layout.TEMPLATES}/{language.FOLDER}/{settings["language"]}.md to translate them'))
    data = {}
    for kind in ('tags', 'sources', 'narratives'):
        rel = manifest.FILES[kind]
        try:
            data[kind] = manifest.load(root, kind)
        except wikiyaml.YamlError as e:
            add(('error', 'YAML_INVALID', rel, str(e)))
            data[kind] = {}
            continue
        for f in schema.validate(kind, data[kind], rel):
            add(('error', f['code'], rel, f['message']))
    if any(f[1] == 'YAML_INVALID' for f in out):
        return out  # the rest reads these files
    tree = tagtree.Tree(data['tags'], data['sources'], data['narratives'])
    for code, _, msg in tree.problems():
        add(('error', code, layout.TAGS, msg))

    sources, narratives = data['sources'], data['narratives']
    saved = {f for f in os.listdir(os.path.join(root, layout.SOURCES))} if os.path.isdir(os.path.join(root, layout.SOURCES)) else set()
    recorded_files = {os.path.basename(e['file']) for e in sources.values() if e.get('file')}
    for name in sorted(saved - recorded_files - {'manifest.yaml'}):
        if name.endswith('.md'):
            add(('error', 'SOURCE_UNRECORDED', f'{layout.SOURCES}/{name}', f'{name} isn\'t in the sources manifest; save sources with fetch-source.py'))
    seen_by = seen_by or (policy.visibility(root) if any(e.get('file') for e in sources.values()) else 'private')
    for slug, e in sources.items():
        if e.get('upstream_changed'):
            add(('warning', 'SOURCE_UPSTREAM_CHANGED', layout.SOURCES_MANIFEST, f'{slug}: the original changed on {e["upstream_changed"]}; re-ingest it (fetch-source.py --refresh)'))
        if e.get('abstract_draft'):
            add(('warning', 'ABSTRACT_DRAFT', layout.SOURCES_MANIFEST, f'{slug}: still the starter abstract; read it and run manifest.py set-abstract'))
        if not e.get('file'):
            continue
        rel = layout.in_content(e['file'])
        if os.path.basename(e['file']) != f'{slug}.md':
            add(('error', 'FILE_NAME', rel, f'{slug}: its file should be sources/{slug}.md'))
        if not os.path.isfile(os.path.join(root, rel)):
            add(('error', 'SOURCE_MISSING', rel, f'{slug}: no saved file {rel}'))
            continue
        foot = footer.read(read_bytes(os.path.join(root, rel)))
        if not foot or foot['url'] != e.get('url'):
            add(('error', 'SOURCE_ATTRIBUTION', rel, f'{slug}: its footer must give its URL, {e.get("url")} (fetch-source.py --refresh rewrites it)'))
        ok, why = policy.may_copy(settings['source_copies'], seen_by, e.get('license'), e.get('permission'))
        if not ok:
            add(('error', 'SOURCE_POLICY', rel, f'{slug}: {why}'))

    folder = os.path.join(root, layout.NARRATIVES)
    written = {f[:-3] for f in os.listdir(folder) if f.endswith('.md')} if os.path.isdir(folder) else set()
    for slug in sorted(written - set(narratives)):
        add(('error', 'NARRATIVE_UNRECORDED', f'{layout.NARRATIVES}/{slug}.md', f'{slug} isn\'t recorded; run finish-narrative.py {slug}'))
    for slug, e in narratives.items():
        if slug not in written:
            add(('error', 'NARRATIVE_MISSING', layout.NARRATIVES_MANIFEST, f'{slug}: no file {layout.NARRATIVES}/{slug}.md'))
        for src, pin in (e.get('read') or {}).items():
            s = sources.get(src)
            if not s or not s.get('file'):
                add(('error', 'PIN_UNKNOWN', layout.NARRATIVES_MANIFEST, f'{slug}: read {src}, which isn\'t a saved source'))
                continue
            path = os.path.join(root, layout.in_content(s['file']))
            if os.path.isfile(path) and source_hash(read_bytes(path)) != pin:
                add(('warning', 'NARRATIVE_SOURCE_CHANGED', f'{layout.NARRATIVES}/{slug}.md',
                     f'{slug} was built on an older version of {src}: lint it against the new one'))
        for base, pin in (e.get('built_on') or {}).items():
            path = os.path.join(root, layout.NARRATIVES, f'{base}.md')
            if not os.path.isfile(path) or manifest.narrative_hash(read_text(path)) != pin:
                add(('warning', 'NARRATIVE_BASE_CHANGED', f'{layout.NARRATIVES}/{slug}.md',
                     f'{slug} builds on {base}, which ' + ('changed since' if os.path.isfile(path) else 'is gone')
                     + ': recheck the wording it reuses, and lint it'))

    out += figures.unused(root)
    out += xrefs.check_all(root, fix)
    findings, changed = wikiindex.sync(root, fix)
    out += [(sev, code, rel, msg) for sev, code, rel, msg in findings if not (fix and rel in changed)]
    for rel in pages(root):  # after --fix, so a page it regenerates is checked as it now is
        text = read_text(os.path.join(root, rel))
        for sev, code, line, msg in compat.check(text) + compat.check_links(text, os.path.dirname(os.path.join(root, rel)), root):
            out.append((sev, code, f'{rel}:{line}', msg))
    return out


def pages(root):
    """Every markdown page under sllmwiki/ but the saved sources (verbatim) and hidden folders such as .obsidian."""
    out = []
    for folder, dirs, files in os.walk(os.path.join(root, layout.CONTENT)):
        rel_dir = os.path.relpath(folder, root).replace(os.sep, '/')
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and f'{rel_dir}/{d}' != layout.SOURCES)
        out += [f'{rel_dir}/{f}' for f in sorted(files) if f.endswith('.md')]
    return out


def main(argv):
    p = argparse.ArgumentParser(prog='wiki-check.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--fix', action='store_true')
    p.add_argument('--json', action='store_true')
    p.add_argument('--visibility', choices=['public', 'private'])
    p.add_argument('--root')
    args = p.parse_args(argv)
    root = cli.wiki(args.root)
    found = check(root, args.fix, args.visibility)
    errors = sum(1 for f in found if f[0] == 'error')
    if args.json:
        print(dumps({'errors': errors, 'warnings': len(found) - errors,
                     'findings': [dict(zip(('severity', 'code', 'file', 'message'), f)) for f in found]}))
    else:
        for sev, code, rel, msg in found:
            print(f'{sev:<8} {code:<26} {rel}: {msg}')
        print(f'wiki-check: {errors} error(s), {len(found) - errors} warning(s)')
    return 1 if errors else 0


if __name__ == '__main__':  # pragma: no cover
    entry(main)
