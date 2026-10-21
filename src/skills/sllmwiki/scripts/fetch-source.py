#!/usr/bin/env python3
"""fetch-source: save a source in the wiki, verbatim, and record it (design doc §4.3, §4.7).

  fetch-source.py <slug> --url URL --tags a,b --license ID [--license-url URL]
                  [--published YYYY-MM-DD] [--file PATH] [--refresh]
                  [--allow-restricted "<who, when>"] [--json] [--root <wiki>]

Fetches URL (or reads PATH, a copy you already have of the source at URL) and
saves it as sllmwiki/sources/<slug>.md: markdown and text byte for byte, an
HTML page's main content converted, with the "Original source" footer. The
source is recorded with a starter abstract (its opening words, marked
abstract_draft); read the source and replace it with
`manifest.py set-abstract <slug> --abstract "..."`.

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

from lib import config, fetch, footer, html2md, layout, manifest, policy, wikiindex  # noqa: E402
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


def to_markdown(kind, data, url, content_type=''):
    if kind == 'pdf':
        cli.fail('PDFs can\'t be saved yet; record it as a link (manifest.py put-source --kind link)')
    if kind is None:
        cli.fail('not markdown, text, HTML or PDF; record it as a link (manifest.py put-source --kind link)')
    if kind == 'html':
        page = data.decode(fetch.charset(content_type) or 'utf-8', 'replace')
        return html2md.convert(page, url)[0].encode()
    try:
        data.decode('utf-8')
    except UnicodeDecodeError:
        cli.fail('the text isn\'t UTF-8; save a UTF-8 copy and pass it with --file')
    return data


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
    body = to_markdown(kind, data, final_url, content_type)
    if not body.strip():
        cli.fail('nothing to save: the source has no text')
    rel = f'sources/{args.slug}.md'
    saved = footer.add(body, args.url, args.license, args.license_url)
    keep_abstract = existing and not existing.get('abstract_draft')
    fields = {
        'file': rel, 'kind': kind, 'url': args.url, 'published': args.published or (existing or {}).get('published'),
        'ingested': today(), 'license': args.license, 'license_url': args.license_url, 'permission': args.allow_restricted,
        'tags': args.tags,
        'abstract': existing['abstract'] if keep_abstract else draft_abstract(body.decode()),
        'abstract_draft': None if keep_abstract else True,
    }
    try:
        manifest.save(root, 'sources', args.slug, fields)  # checked before anything is written
    except manifest.ManifestError as e:
        cli.fail(str(e))
    path = os.path.join(root, layout.in_content(rel))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(saved)
    wikiindex.sync(root, write=True)  # the tag pages list the new source
    result = {'slug': args.slug, 'file': layout.in_content(rel), 'kind': kind, 'bytes': len(saved), 'refreshed': bool(existing),
              'abstract_draft': not keep_abstract, 'policy': why}
    if args.json:
        print(dumps(result))
    else:
        print(f'{"refreshed" if existing else "saved"} {result["file"]} ({kind}, {len(saved):,} bytes): {why}')
        if not keep_abstract:
            print(f'next: read it and write its abstract: manifest.py set-abstract {args.slug} --abstract "..."')
    return 0


if __name__ == '__main__':  # pragma: no cover
    entry(main)
