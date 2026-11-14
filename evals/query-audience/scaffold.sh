#!/usr/bin/env bash
# The fixture wiki, with an audience profile (sllmwiki/.templates/audience.md) the answer must follow.
set -euo pipefail
"$(dirname "${BASH_SOURCE[0]}")/../_fixture/wiki.sh"
mkdir -p sllmwiki/.templates
cat > sllmwiki/.templates/audience.md <<'MD'
# Who reads this wiki

The payments team's product managers. They don't read code and have no time for detail: every answer
opens with a line that starts "Bottom line:", one plain sentence they can repeat in a meeting.
MD
