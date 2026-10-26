"""Links from a narrative to a section of another narrative (design doc §4.5): a
narrative that mentions a concept another one covers links to it there, instead
of explaining it again. Section anchors carry the section's number, so a link
breaks when its target renumbers; these find and repair that.

  check(root, rel, text)    findings (severity, NARRATIVE_ANCHOR, line, message)
  repair(root, rel, text)   (text, links fixed): a link whose section only moved gets its new number
  check_all(root, fix)      [(severity, code, file, message)] across the narratives; with fix, repaired first
"""

import os
import re

from . import layout, manifest, numbering
from .compat import scan
from .util import read_text, write_text

_LINK = re.compile(r'\]\((?P<file>[^)\s#]+\.md)#(?P<anchor>[^)\s]+)\)')
_NUMBER = re.compile(r'\A[0-9]+-?')


def links(root, rel, text):
    """[(line, match, target text or None)] for each link to a section of another narrative."""
    folder = os.path.dirname(os.path.join(root, rel))
    narratives = os.path.realpath(os.path.join(root, layout.NARRATIVES))
    own = os.path.realpath(os.path.join(root, rel))
    lines = text.split('\n')
    kinds, _ = scan(lines)
    out = []
    for i, line in enumerate(lines):
        for m in _LINK.finditer(line) if kinds[i] == 'text' else ():
            path = os.path.realpath(os.path.join(folder, m.group('file')))
            if os.path.dirname(path) == narratives and path != own:
                out.append((i, m, read_text(path) if os.path.isfile(path) else None))  # a missing file is compat's LINK_PATH
    return out


def moved(anchor, target):
    """The anchor a section has now when only its number changed: the one heading with the same title, or None."""
    title = _NUMBER.sub('', anchor)
    found = [a for a in numbering.anchors(target) if _NUMBER.sub('', a) == title]
    return found[0] if len(found) == 1 else None


def _broken(root, rel, text):
    return [(i, m, target) for i, m, target in links(root, rel, text)
            if target is not None and m.group('anchor') not in numbering.anchors(target)]


def check(root, rel, text):
    return [('error', 'NARRATIVE_ANCHOR', i + 1, f'{m.group("file")} has no section #{m.group("anchor")}'
             + (f'; it is #{moved(m.group("anchor"), target)} now (finish-narrative.py repairs it)' if moved(m.group('anchor'), target) else ''))
            for i, m, target in _broken(root, rel, text)]


def repair(root, rel, text):
    lines = text.split('\n')
    fixed = 0
    for i, m, target in reversed(_broken(root, rel, text)):
        new = moved(m.group('anchor'), target)
        if new:
            lines[i] = lines[i][:m.start('anchor')] + new + lines[i][m.end('anchor'):]
            fixed += 1
    return '\n'.join(lines), fixed


def check_all(root, fix=False):
    out = []
    for slug in sorted(manifest.load(root, 'narratives')):
        rel = f'{layout.NARRATIVES}/{slug}.md'
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            continue
        text = read_text(path)
        if fix:
            new, n = repair(root, rel, text)
            if n:
                write_text(path, new)
                text = new
        out += [(sev, code, f'{rel}:{line}', msg) for sev, code, line, msg in check(root, rel, text)]
    return out
