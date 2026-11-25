"""SMEs say who to ask, never how good anyone is (design doc §5.1): no entry scores,
ranks or compares the people it names. One check, used where SMEs are written
(`manifest put-tag --smes`) and where they're read (tags.yaml in wiki-check, a
narrative's SMEs section in narrative-format).

An entry is "<who>: <evidence>; ask: <question>". Only the part before the question
is checked, so a question may ask about "the best retry limit".
"""

import re

from . import language, numbering

CODE = 'SMES_RANKED'
QUESTION = re.compile(r'\b(?:ask|question)s?\s*:', re.I)
NUMBERED = re.compile(r'\A\s*(?:[-*+]\s+)?(?:\d+[.)]|#\d+)\s')  # 1. 2) #1, even inside a bullet
RANKING = re.compile(
    r'\b(?:best|strongest|foremost|top(?![- ](?:level|down|of)\b)|first choice|number one|no\.\s*1'
    r'|most (?:knowledgeable|experienced|expert|qualified|senior|active)'
    r'|rank(?:s|ed|ing)?|scor(?:e|es|ed|ing)|rat(?:ing|ings|ed)|better than|more than (?:anyone|others))\b'
    r'|#1\b|(?<![\d/.])\d{1,3}(?:\.\d+)?\s*/\s*(?:5|10|100)(?![\d/])', re.I)  # a score: 8/10, not a date


def problem(entry):
    """What in one SME entry scores or ranks the person, or None."""
    m = QUESTION.search(entry)
    who = re.sub(r'`[^`]*`', '', entry[:m.start()] if m else entry)
    if NUMBERED.match(who):
        return 'a numbered list'
    found = RANKING.search(who)
    return f'"{found.group(0).strip()}"' if found else None


def message(entry, what):
    return (f'{what} in "{entry.strip()[:60]}" ranks or scores a named person: SMEs say who to ask '
            'and the evidence, by name, never who is best')


def check_entries(entries):
    """[(entry, message)] for each tags.yaml SME entry that ranks or scores."""
    return [(e, message(e, p)) for e in entries for p in [problem(e)] if p]


def check(text):
    """Findings (severity, code, line, message) for the lines of a narrative's SMEs section."""
    titles = {t.lower() for t in language.names('SMEs')}
    heads = numbering.headings(text)
    lines = text.split('\n')
    out = []
    for n, h in enumerate(heads):
        if h.level != 2 or h.title.strip().lower() not in titles:
            continue
        end = next((x.line for x in heads[n + 1:] if x.level <= 2), len(lines))
        for i in range(h.line + 1, end):
            p = problem(lines[i]) if lines[i].strip() else None
            if p:
                out.append(('error', CODE, i + 1, message(lines[i], p)))
    return out
