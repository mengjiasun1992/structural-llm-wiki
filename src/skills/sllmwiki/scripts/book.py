#!/usr/bin/env python3
"""book: the wiki as a book (docs/book_design.md).

  book.py stage OUT [--name N] [--version V] [--date YYYY-MM-DD] [--commit C] [--source URL]
      Writes the book as plain Markdown for Sphinx into the folder OUT, which
      must be empty or not exist yet: index.md (the cover, the front page and
      the contents), parts/<tag>.md, chapters/<slug>.md with their figures,
      and the appendices (sources, glossary, open questions). Also writes
      OUT/book.json: the parts, the chapter order, every anchor, every diagram
      and formula to render, and the problems found. The wiki is only read.
      --name defaults to the wiki's folder name, --version to "preview",
      --date to today, --commit to the current commit and --source (the
      wiki's web page, which the cover links to) to its origin remote's.
      Problems: BOOK_LINK (a link or anchor the book can't resolve),
      BOOK_CYCLE (narratives built on each other in a cycle), BOOK_FIGURE (a
      figure that isn't there). Exit code 1 when there are any.
  book.py render STAGED --vendor DIR [--chrome PATH] [--cache DIR]
      Draws every diagram and formula book.json lists as SVG, in headless
      Chrome with the mermaid.js and MathJax in DIR (mermaid.min.js,
      tex-svg-full.js), and puts the SVG in the staged pages in their place.
      --chrome defaults to $CHROME, else the Chrome on PATH; --cache keeps
      each SVG by its source and the libraries, so a rerun draws only what
      changed. One that fails to draw stays as written and is a warning,
      BOOK_RENDER, kept in book.json's warnings.
  book.py build OUT --vendor DIR [--formats pdf,html] [--chrome PATH] [--cache DIR]
                [--sphinx CMD] [--name N] [--version V] [--date D] [--commit C] [--source URL]
      stage into OUT/staged, render, then Sphinx (--sphinx, default
      sphinx-build, with MyST-Parser) with the skill's templates/book/
      settings, and writes OUT/<name>-<version>.html: one file with every
      stylesheet, image and diagram in it; for pdf, Chrome prints that file
      to OUT/<name>-<version>.pdf (A4, page numbers, the title as the running
      head). --formats (pdf, html) defaults to the ones
      Config.toml's [structural-llm-wiki-release] turns on; with none, the
      book is staged and no file is written. Problems and warnings are listed
      (Sphinx's are BOOK_SPHINX) and don't stop the book; exit code 1 when a
      format fails.
  book.py issues STAGED
      The release notes' "Known issues" section for a built book: its
      problems, warnings and failed formats from book.json, in the wiki's
      language; nothing when there are none.

Options: --json, --root <wiki>.
Exit code: as above; 2 on a usage error.
"""

import argparse
import datetime
import json
import os
import shlex
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True

from lib import book, bookbuild, config, language, layout  # noqa: E402
from lib.layout import Cli, entry  # noqa: E402
from lib.util import dumps, write_text  # noqa: E402

cli = Cli('book.py', 'usage: book.py stage|render|build ... (book.py --help)')
FORMATS = ('pdf', 'html')  # what build makes, as Config.toml's <format>_book names it
TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates', 'book')


def _git(root, *args):
    """git's output in root, or '' when it fails."""
    try:
        r = subprocess.run(['git', '-C', root, *args], capture_output=True, text=True, check=False)
    except OSError:  # pragma: no cover (no git)
        return ''
    return r.stdout.strip() if r.returncode == 0 else ''


def _empty(cli_out):
    out = os.path.abspath(cli_out)
    if os.path.exists(out) and (not os.path.isdir(out) or os.listdir(out)):
        cli.usage(f'{cli_out} must be an empty folder, or not exist yet')
    return out


def stage(root, out, args):
    """Write the staged book into out; its book.json."""
    staged = book.stage(root, args.name or os.path.basename(root), args.version, args.date,
                        _git(root, 'rev-parse', '--short', 'HEAD') if args.commit is None else args.commit,
                        book.web_url(_git(root, 'remote', 'get-url', 'origin')) if args.source is None else args.source or None)
    for rel, text in staged.files.items():
        write_text(os.path.join(out, rel), text)
    for fig in staged.figures:
        dest = os.path.join(out, 'chapters', fig)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(os.path.join(root, layout.NARRATIVES, fig), dest)
    _save(out, staged.manifest)
    return staged.manifest


