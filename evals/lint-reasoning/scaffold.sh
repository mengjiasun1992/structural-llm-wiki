#!/usr/bin/env bash
# The fixture wiki, with a worked example in what-is-alpha planting two reasoning errors arithmetic alone misses:
# parts that add up to more than their total, and a "must" resting only on habit. Lint's audit should find both.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$here/../_fixture/wiki.sh"
tests="$(cd "$here/../../tests" && pwd)"
PYTHONDONTWRITEBYTECODE=1 python3 - "$tests" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import helpers
example = ('\nTake a client that gives up after 10 seconds. Its first wait is 1 second, so its waits are 1, 2 and 4 seconds, '
           '7 seconds in all. Its three tries take 2 seconds each, 6 seconds in all. So waiting is 7 / 10 = 70% of the '
           'time the client spends on the request. A client must double its wait each time, because that is what retry '
           'libraries do.\n')
helpers.write('.', 'sllmwiki/narratives/what-is-alpha.md', helpers.narrative_text(extra=example))
PY
git commit -qam "a worked example in what-is-alpha"
git push -q
