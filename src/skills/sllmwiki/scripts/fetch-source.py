#!/usr/bin/env python3
"""fetch-source: save a source in the wiki, verbatim, and record it (design doc §4.3, §4.7).

  fetch-source.py <slug> --url URL --tags a,b --license ID [--license-url URL]
                  [--published YYYY-MM-DD] [--file PATH] [--refresh]
                  [--allow-restricted "<who, when>"] [--json] [--root <wiki>]

Fetches URL (or reads PATH, a copy you already have of the source at URL) and
saves it as sllmwiki/sources/<slug>.md: markdown and text byte for byte, an
HTML page's main content converted, a PDF's text layer with its outline as
headings, a LaTeX source's sections as headings and its math kept as TeX (its
\\input files read from beside --file), a plain-text standard (an RFC) with its
numbered sections as headings, a code file in one fenced block so citations
can name its lines (#L10-L20), with the "Original source" footer. The source is recorded with a
starter abstract (its opening words, marked abstract_draft); read the source
and replace it with `manifest.py set-abstract <slug> --abstract "..."`.

A PDF over 100 pages with an outline is saved as one source per top-level
outline entry, <slug>-<n>-<chapter>, each with a starter abstract to replace
when a question first reads it. Such slices can't be refreshed yet; save the
PDF again under a new slug.

--license is what you found in the source's license or terms (an SPDX id such
as CC-BY-4.0, or "unknown", or "proprietary"). The source policy decides
whether a copy may be kept: never with source_copies = "links-only"; in a
public wiki, only openly licensed sources, unless the owner gave permission
(--allow-restricted records who and when). A page behind a login or paywall
is never worked around. When a copy isn't allowed, record a link instead:
manifest.py put-source <slug> --kind link ...

--refresh saves a source again (for example when check-upstream says it
changed); narratives pinned to its old version are then reported by
wiki-check.

Exit code: 0 saved, 1 refused or failed (the reason is printed), 2 usage error.
"""

import argparse
import os
import re
import sys

sys.dont_write_bytecode = True

from lib import config, convert, fetch, footer, layout, manifest, pdf, policy, wikiindex  # noqa: E402
from lib.layout import Cli, entry  # noqa: E402
from lib.util import dumps, read_bytes, today  # noqa: E402

cli = Cli('fetch-source.py', 'usage: fetch-source.py <slug> --url URL --tags a,b --license ID [...]; see --help')
DRAFT_WORDS = 60


def draft_abstract(text):
    """The source's opening words, as a placeholder until the agent writes its abstract."""
    words = []
    for line in text.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith(('#', '```', '|', '<!--', '---', '![')):
            continue
        words += re.sub(r'[*_`>\\]', '', stripped).split()
        if len(words) >= DRAFT_WORDS:
            break
    return ' '.join(words[:DRAFT_WORDS]) + ('…' if len(words) > DRAFT_WORDS else '') or 'No text found.'


def read_source(args):
    """(kind, bytes, final URL, content type) of the source, from --file or the network."""
    if args.file:
        if not os.path.isfile(args.file):
            cli.fail(f'no such file: {args.file}')
        return fetch.kind_of('', args.file), read_bytes(args.file), args.url, ''
    try:
        r = fetch.fetch(args.url)
    except fetch.FetchError as e:
        cli.fail(str(e))
    return fetch.kind_of(r.content_type, r.url), r.data, r.url, r.content_type


def to_markdown(kind, data, url, content_type='', include=None, name=''):
    """(the markdown, [(title, page, markdown)] slices of a long outlined PDF)."""
    try:
        return convert.convert(kind, data, url, content_type, include, name)
    except convert.ConvertError as e:
        cli.fail(str(e))


def beside(path):
    """A reader of the files next to path, for a LaTeX source's \\input; None without a path."""
    if not path:
        return None
    base = os.path.dirname(os.path.abspath(path))

    def include(name):
        for candidate in (name, name + '.tex'):
            full = os.path.abspath(os.path.join(base, candidate))
            if full.startswith(base + os.sep) and os.path.isfile(full):
                return read_bytes(full).decode('utf-8', 'replace')
        return None
    return include


def slice_slug(slug, n, title):
    words = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:40].strip('-')
    return f'{slug}-{n}-{words}' if words else f'{slug}-{n}'


