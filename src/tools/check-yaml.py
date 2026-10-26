#!/usr/bin/env python3
"""check-yaml: check that YAML is valid by the spec, with a real YAML parser.

Usage: python3 check-yaml.py [--json] [<file>...]

What it checks:
  - With files, those files: a *.md file for its ```yaml blocks, any other
    file as YAML.
  - With no files, every file git tracks in the current repository that ends
    in .yaml, .yml or .md, skipping node_modules/ and the sources folder
    (sllmwiki/sources/), whose files are verbatim copies of other people's
    work. The sources' manifest is the wiki's own, so it is
    checked.
  - Every document in a file (a file can hold several, split by ---) must
    parse with PyYAML's safe loader: YAML_ERROR, with the line of the problem.
  - No mapping may repeat a key, at any depth: DUPLICATE_KEY. PyYAML keeps
    the last value silently, so a repeated key would otherwise hide an entry.
  - In markdown, every fenced code block whose language is yaml or yml is
    checked the same way, with lines reported as lines of the .md file.

Why it exists: wiki-check reads the wiki's own YAML files with a small subset
reader; this script is the spec-level check next to it. It is the one script
that needs a package, PyYAML: CI installs it with `pip install pyyaml==6.0.2`.
It lives in tools/, outside the skill, which stays dependency-free.

Output: one line per finding (`error  CODE  file:line: message`) and a
summary line, or, with --json, {"errors": N, "findings": [...]} where each
finding has file, line, code and message.

It reports; it never edits. Exit code: 0 = valid, 1 = errors, 2 = usage error
(an unknown option, or PyYAML not installed).
"""

import sys

sys.dont_write_bytecode = True

import os  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402

# the skill's library: the wiki's fixed layout and the shared helpers
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'plugin', 'skills', 'sllmwiki', 'scripts'))
from lib.layout import SOURCES, SOURCES_MANIFEST  # noqa: E402
from lib.util import dumps, read_text, setup_stdio  # noqa: E402

# PyYAML is the only dependency; without it, stop with a usage error rather than skip the check
try:
    import yaml
except ImportError:
    print('check-yaml: needs PyYAML (pip install pyyaml)', file=sys.stderr)
    sys.exit(2)


def skip(f):
    """True for a file the check leaves alone: a saved source, or anything under node_modules/."""
    # the sources folder holds verbatim sources; its manifest is the wiki's own and is checked
    return (f.startswith(SOURCES + '/') and f != SOURCES_MANIFEST) or bool(re.match(r'(.*/)?node_modules/', f))


def _duplicate_keys(node, findings, file, line_offset):
    """Walk a composed YAML node tree and report every key a mapping repeats (DUPLICATE_KEY)."""
    if isinstance(node, yaml.MappingNode):
        seen = set()
        for k, v in node.value:
            if isinstance(k, yaml.ScalarNode):
                if k.value in seen:
                    findings.append({
                        'file': file,
                        'line': k.start_mark.line + 1 + line_offset,
                        'code': 'DUPLICATE_KEY',
                        'message': f'Map keys must be unique; "{k.value}" is repeated',
                    })
                seen.add(k.value)
            _duplicate_keys(v, findings, file, line_offset)
    elif isinstance(node, yaml.SequenceNode):
        for v in node.value:
            _duplicate_keys(v, findings, file, line_offset)


def check(file, text, line_offset, findings):
    """Parse every document in text; add a YAML_ERROR or DUPLICATE_KEY finding for each problem.

    line_offset shifts the reported lines, so a ```yaml block's findings point at
    lines of the markdown file it sits in.
    """
    # compose (not load) keeps each key's position, which the duplicate check needs
    try:
        for doc in yaml.compose_all(text, Loader=yaml.SafeLoader):
            _duplicate_keys(doc, findings, file, line_offset)
    except yaml.MarkedYAMLError as e:
        mark = e.problem_mark or e.context_mark
        findings.append({
            'file': file,
            'line': (mark.line + 1 if mark else 1) + line_offset,
            'code': 'YAML_ERROR',
            'message': ' '.join(x for x in (e.context, e.problem) if x),
        })
    except yaml.YAMLError as e:
        findings.append({'file': file, 'line': 1 + line_offset, 'code': 'YAML_ERROR', 'message': str(e).split('\n')[0]})


# an opening or closing code fence: its indent, its marker (``` or ~~~, three or more) and its language
_FENCE = re.compile(r'(\s*)(`{3,}|~{3,})\s*(\S*)')


def yaml_blocks(text):
    """```yaml blocks: the opening fence's marker and indent decide where it ends."""
    blocks = []
    open_ = None
    for i, l in enumerate(text.split('\n')):
        m = _FENCE.match(l)
        if not open_:
            if m:
                open_ = {'marker': m.group(2), 'indent': len(m.group(1)), 'lang': m.group(3).lower(), 'start': i + 1, 'body': []}
            continue
        if m and m.group(2)[0] == open_['marker'][0] and len(m.group(2)) >= len(open_['marker']) and l.strip() == m.group(2):
            if open_['lang'] in ('yaml', 'yml'):
                blocks.append(open_)
            open_ = None
            continue
        open_['body'].append(l[min(open_['indent'], len(l) - len(l.lstrip())) :])
    return blocks


def main(argv):
    """Check the given files, or every tracked YAML and markdown file; print findings; return the exit code."""
    setup_stdio()
    as_json = '--json' in argv
    files = [a for a in argv if a != '--json']
    if any(f.startswith('--') for f in files):
        print('usage: check-yaml.py [--json] [<file>...]', file=sys.stderr)
        return 2
    if not files:
        # every tracked .yaml, .yml and .md file, minus the saved sources
        tracked = [f for f in subprocess.run(['git', 'ls-files', '-z'], capture_output=True, text=True, check=True).stdout.split('\0') if f]
        files = [f for f in tracked if re.search(r'\.(ya?ml|md)\Z', f) and not skip(f)]

    findings = []
    for file in files:
        text = read_text(file)
        # markdown: only its ```yaml blocks; anything else is YAML through and through
        if file.endswith('.md'):
            for b in yaml_blocks(text):
                check(file, '\n'.join(b['body']), b['start'], findings)
        else:
            check(file, text, 0, findings)

    if as_json:
        print(dumps({'errors': len(findings), 'findings': findings}))
    else:
        for f in findings:
            print(f"error    {f['code'].ljust(22)} {f['file']}:{f['line']}: {f['message']}")
        if findings:
            print('')
        print(f'check-yaml: {len(findings)} error(s) in {len(files)} file(s)')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
