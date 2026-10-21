"""The schema of a wiki's three registry files: tags.yaml,
ingested/manifest.yaml and groomed/manifest.yaml.

Each file is a mapping of entries (a tag name or a slug) to a mapping of
fields. FIELDS declares every field an entry may have: its kind, whether it
is required, and whether it may be null. validate() reports missing fields,
unknown fields (with a did-you-mean hint), wrong types and bad values;
wiki-check runs it, so the wiki's CI enforces it on every pull request.

Kinds: str, int, date (ISO 8601), md5 (32 hex digits), version ("1.2",
quoted so YAML keeps it a string), slug (kebab-case), path (repository-
relative), enum (one of `values`), list (of `item`), map (of `fields`), and
pins (sources_read_full: slug -> md5).
"""

import difflib
import re

from .util import date_parse

SLUG = re.compile(r'[a-z0-9][a-z0-9-]*\Z')
MD5 = re.compile(r'[0-9a-f]{32}\Z')
VERSION = re.compile(r'[0-9]+\.[0-9]+\Z')

SOURCE_TYPES = ('raw_content', 'link', 'image', 'other')


def F(kind, required=True, nullable=False, **extra):
    return {'kind': kind, 'required': required, 'nullable': nullable, **extra}


SCHEMAS = {
    'tags': {
        'description': F('str'),
        'parent': F('slug', nullable=True),
        'sub_tags': F('list', item='slug'),
        'ingested': F('list', item='path'),
        'groomed': F('list', item='path'),
        'smes': F('list', item='str'),
        'contact_channels': F('list', required=False, item='str'),
        'abstract': F('str', required=False),
        'abstract_inputs': F('md5', required=False),
    },
    'ingested': {
        'file': F('path', required=False),
        'original_file': F('path', required=False),
        'type': F('enum', values=SOURCE_TYPES),
        'size_bytes': F('int', nullable=True),
        'original_url': F('str'),
        'content_modified': F('date'),
        'content_ingested': F('date'),
        'content_md5': F('md5', nullable=True),
        'tags': F('list', item='slug'),
        'abstract': F('str'),
        'license': F('str', required=False),
        'fetch': F('map', required=False, fields={
            'start': F('str', required=False),
            'end': F('str', required=False),
            'exclude_class': F('list', required=False, item='str'),
        }),
    },
    'groomed': {
        'file': F('path'),
        'question': F('str'),
        'size_bytes': F('int'),
        'version': F('version'),
        'created': F('date'),
        'last_modified': F('date'),
        'tags': F('map', fields={
            'primary': F('list', item='slug'),
            'supporting': F('list', item='slug'),
        }),
        'sources_read_full': F('pins'),
        'sources_abstract_only': F('list', item='slug'),
        'abstract': F('str', required=False),
        'status': F('enum', required=False, values=('draft', 'published')),
    },
}

# Rules that span fields, as (schema, check(entry) -> message or None).
RULES = {
    'tags': [lambda e: 'abstract_inputs needs an abstract' if e.get('abstract_inputs') and not e.get('abstract') else None],
    'ingested': [
        lambda e: f"type {e.get('type')} needs a \"file\"" if e.get('type') in ('raw_content', 'image') and not e.get('file') else None,
        lambda e: f"type {e.get('type')} has no saved file, so \"file\" must be absent" if e.get('type') in ('link', 'other') and e.get('file') else None,
    ],
    'groomed': [],
}


