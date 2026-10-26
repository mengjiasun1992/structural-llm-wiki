"""The narrative templates (design doc §4.5): the bundled ones and the wiki's own,
each a folder with template.md and guide.md.

template.md starts with a YAML header (description, use_when, max_words,
abstract_words) and holds the template's body sections. The skeleton a
narrative follows is shared-skeleton.md with the body put where it says
<!-- sllmwiki:body -->, and the skeleton is the schema: its ## headings are the
required sections, in order; a heading ending in "(optional)" may be left out;
<...> in a heading matches any text; a section holding a ```mermaid block
needs a diagram. A wiki's own template in sllmwiki/templates/<name>/ is offered next to
the bundled ones, and one with a bundled template's name replaces it.
Config.toml's [structural-llm-wiki-templates.<name>] tables set budgets over a
template's header.
"""

import os
import re
import shutil

from . import config, language, layout, numbering, wikiyaml
from .util import read_text

BUNDLED = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'templates', 'narratives'))
SHARED_SKELETON = os.path.join(BUNDLED, 'shared-skeleton.md')
BODY_MARK = '<!-- sllmwiki:body -->'
GUIDE_SECTIONS = ('Audience and purpose', 'Voice and tone', 'Structure', 'Evidence', 'Length', 'Checklist')
HEADER_KEYS = ('description', 'use_when', 'max_words', 'abstract_words')
OPTIONAL = re.compile(r'\s*\(optional\)\s*\Z', re.I)
NAME = re.compile(r'[a-z0-9][a-z0-9_-]*\Z')  # as Config.toml's [structural-llm-wiki-templates.<name>]


class TemplateError(Exception):
    pass


def _pattern(title):
    parts = re.split(r'<[^>]*>', title)
    return re.compile(r'\s*' + '.+?'.join(re.escape(p.strip()) if p.strip() else '' for p in parts) + r'\s*\Z', re.I)


class Section:
    """A required (or optional) ## section: its title as written, the patterns its title must match
    (the English title's, and each language pack's translation's), and whether it needs a diagram."""

    def __init__(self, title, optional, diagram):
        self.title, self.optional, self.diagram = title, optional, diagram
        self.patterns = [_pattern(t) for t in language.names(title)]

    def matches(self, title):
        return any(p.match(title) for p in self.patterns)

    def matches_english(self, title):
        return bool(self.patterns[0].match(title))


class Template:
    def __init__(self, name, folder, source):
        self.name, self.folder, self.source = name, folder, source
        text = read_text(os.path.join(folder, 'template.md'))
        m = re.match(r'---\n(.*?)\n---\n', text, re.S)
        if not m:
            raise TemplateError(f'{name}: template.md must start with a --- header ---')
        try:
            header = wikiyaml.parse(m.group(1))
        except wikiyaml.YamlError as e:
            raise TemplateError(f'{name}: its header: {e}') from None
        missing = [k for k in HEADER_KEYS if k not in header]
        unknown = [k for k in header if k not in HEADER_KEYS]
        if missing or unknown:
            raise TemplateError(f'{name}: its header needs exactly {", ".join(HEADER_KEYS)}'
                                + (f'; missing {", ".join(missing)}' if missing else '') + (f'; unknown {", ".join(unknown)}' if unknown else ''))
        self.description, self.use_when = header['description'], header['use_when']
        self.max_words, self.abstract_words = header['max_words'], header['abstract_words']
        if not (isinstance(self.max_words, int) and self.max_words > 0 and isinstance(self.abstract_words, list) and len(self.abstract_words) == 2
                and all(isinstance(v, int) and v > 0 for v in self.abstract_words) and self.abstract_words[0] <= self.abstract_words[1]):
            raise TemplateError(f'{name}: max_words must be a positive whole number and abstract_words [min, max]')
        self.body = text[m.end():].strip('\n') + '\n'
        self.guide = os.path.join(folder, 'guide.md')
        if not os.path.isfile(self.guide):
            raise TemplateError(f'{name}: no guide.md next to its template.md')
        guide = read_text(self.guide)
        heads = [h.title for h in numbering.headings(guide) if h.level == 2]
        missing = [s for s in GUIDE_SECTIONS if s not in heads]
        if missing:
            raise TemplateError(f'{name}: guide.md needs the sections {", ".join(GUIDE_SECTIONS)}; missing {", ".join(missing)}')
        self.takeaway, self.aim = _purpose(name, guide)
        _check_body(name, self.body)

    def skeleton(self, tag=None):
        """The narrative's skeleton: the shared top, this template's body, the shared appendices, numbered;
        with a language tag, written for that language (its pack's headings and labels, and its Metadata field)."""
        shared = read_text(SHARED_SKELETON)
        top, bottom = shared.split(BODY_MARK)
        text = top.rstrip('\n') + '\n\n' + self.body.strip('\n') + '\n\n' + bottom.lstrip('\n')
        text = text.replace('<template name>', self.name).replace('<language>', tag or language.DEFAULT)
        text = numbering.renumber(text)[0]
        return language.translate(text, language.pack(tag) or language.ENGLISH) if tag else text

    def sections(self):
        """The ## sections, in order, from the skeleton."""
        skel = self.skeleton()
        lines = skel.split('\n')
        heads = [h for h in numbering.headings(skel) if h.level == 2]
        out = []
        for i, h in enumerate(heads):
            end = heads[i + 1].line if i + 1 < len(heads) else len(lines)
            diagram = any(line.strip().startswith('```mermaid') for line in lines[h.line:end])
            out.append(Section(OPTIONAL.sub('', h.title), bool(OPTIONAL.search(h.title)), diagram))
        return out


