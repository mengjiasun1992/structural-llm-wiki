#!/usr/bin/env bash
# The fixture wiki, and notes with a contacts section in ../incoming/.
set -euo pipefail
"$(dirname "${BASH_SOURCE[0]}")/../_fixture/wiki.sh"
mkdir -p ../incoming
cat > ../incoming/oncall-notes.md <<'MD'
# On-call notes

## Retries

Retry a failed call twice, then page the on-call engineer.

## Contacts

Dana Smith, dana.smith@example.com, +1 555-0100.
MD
