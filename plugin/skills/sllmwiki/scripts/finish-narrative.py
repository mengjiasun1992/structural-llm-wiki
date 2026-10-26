#!/usr/bin/env python3
"""finish-narrative: everything mechanical after a narrative is written or edited,
in one command (design doc §7.5).

  finish-narrative.py <slug> [--primary a,b] [--supporting c] [--read s1,s2]
                      [--grades GRADES.json] [--model NAME]
                      [--bump minor|major --note TEXT] [--json] [--root <wiki>]

In order: numbers the headings and figure captions; repairs links to a renumbered
section of another narrative; moves references and markers inside their
sentence, before its closing punctuation; writes the renderer escapes; converts old markers
and adds a Terminology row for each marker the narrative uses (when markers are on); sets the
Metadata's dates and, for a new narrative, version 1.0 and its first history
entry, or with --bump, the next version and --note as its history entry;
records the narrative with its template, tags, the current pins of the sources
it read, the reading plan's grades (--grades, the file given to reading-plan.py
order, which must have run on it since it last changed)
and the model that wrote a new version (this session's, or --model); writes the
model and the reading plan into the Metadata; regenerates the index and tag
pages; then checks it with narrative-format and prints what's left.

A new narrative needs --primary (its core tags) and --read (the saved sources it
read in full); later runs reuse what was recorded unless given again.

Exit code: 0 finished with no errors, 1 when errors remain or it was refused,
2 on a usage error.
"""

import argparse
import os
import sys

sys.dont_write_bytecode = True

from lib import citations, compat, config, figures, language, layout, manifest, markers, metadata, numbering, readingplan, runstats, templates, wikiindex, xrefs  # noqa: E402
from lib.narrativecheck import check as check_narrative  # noqa: E402
from lib.layout import Cli, entry  # noqa: E402
from lib.util import dumps, read_text, today, write_text  # noqa: E402

cli = Cli('finish-narrative.py', 'usage: finish-narrative.py <slug> [--primary a,b] [--supporting c] [--read s1,s2] [--grades FILE] [--model NAME] '
          '[--bump minor|major --note TEXT]')


def tag_list(value):
    return [t.strip() for t in value.split(',') if t.strip()]


