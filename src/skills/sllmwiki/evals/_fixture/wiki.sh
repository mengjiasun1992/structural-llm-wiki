#!/usr/bin/env bash
# Builds the eval fixture wiki in the current directory, the agent's working
# directory: the unit tests' fixture wiki (make_wiki in ../../tests/helpers.py),
# committed on mainline with a repository-local identity (a run's HOME is a
# sandbox), and a local bare "origin" beside it, so a run can push branches
# without the network. A case's scaffold.sh calls this, then changes only what
# the case needs.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
tests="$(cd "$here/../../tests" && pwd)"
PYTHONDONTWRITEBYTECODE=1 python3 -c 'import os, sys; sys.path.insert(0, sys.argv[1]); import helpers; helpers.make_wiki(os.getcwd(), git=False)' "$tests"
git init -q -b mainline
git config user.name "Eval Agent"
git config user.email "eval-agent@example.com"
git add -A
git commit -q -m "fixture wiki"
origin="$(pwd)/../origin.git"
git init -q --bare "$origin"
git remote add origin "$origin"
git push -q -u origin mainline
