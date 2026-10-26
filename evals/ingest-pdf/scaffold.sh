#!/usr/bin/env bash
# The fixture wiki, and a PDF with an outline in ../incoming/.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$here/../_fixture/wiki.sh"
mkdir -p ../incoming
tests="$(cd "$here/../../tests" && pwd)"
PYTHONDONTWRITEBYTECODE=1 python3 - "$tests" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import pdfmaker
pages = [pdfmaker.text((72, 720, b'1 Backoff'), (72, 700, b'Each retry waits twice as long as the one before.')),
         pdfmaker.text((72, 720, b'2 Jitter'), (72, 700, b'A random part of the wait keeps clients apart.'))]
open('../incoming/backoff.pdf', 'wb').write(pdfmaker.make(pages, [(0, b'Backoff', 0, None), (0, b'Jitter', 1, None)], title=b'Retry Backoff'))
PY
