"""Rendering a narrative's mermaid diagrams, for sllmwiki narrative-format --render-mermaid (issue #190): a
diagram with a syntax error renders as an error box on GitHub, and nothing else checks it before review.

It runs mermaid-cli (mmdc) through Node's npx, which fetches it, and the headless browser it draws with, on
first use; that is why it runs only when asked. Without npx, or when the renderer itself fails to start, it
says so in one MERMAID_UNCHECKED warning, and the narrative step has the agent look at the diagrams on GitHub
instead. SLLMWIKI_MERMAID=off skips it, for tests and sandboxes with no network.
"""

import os
import re
import shutil
import subprocess
import tempfile

from . import figures

VERSION = '11.4.0'
TIMEOUT = 300  # seconds: the first run downloads mermaid-cli and a browser
SYNTAX = ('Parse error', 'Syntax error', 'Lexical error', 'Error: ')


def blocks(text):
    """[(first line, source)] for each ```mermaid block."""
    lines = text.split('\n')
    return [(first, '\n'.join(lines[first + 1:last])) for first, last, _ in figures.pictures(text)
            if figures._MERMAID.match(lines[first])]


CLICK = re.compile(r'\s*click\s+\S+\s+(?:href\s+)?"([^"]*)"')


def check_clicks(text):
    """[(severity, code, line, message)]: MERMAID_RELATIVE_CLICK for a `click` link that isn't an absolute URL.
    GitHub draws mermaid in an iframe on another host, where a relative link resolves to a page that isn't there
    (issue #199)."""
    out = []
    for first, source in blocks(text):
        for n, line in enumerate(source.split('\n'), first + 2):
            m = CLICK.match(line)
            if m and not re.match(r'(?:https?|mailto):', m.group(1)):
                out.append(('error', 'MERMAID_RELATIVE_CLICK', n, f'click "{m.group(1)}" is relative, so it breaks on GitHub, '
                                                                  'which draws mermaid on another host: use an https:// URL, '
                                                                  'or a markdown link beside the diagram'))
    return out


def check_charts(text):
    """[(severity, code, line, message)] for the charts among the ```mermaid blocks (shared-guide.md, Pictures):
    CHART_PIE for a pie, whose angles readers compare worse than bars' lengths, and CHART_AXIS for an
    xychart axis with no title to say what it measures and in what unit."""
    out = []
    for first, source in blocks(text):
        body = [line.strip() for line in source.split('\n') if line.strip() and not line.strip().startswith('%%')]
        kind = body[0].split()[0] if body else ''
        if kind == 'pie':
            out.append(('warning', 'CHART_PIE', first + 1, 'a pie chart: draw bars (xychart-beta), whose lengths compare at a glance'))
        elif kind.startswith('xychart'):
            for axis in ('x-axis', 'y-axis'):
                if not any(re.match(axis + r'\s+"', line) for line in body):
                    out.append(('warning', 'CHART_AXIS', first + 1, f'the {axis} has no title: give it one, '
                                                                  f'with its unit ({axis} "Latency (ms)" …)'))
    return out


def render(text):
    """[(severity, code, line, message)]: MERMAID_SYNTAX for each block that doesn't render, or one
    MERMAID_UNCHECKED warning when the renderer can't run; [] when every block renders or there are none."""
    found = blocks(text)
    if not found or os.environ.get('SLLMWIKI_MERMAID', '').lower() in ('off', '0', 'false', 'no'):
        return []
    npx = shutil.which('npx')
    if not npx:
        return [('warning', 'MERMAID_UNCHECKED', found[0][0] + 1, 'Node isn\'t installed, so the diagrams weren\'t rendered '
                 'here: look at each on GitHub before asking for review')]
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        for first, source in found:
            src, svg = os.path.join(tmp, 'in.mmd'), os.path.join(tmp, 'out.svg')
            with open(src, 'w', encoding='utf-8') as f:
                f.write(source + '\n')
            try:
                p = subprocess.run([npx, '--yes', '-p', f'@mermaid-js/mermaid-cli@{VERSION}', 'mmdc', '-q', '-i', src, '-o', svg],
                                   capture_output=True, text=True, timeout=TIMEOUT)
            except (OSError, subprocess.TimeoutExpired) as e:
                return [('warning', 'MERMAID_UNCHECKED', first + 1, f'the renderer couldn\'t run ({e}): look at each diagram on GitHub')]
            said = (p.stderr or p.stdout).strip().splitlines()
            reason = next((s.strip() for s in said if s.strip().startswith(SYNTAX)), None)
            if p.returncode == 0 and os.path.isfile(svg):
                continue
            if not reason:
                tail = said[-1] if said else 'no output'
                return [('warning', 'MERMAID_UNCHECKED', first + 1, f'the renderer couldn\'t run ({tail}): look at each diagram on GitHub')]
            out.append(('error', 'MERMAID_SYNTAX', first + 1, f'this diagram doesn\'t render: {reason}'))
    return out
