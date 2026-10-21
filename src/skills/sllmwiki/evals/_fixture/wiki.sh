#!/usr/bin/env bash
# Builds the eval fixture wiki in the current directory (the agent's working
# directory): the same small wiki the unit tests use
# (src/skills/sllmwiki/tests/helpers.py), as a
# git repository on mainline with a local bare "origin", so branches can be
# pushed without the network. The run's HOME is a sandbox, so git gets a
# repo-local identity. Usage: wiki.sh [extra-step]   (see the case scaffolds)
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
skill="$(cd "$here/../.." && pwd)"  # src/skills/sllmwiki
python3 - "$skill" <<'PY'
import os, sys
sys.path.insert(0, os.path.join(sys.argv[1], 'tests'))
import helpers
helpers.make_wiki(os.getcwd(), git=False)
PY
git init -q -b mainline
git config user.name "Eval Agent"
git config user.email "eval-agent@example.com"
git add -A
git commit -q -m "fixture wiki"
origin="$(pwd)/../origin.git"
git init -q --bare "$origin"
git remote add origin "$origin"
git push -q -u origin mainline
