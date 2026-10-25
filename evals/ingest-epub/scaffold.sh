#!/usr/bin/env bash
# The fixture wiki, and an EPUB book in ../incoming/.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$here/../_fixture/wiki.sh"
mkdir -p ../incoming
tests="$(cd "$here/../../src/skills/sllmwiki/tests" && pwd)"
PYTHONDONTWRITEBYTECODE=1 python3 - "$tests" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import epubmaker
chapters = [('backoff.xhtml', '<h1>Backoff</h1><p>Each retry waits twice as long as the one before.</p>'),
            ('jitter.xhtml', '<h1>Jitter</h1><p>A random part of the wait keeps clients apart.</p>')]
toc = [(0, 'Backoff', 'backoff.xhtml'), (0, 'Jitter', 'jitter.xhtml')]
open('../incoming/retries.epub', 'wb').write(epubmaker.make(chapters, toc, title='Retries in Practice'))
PY
