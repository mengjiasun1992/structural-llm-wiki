"""Reading and writing tags.yaml and the two manifests, one entry at a time,
each entry checked against lib/schema.py before it is written (design doc
§4.2-§4.4). Nothing derived is stored: sizes, hashes, titles and versions are
read from the files when needed.
"""

import copy
import os
import re

from . import layout, metadata, numbering, schema, wikiyaml
from . import smes as smesrules
from .util import read_bytes, read_text, source_hash, write_text

FILES = {'tags': layout.TAGS, 'sources': layout.SOURCES_MANIFEST, 'narratives': layout.NARRATIVES_MANIFEST}
HEADERS = {
    'tags': '# The tag tree: each tag\'s description, parent and SMEs (design doc §4.2).\n# Written by sllmwiki manifest; children, sources and narratives are derived.\n',
    'sources': '# Sources, keyed by slug (design doc §4.3). Written by sllmwiki fetch-source and sllmwiki manifest.\n',
    'narratives': '# Narratives, keyed by question slug (design doc §4.4). Written by sllmwiki finish-narrative.\n',
}


class ManifestError(Exception):
    pass


_PARSED = {}  # path -> ((mtime, size), parsed): one command loads a manifest many times


def load(root, kind):
    """The parsed file (an empty mapping when it doesn't exist yet); a copy the caller may change."""
    path = os.path.join(root, FILES[kind])
    try:
        st = os.stat(path)
    except OSError:
        return {}
    stamp = (st.st_mtime_ns, st.st_size)
    cached = _PARSED.get(path)
    if not cached or cached[0] != stamp:
        cached = _PARSED[path] = (stamp, wikiyaml.parse(read_text(path)))
    return copy.deepcopy(cached[1])


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
    copy's file and kind are sllmwiki fetch-source's). drop_copy turns a saved copy
    into a link in place: its file is deleted, its other fields and place kept."""
    entries = load(root, 'sources')
    entry = dict(entries.get(slug, {}))
    if slug not in entries and changes.get('kind') != 'link':
        raise ManifestError(f'{slug} is new: save a copy with sllmwiki fetch-source, or record a link with kind link')
    copy = slug in entries and entry.get('kind') != 'link'
    if drop_copy and not (copy and changes.get('kind') == 'link'):
        raise ManifestError(f'--drop-copy turns a saved copy into a link (with --kind link); {slug} isn\'t a saved copy' if not copy
                            else '--drop-copy needs --kind link')
    if copy and not drop_copy and {'file', 'kind'} & {k for k, v in changes.items() if v is not None}:
        raise ManifestError(f'{slug} is a saved copy: sllmwiki fetch-source --refresh changes its file and kind, '
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


def _without_metadata(text):
    span = numbering.section(text, 'Metadata')
    lines = text.split('\n')
    return '\n'.join(lines[:span[0]] + lines[span[1]:]) if span else text


def narrative_hash(text):
    """A narrative's content hash: without its Metadata, what lib/prerequisites.py generates, and its heading numbers,
    so new dates, a version, another narrative's new prerequisite or a renumbering alone aren't a change."""
    lines = metadata.without_generated(_without_metadata(text)).split('\n')
    for h in numbering.headings('\n'.join(lines)):
        lines[h.line] = f'{"#" * h.level} {h.title}'
    return source_hash(re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).encode('utf-8'))  # nor where blank lines were


def legacy_hash(text):
    """The hash pins had before prerequisites (issue #205): it kept heading numbers. Still accepted until re-pinned."""
    return source_hash(_without_metadata(text).encode('utf-8'))


def pin_matches(text, pin):
    return pin in (narrative_hash(text), legacy_hash(text))


def narrative_pins(root, slugs):
    """{slug: hash} of the narratives one builds on; a missing one isn't pinned."""
    out = {}
    for slug in slugs:
        path = os.path.join(root, layout.NARRATIVES, f'{slug}.md')
        if os.path.isfile(path):
            out[slug] = narrative_hash(read_text(path))
    return out


def repin(root, before):
    """After narratives were rewritten without a change in content (a regenerated region, a moved section): every pin
    on one of them that matched its text before, now on its text after. before is {slug: text before}; the entries changed."""
    entries = load(root, 'narratives')
    changed = []
    for slug, e in entries.items():
        new = dict(e)
        for field in ('built_on', 'prerequisites'):
            pins = dict(e.get(field) or {})
            for base, pin in pins.items():
                path = os.path.join(root, layout.NARRATIVES, f'{base}.md')
                if base in before and pin_matches(before[base], pin) and os.path.isfile(path):
                    pins[base] = narrative_hash(read_text(path))
            if pins != (e.get(field) or {}):
                new[field] = pins
        if new != e:
            save(root, 'narratives', slug, new)
            changed.append(slug)
    return changed


def put_narrative(root, slug, template, primary, supporting, read, grades=None, model=None, built_on=None, prerequisites=None):
    """Write a narrative's entry: its template, tags and the current pins of the sources it read;
    grades, the reading plan's, replace the recorded ones; model, (version, name), is added to models;
    built_on, the narratives it builds on, and prerequisites, those a reader reads first, are pinned
    (None keeps the recorded ones, re-pinned; a prerequisite must be a narrative)."""
    tags = load(root, 'tags')
    unknown = [t for t in list(primary) + list(supporting) if t not in tags]
    if unknown:
        raise ManifestError(f'no such tag(s): {", ".join(unknown)}; add them first (sllmwiki manifest add-tag)')
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
    wanted = list(recorded.get('prerequisites') or {}) if prerequisites is None else list(prerequisites)
    missing = [p for p in wanted if not os.path.isfile(os.path.join(root, layout.NARRATIVES, f'{p}.md'))]
    if missing or slug in wanted:
        raise ManifestError(f'a prerequisite is another narrative; no narrative {", ".join(missing)}' if missing else 'a narrative isn\'t its own prerequisite')
    firsts = narrative_pins(root, wanted)
    if firsts:
        entry['prerequisites'] = firsts
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
        ranked = smesrules.check_entries(smes)
        if ranked:
            raise ManifestError(ranked[0][1])
        entry['smes'] = smes
        if not smes:
            entry.pop('smes')
    return save(root, 'tags', name, {**entry, 'parent': entry.get('parent')})
