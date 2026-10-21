"""The fields of tags.yaml and the two manifests (design doc §4.2-§4.4), and
validate(), which wiki-check reports from.

Each file is a mapping of entries keyed by a kebab-case slug. A finding is a dict
with file, entry, field, code and message; the codes are BAD_ENTRY (an entry
that isn't a mapping, or a bad key), MISSING_FIELD, UNKNOWN_FIELD (with a
did-you-mean hint), BAD_TYPE and BAD_VALUE.
"""

import difflib
import re

from .util import is_date

SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
TEMPLATE = re.compile(r'[a-z0-9][a-z0-9_-]*\Z')
MD5 = re.compile(r'[0-9a-f]{32}\Z')
VERSION = re.compile(r'[0-9]+\.[0-9]+\Z')
URL = re.compile(r'https?://\S+\Z')
KINDS = ('text', 'html', 'pdf', 'tex', 'link')


class Field:
    """kind: str, bool, date, slug, template, md5, url, enum, list, map,
    struct. A list has an item Field; a map a value Field (its keys are slugs,
    or versions with versions=True); a struct its own fields."""

    def __init__(self, kind, required=False, nullable=False, item=None, choices=None, fields=None, nonempty=False, versions=False):
        self.kind, self.required, self.nullable = kind, required, nullable
        self.item, self.choices, self.fields, self.nonempty, self.versions = item, choices, fields, nonempty, versions


SCHEMAS = {
    'tags': {
        'description': Field('str', required=True),
        'parent': Field('slug', required=True, nullable=True),
        'smes': Field('list', item=Field('str')),
    },
    'sources': {
        'file': Field('str'),  # sources/<slug>.md: checked in _cross
        'kind': Field('enum', required=True, choices=KINDS),
        'url': Field('url', required=True),
        'published': Field('date'),
        'ingested': Field('date', required=True),
        'license': Field('str', required=True),
        'license_url': Field('url'),
        'permission': Field('str'),  # the owner's permission to keep a copy the license alone doesn't allow
        'tags': Field('list', required=True, item=Field('slug'), nonempty=True),
        'abstract': Field('str', required=True),
        'abstract_draft': Field('bool'),
        'upstream_changed': Field('date'),
    },
    'narratives': {
        'template': Field('template', required=True),
        'tags': Field('struct', required=True, fields={
            'primary': Field('list', required=True, item=Field('slug'), nonempty=True),
            'supporting': Field('list', required=True, item=Field('slug')),
        }),
        'read': Field('map', required=True, item=Field('md5')),
        'grades': Field('map', item=Field('struct', fields={  # the reading plan's grades (design doc §7.1)
            'relevance': Field('enum', required=True, choices=('high', 'medium', 'low')),
            'authority': Field('enum', required=True, choices=('A', 'B', 'C')),
        })),
        'models': Field('map', item=Field('str'), versions=True),  # the model that wrote each version
    },
}

_TYPE_NAMES = {'list': 'a list', 'map': 'a mapping', 'struct': 'a mapping'}


def _check(field, value, where, emit):
    """Check one value against its Field, emitting (code, field path, message)."""
    if value is None:
        if not field.nullable:
            emit('BAD_TYPE', where, f'{where} must not be empty')
        return
    k = field.kind
    if k in ('list', 'map', 'struct'):
        want = list if k == 'list' else dict
        if not isinstance(value, want):
            emit('BAD_TYPE', where, f'{where} must be {_TYPE_NAMES[k]}')
            return
        if field.nonempty and not value:
            emit('BAD_VALUE', where, f'{where} must list at least one')
        if k == 'list':
            for i, v in enumerate(value):
                _check(field.item, v, f'{where}[{i}]', emit)
        elif k == 'map':
            for key, v in value.items():
                if field.versions and not VERSION.match(str(key)):
                    emit('BAD_VALUE', where, f'{where} key {key!r} must be a version, such as 1.0')
                elif not field.versions and not SLUG.match(str(key)):
                    emit('BAD_VALUE', where, f'{where} key {key!r} must be a kebab-case slug')
                _check(field.item, v, f'{where}.{key}', emit)
        else:
            _fields(field.fields, value, where, emit)
        return
    if k == 'bool':
        if not isinstance(value, bool):
            emit('BAD_TYPE', where, f'{where} must be true or false')
        return
    if not isinstance(value, str):
        emit('BAD_TYPE', where, f'{where} must be a string')
        return
    if not value.strip():
        emit('BAD_VALUE', where, f'{where} must not be empty')
        return
    bad = {
        'date': (lambda v: not is_date(v), 'a date, YYYY-MM-DD'),
        'slug': (lambda v: not SLUG.match(v), 'a kebab-case slug, such as load-balancer'),
        'template': (lambda v: not TEMPLATE.match(v), 'a template name, such as technical_brief_overview'),
        'md5': (lambda v: not MD5.match(v), 'an MD5, 32 lowercase hex digits'),
        'url': (lambda v: not URL.match(v), 'an http(s) URL'),
        'enum': (lambda v: v not in field.choices, ' or '.join(field.choices or ())),
    }.get(k)
    if bad and bad[0](value):
        emit('BAD_VALUE', where, f'{where} must be {bad[1]}, not {value!r}')


def _fields(spec, entry, where, emit):
    for name, field in spec.items():
        if field.required and name not in entry:
            emit('MISSING_FIELD', f'{where}.{name}' if where else name, f'{where + "." if where else ""}{name} is required')
    for name, value in entry.items():
        path = f'{where}.{name}' if where else name
        if name not in spec:
            near = difflib.get_close_matches(str(name), list(spec), n=1)
            emit('UNKNOWN_FIELD', path, f'unknown field {path}' + (f' (did you mean {near[0]}?)' if near else ''))
        else:
            _check(spec[name], value, path, emit)


def _cross(kind, entry, emit):
    """Rules across fields."""
    if kind == 'sources':
        if entry.get('kind') == 'link' and 'file' in entry:
            emit('BAD_VALUE', 'file', 'a link source has no saved file: remove file')
        elif entry.get('kind') in ('text', 'html', 'pdf', 'tex') and 'file' not in entry:
            emit('MISSING_FIELD', 'file', f'a {entry["kind"]} source needs file, its saved copy')
        f = entry.get('file')
        if isinstance(f, str) and not re.fullmatch(r'sources/[^/]+\.md', f):
            emit('BAD_VALUE', 'file', f'file must be sources/<slug>.md, not {f!r}')


def validate(kind, data, file):
    """Findings for a parsed file of kind tags, sources or narratives."""
    findings = []
    if not isinstance(data, dict):
        return [{'file': file, 'entry': None, 'field': None, 'code': 'BAD_TYPE', 'message': 'the file must be a mapping of entries'}]
    for key, entry in data.items():
        def emit(code, field, message, key=key):
            findings.append({'file': file, 'entry': key, 'field': field, 'code': code, 'message': f'{key}: {message}'})
        if not SLUG.match(str(key)):
            emit('BAD_ENTRY', None, 'an entry\'s key must be a kebab-case slug')
        if not isinstance(entry, dict):
            emit('BAD_ENTRY', None, 'an entry must be a mapping of fields')
            continue
        _fields(SCHEMAS[kind], entry, '', emit)
        _cross(kind, entry, emit)
    return findings
