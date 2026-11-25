"""The plain-sentence checks narrative-format runs on an English narrative (shared-guide.md, "Plain
sentences"): the parts of that rule a script can find without judging. They give warnings, because a
long sentence is sometimes the clearest one. Lint judges the rest: passive voice, nested clauses, noun stacks.

- SENTENCE_LONG: a sentence over MAX_WORDS words.
- SENTENCE_FILLER: a throat-clearing phrase ("it is important to note that", "this section explains"), a phrase one word
  says ("in order to": "to"), a pair of words that mean the same ("each and every"), a modifier the word implies
  ("end result"), "I think" before a claim, or a point announced instead of made ("I want to point out that").
- SENTENCE_TRAILING: a trailing participle clause, such as ", allowing …" or ", resulting in …".
- SENTENCE_REFERENCE: "it" or "they" opening a paragraph or list item, with nothing before it to point at, or a
  bare "this" or "these" as a sentence's subject ("This means …"): name the thing.
- SENTENCE_VAGUE: a vague word ("thing", "stuff", "very", "a lot"), a qualifier a number should replace ("significantly",
  "recently"), a comparison or frequency in a paragraph with no number ("often", "soon", "faster"), or a verb
  and noun one verb says ("make a decision").
- ABBREV_UNDEFINED: an abbreviation (two or more capitals) whose first use outside the title and Terminology isn't
  spelled out beside it, though the title may spell it out; "continuous integration (CI)" or "CI (continuous integration)"; general computing ones (GENERAL) need none.
- ABBREV_LONG_FORM: the words an abbreviation was defined for, written out again after its definition: use the abbreviation.
- PASSIVE_SHARE: more than MAX_PASSIVE of a narrative's sentences in the passive ("is cached", "were sent"), once
  it has MIN_SENTENCES; one sentence alone may need the passive, so only the share is reported.
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
    # a modifier the word already implies
    ('end result', 'result'), ('final outcome', 'outcome'), ('past history', 'history'), ('future plans', 'plans'),
    ('advance planning', 'planning'), ('completely eliminate', 'eliminate'), ('completely eliminates', 'eliminates'),
    ('absolutely essential', 'essential'), ('basic fundamentals', 'fundamentals'), ('close proximity', 'proximity'),
    ('unexpected surprise', 'surprise'), ('join together', 'join'), ('repeat again', 'repeat'),
)
SHORTER_RE = re.compile(r'\b(?:' + '|'.join(re.escape(p) for p, _ in SHORTER) + r')\b', re.I)
FILLER = re.compile(r'\b(?:it is (?:important|worth|interesting) (?:to note|noting) that|it should be noted that|'
                    r'when it comes to|the fact that|(?:I|we) (?:think|believe|feel) (?:that )?|'
                    r'(?:I|we) (?:want|would like|wish) to (?:point out|note|mention|stress|emphasi[sz]e|highlight)(?: that)?|'
                    r'it is worth mentioning that|needless to say|it goes without saying that|'
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
GENERAL = frozenset('ACM AI API ARPANET ASCII AWS CLI CPU CSS CSV DNS EU FAQ GB GPU HTML HTTP HTTPS IBM ID IEEE IP ISO JSON KB MB MIT NASA '
                    'NIST OK OS PDF PNG RAM RFC SHA SQL SSD SSH SVG TB TCP TLS UDP UI UK URI URL US USB UTC UTF XML YAML'
                    .split())  # the reader's field knows these, or knows them by these names
WEASEL = re.compile(r'\b(?:(?<!how )often|generally|soon|better|faster|slower)\b', re.I)  # vague only in a paragraph with no number
DIGIT = re.compile(r'[0-9]')
ABBR = re.compile(r'\b([A-Z]{2,})s?\b')
NUMERAL = re.compile(r'[IVX]+')
PASSIVE = re.compile(r"\b(?:is|are|was|were|be|been|being)\s+(?:not\s+|\w+ly\s+)?(?:\w+ed|built|chosen|done|drawn|given|"
                     r'known|made|kept|sent|set|shown|taken|written|held|found|run|seen|split|spent|told|left|put|paid|'
                     r'brought|broken|driven|hidden|bound|caught|led|lost|meant|sold|taught|won|grown|thrown)\b', re.I)
MAX_PASSIVE, MIN_SENTENCES = 0.15, 20  # most writing standards ask for under 15% passive; too few sentences say nothing
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


def _spelled(text, m):
    """Whether the abbreviation m matched is spelled out beside it: "words (ABBR)" or "ABBR (words)"."""
    before, after = text[:m.start()].rstrip(' *_'), text[m.end():].lstrip(' *_')
    return after.startswith('(') or (before.endswith('(') and after.startswith(')'))


def _long_form(text, m):
    """The words m's abbreviation is spelled out as beside it, when their initials make it, else None."""
    word = m.group(1)
    before, after = text[:m.start()].rstrip(' *_'), text[m.end():].lstrip(' *_')
    if after.startswith('('):
        found = re.findall(r"[A-Za-z][\w'-]*", after[1:after.find(')')] if ')' in after else '')
        tries = [found]
    elif before.endswith('(') and after.startswith(')'):
        found = re.findall(r"[A-Za-z][\w'-]*", before[:-1])
        tries = [found[-k:] for k in range(1, len(word) + 1)]  # the words just before, as many as make the initials
    else:
        return None
    for words in tries:
        initials = ''.join(w[0] for w in re.split(r'[\s-]+', ' '.join(words)) if w)
        if len(initials) > 1 and initials.lower() == word.lower():
            return ' '.join(words)
    return None


