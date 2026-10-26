#!/usr/bin/env bash
# Run the behavior evals (claude plugin eval) against the plugin. The CLI looks for evals/ inside the
# plugin's root, and the plugin ships without them, so this assembles a copy: plugin/'s contents, with
# evals/ and tests/ (the scaffolds build their fixture wikis with tests/helpers.py) beside them. It runs
# there and copies the results back to evals/results/. Arguments go to claude plugin eval.
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
work="$(mktemp -d "${TMPDIR:-/tmp}/sllmwiki-evals.XXXXXX")"
cp -R "$repo/plugin/." "$work/"
cp -R "$repo/evals" "$work/evals"
cp -R "$repo/tests" "$work/tests"
rm -rf "$work/evals/results"
status=0
(cd "$work" && claude plugin eval . "$@") || status=$?
mkdir -p "$repo/evals/results"
if [ -d "$work/evals/results" ]; then
  cp -R "$work/evals/results/." "$repo/evals/results/"
fi
exit "$status"
