"""The narrative templates (design doc §4.5): the bundled ones and the wiki's own,
each a folder with template.md and guide.md.

template.md starts with a YAML header (description, use_when, max_words,
abstract_words) and holds the template's body sections. The skeleton a
narrative follows is shared-skeleton.md with the body put where it says
<!-- sllmwiki:body -->, and the skeleton is the schema: its ## headings are the
required sections, in order; a heading ending in "(optional)" may be left out;
<...> in a heading matches any text; a section holding a ```mermaid block
needs a diagram. A wiki's own template in templates/<name>/ is offered next to
the bundled ones, and one with a bundled template's name replaces it.
Config.toml's [structural-llm-wiki-templates.<name>] tables set budgets over a
template's header.
"""

import os
import re

from . import config, layout, numbering, wikiyaml
from .util import read_text

BUNDLED = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'templates', 'narratives'))
SHARED_SKELETON = os.path.join(BUNDLED, 'shared-skeleton.md')
BODY_MARK = '<!-- sllmwiki:body -->'
GUIDE_SECTIONS = ('Audience and purpose', 'Voice and tone', 'Structure', 'Evidence', 'Length', 'Checklist')
HEADER_KEYS = ('description', 'use_when', 'max_words', 'abstract_words')
OPTIONAL = re.compile(r'\s*\(optional\)\s*\Z', re.I)


class TemplateError(Exception):
    pass


class Section:
    """A required (or optional) ## section: its title as written, a pattern its title must match, and whether it needs a diagram."""

    def __init__(self, title, optional, diagram):
        self.title, self.optional, self.diagram = title, optional, diagram
        parts = re.split(r'<[^>]*>', title)
        self.pattern = re.compile(r'\s*' + '.+?'.join(re.escape(p.strip()) if p.strip() else '' for p in parts) + r'\s*\Z', re.I)

    def matches(self, title):
        return bool(self.pattern.match(title))


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
        heads = [h.title for h in numbering.headings(read_text(self.guide)) if h.level == 2]
        missing = [s for s in GUIDE_SECTIONS if s not in heads]
        if missing:
            raise TemplateError(f'{name}: guide.md needs the sections {", ".join(GUIDE_SECTIONS)}; missing {", ".join(missing)}')

    def skeleton(self):
        """The narrative's skeleton: the shared top, this template's body, the shared appendices, numbered."""
        shared = read_text(SHARED_SKELETON)
        top, bottom = shared.split(BODY_MARK)
        text = top.rstrip('\n') + '\n\n' + self.body.strip('\n') + '\n\n' + bottom.lstrip('\n')
        text = text.replace('<template name>', self.name)
        return numbering.renumber(text)[0]

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