def _long_forms(line, longs, at):
    """ABBREV_LONG_FORM for each defined abbreviation's words written out again on a later line."""
    text = LINK.sub(r'\1', CITE.sub('', mask_spans(line)))
    out = []
    for words, (word, defined) in longs.items():
        if at > defined:
            for m in re.finditer(r'\b' + re.escape(words) + r'\b', text, re.I):
                if not text[m.end():].lstrip(' *_').startswith(f'({word})'):
                    out.append(('warning', 'ABBREV_LONG_FORM', at, f'"{m.group(0)}" was defined as {word}: write {word}'))
                    break
    return out


def _abbreviations(line, seen, at, longs=None):
    """ABBREV_UNDEFINED for each abbreviation first met on this line and not spelled out beside it; longs
    collects {spelled-out words: (abbreviation, line)} for those that are."""
    out = []
    text = LINK.sub(r'\1', CITE.sub('', mask_spans(line)))
    for m in ABBR.finditer(text):
        word = m.group(1)
        if word in seen or word in GENERAL or NUMERAL.fullmatch(word):
            continue
        seen.add(word)
        words = _long_form(text, m)
        if words and longs is not None:
            longs.setdefault(words.lower(), (word, at))
        if not _spelled(text, m):
            out.append(('warning', 'ABBREV_UNDEFINED', at, f'"{word}" isn\'t spelled out at its first use: write the words, '
                                                          f'then ({word}); a word in capitals goes in lowercase'))
    return out


def check(text, tag):
    """[(severity, code, line, message)] for the narrative's prose; [] unless it is in English."""
    if tag.lower().split('-')[0] != 'en':
        return []
    lines = text.split('\n')
    kinds, _ = scan(lines)
    terminology = {t.lower() for t in language.names('Terminology')}
    out, skip, glossary, passive, total, longs = [], False, False, [], 0, {}
    title = next((line for line in lines if line.startswith('# ')), '')
    seen = {m.group(1) for m in ABBR.finditer(title) if _spelled(title, m)}  # what the title spells out is defined
    for i, line in enumerate(lines):
        if line.startswith('#'):
            if line.startswith('## '):
                section = re.sub(r'^##\s+(?:[0-9.]+\s+)?', '', line).strip()
                skip, glossary = _skipped(section), section.lower() in terminology
            continue
        if skip or kinds[i] != 'text' or line.lstrip().startswith(('|', '>', '$$', '!')):
            continue
        if not glossary:
            out += _long_forms(line, longs, i + 1)
            out += _abbreviations(line, seen, i + 1, longs)
        parts = sentences(line)
        total += len(parts)
        passive += [i + 1 for s in parts if PASSIVE.search(s)]
        if parts and OPENER.match(parts[0]):
            out.append(('warning', 'SENTENCE_REFERENCE', i + 1, f'"{parts[0].split()[0]}" opens the paragraph: name the thing'))
        for s in parts:
            m = BARE.match(s)
            if m:
                out.append(('warning', 'SENTENCE_REFERENCE', i + 1, f'"{m.group(0)}": say what "{m.group(0).split()[0].lower()}" is'))
            n = len(re.findall(r"[A-Za-z0-9][\w'’-]*", s))
            if n > MAX_WORDS:
                out.append(('warning', 'SENTENCE_LONG', i + 1, f'a {n}-word sentence ("{s[:40]}…"): split it, one idea per sentence'))
            m = VAGUE.search(s) or (None if DIGIT.search(line) else WEASEL.search(s))  # a number anywhere in the paragraph
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
    if total >= MIN_SENTENCES and len(passive) > MAX_PASSIVE * total:
        where = ', '.join(str(n) for n in passive[:5]) + (', …' if len(passive) > 5 else '')
        out.append(('warning', 'PASSIVE_SHARE', passive[0], f'{len(passive)} of {total} sentences ({len(passive) * 100 // total}%) '
                                                           f'are passive, over {int(MAX_PASSIVE * 100)}%: say who acts (lines {where})'))
    return out
