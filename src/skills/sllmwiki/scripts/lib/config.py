"""A wiki's config: Config.toml at the repository root.

    [structural-llm-wiki-paths]              # where the wiki keeps its files
    ingested = "ingested"                     # sources, saved verbatim (images/ and files/ inside)
    ingested_manifest = "ingested/manifest.yaml"
    groomed = "groomed"                       # narratives
    groomed_manifest = "groomed/manifest.yaml"
    tags = "tags/tags.yaml"                   # its folder also holds the tag pages (Obsidian add-on)
    index = "SLLMWIKI_INDICES.md"
    templates = "templates"                   # the wiki's own narrative templates' files

    [structural-llm-wiki-settings]           # the skill's settings (SETTING_DEFAULTS)
    slice_large_sources = true                # a PDF over large_source_kb is saved one section per source
    large_source_kb = 50                      # the size above which a source is large: sliced, and ingest asks first
    reasoning_marker = "[sllmwiki_reasoning]" # marks a narrative's own reasoning; "" writes no marker
    gap_marker = "[sllmwiki_gap]"             # marks what the sources don't answer; "" writes no marker
    max_words = 0                             # every narrative template's body budget; 0 keeps each template's own
    abstract_words = []                       # every template's Abstract range, such as [150, 300]; [] keeps each template's own
    max_quote_words = 50                      # the longest quotation a narrative may take from a source

    [structural-llm-wiki-settings.addons.obsidian]  # the Obsidian add-on (lib/obsidian.py)
    enabled = false                           # tag pages, narrative headers, default graph settings
    show_sources = false                      # the default graph shows sources, in grey; false hides them

    [structural-llm-wiki-templates]          # the narrative templates (lib/templates.py)
    default = "technical_brief_overview"      # for narratives that name no template
    exclude = ["comparison"]                  # bundled templates not offered for new narratives

    [structural-llm-wiki-templates.technical_brief_overview]  # a bundled template: lengths over the two settings above
    max_words = 3000
    abstract_words = [150, 300]

    [structural-llm-wiki-templates.runbook]  # the wiki's own: its files (from the repository root) and lengths
    template = "templates/runbook/template.md"
    guide = "templates/runbook/guide.md"
    max_words = 800

The tables are prefixed with the project's name, so Config.toml can also hold
other tools' tables, which are left alone.

Paths are relative to the repository root. A key left out takes its default,
and a wiki without Config.toml uses the defaults throughout. Changing a path after the wiki has content is done by rerunning
init, which moves the files and rewrites the paths that point at them.
"""

import os
import re

from .toml import TomlError, dumps_value, loads

