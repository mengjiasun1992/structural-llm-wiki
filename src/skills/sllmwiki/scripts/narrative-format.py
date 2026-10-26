#!/usr/bin/env python3
"""narrative-format: check narratives against their template, and the rules every
narrative shares (design doc §4.5, §4.8, §4.10).

  narrative-format.py [<narrative.md> ...] [--fix-numbering] [--fix-style] [--json]
      Checks the given narratives, or every one in sllmwiki/narratives/:
        the # title; the template named in Metadata; the template's sections, in
        order, and its diagrams, in the narrative's language; heading numbers; the Abstract's word range and
        the body's budget; citations (numbered in order, listed, pointing at an
        existing section of a saved source); the markers; leftover <placeholders>;
        and markdown every renderer reads alike, links included.
      --fix-numbering renumbers the headings and figure captions; --fix-style moves references inside
      their sentence and writes the renderer escapes. finish-narrative.py does both, and more.
  narrative-format.py <narrative.md> ... --stats [--json]
      The numbers lint grades a narrative's aim with: the body against its budget,
      the words, subsections, citations and markers in each section, citations
      by the authority of the sources they cite (the reading plan's grades), and
      pictures.
  narrative-format.py --templates     the templates this wiki offers, with use_when, budgets and the aim lint
                                      grades on; a problem with one of the wiki's own (exit 1), and a heading
                                      its language pack doesn't translate (a warning)
  narrative-format.py --new-template NAME --from BASE
                     starts the wiki's own template NAME in sllmwiki/.templates/NAME/, a copy of
                     BASE's template.md and guide.md to edit; named like a bundled
                     template, it replaces it
  narrative-format.py --skeleton NAME the skeleton a new narrative starts from, in the wiki's language
                     [--language TAG]  or in another one (a BCP 47 tag, such as zh-Hans)

Options: --root <wiki>. Exit code: 0 with no errors (warnings are printed),
1 with errors, 2 on a usage error.
"""

import argparse
import glob
import os
import sys

sys.dont_write_bytecode = True

from lib import citations, compat, config, figures, language, layout, numbering, templates  # noqa: E402
from lib.narrativecheck import check, stats  # noqa: E402
from lib.layout import Cli, entry  # noqa: E402
from lib.util import dumps, read_text, write_text  # noqa: E402

