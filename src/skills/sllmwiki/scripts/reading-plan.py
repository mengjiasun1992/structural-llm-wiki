#!/usr/bin/env python3
"""reading-plan: what a narrative reads, and in what order (design doc §7.1).

  reading-plan.py list --primary a,b [--supporting c]
      The candidates for a question's tags: the narratives filed under them
      (background) and their sources, each with its kind, size, date and
      abstract, for you to grade.
  reading-plan.py order --primary a,b [--supporting c] --grades GRADES.json
      GRADES.json gives each source its relevance and authority, and each
      existing narrative its relevance (high when this narrative builds on it):
        {"<source>": {"relevance": "high|medium|low", "authority": "A|B|C"},
         "<narrative>": {"relevance": "high|medium|low"}, ...}
      (A: the code, specs and standards, original papers or creators, official
      docs; B: textbooks and references; C: practitioner write-ups and
      encyclopedias.)
      Prints the plan: existing narratives first, as background (ungraded) or
      medium relevance; then the medium-relevance sources; the high-relevance
      ones; and last the narratives this one builds on (high), so their wording
      is the freshest when it is reused. Within the sources, least to most
      authoritative, then oldest to newest by publication date (undated
      first). Low-relevance sources and narratives are read by abstract only;
      links aren't read. Paste the plan into the PR.
      The plan is also kept in GRADES.json.plan.json, so finish-narrative
      records the narratives read then, not ones written since.

Only the given tags' own narratives and sources are candidates: their parents'
and siblings' are noted, never read. Options: --json, --root <wiki>.
Exit code: 0, 1 when grades are missing or invalid, 2 on a usage error.
"""

import argparse
import json
import sys

sys.dont_write_bytecode = True

from lib import readingplan  # noqa: E402
from lib.layout import Cli, entry  # noqa: E402
from lib.util import dumps  # noqa: E402

cli = Cli('reading-plan.py', 'usage: reading-plan.py list|order --primary a,b [--supporting c] [--grades FILE]')
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
    try:
        found = readingplan.candidates(root, args.primary, args.supporting)
    except ValueError as e:
        cli.fail(str(e))

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
        grades = readingplan.load_grades(args.grades)
    except ValueError as e:
        cli.fail(str(e))
    rows, problems = readingplan.order(found, grades)
    if problems:
        cli.fail('grade every saved source first: ' + '; '.join(problems))
    with open(readingplan.plan_path(args.grades), 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=2)
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