FILE = 'Config.toml'
PATHS = 'structural-llm-wiki-paths'        # the tables are prefixed, so Config.toml can hold other tools' tables
SETTINGS = 'structural-llm-wiki-settings'  # the skill's settings (SETTING_DEFAULTS)
TEMPLATES = 'structural-llm-wiki-templates'  # the narrative templates: default, exclude, and a [structural-llm-wiki-templates.<name>] table per template
LENGTH_KEYS = ('max_words', 'abstract_words')
TEMPLATE_KEYS = ('template', 'guide', *LENGTH_KEYS)
TEMPLATE_SETTINGS = ('default', 'exclude')  # the plain keys of [structural-llm-wiki-templates]
# Settings and their defaults; a key left out of Config.toml takes its default.
SETTING_DEFAULTS = {
    'slice_large_sources': True,  # fetch-source saves a PDF over large_source_kb one section per source instead of refusing it
    'large_source_kb': 50,        # a source above this size is large: sliced (slice_large_sources), and ingest asks before saving it
    'reasoning_marker': '[sllmwiki_reasoning]',  # marks a narrative's own reasoning (shared.md "Markers"); "" turns it off
    'gap_marker': '[sllmwiki_gap]',              # marks what the sources don't answer; "" turns it off
    'max_words': 0,        # body budget for every bundled narrative template; 0 keeps each template's own (lib/templates.py)
    'abstract_words': [],  # Abstract range [min, max] for every bundled template; [] keeps each template's own
    'max_quote_words': 50,  # the longest quotation a narrative may take from a source (lib/quotes.py)
}
# Add-ons: optional features, each with its own table [structural-llm-wiki-settings.addons.<name>]
# of settings typed like their defaults; settings(root)['addons'][<name>] holds each.
ADDON = 'addons'
ADDON_TABLES = f'{SETTINGS}.{ADDON}'  # prefix of each add-on's table
# The Obsidian add-on (lib/obsidian.py)
OBSIDIAN = 'obsidian'
OBSIDIAN_DEFAULTS = {
    'enabled': False,       # tag pages next to tags.yaml, a header of tags on each narrative, default graph settings
    'show_sources': False,  # the default graph shows sources, in grey; false hides them
    'vault': 'content',     # the folder opened in Obsidian: "content" (the folder the content path names) or "root"
}
# The book add-ons: the wiki built as a book, a release artifact. Sphinx + MyST-Parser is the
# primary build, mdBook the light one. Planned.
SPHINX = 'sphinx'
SPHINX_DEFAULTS = {
    'enabled': False,                   # build the wiki as a book with Sphinx and MyST-Parser
    'formats': ['html', 'epub', 'pdf'],  # what a build produces (BOOK_FORMATS)
}
MDBOOK = 'mdbook'
MDBOOK_DEFAULTS = {
    'enabled': False,                   # build the wiki as a book with mdBook
    'formats': ['html', 'pdf'],         # what a build produces (BOOK_FORMATS)
}
# Settings that take one of a few words
ADDON_CHOICES = {(OBSIDIAN, 'vault'): ('content', 'root')}
# The formats each book build can produce
BOOK_FORMATS = {SPHINX: ('html', 'epub', 'pdf'), MDBOOK: ('html', 'pdf')}
# The add-ons, in the order Config.toml lists them
ADDONS = {OBSIDIAN: OBSIDIAN_DEFAULTS, SPHINX: SPHINX_DEFAULTS, MDBOOK: MDBOOK_DEFAULTS}
ADDON_NAMES = {OBSIDIAN: 'Obsidian', SPHINX: 'Sphinx', MDBOOK: 'mdBook'}  # as people write them
# Settings that must stay false until their feature exists: CONFIG_INVALID otherwise. Remove an
# entry when its feature lands.
NOT_YET = {
    (SPHINX, 'enabled'): 'the Sphinx book add-on is planned, not built yet',
    (MDBOOK, 'enabled'): 'the mdBook book add-on is planned, not built yet',
}
MARKERS = ('reasoning_marker', 'gap_marker')  # settings narrative-format checks are defined in Terminology
DEFAULTS = {
    'content': '.',  # the content folder (docs/content_folder_proposal.md); the template writes NEW_WIKI_CONTENT
    'ingested': 'ingested',
    'ingested_manifest': 'ingested/manifest.yaml',
    'groomed': 'groomed',
    'groomed_manifest': 'groomed/manifest.yaml',
    'tags': 'tags/tags.yaml',  # its folder also holds the tag pages (lib/obsidian.py)
    'index': 'SLLMWIKI_INDICES.md',
    'templates': 'templates',
}
# The content folder: the knowledge (CONTENT_KEYS, written relative to it in Config.toml) and
# the Obsidian vault; the other paths are from the repository root. A Config.toml without
# `content` keeps "." (the repository root); init writes NEW_WIKI_CONTENT for a new wiki.
CONTENT = 'content'
CONTENT_KEYS = ('ingested', 'ingested_manifest', 'groomed', 'groomed_manifest', 'tags')
NEW_WIKI_CONTENT = 'sllmwiki'
FOLDERS = ('ingested', 'groomed', 'templates')
_SUFFIX = {'ingested_manifest': ('.yaml', '.yml'), 'groomed_manifest': ('.yaml', '.yml'), 'tags': ('.yaml', '.yml'), 'index': ('.md',)}


class SettingsError(Exception):
    pass


def resolve(paths):
    """Paths as Config.toml writes them (the content keys relative to the content
    folder) -> paths from the repository root."""
    content = _norm(paths.get(CONTENT, '.')) or '.'
    return {k: (f'{content}/{_norm(v)}' if k in CONTENT_KEYS and content != '.' else (_norm(v) or '.')) for k, v in paths.items()}


