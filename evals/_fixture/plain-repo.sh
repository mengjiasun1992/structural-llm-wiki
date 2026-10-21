#!/usr/bin/env bash
# A repository with no wiki in it, in the run's working directory: the one-line
# README GitHub creates (plain-repo.sh new), or a project's own files (plain-repo.sh project).
set -euo pipefail
git init -q -b mainline
git config user.name "Eval Agent"
git config user.email "eval-agent@example.com"
if [ "${1:-new}" = project ]; then
  printf '# A project\n\nSome code lives here.\n' > README.md
  printf 'print("hello")\n' > app.py
else
  printf '# team-wiki\n' > README.md
fi
git add -A
git commit -q -m "Initial commit"
