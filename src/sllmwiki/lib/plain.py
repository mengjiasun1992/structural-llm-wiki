"""The plain-sentence checks narrative-format runs on an English narrative (shared-guide.md, "Plain
sentences"): the parts of that rule a script can find without judging. They give warnings, because a
long sentence is sometimes the clearest one. Lint judges the rest: passive voice, nested clauses, noun stacks.

- SENTENCE_LONG: a sentence over MAX_WORDS words.
- SENTENCE_FILLER: a throat-clearing phrase, such as "it is important to note that" or "in order to".
- SENTENCE_TRAILING: a trailing participle clause, such as ", allowing …" or ", resulting in …".

Only prose is checked: code, math, tables, block quotes (often a source's words), headings, and the
References, SMEs and Metadata sections are not.
"""

import re

from . import language
from .compat import mask_spans, scan

MAX_WORDS = 30  # the guide asks for most sentences under 20; past 30, one almost always holds two ideas
SKIPPED = ('References', 'SMEs', 'Metadata')
FILLER = re.compile(r'\b(?:it is (?:important|worth|interesting) (?:to note|noting) that|it should be noted that|'
                    r'in order to|when it comes to|the fact that)\b', re.I)
TRAILING = re.compile(r',\s+(?:thereby\s+\w+ing|allowing|enabling|ensuring|resulting in|leading to|making it possible)\b', re.I)
SPLIT = re.compile(r'(?<=[.!?;:])["\')*]*\s+')  # a colon or semicolon ends a clause the reader can stop at
LINK = re.compile(r'\[([^\]]*)\]\([^)]*\)')
CITE = re.compile(r'\[\\\[[0-9]+\\\]\]\([^)]*\)|\[→\]')


def sentences(line):
    """The sentences of one prose line, with link targets, citations and code left out."""
    text = CITE.sub('', mask_spans(line))
    text = LINK.sub(r'\1', text)
    text = re.sub(r'^\s*(?:[-*+]|[0-9]+\.)\s+', '', text)  # a list item's bullet
    return [s.strip() for s in SPLIT.split(text) if s.strip()]


def _skipped(title):
    return title.lower() in {t.lower() for e in SKIPPED for t in language.names(e)}


def check(text, tag):
    """[(severity, code, line, message)] for the narrative's prose; [] unless it is in English."""
    if tag.lower().split('-')[0] != 'en':
        return []
    lines = text.split('\n')
    kinds, _ = scan(lines)
    out, skip = [], False
    for i, line in enumerate(lines):
        if line.startswith('#'):
            skip = line.startswith('## ') and _skipped(re.sub(r'^##\s+(?:[0-9.]+\s+)?', '', line).strip())
            continue
        if skip or kinds[i] != 'text' or line.lstrip().startswith(('|', '>', '$$', '!')):
            continue
        for s in sentences(line):
            n = len(re.findall(r"[A-Za-z0-9][\w'’-]*", s))
            if n > MAX_WORDS:
                out.append(('warning', 'SENTENCE_LONG', i + 1, f'a {n}-word sentence ("{s[:40]}…"): split it, one idea per sentence'))
            m = FILLER.search(s)
            if m:
                out.append(('warning', 'SENTENCE_FILLER', i + 1, f'"{m.group(0)}" says nothing: start with who does what'))
            m = TRAILING.search(s)
            if m:
                out.append(('warning', 'SENTENCE_TRAILING', i + 1, f'"{m.group(0).lstrip(", ")} …" trails the sentence: '
                                                                  'give the result its own sentence'))
    return out