class Layout:
    """Where a wiki keeps its files: .paths (and an attribute per key) from the
    repository root, with /; .raw as Config.toml writes them, the content keys
    relative to the content folder (.content)."""

    def __init__(self, paths=None):
        self.raw = {**DEFAULTS, **(paths or {})}
        self.paths = resolve(self.raw)
        for key, value in self.paths.items():
            setattr(self, key, value)
        self.images = f'{self.ingested}/images'
        self.files = f'{self.ingested}/files'

    def manifest(self, kind):
        """The manifest file for kind ("ingested" or "groomed")."""
        return self.paths[f'{kind}_manifest']



def _norm(value):
    return value.replace('\\', '/').strip('/')


def path_problems(paths):
    """What's wrong with a set of path values as Config.toml writes them (already
    merged with the defaults)."""
    problems = []
    for key, value in paths.items():
        if not isinstance(value, str) or not value.strip():
            problems.append(f'{PATHS}.{key} must be a path (a non-empty string)')
            continue
        if key == CONTENT and _norm(value) in ('', '.'):
            continue  # the repository root
        parts = _norm(value).split('/')
        if os.path.isabs(value) or re.match(r'[A-Za-z]:', value):
            problems.append(f'{PATHS}.{key} = "{value}" must be relative to ' + ('the content folder' if key in CONTENT_KEYS else 'the repository root'))
        elif any(p in ('', '.', '..') for p in parts):
            problems.append(f'{PATHS}.{key} = "{value}" must not contain empty, "." or ".." parts')
        elif parts[0] in ('.git', '.github', '.claude'):
            problems.append(f'{PATHS}.{key} = "{value}" must not be inside {parts[0]}/')
        elif key in _SUFFIX and not value.endswith(_SUFFIX[key]):
            problems.append(f'{PATHS}.{key} = "{value}" must end with {" or ".join(_SUFFIX[key])}')
    if problems:
        return problems
    norm = resolve(paths)
    content = norm.get(CONTENT, '.')
    if content != '.':
        for key in (k for k in norm if k not in CONTENT_KEYS and k != CONTENT):
            if norm[key] == content or norm[key].startswith(content + '/'):
                problems.append(f'{PATHS}.{key} = "{norm[key]}" must be outside the content folder ("{content}"): it runs the wiki, it isn\'t knowledge')
    norm = {k: v for k, v in norm.items() if k != CONTENT}
    keys = list(norm)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if norm[a] == norm[b]:
                problems.append(f'{PATHS}.{a} and {PATHS}.{b} are the same path ("{norm[a]}")')
    for folder in FOLDERS:
        for other in keys:
            if other == folder or norm[other] == norm[folder]:
                continue
            inside = norm[other].startswith(norm[folder] + '/')
            own_manifest = other == f'{folder}_manifest'
            if inside and not own_manifest:
                problems.append(f'{PATHS}.{other} = "{norm[other]}" must not be inside the {folder} folder ("{norm[folder]}")')
    return problems


def read(root):
    """Config.toml parsed, or {} when the wiki has none."""
    path = os.path.join(root, FILE)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding='utf-8') as f:
            data = loads(f.read())
    except (OSError, UnicodeDecodeError) as e:
        raise SettingsError(f'{FILE}: cannot read it ({e})') from None
    except TomlError as e:
        raise SettingsError(f'{FILE}: {e}') from None
    for table in (PATHS, SETTINGS, TEMPLATES):  # other tables belong to other tools: left alone
        if table in data and not isinstance(data[table], dict):
            raise SettingsError(f'{FILE}: {table} must be a table ([{table}])')
    return data


def load_layout(root):
    """The wiki's Layout; raises SettingsError when Config.toml is broken."""
    paths = read(root).get(PATHS) or {}
    unknown = sorted(set(paths) - set(DEFAULTS))
    if unknown:
        raise SettingsError(f'{FILE}: unknown path(s) {", ".join(PATHS + "." + k for k in unknown)} (known: {", ".join(DEFAULTS)})')
    merged = {**DEFAULTS, **paths}
    problems = path_problems(merged)
    if problems:
        raise SettingsError(f'{FILE}: ' + '; '.join(problems))
    return Layout({k: _norm(v) or '.' for k, v in merged.items()})


def layout(root):
    """The wiki's Layout, or the defaults when Config.toml is broken (wiki-check
    reports CONFIG_INVALID, so the problem is never silent)."""
    try:
        return load_layout(root)
    except SettingsError:
        return Layout()


