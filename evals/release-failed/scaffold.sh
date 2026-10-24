#!/usr/bin/env bash
set -euo pipefail
"$(dirname "${BASH_SOURCE[0]}")/../_fixture/release.sh" passing failure