def _type_error(kind, value, spec):
    """Why `value` doesn't fit `kind`, or None."""
    if kind == 'str':
        return None if isinstance(value, str) and value.strip() else 'must be a non-empty string'
    if kind == 'int':
        return None if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 'must be a whole number ≥ 0'
    if kind == 'date':
        return None if isinstance(value, str) and date_parse(value) is not None else 'must be an ISO 8601 date, quoted (e.g. "2026-10-18" or "2026-10-18T06:01:05Z")'
    if kind == 'md5':
        return None if isinstance(value, str) and MD5.match(value) else 'must be an MD5 (32 lowercase hex digits)'
    if kind == 'version':
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return f'must be a quoted string such as "{value}"; unquoted, YAML reads it as a number (1.10 becomes 1.1)'
        return None if isinstance(value, str) and VERSION.match(value) else 'must be a version such as "1.2"'
    if kind == 'slug':
        return None if isinstance(value, str) and SLUG.match(value) else 'must be a kebab-case name (a-z, 0-9, -)'
    if kind == 'path':
        return None if isinstance(value, str) and value and not value.startswith(('/', '../')) and '\\' not in value else 'must be a path relative to the repository root'
    if kind == 'enum':
        return None if value in spec['values'] else f"must be one of {', '.join(spec['values'])}"
    return None


def _check(spec, value, where, field, out):
    if value is None:
        if not spec['nullable']:
            out.append(('error', 'BAD_TYPE', where, f'"{field}" must not be empty'))
        return
    kind = spec['kind']
    if kind == 'list':
        if not isinstance(value, list):
            out.append(('error', 'BAD_TYPE', where, f'"{field}" must be a list (use [] when empty)'))
            return
        for i, item in enumerate(value):
            why = _type_error(spec['item'], item, spec)
            if why:
                out.append(('error', 'BAD_TYPE', where, f'"{field}" item {i + 1} ({item!r}) {why}'))
        if len(set(map(str, value))) != len(value):
            out.append(('error', 'BAD_VALUE', where, f'"{field}" lists the same item twice'))
        return
    if kind == 'map':
        if not isinstance(value, dict):
            out.append(('error', 'BAD_TYPE', where, f'"{field}" must be a mapping'))
            return
        _fields(spec['fields'], value, where, out, prefix=f'{field}.')
        return
    if kind == 'pins':
        if not isinstance(value, dict):
            out.append(('error', 'BAD_TYPE', where, f'"{field}" must map each source slug to the MD5 read'))
            return
        for slug, md5 in value.items():
            if _type_error('slug', slug, spec) or (md5 is not None and _type_error('md5', md5, spec)):
                out.append(('error', 'BAD_TYPE', where, f'"{field}.{slug}" must be a source slug mapped to an MD5'))
        return
    why = _type_error(kind, value, spec)
    if why:
        out.append(('error', 'BAD_VALUE' if kind == 'enum' else 'BAD_TYPE', where, f'"{field}" {why} (got {value!r})'))


def _fields(fields, entry, where, out, prefix=''):
    for name, spec in fields.items():
        if name not in entry:
            if spec['required']:
                out.append(('error', 'MISSING_FIELD', where, f'missing field "{prefix}{name}"'))
            continue
        _check(spec, entry[name], where, prefix + name, out)
    for key in entry:
        if key in fields:
            continue
        near = difflib.get_close_matches(str(key), list(fields), n=1, cutoff=0.6)
        hint = f'; did you mean "{prefix}{near[0]}"?' if near else f"; allowed: {', '.join(prefix + f for f in fields)}"
        out.append(('error', 'UNKNOWN_FIELD', where, f'unknown field "{prefix}{key}"{hint}'))


def validate(schema, data, file):
    """Findings as (severity, code, where, message) for one registry file,
    already parsed into a mapping of entries."""
    out = []
    for name, entry in (data or {}).items():
        where = f'{file}:{name}'
        if not SLUG.match(str(name)):
            out.append(('error', 'BAD_TYPE', where, f'{"tag names" if schema == "tags" else "entry keys"} must be kebab-case (a-z, 0-9, -)'))
        if not isinstance(entry, dict):
            out.append(('error', 'BAD_ENTRY', where, 'entry must be a mapping'))
            continue
        _fields(SCHEMAS[schema], entry, where, out)
        for rule in RULES[schema]:
            msg = rule(entry)
            if msg:
                out.append(('error', 'BAD_VALUE', where, msg))
    return out