def addon_table(name):
    """An add-on's table name, such as structural-llm-wiki-settings.addons.obsidian."""
    return f'{ADDON_TABLES}.{name}'


def default_settings():
    """SETTING_DEFAULTS, with each add-on's defaults under 'addons' (ADDONS)."""
    return {**SETTING_DEFAULTS, ADDON: {name: dict(defaults) for name, defaults in ADDONS.items()}}


def _addon_tables(values):
    """Each add-on's table, from the settings table (values, changed in place:
    what is taken out of it is no longer a plain setting), as {name: table},
    {} for one Config.toml doesn't set."""
    addon = values.pop(ADDON, {})
    if not isinstance(addon, dict) or not all(isinstance(t, dict) for t in addon.values()):
        raise SettingsError(f'{FILE}: {ADDON_TABLES} holds a table per add-on, such as [{addon_table(OBSIDIAN)}]')
    unknown = sorted(set(addon) - set(ADDONS))
    if unknown:
        raise SettingsError(f'{FILE}: unknown add-on(s) {", ".join(addon_table(k) for k in unknown)} (known: {", ".join(ADDONS)})')
    return {name: addon.get(name, {}) for name in ADDONS}


def load_settings(root):
    """The skill's settings ([structural-llm-wiki-settings] over SETTING_DEFAULTS,
    and each add-on's [structural-llm-wiki-settings.addons.<name>] table over its
    defaults in ADDONS, as settings['addons'][<name>]); raises SettingsError when
    they are invalid."""
    values = dict(read(root).get(SETTINGS) or {})
    tables = {}
    for name, table in _addon_tables(values).items():
        defaults, where = ADDONS[name], addon_table(name)
        unknown = sorted(set(table) - set(defaults))
        if unknown:
            raise SettingsError(f'{FILE}: unknown setting(s) {", ".join(where + "." + k for k in unknown)} (known: {", ".join(defaults)})')
        for key, value in table.items():
            if type(value) is not type(defaults[key]):
                kind = {bool: 'true or false', list: 'a list', str: 'a string'}[type(defaults[key])]
                raise SettingsError(f'{FILE}: {where}.{key} must be {kind}')
            if (name, key) in ADDON_CHOICES and value not in ADDON_CHOICES[(name, key)]:
                raise SettingsError(f'{FILE}: {where}.{key} must be {" or ".join(map(repr, ADDON_CHOICES[(name, key)]))}, not {value!r}')
            if key == 'formats':
                choices = BOOK_FORMATS[name]
                bad = [v for v in value if v not in choices]
                if bad or not value or len(set(value)) != len(value):
                    raise SettingsError(f'{FILE}: {where}.formats must list one or more of {", ".join(choices)}, each once'
                                        + (f' (not {", ".join(map(str, bad))})' if bad else ''))
            if value is True and (name, key) in NOT_YET:
                raise SettingsError(f'{FILE}: {where}.{key} must be false for now: {NOT_YET[(name, key)]}')
        tables[name] = {**defaults, **table}
    unknown = sorted(set(values) - set(SETTING_DEFAULTS))
    if unknown:
        raise SettingsError(f'{FILE}: unknown setting(s) {", ".join(SETTINGS + "." + k for k in unknown)} (known: {", ".join(SETTING_DEFAULTS)})')
    for key, value in values.items():
        if type(value) is not type(SETTING_DEFAULTS[key]):
            raise SettingsError(f'{FILE}: {SETTINGS}.{key} must be {type(SETTING_DEFAULTS[key]).__name__.replace("bool", "true or false").replace("str", "a string").replace("int", "a whole number").replace("list", "a list")}')
    merged = {**SETTING_DEFAULTS, **values}
    for key in MARKERS:
        value = merged[key]
        if value != value.strip() or '\n' in value or '\r' in value:
            raise SettingsError(f'{FILE}: {SETTINGS}.{key} must be one line with no leading or trailing spaces, or "" for no marker')
    for key in ('large_source_kb', 'max_quote_words'):
        if merged[key] < 1:
            raise SettingsError(f'{FILE}: {SETTINGS}.{key} must be a positive whole number')
    if merged['max_words'] < 0:
        raise SettingsError(f'{FILE}: {SETTINGS}.max_words must be 0 (each template\'s own budget) or a positive whole number')
    words = merged['abstract_words']
    if words and not (len(words) == 2 and all(type(w) is int and w > 0 for w in words) and words[0] <= words[1]):
        raise SettingsError(f'{FILE}: {SETTINGS}.abstract_words must be [] (each template\'s own range) or [min, max], two positive whole numbers with min <= max')
    if merged['reasoning_marker'] and merged['reasoning_marker'] == merged['gap_marker']:
        raise SettingsError(f'{FILE}: {SETTINGS}.reasoning_marker and gap_marker must differ, so a reader can tell them apart')
    merged[ADDON] = tables
    return merged