def _purpose(name, guide):
    """(takeaway, [aim's axes]) from the guide's Audience and purpose: the **Takeaway:** line and the
    **Aim:** line, whose axes, before its first period, lint grades every narrative on (steps/lint.md)."""
    span = numbering.section(guide, 'Audience and purpose')
    text = '\n'.join(guide.split('\n')[span[0]:span[1]])
    take = re.search(r'^\*\*Takeaway:\*\*[ \t]*(.+)$', text, re.M)
    aim = re.search(r'^\*\*Aim:\*\*[ \t]*([^.\n]+)', text, re.M)
    if not take or not aim:
        raise TemplateError(f'{name}: guide.md\'s Audience and purpose needs a **Takeaway:** line (what the reader takes away) and an '
                            '**Aim:** line (the axes lint grades each narrative on, then what each means), as the bundled guides have')
    axes = [re.sub(r'^with\s+', '', a.strip()) for a in re.split(r'[,;]', aim.group(1)) if a.strip()]
    return take.group(1).strip(), axes


def _check_body(name, body):
    """The body's sections: at least one ##, none repeating a section every narrative already has, and each
    with a <...> line saying what goes there."""
    lines = body.split('\n')
    heads = [h for h in numbering.headings(body) if h.level == 2]
    if not heads:
        raise TemplateError(f'{name}: template.md\'s body needs at least one ## section, the parts every answer of this kind has')
    shared = [h.title for h in numbering.headings(read_text(SHARED_SKELETON).replace(BODY_MARK, '')) if h.level == 2]
    shared = {n.lower() for t in shared for n in language.names(OPTIONAL.sub('', t))}
    for i, h in enumerate(heads):
        title = OPTIONAL.sub('', h.title)
        if title.lower() in shared:
            raise TemplateError(f'{name}: template.md\'s body repeats "{title}", which every narrative already has; leave it out')
        end = heads[i + 1].line if i + 1 < len(heads) else len(lines)
        if not re.search(r'<[^<>\n]+>', '\n'.join(lines[h.line + 1:end])):
            raise TemplateError(f'{name}: template.md\'s section "{title}" needs a <...> line saying what goes there')


def untranslated(template, pack):
    """The template's section titles pack doesn't translate (its narratives keep them in English)."""
    titles = [OPTIONAL.sub('', h.title) for h in numbering.headings(template.body) if h.level == 2 and '<' not in h.title]
    return [t for t in titles if not pack.strings.get(t)]


def _folders(base):
    if not os.path.isdir(base):
        return {}
    return {n: os.path.join(base, n) for n in sorted(os.listdir(base)) if os.path.isfile(os.path.join(base, n, 'template.md'))}


def available(root):
    """({name: Template}, [problems]): the bundled templates, then the wiki's own
    (replacing a bundled one of the same name), with Config.toml's budgets applied.
    A template that doesn't load is a problem, not a template."""
    found, problems = {}, []
    for source, base in (('bundled', BUNDLED), ('wiki', os.path.join(root, layout.TEMPLATES))):
        for name, folder in _folders(base).items():
            try:
                found[name] = Template(name, folder, source)
            except TemplateError as e:
                problems.append(f'{source} template {e}')
    for name, lengths in config.get(root).templates.items():
        if name not in found:
            problems.append(f'Config.toml sets budgets for [structural-llm-wiki-templates.{name}], but there\'s no template {name}')
            continue
        found[name].max_words = lengths.get('max_words', found[name].max_words)
        found[name].abstract_words = lengths.get('abstract_words', found[name].abstract_words)
    return found, problems


def get(root, name):
    """The template called name; raises TemplateError naming the ones there are."""
    found, _ = available(root)
    if name not in found:
        raise TemplateError(f'no template {name}; there are {", ".join(sorted(found))}')
    return found[name]


def create(root, name, base):
    """Start the wiki's own template name from base (a template it offers, bundled or its own), as a copy of
    its template.md and guide.md in sllmwiki/templates/<name>/; the folder. Named like a bundled template, it replaces
    it. Raises TemplateError when the name is taken or not a template's, or base isn't offered."""
    if not NAME.match(name):
        raise TemplateError(f'{name}: a template\'s name is lowercase letters, digits, _ and -')
    folder = os.path.join(root, layout.TEMPLATES, name)
    if os.path.exists(folder):
        raise TemplateError(f'{layout.TEMPLATES}/{name} already exists: edit it there')
    source = get(root, base).folder
    os.makedirs(folder)
    for f in ('template.md', 'guide.md'):
        shutil.copyfile(os.path.join(source, f), os.path.join(folder, f))
    return folder
