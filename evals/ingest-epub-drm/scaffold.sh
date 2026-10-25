#!/usr/bin/env bash
# The fixture wiki, and an EPUB whose chapters are encrypted (DRM) in ../incoming/.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$here/../_fixture/wiki.sh"
mkdir -p ../incoming
tests="$(cd "$here/../../src/skills/sllmwiki/tests" && pwd)"
PYTHONDONTWRITEBYTECODE=1 python3 - "$tests" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import epubmaker
chapters = [('backoff.xhtml', '<h1>Backoff</h1><p>Each retry waits twice as long as the one before.</p>')]
open('../incoming/bought.epub', 'wb').write(epubmaker.make(chapters, [(0, 'Backoff', 'backoff.xhtml')], title='Retry Patterns',
                                                           encrypted=[('backoff.xhtml', epubmaker.ENC)]))
PY