def _lengths_problem(where, key, value):
    if key == 'max_words':
        if type(value) is not int or value < 1:
            return f'{where}.max_words must be a positive whole number (the body\'s word budget)'
    elif not (type(value) is list and len(value) == 2 and all(type(w) is int and w > 0 for w in value) and value[0] <= value[1]):
        return f'{where}.abstract_words must be [min, max], two positive whole numbers with min <= max'
    return None


_TEMPLATE_NAME = re.compile(r'[a-z0-9][a-z0-9_-]*\Z')


def load_templates_config(root):
    """[structural-llm-wiki-templates] (which narrative templates the wiki
    offers, and its own) as {default, exclude, templates: {name: {template,
    guide, max_words, abstract_words}}}, each key present only when set;
    template and guide are paths from the repository root. Raises
    SettingsError when it is invalid. Whether a name is a template, and
    whether its files exist, is checked by lib/templates.py."""
    table = read(root).get(TEMPLATES) or {}
    default, exclude = table.get('default'), table.get('exclude', [])
    if default is not None and (not isinstance(default, str) or not default):
        raise SettingsError(f'{FILE}: {TEMPLATES}.default must be a template name')
    if not isinstance(exclude, list) or not all(isinstance(x, str) for x in exclude):
        raise SettingsError(f'{FILE}: {TEMPLATES}.exclude must be a list of template names')
    entries = {}
    for name, spec in table.items():
        if name in TEMPLATE_SETTINGS:
            continue
        where = f'{FILE}: [{TEMPLATES}.{name}]'
        if not isinstance(spec, dict):
            raise SettingsError(f'{FILE}: {TEMPLATES}.{name} must be a table ([{TEMPLATES}.{name}]); the only plain keys are {" and ".join(TEMPLATE_SETTINGS)}')
        if not _TEMPLATE_NAME.match(name):
            raise SettingsError(f'{where}: "{name}" is not a valid template name (lowercase letters, digits, _ and -)')
        unknown = sorted(set(spec) - set(TEMPLATE_KEYS))
        if unknown:
            raise SettingsError(f'{where}: unknown key(s) {", ".join(unknown)} (known: {", ".join(TEMPLATE_KEYS)})')
        entry = {}
        for key, value in spec.items():
            if key in LENGTH_KEYS:
                problem = _lengths_problem(f'{FILE}: {TEMPLATES}.{name}', key, value)
                if problem:
                    raise SettingsError(problem)
                entry[key] = value
                continue
            if not isinstance(value, str) or not value.strip():
                raise SettingsError(f'{where}: {key} must be a path to the file, from the repository root')
            parts = _norm(value).split('/')
            if os.path.isabs(value) or re.match(r'[A-Za-z]:', value) or any(x in ('', '.', '..') for x in parts):
                raise SettingsError(f'{where}: {key} = "{value}" must be a path inside the repository, from its root')
            entry[key] = _norm(value)
        entries[name] = entry
    return {'default': default, 'exclude': list(exclude), 'templates': entries}


def templates_config(root):
    """load_templates_config, or no configuration when Config.toml is broken
    (wiki-check reports CONFIG_INVALID, so the problem is never silent)."""
    try:
        return load_templates_config(root)
    except SettingsError:
        return {'default': None, 'exclude': [], 'templates': {}}


def settings(root):
    """The skill's settings, or the defaults when Config.toml is broken
    (wiki-check reports CONFIG_INVALID, so the problem is never silent)."""
    try:
        return load_settings(root)
    except SettingsError:
        return default_settings()