def _save(staged, data):
    write_text(os.path.join(staged, 'book.json'), json.dumps(data, indent=1, ensure_ascii=False) + '\n')


def render(staged, vendor, chrome, cache):
    """Draw book.json's diagrams and formulas and put them in the staged pages; book.json, with its warnings."""
    with open(os.path.join(staged, 'book.json'), encoding='utf-8') as f:
        data = json.load(f)
    items = {r['id']: r for r in data['renders']}
    libs = bookbuild.libraries(vendor)
    svgs = {}
    for rid in items:
        path = os.path.join(cache, f'{rid}-{libs}.svg') if cache else None
        if path and os.path.isfile(path):
            with open(path, encoding='utf-8') as f:
                svgs[rid] = f.read()
    todo = [{'id': r['id'], 'kind': r['kind'], 'source': r['source']} for rid, r in items.items() if rid not in svgs]
    if todo:
        found = bookbuild.find_chrome(chrome)
        if not found:
            cli.fail('no Chrome found: pass --chrome or set $CHROME')
        try:
            drawn = bookbuild.draw(todo, vendor, found, staged)
        except ValueError as e:
            cli.fail(str(e))
        for rid, svg in drawn.items():
            if isinstance(svg, str):
                svgs[rid] = bookbuild.clean(svg, items[rid]['source'])
                if cache:
                    write_text(os.path.join(cache, f'{rid}-{libs}.svg'), svgs[rid])
            else:
                svgs[rid] = svg
    warnings = [w for w in data.get('warnings', []) if w['code'] != 'BOOK_RENDER']
    for rid, svg in svgs.items():
        if not isinstance(svg, str):
            r = items[rid]
            warnings.append({'code': 'BOOK_RENDER', 'where': r['files'][0],
                             'message': f'a {r["kind"]} that doesn\'t draw stays as written: {svg["error"]}: {r["source"][:80]}'})
    counts = {}
    for folder, _, files in sorted(os.walk(staged)):
        for name in sorted(files):
            if name.endswith('.md'):
                path = os.path.join(folder, name)
                with open(path, encoding='utf-8') as f:
                    text = f.read()
                write_text(path, bookbuild.put_in(text, svgs, book.render_id, counts))
    data['warnings'] = warnings
    _save(staged, data)
    return data


def html_book(root, out, staged, data, sphinx):
    """Sphinx's single-file HTML of the rendered staged book: (path, Sphinx's warnings), or (None, why it failed)."""
    lang = bookbuild.sphinx_language(config.get(root).settings['language'])
    build = os.path.join(out, '_build')
    cmd = [*shlex.split(sphinx), '-q', '-b', 'singlehtml', '-c', TEMPLATE, '-d', os.path.join(build, 'doctrees'),
           '-D', f'project={data["name"]}', '-D', f'version={data["version"]}', '-D', f'release={data["version"]}',
           '-D', f'copyright={data["name"]}', '-D', f'language={lang}', staged, os.path.join(build, 'singlehtml')]
    try:
        run = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as e:
        return None, f'{sphinx} didn\'t run: {e}'
    if run.returncode != 0 or not os.path.isfile(os.path.join(build, 'singlehtml', 'index.html')):
        return None, f'Sphinx failed: {(run.stderr or run.stdout).strip()[-2000:]}'
    path = os.path.join(out, f'{data["name"]}-{data["version"]}.html')
    write_text(path, bookbuild.self_contained(os.path.join(build, 'singlehtml')))
    return path, [line for line in run.stderr.splitlines() if 'WARNING' in line or 'ERROR' in line]


