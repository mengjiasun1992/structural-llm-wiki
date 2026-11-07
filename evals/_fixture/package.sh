#!/usr/bin/env bash
# Installs this checkout's sllmwiki package where the skill's bootstrap looks for it, the plugin's
# data folder: a run's sandbox has no network to fetch it from PyPI, and a run should test the
# branch, not a published version. src/tools/eval-plugin.sh builds the wheel beside the evals;
# without it (the unit tests run these fixtures too), this does nothing. A scaffold runs with HOME
# set to the run's home, whose sibling config/ is the run's Claude Code configuration, so the
# data folder is config/plugins/data/sllmwiki-inline/ (a plugin loaded from a folder is "inline").
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
wheel="$(ls "$here"/../../dist/sllmwiki-*.whl 2>/dev/null | head -n 1 || true)"
[ -n "$wheel" ] || exit 0
version="${wheel##*/sllmwiki-}"
version="${version%%-*}"
venv="$HOME/../config/plugins/data/sllmwiki-inline/venv-$version"
python3 -m venv "$venv"
"$venv/bin/python" -m pip install --quiet --disable-pip-version-check --no-index --no-deps "$wheel"
# for the Evals workflow, which keeps it beside the run's trace
echo "installed $("$venv/bin/sllmwiki" --version) in $venv" >> "$HOME/../out/package.log"