def problems(root):
    """Everything wrong with Config.toml (its paths and settings), as a list of messages."""
    out = []
    for load in (load_layout, load_settings, load_templates_config):
        try:
            load(root)
        except SettingsError as e:
            if str(e) not in out:
                out.append(str(e))
    return out


TEMPLATE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'templates', 'wiki', FILE))


def render(paths=None):
    """A new Config.toml: the template with these path values (the
    defaults for any left out)."""
    with open(TEMPLATE, encoding='utf-8') as f:
        text = f.read()
    merged = {**DEFAULTS, CONTENT: NEW_WIKI_CONTENT, **(paths or {})}
    for key in DEFAULTS:
        text = text.replace('{{' + key + '}}', dumps_value(merged[key]))
    return text.replace('{{templates_dir}}', _norm(merged['templates']))  # inside the template tables' path strings


def add_templates_notes(text, templates_dir='templates'):
    """text (a Config.toml) with the template's [structural-llm-wiki-templates]
    section, its notes on default, exclude and per-template tables (no
    values), added when the file has no such table: before its first
    [structural-llm-wiki-templates.<name>] table, else at the end. Returns
    (text, True when it added them)."""
    lines = text.rstrip('\n').split('\n')
    header = re.compile(r'\s*\[' + re.escape(TEMPLATES) + r'\]\s*(#.*)?$')
    if any(header.match(line) for line in lines):
        return text, False
    with open(TEMPLATE, encoding='utf-8') as f:
        template = f.read().replace('{{templates_dir}}', _norm(templates_dir)).split('\n')
    start = next(n for n, line in enumerate(template) if line.startswith('# Narrative templates:'))
    end = next(n for n, line in enumerate(template) if line.startswith("# A template of this wiki's own"))
    block = template[start:end]
    while block and not block[-1].strip():
        block.pop()
    sub = re.compile(r'\s*\[' + re.escape(TEMPLATES) + r'\.')
    at = next((n for n, line in enumerate(lines) if sub.match(line)), None)
    if at is None:
        return '\n'.join(lines + [''] + block) + '\n', True
    while at > 0 and lines[at - 1].strip().startswith('#'):  # keep a table's own comment with it
        at -= 1
    return '\n'.join(lines[:at] + block + [''] + lines[at:]) + '\n', True


def add_missing_settings(text):
    """text (a Config.toml) with every skill setting it lacks added to
    [structural-llm-wiki-settings] at its default, with the template's notes
    (the comment lines above it and its trailing comment), so an older wiki
    learns what each new setting does. Returns (text, the keys added); a
    file that doesn't parse is returned unchanged."""
    try:
        have = loads(text).get(SETTINGS)
    except TomlError:
        return text, []
    have = have if isinstance(have, dict) else {}
    missing = [k for k in SETTING_DEFAULTS if k not in have]
    if not missing:
        return text, []
    with open(TEMPLATE, encoding='utf-8') as f:
        template = f.read().split('\n')
    start = next(n for n, line in enumerate(template) if line.strip() == f'[{SETTINGS}]')
    notes, block = [], []
    for line in template[start + 1:]:
        if line.startswith('['):
            break
        if line.startswith('#'):
            notes.append(line)
            continue
        key = line.split('=', 1)[0].strip()
        if key in missing:
            block += notes + [line]
        notes = []
    lines = text.rstrip('\n').split('\n')
    at = next((n for n, line in enumerate(lines) if re.match(r'\s*\[' + re.escape(SETTINGS) + r'\]\s*(#.*)?$', line)), None)
    if at is None:
        body = '\n'.join(lines).rstrip('\n')
        return (body + '\n\n' if body else '') + f'# Settings for the sllmwiki skill.\n[{SETTINGS}]\n' + '\n'.join(block) + '\n', missing
    end = next((n for n in range(at + 1, len(lines)) if re.match(r'\s*\[', lines[n])), len(lines))
    if end < len(lines):  # comments right above the next table are its notes: add before them
        while end > at + 1 and lines[end - 1].strip().startswith('#'):
            end -= 1
    while end > at + 1 and lines[end - 1].strip() == '':
        end -= 1
    lines[end:end] = block
    return '\n'.join(lines) + '\n', missing