def main(argv):
    p = argparse.ArgumentParser(prog='finish-narrative.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('slug')
    p.add_argument('--primary', type=tag_list)
    p.add_argument('--supporting', type=tag_list)
    p.add_argument('--read', type=tag_list)
    p.add_argument('--grades')
    p.add_argument('--model')
    p.add_argument('--bump', choices=['minor', 'major'])
    p.add_argument('--note')
    p.add_argument('--json', action='store_true')
    p.add_argument('--root')
    args = p.parse_args(argv)
    if args.bump and not args.note:
        cli.usage('--bump needs --note, the history entry')
    root = cli.wiki(args.root)
    try:
        settings = config.load(root).settings
    except config.ConfigError as e:
        cli.fail('Config.toml is invalid, fix it first: ' + '; '.join(e.problems))
    rel = f'{layout.NARRATIVES}/{args.slug}.md'
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        cli.fail(f'no narrative {rel}')
    recorded = manifest.load(root, 'narratives').get(args.slug)
    primary = args.primary if args.primary is not None else (recorded or {}).get('tags', {}).get('primary')
    supporting = args.supporting if args.supporting is not None else (recorded or {}).get('tags', {}).get('supporting', [])
    read = args.read if args.read is not None else list((recorded or {}).get('read', {}))
    if not primary:
        cli.fail(f'{args.slug} is new: pass --primary (its core tags) and --read (the saved sources it read)')

    plan, grades, built_on = None, None, None
    if args.grades:
        try:
            found = readingplan.candidates(root, primary, supporting)
            given = readingplan.load_grades(args.grades)
        except ValueError as e:
            cli.fail(str(e))
        read_then = readingplan.narratives_read(args.grades)  # the narratives the plan had read, not ones written since
        found['narratives'] = [n for n in found['narratives'] if n['slug'] != args.slug and (read_then is None or n['slug'] in read_then)]
        rows, problems = readingplan.order(found, given)
        if problems:
            cli.fail('grade every saved source first: ' + '; '.join(problems))
        saved = readingplan.plan_path(args.grades)
        if not os.path.isfile(saved):
            cli.fail(f'no reading plan for {args.grades}: run reading-plan.py order --grades {args.grades} first; its plan '
                     'is the order the narrative is read in, and its table goes in the summary')
        if os.path.getmtime(args.grades) > os.path.getmtime(saved):
            cli.fail(f'{args.grades} changed after its reading plan: run reading-plan.py order --grades {args.grades} again')
        plan = readingplan.metadata_lines(rows)
        grades = {s['slug']: {k: given[s['slug']][k] for k in ('relevance', 'authority')} for s in found['sources'] if s['kind'] != 'link'}
        built_on = [n['slug'] for n in found['narratives'] if (given.get(n['slug']) or {}).get('relevance') == 'high']

    text = read_text(path)
    done = []
    text, n = numbering.renumber(text)
    done += [f'numbered {n} heading(s)'] if n else []
    text, n = figures.renumber(text)
    done += [f'numbered {n} figure caption(s)'] if n else []
    text, n = xrefs.repair(root, rel, text)
    done += [f'repaired {n} link(s) to a renumbered section of another narrative'] if n else []
    if settings['markers']:
        text, n = markers.migrate(text)
        done += [f'converted {n} old marker(s)'] if n else []
    text, n = citations.place(text)  # after the old markers become new ones, so they move inside too
    done += [f'moved {n} reference(s) inside their sentence'] if n else []
    text, n = compat.escape(text)
    done += [f'wrote {n} renderer escape(s)'] if n else []
    if settings['markers']:
        text, n = markers.add_rows(text, language.for_narrative(text, settings['language'])[1])
        done += [f'defined {n} marker(s) in Terminology'] if n else []
    meta = metadata.read(text)
    name = meta['template']
    try:
        templates.get(root, name or '')
    except templates.TemplateError as e:
        cli.fail(f'Metadata names no template this wiki offers: {e}')
    fields = {'last_modified': today(), 'created': meta['created'] or today(), 'language': meta['language'] or settings['language']}
    history = None
    if not meta['version']:
        fields['version'], history = '1.0', ('1.0', today(), 'First version.')
    elif args.bump:
        fields['version'] = metadata.bump(meta['version'], args.bump)
        history = (fields['version'], today(), args.note)
    if not meta['history'] and not history:
        history = (meta['version'], meta['created'] or today(), 'First version.')
    model = args.model or (runstats.model(runstats.transcript()) if history else None)
    version = fields.get('version') or meta['version']
    if model:
        fields['model'] = model
    fields['words'] = metadata.reading_label(text)  # Metadata isn't counted, so writing it doesn't change it
    text = metadata.write(text, fields, history, plan)  # the template was read from the Metadata section, so there is one
    write_text(path, text)
    try:
        manifest.put_narrative(root, args.slug, name, primary, supporting, read, grades, (version, model) if model else None, built_on)
    except manifest.ManifestError as e:
        cli.fail(f'recording {args.slug}: {e}')
    done.append(f'recorded {args.slug} (version {metadata.read(text)["version"]}, pins: {", ".join(read) or "none"})')
    changed = wikiindex.sync(root, write=True)[1]
    done += [f'regenerated {len(changed)} page(s): {", ".join(changed)}'] if changed else []

    check = check_narrative(root, rel, text, settings, templates.available(root)[0])
    errors = [f for f in check if f[0] == 'error']
    if args.json:
        print(dumps({'slug': args.slug, 'done': done, 'findings': [dict(zip(('severity', 'code', 'line', 'message'), f)) for f in check]}))
    else:
        for line in done:
            print(line)
        for sev, code, line, msg in check:
            print(f'{sev:<8} {code:<20} {rel}:{line}: {msg}')
        print(f'finish-narrative: {len(errors)} error(s) left' if errors else 'finish-narrative: done, no errors')
    return 1 if errors else 0


if __name__ == '__main__':  # pragma: no cover
    entry(main)
