"""A wiki's settings and add-ons: the optional sllmwiki/Config.toml (design doc §4.9).

    [structural-llm-wiki-settings]
    source_copies = "allow"     # or "links-only"
    max_quote_words = 50
    smes_exclude = []
    markers = true
    images = true
    language = "en"

    [structural-llm-wiki-templates.technical_brief_overview]
    max_words = 3000
    abstract_words = [150, 300]

    [structural-llm-wiki-addons]
    obsidian = false

    [structural-llm-wiki-release]
    pdf_book = true
    epub_book = false
    html_book = false
    title = ""
    author = ""

Every setting has a default, so the file is optional. Tables whose names don't
start with structural-llm-wiki- belong to other tools and are left alone; a
problem in ours makes load() raise ConfigError, which wiki-check reports as
CONFIG_INVALID and the scripts that write refuse to run on. Whether a template
named here exists is lib/templates.py's to check.
"""

import difflib
import os
import re

from .layout import CONFIG, config_path
from .toml import TomlError, loads
from .util import read_text

PREFIX = 'structural-llm-wiki-'
SETTINGS = PREFIX + 'settings'
TEMPLATES = PREFIX + 'templates'
ADDONS = PREFIX + 'addons'
RELEASE = PREFIX + 'release'

DEFAULTS = {
    'source_copies': 'allow',  # "allow": private wikis keep copies, public ones only openly licensed; "links-only": none
    'max_quote_words': 50,     # the longest quotation a narrative may take from a source
    'smes_exclude': [],        # people and bots never listed as SMEs
    'markers': True,           # the [→] and [?] markers (design doc §4.10)
    'images': True,            # generated figures in narratives/figures/, where mermaid can't show an idea well (design doc §4.5)
    'language': 'en',          # the language narratives are written in, a BCP 47 tag; sources keep their own (lib/language.py)
}
SOURCE_COPIES = ('allow', 'links-only')
TEMPLATE_KEYS = ('max_words', 'abstract_words')
ADDON_DEFAULTS = {
    'obsidian': False,  # init writes sllmwiki/.obsidian/graph.json (design doc §4.8)
}
RELEASE_DEFAULTS = {  # what a release attaches (docs/book_design.md §3)
    'pdf_book': True,    # a PDF: share, print, read anywhere
    'epub_book': False,  # an EPUB: e-readers and phones
    'html_book': False,  # one self-contained HTML file, for a browser
    'title': '',         # the book's title; empty: the repository's name
    'author': '',        # its author; empty: the title
}
_TEMPLATE_NAME = re.compile(r'[a-z0-9][a-z0-9_-]*\Z')
_LANGUAGE = re.compile(r'[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*\Z')  # as lib/language.py's TAG


class ConfigError(Exception):
    def __init__(self, problems):
        super().__init__('; '.join(problems))
        self.problems = problems


class Config:
    """settings: DEFAULTS merged with the file; templates: {name: {max_words, abstract_words}}
    for the keys the file sets; addons: ADDON_DEFAULTS merged with the file; release:
    RELEASE_DEFAULTS merged with the file."""

    def __init__(self, settings=None, templates=None, addons=None, release=None):
        self.settings = {**DEFAULTS, **(settings or {})}
        self.templates = templates or {}
        self.addons = {**ADDON_DEFAULTS, **(addons or {})}
        self.release = {**RELEASE_DEFAULTS, **(release or {})}

    def book_formats(self):
        """The formats a release builds: 'html' for html_book, and so on."""
        return [key[:-len('_book')] for key, on in self.release.items() if key.endswith('_book') and on]


def _hint(key, known):
    near = difflib.get_close_matches(key, known, n=1)
    return f' (did you mean {near[0]}?)' if near else f' (known: {", ".join(known)})'


def _kind(value):
    return {bool: 'true or false', int: 'a whole number', str: 'a string', list: 'a list', dict: 'a table'}[type(value)]