def history(root):
    """The paths the last 20 commits of Config.toml set, newest first, from the
    repository root (each commit's content keys resolved through its own content
    folder; "." when it had none): what init moves files from when a path
    changes."""
    import subprocess
    out = []
    log = subprocess.run(['git', '-C', root, 'log', '-n20', '--format=%H', '--', FILE], capture_output=True, text=True)
    for commit in log.stdout.split() if log.returncode == 0 else []:
        show = subprocess.run(['git', '-C', root, 'show', f'{commit}:{FILE}'], capture_output=True, text=True)
        try:
            paths = loads(show.stdout).get(PATHS) if show.returncode == 0 else None
        except TomlError:
            paths = None
        if isinstance(paths, dict):
            known = {k: v for k, v in paths.items() if k in DEFAULTS and isinstance(v, str)}
            out.append({CONTENT: '.', **resolve(known)})  # with the content folder it had ("." when none)
    return out


def _settings_end(lines):
    """Where text after the settings tables goes: the line after the last
    [structural-llm-wiki-settings] or [structural-llm-wiki-settings.<name>]
    table, before the next table's notes; None when there is none."""
    own = re.compile(r'\s*\[' + re.escape(SETTINGS) + r'(\.[^\]]+)?\]\s*(#.*)?$')
    last = next((n for n in range(len(lines) - 1, -1, -1) if own.match(lines[n])), None)
    if last is None:
        return None
    end = next((n for n in range(last + 1, len(lines)) if re.match(r'\s*\[', lines[n])), len(lines))
    if end < len(lines):  # comments right above the next table are its notes: add before them
        while end > last + 1 and lines[end - 1].strip().startswith('#'):
            end -= 1
    while end > last + 1 and lines[end - 1].strip() == '':
        end -= 1
    return end


def _template_table(template, name):
    """The template's [structural-llm-wiki-settings.addons.<name>] table with the notes
    above it, as lines."""
    head = next(n for n, line in enumerate(template) if line.strip() == f'[{addon_table(name)}]')
    start, stop = head, head + 1
    while start > 0 and template[start - 1].startswith('#'):
        start -= 1
    while stop < len(template) and template[stop].strip() and not template[stop].startswith('['):
        stop += 1
    return template[start:stop]


def add_addon_tables(text):
    """text (a Config.toml) with every add-on table (ADDONS) the template has, at
    [structural-llm-wiki-settings.addons.<name>]: a missing one added after the
    settings tables with its notes, a missing key added to one that exists with
    its comment. Returns (text, [(add-on, 'added' or 'completed' (keys added to
    its table))]); a file that doesn't parse is returned unchanged."""
    try:
        data = loads(text)
    except TomlError:
        return text, []
    settings = data.get(SETTINGS) if isinstance(data.get(SETTINGS), dict) else {}
    addon = settings.get(ADDON) if isinstance(settings.get(ADDON), dict) else {}
    lines = text.rstrip('\n').split('\n')
    with open(TEMPLATE, encoding='utf-8') as f:
        template = f.read().split('\n')
    changes = []
    for name, defaults in ADDONS.items():
        table = addon.get(name) if isinstance(addon.get(name), dict) else None
        if table is not None:
            missing = [k for k in defaults if k not in table]
            if missing:  # the template's line for each, with its comment, at the end of the table
                block = {re.match(r'\s*(\w+)', line).group(1): line for line in _template_table(template, name)
                         if re.match(r'\s*\w+\s*=', line)}
                own = re.compile(r'\s*\[' + re.escape(addon_table(name)) + r'\]\s*(#.*)?$')  # a comment after the header is fine
                head = next(n for n, line in enumerate(lines) if own.match(line))
                end = next((n for n in range(head + 1, len(lines)) if re.match(r'\s*\[', lines[n])), len(lines))
                while end > head + 1 and (not lines[end - 1].strip() or lines[end - 1].lstrip().startswith('#')):
                    end -= 1
                lines[end:end] = [block.get(k) or f'{k} = {dumps_value(defaults[k])}' for k in missing]
                changes.append((name, 'completed'))  # the table was there: only keys were added
            continue
        block = _template_table(template, name)
        end = _settings_end(lines)
        if end is None:
            lines += [''] + block if any(x.strip() for x in lines) else block
        else:
            lines[end:end] = [''] + block
        changes.append((name, 'added'))
    return '\n'.join(lines) + '\n', changes