def main(argv):
    p = argparse.ArgumentParser(prog='fetch-source.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('slug')
    p.add_argument('--url', required=True)
    p.add_argument('--tags', required=True, type=lambda v: [t.strip() for t in v.split(',') if t.strip()])
    p.add_argument('--license', required=True)
    p.add_argument('--license-url')
    p.add_argument('--published')
    p.add_argument('--file')
    p.add_argument('--refresh', action='store_true')
    p.add_argument('--allow-restricted', metavar='WHO_WHEN')
    p.add_argument('--json', action='store_true')
    p.add_argument('--root')
    args = p.parse_args(argv)

    root = cli.wiki(args.root)
    try:
        settings = config.load(root).settings
    except config.ConfigError as e:
        cli.fail('Config.toml is invalid, fix it first: ' + '; '.join(e.problems))
    sources = manifest.load(root, 'sources')
    existing = sources.get(args.slug)
    if existing and not args.refresh:
        cli.fail(f'{args.slug} is already saved; pass --refresh to save it again')
    if args.refresh and not existing:
        cli.fail(f'no source {args.slug} to refresh')
    if existing and existing.get('kind') == 'link':
        cli.fail(f'{args.slug} is a link; save a copy under a new slug, or change the link with manifest.py put-source')
    unknown = [t for t in args.tags if t not in manifest.load(root, 'tags')]
    if unknown:
        cli.fail(f'no such tag(s): {", ".join(unknown)}; add them first (manifest.py add-tag)')

    seen_by = policy.visibility(root)
    ok, why = policy.may_copy(settings['source_copies'], seen_by, args.license, args.allow_restricted)
    if not ok:
        cli.fail(why)

    kind, data, final_url, content_type = read_source(args)
    body, slices = to_markdown(kind, data, final_url, content_type, beside(args.file), args.file or final_url)
    if not body.strip():
        cli.fail('nothing to save: the source has no text')
    keep_abstract = existing and not existing.get('abstract_draft')
    if slices and existing:
        cli.fail(f'{args.slug} is now over {pdf.SLICE_PAGES} pages with an outline, so it would be saved in slices; save it again under a new slug')
    if slices:
        parts = [(slice_slug(args.slug, n, title), text.encode(), args.url + (f'#page={page + 1}' if page is not None else ''),
                  f'{title}: {draft_abstract(text)}') for n, (title, page, text) in enumerate(slices, 1)]
        taken = [s for s, _, _, _ in parts if s in sources]
        if taken:
            cli.fail(f'already saved: {", ".join(taken)}')
    else:
        parts = [(args.slug, body, args.url, existing['abstract'] if keep_abstract else draft_abstract(body.decode()))]
    results = []
    for slug, text, url, abstract in parts:
        rel = f'sources/{slug}.md'
        saved = footer.add(text, url, args.license, args.license_url)
        fields = {
            'file': rel, 'kind': kind, 'url': url, 'published': args.published or (existing or {}).get('published'),
            'ingested': today(), 'license': args.license, 'license_url': args.license_url, 'permission': args.allow_restricted,
            'tags': args.tags, 'abstract': abstract, 'abstract_draft': None if keep_abstract else True,
        }
        try:
            manifest.save(root, 'sources', slug, fields)  # checked before anything is written
        except manifest.ManifestError as e:
            cli.fail(str(e))
        path = os.path.join(root, layout.in_content(rel))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(saved)
        results.append({'slug': slug, 'file': layout.in_content(rel), 'kind': kind, 'bytes': len(saved), 'refreshed': bool(existing),
                        'abstract_draft': not keep_abstract, 'policy': why})
    wikiindex.sync(root, write=True)  # the tag pages list the new source
    if args.json:
        print(dumps(results[0] if not slices else {'slices': results}))
        return 0
    if slices:
        print(f'saved {args.slug} in {len(results)} slices, one per top-level outline entry ({why}):')
    for r in results:
        print(f'{"refreshed" if existing else "saved"} {r["file"]} ({kind}, {r["bytes"]:,} bytes)' + ('' if slices else f': {why}'))
    if not keep_abstract:
        print('next: write the abstract of each slice a question reads' if slices else
              f'next: read it and write its abstract: manifest.py set-abstract {args.slug} --abstract "..."')
    return 0


if __name__ == '__main__':  # pragma: no cover
    entry(main)
