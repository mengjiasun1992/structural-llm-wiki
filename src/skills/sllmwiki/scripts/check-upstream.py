#!/usr/bin/env python3
"""check-upstream: has a saved source changed where it came from? (design doc §7.2)

  check-upstream.py [<slug> ...] [--tags a,b] [--json] [--root <wiki>]

Fetches each saved source again (all of them, the given slugs, or those under
the given tags), converts it the way fetch-source saved it, and compares it
with the saved copy. A changed one is marked upstream_changed: <today> in the
sources manifest, which wiki-check then reports (SOURCE_UPSTREAM_CHANGED: re-ingest
it with fetch-source.py --refresh, and narratives pinned to it get rechecked).
An unchanged one loses any earlier mark. A source that can't be fetched or
converted is reported and left as it is. A long PDF saved in slices is fetched
once and each slice compared with the new slice at the same place: the same
page of a PDF, the same top-level entry of an EPUB's contents.

A saved copy also differs when the skill's converter has improved since it was
saved (a PDF's placeholder title dropped, say): re-ingesting takes the better copy.

It uses the network, so it runs on request, never as part of a check.
Exit code: 0, 1 on a refusal (no such slug or tag), 2 on a usage error.
"""

import argparse
import os
import re
import sys

sys.dont_write_bytecode = True

from lib import convert, fetch, layout, manifest, wikiindex  # noqa: E402
from lib.layout import Cli, entry  # noqa: E402
from lib.util import dumps, read_bytes, split_footer, today  # noqa: E402

cli = Cli('check-upstream.py', 'usage: check-upstream.py [<slug> ...] [--tags a,b] [--json]')


def fetch_converted(url):
    """(markdown bytes, slices) of the source at url, or raises FetchError or ConvertError."""
    r = fetch.fetch(url)
    return convert.convert(fetch.kind_of(r.content_type, r.url), r.data, r.url, r.content_type, None, r.url)


def place_of(url):
    """A slice's place from its URL's fragment (page=N, chapter=N), or None."""
    _, _, frag = url.partition('#')
    return frag if re.match(r'(page|chapter)=\d+\Z', frag) else None


def compare(root, entry, fetched):
    """(status, detail) for one saved source against what its URL serves now."""
    base = entry['url'].split('#')[0]
    if base not in fetched:
        try:
            fetched[base] = fetch_converted(base)
        except (fetch.FetchError, convert.ConvertError) as e:
            fetched[base] = e
    got = fetched[base]
    if isinstance(got, Exception):
        return 'unreachable', str(got)
    body, slices = got
    place = place_of(entry['url'])
    if place is not None:
        match = [s for s in slices if s[1] == place]
        if not match:
            kind, n = place.split('=')
            return 'changed', f'no slice starts on page {n} any more' if kind == 'page' else f'no top-level entry {n} in its contents any more'
        body = match[0][2].encode()
    saved = split_footer(read_bytes(os.path.join(root, layout.in_content(entry['file']))))[0]
    if split_footer(body)[0].rstrip(b'\n') == saved.rstrip(b'\n'):
        return 'unchanged', ''
    return 'changed', f'{len(saved):,} bytes saved, {len(body):,} now'


def main(argv):
    p = argparse.ArgumentParser(prog='check-upstream.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('slugs', nargs='*')
    p.add_argument('--tags', type=lambda v: [t.strip() for t in v.split(',') if t.strip()], default=[])
    p.add_argument('--json', action='store_true')
    p.add_argument('--root')
    args = p.parse_args(argv)
    root = cli.wiki(args.root)
    sources = manifest.load(root, 'sources')
    unknown = [s for s in args.slugs if s not in sources] + [t for t in args.tags if t not in manifest.load(root, 'tags')]
    if unknown:
        cli.fail(f'no such source or tag: {", ".join(unknown)}')
    chosen = [s for s, e in sources.items() if e.get('file') and (not args.slugs and not args.tags or s in args.slugs
                                                                    or set(args.tags) & set(e.get('tags') or []))]
    results, fetched, marked = [], {}, False
    for slug in chosen:
        e = sources[slug]
        status, detail = compare(root, e, fetched)
        if status == 'changed' and not e.get('upstream_changed'):
            manifest.save(root, 'sources', slug, dict(e, upstream_changed=today()))
            marked = True
        elif status == 'unchanged' and e.get('upstream_changed'):
            manifest.save(root, 'sources', slug, {k: v for k, v in e.items() if k != 'upstream_changed'})
            marked = True
        results.append({'slug': slug, 'status': status, 'detail': detail})
    if marked:
        wikiindex.sync(root, write=True)
    if args.json:
        print(dumps({'sources': results}))
        return 0
    for r in results:
        print(f'{r["status"]:<12} {r["slug"]}' + (f': {r["detail"]}' if r['detail'] else ''))
    changed = [r['slug'] for r in results if r['status'] == 'changed']
    print(f'{len(results)} checked, {len(changed)} changed' + (f': re-ingest with fetch-source.py --refresh ({", ".join(changed)})' if changed else ''))
    return 0


if __name__ == '__main__':  # pragma: no cover
    entry(main)
