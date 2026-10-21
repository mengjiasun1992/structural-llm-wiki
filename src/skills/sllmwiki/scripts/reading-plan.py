#!/usr/bin/env python3
"""reading-plan: what a narrative reads, and in what order (design doc §7.1).

  reading-plan.py list --primary a,b [--supporting c]
      The candidates for a question's tags: the narratives filed under them
      (background) and their sources, each with its kind, size, date and
      abstract, for you to grade.
  reading-plan.py order --primary a,b [--supporting c] --grades GRADES.json
      GRADES.json gives each source its relevance and authority:
        {"<slug>": {"relevance": "high|medium|low", "authority": "A|B|C"}, ...}
      (A: the code, specs and standards, original papers or creators, official
      docs; B: textbooks and references; C: practitioner write-ups.)
      Prints the plan: existing narratives first, as background; then the
      medium-relevance sources; the high-relevance ones last. Within each, least
      to most authoritative, then oldest to newest, so the most relevant,
      authoritative and newest material is read last. Low-relevance sources are
      read by abstract only; links aren't read. Paste the plan into the PR.

Only the given tags' own narratives and sources are candidates: their parents'
and siblings' are noted, never read. Options: --json, --root <wiki>.
Exit code: 0, 1 when grades are missing or invalid, 2 on a usage error.
"""

import argparse
import json
import os
import sys

sys.dont_write_bytecode = True

from lib import layout, metadata, tagtree  # noqa: E402
from lib.layout import Cli, entry  # noqa: E402
from lib.util import dumps, read_text  # noqa: E402

cli = Cli('reading-plan.py', 'usage: reading-plan.py list|order --primary a,b [--supporting c] [--grades FILE]')
RELEVANCE = ('high', 'medium', 'low')
AUTHORITY = ('A', 'B', 'C')


def candidates(root, primary, supporting):
    tree = tagtree.load(root)
    unknown = [t for t in primary + supporting if t not in tree.tags]
    if unknown:
        cli.fail(f'no such tag(s): {", ".join(unknown)}')
    tags = primary + supporting
    narratives = []
    for slug in dict.fromkeys(n for t in tags for role in ('primary', 'supporting') for n in tree.narratives_of(t)[role]):
        path = os.path.join(root, layout.NARRATIVES, f'{slug}.md')
        if os.path.isfile(path):
            text = read_text(path)
            narratives.append({'slug': slug, 'question': metadata.title(text), 'created': metadata.read(text)['created'] or '',
                               'path': f'{layout.NARRATIVES}/{slug}.md'})
    sources = []
    for slug in dict.fromkeys(s for t in tags for s in tree.sources_of(t)):
        e = tree.sources[slug]
        path = os.path.join(root, layout.in_content(e['file'])) if e.get('file') else None
        sources.append({'slug': slug, 'kind': e.get('kind'), 'bytes': os.path.getsize(path) if path and os.path.isfile(path) else None,
                        'date': e.get('published') or e.get('ingested') or '', 'abstract': e.get('abstract'),
                        'abstract_draft': bool(e.get('abstract_draft')), 'tags': e.get('tags')})
    noted = sorted({a for t in tags for a in tree.ancestors(t) + tree.adjacent(t)} - set(tags))
    return {'narratives': narratives, 'sources': sources, 'noted_not_read': noted}


def order(found, grades):
    """(plan rows, problems): each row {step, read, slug, why}."""
    problems = []
    graded = {}
    for s in found['sources']:
        g = grades.get(s['slug'])
        if s['kind'] == 'link':
            continue
        if not isinstance(g, dict) or g.get('relevance') not in RELEVANCE or g.get('authority') not in AUTHORITY:
            problems.append(f'{s["slug"]}: needs {{"relevance": "high|medium|low", "authority": "A|B|C"}}')
        else:
            graded[s['slug']] = (g, s)
    rows = [{'read': 'in full', 'slug': n['slug'], 'why': 'existing narrative, background'}
            for n in sorted(found['narratives'], key=lambda n: n['created'])]
    for level in ('medium', 'high'):
        chosen = [(g, s) for g, s in graded.values() if g['relevance'] == level]
        for g, s in sorted(chosen, key=lambda gs: (-AUTHORITY.index(gs[0]['authority']), gs[1]['date'])):
            rows.append({'read': 'in full', 'slug': s['slug'], 'why': f'{level} relevance, authority {g["authority"]}, {s["date"] or "undated"}'})
    rows += [{'read': 'abstract only', 'slug': s['slug'], 'why': 'low relevance'} for g, s in graded.values() if g['relevance'] == 'low']
    rows += [{'read': 'not read', 'slug': s['slug'], 'why': 'a link, no saved copy'} for s in found['sources'] if s['kind'] == 'link']
    for i, r in enumerate(rows, 1):
        r['step'] = i
    return rows, problems


def main(argv):
    p = argparse.ArgumentParser(prog='reading-plan.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('command', choices=['list', 'order'])
    p.add_argument('--primary', required=True, type=lambda v: [t.strip() for t in v.split(',') if t.strip()])
    p.add_argument('--supporting', default=[], type=lambda v: [t.strip() for t in v.split(',') if t.strip()])
    p.add_argument('--grades')
    p.add_argument('--json', action='store_true')
    p.add_argument('--root')
    args = p.parse_args(argv)
    root = cli.wiki(args.root)
    found = candidates(root, args.primary, args.supporting)

    if args.command == 'list':
        if args.json:
            print(dumps(found))
            return 0
        for n in found['narratives']:
            print(f'narrative {n["slug"]}: {n["question"]} ({n["path"]})')
        for s in found['sources']:
            size = f'{s["bytes"]:,} bytes' if s['bytes'] is not None else 'no saved copy'
            print(f'source {s["slug"]} [{s["kind"]}, {size}, {s["date"] or "undated"}]{" (draft abstract)" if s["abstract_draft"] else ""}: {s["abstract"]}')
        print(f'noted, not read: {", ".join(found["noted_not_read"]) or "none"}')
        return 0

    if not args.grades:
        cli.usage('order needs --grades GRADES.json')
    try:
        with open(args.grades, encoding='utf-8') as f:
            grades = json.load(f)
    except (OSError, ValueError) as e:
        cli.fail(f'can\'t read the grades: {e}')
    rows, problems = order(found, grades if isinstance(grades, dict) else {})
    if problems:
        cli.fail('grade every saved source first: ' + '; '.join(problems))
    if args.json:
        print(dumps({'plan': rows, 'noted_not_read': found['noted_not_read']}))
        return 0
    print('| Step | Read | Source | Why |\n|---|---|---|---|')
    for r in rows:
        print(f'| {r["step"]} | {r["read"]} | {r["slug"]} | {r["why"]} |')
    print(f'\nNoted, not read: {", ".join(found["noted_not_read"]) or "none"}.')
    return 0


if __name__ == '__main__':  # pragma: no cover
    entry(main)
