"""Reading and writing tags.yaml and the two manifests, one entry at a time,
each entry checked against lib/schema.py before it is written (design doc
§4.2-§4.4). Nothing derived is stored: sizes, hashes, titles and versions are
read from the files when needed.
"""

import os

from . import layout, numbering, schema, wikiyaml
from .util import read_bytes, read_text, source_hash, write_text

FILES = {'tags': layout.TAGS, 'sources': layout.SOURCES_MANIFEST, 'narratives': layout.NARRATIVES_MANIFEST}
HEADERS = {
    'tags': '# The tag tree: each tag\'s description, parent and SMEs (design doc §4.2).\n# Written by manifest.py; children, sources and narratives are derived.\n',
    'sources': '# Sources, keyed by slug (design doc §4.3). Written by fetch-source.py and manifest.py.\n',
    'narratives': '# Narratives, keyed by question slug (design doc §4.4). Written by finish-narrative.py.\n',
}


class ManifestError(Exception):
    pass


def load(root, kind):
    """The parsed file (an empty mapping when it doesn't exist yet)."""
    path = os.path.join(root, FILES[kind])
    return wikiyaml.parse(read_text(path)) if os.path.isfile(path) else {}


def _ordered(kind, fields):
    """fields in the schema's order; None left out, except where the field may be null (a root tag's parent)."""
    spec = schema.SCHEMAS[kind]
    order = list(spec)
    keep = [k for k in fields if fields[k] is not None or (k in spec and spec[k].nullable)]
    return {k: fields[k] for k in sorted(keep, key=lambda k: order.index(k) if k in order else len(order))}


def save(root, kind, key, fields):
    """Write one entry, after checking it; raises ManifestError listing its problems."""
    fields = _ordered(kind, fields)
    found = schema.validate(kind, {key: fields}, FILES[kind])
    if found:
        raise ManifestError('; '.join(f['message'] for f in found))
    path = os.path.join(root, FILES[kind])
    text = read_text(path) if os.path.isfile(path) else HEADERS[kind]
    write_text(path, wikiyaml.upsert_entry(text, key, fields))
    return fields


def remove(root, kind, key):
    path = os.path.join(root, FILES[kind])
    if key not in load(root, kind):
        raise ManifestError(f'{FILES[kind]} has no {key}')
    write_text(path, wikiyaml.remove_entry(read_text(path), key))


def put_source(root, slug, drop_copy=False, **changes):
    """Create a link source, or change fields of any existing source (a saved
    copy's file and kind are fetch-source.py's). drop_copy turns a saved copy
    into a link in place: its file is deleted, its other fields and place kept."""
    entries = load(root, 'sources')
    entry = dict(entries.get(slug, {}))
    if slug not in entries and changes.get('kind') != 'link':
        raise ManifestError(f'{slug} is new: save a copy with fetch-source.py, or record a link with kind link')
    copy = slug in entries and entry.get('kind') != 'link'
    if drop_copy and not (copy and changes.get('kind') == 'link'):
        raise ManifestError(f'--drop-copy turns a saved copy into a link (with --kind link); {slug} isn\'t a saved copy' if not copy
                            else '--drop-copy needs --kind link')
    if copy and not drop_copy and {'file', 'kind'} & {k for k, v in changes.items() if v is not None}:
        raise ManifestError(f'{slug} is a saved copy: fetch-source.py --refresh changes its file and kind, '
                            'and --kind link --drop-copy turns it into a link')
    if drop_copy:
        path = os.path.join(root, layout.in_content(entry.pop('file')))
        if os.path.exists(path):
            os.remove(path)
        entry.pop('abstract_draft', None)
    entry.update({k: v for k, v in changes.items() if v is not None})
    return save(root, 'sources', slug, entry)


def set_abstract(root, slug, abstract):
    """Replace a source's abstract with one the agent wrote, clearing abstract_draft."""
    entries = load(root, 'sources')
    if slug not in entries:
        raise ManifestError(f'no source {slug}')
    entry = dict(entries[slug], abstract=abstract)
    entry.pop('abstract_draft', None)
    return save(root, 'sources', slug, entry)


def pins(root, slugs):
    """{slug: hash} of the saved copies a narrative reads; links aren't pinned."""
    sources = load(root, 'sources')
    out = {}
    for slug in slugs:
        if slug not in sources:
            raise ManifestError(f'no source {slug}')
        if sources[slug].get('file'):
            out[slug] = source_hash(read_bytes(os.path.join(root, layout.in_content(sources[slug]['file']))))
    return out


def narrative_hash(text):
    """A narrative's content hash, its Metadata section left out, so new dates or a version alone aren't a change."""
    span = numbering.section(text, 'Metadata')
    lines = text.split('\n')
    body = '\n'.join(lines[:span[0]] + lines[span[1]:]) if span else text
    return source_hash(body.encode('utf-8'))


def narrative_pins(root, slugs):
    """{slug: hash} of the narratives one builds on; a missing one isn't pinned."""
    out = {}
    for slug in slugs:
        path = os.path.join(root, layout.NARRATIVES, f'{slug}.md')
        if os.path.isfile(path):
            out[slug] = narrative_hash(read_text(path))
    return out


def put_narrative(root, slug, template, primary, supporting, read, grades=None, model=None, built_on=None):
    """Write a narrative's entry: its template, tags and the current pins of the sources it read;
    grades, the reading plan's, replace the recorded ones; model, (version, name), is added to models;
    built_on, the narratives it builds on, are pinned (None keeps the recorded ones, re-pinned)."""
    tags = load(root, 'tags')
    unknown = [t for t in list(primary) + list(supporting) if t not in tags]
    if unknown:
        raise ManifestError(f'no such tag(s): {", ".join(unknown)}; add them first (manifest.py add-tag)')
    if not os.path.isfile(os.path.join(root, layout.NARRATIVES, f'{slug}.md')):
        raise ManifestError(f'no narrative {layout.NARRATIVES}/{slug}.md')
    entry = {'template': template, 'tags': {'primary': list(primary), 'supporting': list(supporting)}, 'read': pins(root, read)}
    recorded = load(root, 'narratives').get(slug) or {}
    if grades or recorded.get('grades'):
        entry['grades'] = dict(grades or recorded['grades'])
    models = dict(recorded.get('models') or {}, **dict([model] if model else []))
    if models:
        entry['models'] = models
    bases = narrative_pins(root, list(recorded.get('built_on') or {}) if built_on is None else built_on)
    if bases:
        entry['built_on'] = bases
    return save(root, 'narratives', slug, entry)


def add_tag(root, name, description, parent=None):
    tags = load(root, 'tags')
    if name in tags:
        raise ManifestError(f'tag {name} exists; change it with put-tag')
    if parent and parent not in tags:
        raise ManifestError(f'no parent tag {parent}')
    return save(root, 'tags', name, {'description': description, 'parent': parent})


def put_tag(root, name, description=None, smes=None):
    tags = load(root, 'tags')
    if name not in tags:
        raise ManifestError(f'no tag {name}; add it with add-tag')
    entry = dict(tags[name])
    if description is not None:
        entry['description'] = description
    if smes is not None:
        entry['smes'] = smes
        if not smes:
            entry.pop('smes')
    return save(root, 'tags', name, {**entry, 'parent': entry.get('parent')})