def main(argv):
    p = argparse.ArgumentParser(prog='book.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('command', choices=['stage', 'render', 'build', 'issues'])
    p.add_argument('out')
    p.add_argument('--name')
    p.add_argument('--version', default='preview')
    p.add_argument('--date', default=datetime.date.today().isoformat())
    p.add_argument('--commit')
    p.add_argument('--source')
    p.add_argument('--formats', type=lambda v: [f.strip() for f in v.split(',') if f.strip()])
    p.add_argument('--vendor')
    p.add_argument('--chrome')
    p.add_argument('--cache')
    p.add_argument('--sphinx', default='sphinx-build')
    p.add_argument('--json', action='store_true')
    p.add_argument('--root')
    args = p.parse_args(argv)
    if args.command in ('render', 'build'):
        if not args.vendor or not all(os.path.isfile(os.path.join(args.vendor, n)) for n in (bookbuild.MERMAID, bookbuild.MATHJAX)):
            cli.usage(f'{args.command} needs --vendor DIR holding {bookbuild.MERMAID} and {bookbuild.MATHJAX}')
        unknown = [f for f in args.formats or [] if f not in FORMATS]
        if unknown or args.formats == []:
            cli.usage(f'--formats can be {", ".join(FORMATS)}, not {", ".join(unknown) or "nothing"}')
    if args.command == 'issues':
        path = os.path.join(args.out, 'book.json')
        if not os.path.isfile(path):
            cli.usage(f'{args.out} isn\'t a staged book (no book.json)')
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        root = cli.wiki(args.root) if args.root else None
        text = book.issues(data, language.pack(config.get(root).settings['language']) if root else None)
        if text:
            print(text, end='')
        return 0
    if args.command == 'render':
        staged = os.path.abspath(args.out)
        if not os.path.isfile(os.path.join(staged, 'book.json')):
            cli.usage(f'{args.out} isn\'t a staged book (no book.json): run book.py stage first')
        data = render(staged, args.vendor, args.chrome, args.cache)
        return _report(args, data, staged)
    root = cli.wiki(args.root)
    out = _empty(args.out)
    if args.command == 'stage':
        data = stage(root, out, args)
        _report(args, data, out)
        return 1 if data['problems'] else 0
    staged = os.path.join(out, 'staged')
    formats = args.formats if args.formats is not None else config.get(root).book_formats()
    data = stage(root, staged, args)
    data['files'], data['failed'] = {}, {}
    if formats:
        data = render(staged, args.vendor, args.chrome, args.cache)
        data['files'], data['failed'] = {}, {}
        path, extra = html_book(root, out, staged, data, args.sphinx)  # the PDF is printed from it
        if path:
            data['warnings'] += [{'code': 'BOOK_SPHINX', 'where': 'sphinx', 'message': w} for w in extra]
            if 'html' in formats:
                data['files']['html'] = path
        for fmt in formats:
            if not path:
                data['failed'][fmt] = extra
            elif fmt == 'pdf':
                pdf = os.path.splitext(path)[0] + '.pdf'
                chrome = bookbuild.find_chrome(args.chrome)
                why = bookbuild.print_pdf(path, pdf, chrome, f'{{{data["name"]} 📖}}') if chrome else 'no Chrome found to print it'
                if why:
                    data['failed']['pdf'] = why
                else:
                    data['files']['pdf'] = pdf
    _save(staged, data)
    _report(args, data, out)
    return 1 if data['failed'] else 0


def _report(args, data, out):
    problems, warnings = data['problems'], data.get('warnings', [])
    if args.json:
        print(dumps({'out': out, 'chapters': len(data['order']), 'renders': len(data['renders']), 'problems': problems,
                     'warnings': warnings, 'files': data.get('files', {}), 'failed': data.get('failed', {})}))
        return 0
    for f in problems + warnings:
        print(f'{f["code"]} {f["where"]}: {f["message"]}')
    for fmt, why in data.get('failed', {}).items():
        print(f'{fmt} failed: {why}')
    for fmt, path in data.get('files', {}).items():
        print(f'{fmt}: {path} ({os.path.getsize(path):,} bytes)')
    print(f'{len(data["order"])} chapters, {len(data["renders"])} diagrams and formulas, '
          f'{len(problems)} problem{"s" if len(problems) != 1 else ""}, '
          f'{len(warnings)} warning{"s" if len(warnings) != 1 else ""}: {out}')
    return 0


if __name__ == '__main__':  # pragma: no cover
    entry(main)
