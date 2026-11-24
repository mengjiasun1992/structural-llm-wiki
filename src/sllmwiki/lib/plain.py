"""The plain-sentence checks narrative-format runs on an English narrative (shared-guide.md, "Plain
sentences"): the parts of that rule a script can find without judging. They give warnings, because a
long sentence is sometimes the clearest one. Lint judges the rest: passive voice, nested clauses, noun stacks.

- SENTENCE_LONG: a sentence over MAX_WORDS words.
- SENTENCE_FILLER: a throat-clearing phrase ("it is important to note that", "this section explains"), a phrase one word
  says ("in order to": "to"), a pair of words that mean the same ("each and every"), or "I think" before a claim.
- SENTENCE_TRAILING: a trailing participle clause, such as ", allowing …" or ", resulting in …".
- SENTENCE_REFERENCE: "it" or "they" opening a paragraph or list item, with nothing before it to point at, or a
  bare "this" or "these" as a sentence's subject ("This means …"): name the thing.
- SENTENCE_VAGUE: a vague word ("thing", "stuff", "very", "a lot"), a qualifier a number should replace ("significantly",
  "recently"), or a verb and noun one verb says ("make a decision").
- SENTENCE_UNSOURCED: an authority with no name ("experts agree", "it is widely believed", "studies show"): name and cite it.

Only prose is checked: code, math, tables, block quotes (often a source's words), headings, and the
References, SMEs and Metadata sections are not.
"""

import re

from . import language
from .compat import mask_spans, scan

MAX_WORDS = 30  # the guide asks for most sentences under 20; past 30, one almost always holds two ideas
SKIPPED = ('References', 'SMEs', 'Metadata')
SHORTER = (  # (a phrase, the word that says it)
    ('in order to', 'to'), ('due to the fact that', 'because'), ('in spite of the fact that', 'although'),
    ('in the event that', 'if'), ('for the purpose of', 'to'), ('it is necessary that', 'must'),
    ('at this point in time', 'now'), ('prior to', 'before'), ('has the ability to', 'can'),
    ('each and every', 'each'), ('first and foremost', 'first'), ('full and complete', 'complete'),
    ('whole entire', 'whole'), ('true and accurate', 'accurate'),
)
SHORTER_RE = re.compile(r'\b(?:' + '|'.join(re.escape(p) for p, _ in SHORTER) + r')\b', re.I)
FILLER = re.compile(r'\b(?:it is (?:important|worth|interesting) (?:to note|noting) that|it should be noted that|'
                    r'when it comes to|the fact that|(?:I|we) (?:think|believe|feel) (?:that )?|'
                    r'(?:this|the following) (?:section|chapter|narrative) (?:explains|describes|covers|shows|discusses))', re.I)
UNSOURCED = re.compile(r'\b(?:experts (?:agree|say|believe)|it is (?:widely |generally |commonly )?(?:believed|known|thought|said|accepted)|'
                       r'(?:studies|research) (?:shows?|suggests?)|some (?:people|say)|many believe)\b', re.I)
TRAILING = re.compile(r',\s+(?:thereby\s+\w+ing|allowing|enabling|ensuring|resulting in|leading to|making it possible)\b', re.I)
OPENER = re.compile(r'(?:It|They|Them)\b')  # a paragraph's first word, with no bold lead-in to point at
BARE = re.compile(r'(?:This|These|That|Those) (?:is|are|was|were|means?|makes?|lets?|gives?|keeps?|does|do|can|will|works?|'
                  r'happens|explains?|matters|shows?|says?)\b')
VAGUE = re.compile(r'\b(?:things?|stuff|very|really|quite|a lot|lots of|basically|'
                   r'actually|definitely|extremely|somewhat|arguably|relatively|'
                   r'significantly|substantially|recently|'
                   r'(?:make|makes|made|making) an? (?:decision|choice)|(?:do|does|did|doing) an? (?:review|analysis))\b', re.I)
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
        parts = sentences(line)
        if parts and OPENER.match(parts[0]):
            out.append(('warning', 'SENTENCE_REFERENCE', i + 1, f'"{parts[0].split()[0]}" opens the paragraph: name the thing'))
        for s in parts:
            m = BARE.match(s)
            if m:
                out.append(('warning', 'SENTENCE_REFERENCE', i + 1, f'"{m.group(0)}": say what "{m.group(0).split()[0].lower()}" is'))
            n = len(re.findall(r"[A-Za-z0-9][\w'’-]*", s))
            if n > MAX_WORDS:
                out.append(('warning', 'SENTENCE_LONG', i + 1, f'a {n}-word sentence ("{s[:40]}…"): split it, one idea per sentence'))
            m = VAGUE.search(s)
            if m:
                out.append(('warning', 'SENTENCE_VAGUE', i + 1, f'"{m.group(0)}" is vague: name the thing, the number or the exact verb'))
            m = SHORTER_RE.search(s)
            if m:
                word = dict(SHORTER)[m.group(0).lower()]
                out.append(('warning', 'SENTENCE_FILLER', i + 1, f'"{m.group(0)}": write "{word}"'))
            else:
                m = FILLER.search(s)
                if m:
                    out.append(('warning', 'SENTENCE_FILLER', i + 1, f'"{m.group(0).strip()}" says nothing: start with who does what'))
            m = UNSOURCED.search(s)
            if m:
                out.append(('warning', 'SENTENCE_UNSOURCED', i + 1, f'"{m.group(0)}": name who says it, and cite them'))
            m = TRAILING.search(s)
            if m:
                out.append(('warning', 'SENTENCE_TRAILING', i + 1, f'"{m.group(0).lstrip(", ")} …" trails the sentence: '
                                                                  'give the result its own sentence'))
    return out