def _settings(table, problems):
    out = {}
    for key, value in table.items():
        where = f'{SETTINGS}.{key}'
        if key not in DEFAULTS:
            problems.append(f'unknown setting {where}{_hint(key, list(DEFAULTS))}')
        elif type(value) is not type(DEFAULTS[key]):
            problems.append(f'{where} must be {_kind(DEFAULTS[key])}')
        elif key == 'source_copies' and value not in SOURCE_COPIES:
            problems.append(f'{where} must be "allow" or "links-only", not {value!r}')
        elif key == 'max_quote_words' and value < 1:
            problems.append(f'{where} must be a positive whole number')
        elif key == 'language' and not _LANGUAGE.match(value):
            problems.append(f'{where} must be a language tag, such as "en" or "zh-Hans", not {value!r}')
        elif key == 'smes_exclude' and not all(isinstance(v, str) and v.strip() for v in value):
            problems.append(f'{where} must list names, such as ["@alice", "dependabot"]')
        else:
            out[key] = value
    return out


def _templates(table, problems):
    out = {}
    for name, keys in table.items():
        where = f'[{TEMPLATES}.{name}]'
        if not isinstance(keys, dict):
            problems.append(f'{TEMPLATES}.{name} must be a table, {where}, with a template\'s max_words and abstract_words')
            continue
        if not _TEMPLATE_NAME.match(name):
            problems.append(f'{where}: a template name is lowercase letters, digits, _ and -')
            continue
        lengths = {}
        for key, value in keys.items():
            if key not in TEMPLATE_KEYS:
                problems.append(f'unknown key {key} in {where}{_hint(key, list(TEMPLATE_KEYS))}')
            elif key == 'max_words' and not (type(value) is int and value > 0):
                problems.append(f'{where} max_words must be a positive whole number')
            elif key == 'abstract_words' and not (isinstance(value, list) and len(value) == 2 and all(type(v) is int and v > 0 for v in value)
                                                  and value[0] <= value[1]):
                problems.append(f'{where} abstract_words must be [min, max], two positive whole numbers with min <= max')
            else:
                lengths[key] = value
        out[name] = lengths
    return out


def _addons(table, problems):
    out = {}
    for name, value in table.items():
        if name not in ADDON_DEFAULTS:
            problems.append(f'unknown add-on {ADDONS}.{name}{_hint(name, list(ADDON_DEFAULTS))}')
        elif type(value) is not bool:
            problems.append(f'{ADDONS}.{name} must be true or false')
        else:
            out[name] = value
    return out


def _release(table, problems):
    out = {}
    for key, value in table.items():
        if key not in RELEASE_DEFAULTS:
            problems.append(f'unknown setting {RELEASE}.{key}{_hint(key, list(RELEASE_DEFAULTS))}')
        elif type(value) is not type(RELEASE_DEFAULTS[key]):
            problems.append(f'{RELEASE}.{key} must be {_kind(RELEASE_DEFAULTS[key])}')
        else:
            out[key] = value
    return out


def parse(text):
    """The Config for a Config.toml's text; raises ConfigError listing every problem."""
    try:
        data = loads(text)
    except TomlError as e:
        raise ConfigError([f'{CONFIG}: {e}']) from None
    problems = []
    parts = {}
    readers = {SETTINGS: _settings, TEMPLATES: _templates, ADDONS: _addons, RELEASE: _release}
    for name, table in data.items():
        if not name.startswith(PREFIX):
            continue  # another tool's table
        if name not in readers:
            problems.append(f'[{name}] isn\'t a table this version reads{_hint(name, list(readers))}; the layout is fixed (design doc §3)')
        elif not isinstance(table, dict):
            problems.append(f'{name} must be a table, [{name}]')
        else:
            parts[name] = readers[name](table, problems)
    if problems:
        raise ConfigError([f'{CONFIG}: {p}' for p in problems])
    return Config(parts.get(SETTINGS), parts.get(TEMPLATES), parts.get(ADDONS), parts.get(RELEASE))


def load(root):
    """The wiki's Config (the defaults without a Config.toml); raises ConfigError."""
    path = config_path(root)
    return parse(read_text(path)) if os.path.isfile(path) else Config()


def problems(root):
    """The problems in the wiki's Config.toml, [] when it is valid or absent."""
    try:
        load(root)
    except ConfigError as e:
        return e.problems
    return []


def get(root):
    """The wiki's Config, or the defaults when Config.toml is invalid: for scripts
    that only read, so a broken file doesn't stop a check (wiki-check reports it)."""
    try:
        return load(root)
    except ConfigError:
        return Config()