cli = Cli('narrative-format.py', 'usage: narrative-format.py [<narrative.md> ...] [--fix-numbering] [--fix-style] | --templates | --skeleton NAME [--language TAG]')
def main(argv):
    p = argparse.ArgumentParser(prog='narrative-format.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('files', nargs='*')
    p.add_argument('--fix-numbering', action='store_true')
    p.add_argument('--fix-style', action='store_true')
    p.add_argument('--templates', action='store_true')
    p.add_argument('--new-template', metavar='NAME')
    p.add_argument('--from', dest='base', metavar='BASE')
    p.add_argument('--skeleton', metavar='NAME')
    p.add_argument('--language', metavar='TAG')
    p.add_argument('--stats', action='store_true')
    p.add_argument('--json', action='store_true')
    p.add_argument('--root')
    args = p.parse_args(argv)
    root = cli.wiki(args.root)
    offered, problems = templates.available(root)

    if args.new_template:
        if not args.base:
            cli.usage('--new-template needs --from BASE, the template to start from (--templates lists them)')
        try:
            folder = templates.create(root, args.new_template, args.base)
        except templates.TemplateError as e:
            cli.fail(str(e))
        rel = os.path.relpath(folder, root).replace(os.sep, '/')
        print(f'started {rel}/ from {args.base}: edit template.md (its header and body sections) and guide.md, '
              f'then check it with narrative-format.py --templates and --skeleton {args.new_template}')
        return 0
    if args.templates:
        rows = [{'name': t.name, 'source': t.source, 'description': t.description, 'use_when': t.use_when,
                 'max_words': t.max_words, 'abstract_words': t.abstract_words, 'aim': t.aim} for t in offered.values()]
        tag = config.get(root).settings['language']
        pack = language.pack(tag)
        warnings = [f'template {t.name}: {tag} keeps "{title}" in English: translate it in {layout.TEMPLATES}/{language.FOLDER}/{tag}.md'
                    for t in offered.values() if t.source == 'wiki' and pack and pack.tag != language.DEFAULT
                    for title in templates.untranslated(t, pack)]
        if args.json:
            print(dumps({'templates': rows, 'problems': problems, 'warnings': warnings}))
        else:
            for r in rows:
                print(f'{r["name"]} ({r["source"]}, body up to {r["max_words"]} words; aim: {", ".join(r["aim"])}): {r["description"]}. '
                      f'Use for {r["use_when"]}')
            for prob in problems:
                print(f'problem: {prob}')
            for w in warnings:
                print(f'warning: {w}')
        return 1 if problems else 0
    if args.skeleton:
        if args.skeleton not in offered:
            cli.fail(f'no template {args.skeleton}; there are {", ".join(sorted(offered))}')
        tag = args.language or config.get(root).settings['language']
        p = language.pack(tag)
        if not p:
            print(f'narrative-format: no language pack for {tag}, so the headings are English; '
                  f'add {layout.TEMPLATES}/{language.FOLDER}/{tag}.md to translate them', file=sys.stderr)
        elif p.source == 'wiki' and p.tag not in language.bundled():
            print(f'narrative-format: {p.name} is this wiki\'s own pack; the skill hasn\'t evaluated writing in it', file=sys.stderr)
        if p and p.writing:
            print(f'narrative-format: write in {p.name}: follow the Writing section of {p.path}', file=sys.stderr)
        print(offered[args.skeleton].skeleton(tag), end='')
        return 0

    settings = config.get(root).settings
    files = args.files or sorted(glob.glob(os.path.join(root, layout.NARRATIVES, '*.md')))
    if args.stats:
        return print_stats(root, files, offered, args.json)
    results, errors = [], 0
    for f in files:
        path = f if os.path.isabs(f) else os.path.join(os.getcwd(), f)
        if not os.path.isfile(path):
            cli.fail(f'no such file: {f}')
        rel = os.path.relpath(os.path.realpath(path), os.path.realpath(root)).replace(os.sep, '/')  # real paths: /var is /private/var on macOS
        text = read_text(path)
        fixed = text
        if args.fix_numbering:
            fixed = figures.renumber(numbering.renumber(fixed)[0])[0]
        if args.fix_style:
            fixed = compat.escape(citations.place(fixed)[0])[0]
        if fixed != text:
            write_text(path, fixed)
            print(f'fixed {rel}')
        for sev, code, line, msg in check(root, rel, fixed, settings, offered):
            results.append({'file': rel, 'line': line, 'severity': sev, 'code': code, 'message': msg})
            errors += sev == 'error'
    for prob in problems:
        results.append({'file': layout.TEMPLATES, 'line': 1, 'severity': 'error', 'code': 'TEMPLATE_INVALID', 'message': prob})
        errors += 1
    if args.json:
        print(dumps({'errors': errors, 'warnings': len(results) - errors, 'findings': results}))
    else:
        for r in results:
            print(f'{r["severity"]:<8} {r["code"]:<20} {r["file"]}:{r["line"]}: {r["message"]}')
        print(f'narrative-format: {errors} error(s), {len(results) - errors} warning(s) in {len(files)} narrative(s)')
    return 1 if errors else 0


def print_stats(root, files, offered, as_json):
    rows = []
    for f in files:
        path = f if os.path.isabs(f) else os.path.join(os.getcwd(), f)
        if not os.path.isfile(path):
            cli.fail(f'no such file: {f}')
        rel = os.path.relpath(os.path.realpath(path), os.path.realpath(root)).replace(os.sep, '/')
        rows.append(stats(root, rel, read_text(path), offered))
    if as_json:
        print(dumps({'narratives': rows}))
        return 0
    for r in rows:
        c, m = r['citations'], r['markers']
        print(f'{r["file"]} ({r["template"]}): body {r["body_words"]} of {r["budget"]} words, Abstract {r["abstract_words"]}; '
              f'citations A {c["A"]}, B {c["B"]}, C {c["C"]}, ungraded {c["ungraded"]}; '
              f'markers {m["statements"]} on statements, {m["headings"]} on headings; {r["pictures"]} picture(s)')
        for s in r['sections']:
            print(f'  {s["section"]}: {s["words"]} words, {s["citations"]} citations, {s["markers"]} markers'
                  + (f', {s["subsections"]} subsections' if s['subsections'] else ''))
    return 0


if __name__ == '__main__':  # pragma: no cover
    entry(main)
