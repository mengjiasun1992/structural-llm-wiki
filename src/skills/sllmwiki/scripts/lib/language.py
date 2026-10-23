"""The language a narrative is written in (design doc §4.9), and the language
pack that translates its headings and the few labels the scripts write.

A wiki's language is Config.toml's `language` ("en" by default); a narrative
may name its own in its Metadata, `- **Language:** zh-Hans`. Sources keep the
language they were written in. A pack is templates/languages/<tag>.md, bundled
or the wiki's own (which replaces a bundled one): a # heading naming the
language, then a table of the English text as the skeleton, the templates and
the scripts write it, and its translation.

    # 简体中文

    | English | Translation |
    |---|---|
    | Abstract | 摘要 |

A row left out, or left blank, stays English. Metadata's field names and values
are never translated, so the scripts read them the same in every language. A
language with no pack keeps English headings around prose in its language.

Sections are found by their English title or any loaded pack's translation of
it, so the scripts that look one up need no language; check_language() is
what holds a narrative to its own pack.
"""

import os
import re

from .layout import TEMPLATES
from .util import read_text

BUNDLED = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'templates', 'languages'))
FOLDER = 'languages'  # under the wiki's templates/
DEFAULT = 'en'
TAG = re.compile(r'[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*\Z')
FIELD = re.compile(r'^- \*\*Language:\*\*[ \t]*(\S+)[ \t]*$', re.M)
# Han, kana and the CJK punctuation and full-width forms: scripts written without spaces between words
CJK = re.compile(r'[　-〿぀-ヿ㐀-䶿一-鿿豈-﫿＀-￯]')
CJK_CHARACTERS_PER_WORD = 1.6  # a budget in words, read in characters: about 1.6 Chinese or Japanese characters to an English word
SENTENCE_END = '.!?。！？'
_RULE = re.compile(r'\|?[-: |]+\|?\Z')
_ROW = re.compile(r'\|(?P<english>(?:[^|\\]|\\.)*)\|(?P<translation>(?:[^|\\]|\\.)*)\|\s*\Z')


class Pack:
    def __init__(self, tag, name, strings, source):
        self.tag, self.name, self.strings, self.source = tag, name, strings, source

    def t(self, english):
        """english in this language: its translation, or english when the pack has none."""
        return self.strings.get(english) or english


ENGLISH = Pack(DEFAULT, 'English', {}, 'bundled')
_loaded = {}  # tag (lowercase) -> Pack: the bundled packs, then the wiki's


def parse(tag, text, source):
    """The Pack in a pack file's text; raises ValueError naming the first problem."""
    lines = text.split('\n')
    name = next((line[2:].strip() for line in lines if line.startswith('# ')), None)
    if not name:
        raise ValueError(f'{tag}.md: start it with a # heading naming the language')
    strings = {}
    for n, line in enumerate(lines, 1):
        if not line.lstrip().startswith('|') or _RULE.match(line.strip()) or (n < len(lines) and _RULE.match(lines[n].strip())):
            continue  # a table's rule, or the header row above it
        m = _ROW.match(line.strip())
        if not m:
            raise ValueError(f'{tag}.md:{n}: a row is | English | Translation |')
        english, translation = (m.group(g).strip().replace('\\|', '|') for g in ('english', 'translation'))
        if english in strings:
            raise ValueError(f'{tag}.md:{n}: "{english}" is translated twice')
        strings[english] = translation
    return Pack(tag, name, strings, source)


def _read(base, source):
    out = {}
    if os.path.isdir(base):
        for f in sorted(os.listdir(base)):
            tag, ext = os.path.splitext(f)
            if ext == '.md' and TAG.match(tag):
                out[tag.lower()] = parse(tag, read_text(os.path.join(base, f)), source)
    return out


def use(root):
    """Load the bundled packs and the wiki's own; [problems] for a wiki pack that doesn't parse."""
    _loaded.clear()
    _loaded.update(_read(BUNDLED, 'bundled'))
    problems = []
    base = os.path.join(root, TEMPLATES, FOLDER)
    if os.path.isdir(base):
        for f in sorted(os.listdir(base)):
            tag, ext = os.path.splitext(f)
            if ext != '.md':
                continue
            if not TAG.match(tag):
                problems.append(f'{TEMPLATES}/{FOLDER}/{f}: name a pack by its language tag, such as zh-Hans.md')
                continue
            try:
                _loaded[tag.lower()] = parse(tag, read_text(os.path.join(base, f)), 'wiki')
            except ValueError as e:
                problems.append(f'{TEMPLATES}/{FOLDER}/{e}')
    return problems


def loaded():
    if not _loaded:
        _loaded.update(_read(BUNDLED, 'bundled'))
    return _loaded


def pack(tag):
    """The pack for a language tag: its own, else its base language's (zh-Hans-CN, zh-Hans, zh); None when there's none."""
    packs = loaded()
    parts = (tag or DEFAULT).lower().split('-')
    for i in range(len(parts), 0, -1):
        if '-'.join(parts[:i]) in packs:
            return packs['-'.join(parts[:i])]
    return None


def of(text):
    """The language a narrative's Metadata names, or None."""
    m = FIELD.search(text)
    return m.group(1) if m else None


def for_narrative(text, default=DEFAULT):
    """(tag, Pack) for a narrative: the language it names, else default; English's pack when its own has none."""
    tag = of(text) or default
    return tag, pack(tag) or ENGLISH


def names(english):
    """english and every loaded pack's translation of it."""
    return [english] + [p.strings[english] for p in loaded().values() if p.strings.get(english) and p.strings[english] != english]


def words(text):
    """The text's length in words: its space-separated words, and its CJK characters at CJK_CHARACTERS_PER_WORD."""
    cjk = len(CJK.findall(re.sub(r'[　-〿＀-￯]', '', text)))
    rest = CJK.sub(' ', text)
    return len(re.findall(r'[\w\'’-]+', rest)) + round(cjk / CJK_CHARACTERS_PER_WORD)


_LABEL = re.compile(r'\*\*(?P<label>[^*]+?):\*\*')


def translate(skeleton, p):
    """A skeleton in pack p's language: its headings, bold labels and table headers; Metadata is left as it is."""
    if not p.strings:
        return skeleton
    lines = skeleton.split('\n')
    out, in_metadata = [], False
    for i, line in enumerate(lines):
        h = re.match(r'(?P<hashes>#{2,6} )(?P<number>[0-9.]+ )?(?P<title>.*)\Z', line)
        if h:
            title = h.group('title')
            in_metadata = title == 'Metadata'
            opt = re.search(r'\s*\(optional\)\Z', title)
            base = title[:opt.start()] if opt else title
            line = h.group('hashes') + (h.group('number') or '') + p.t(base) + (' ' + p.t('(optional)') if opt else '')
        elif not in_metadata and line.startswith('|') and i + 1 < len(lines) and re.match(r'\|[-:| ]+\|\s*\Z', lines[i + 1]):
            line = '| ' + ' | '.join(p.t(c.strip()) for c in line.strip().strip('|').split('|')) + ' |'
        elif not in_metadata:
            line = _LABEL.sub(lambda m: f'**{p.t(m.group("label"))}:**', line)
        out.append(line)
    return '\n'.join(out)
