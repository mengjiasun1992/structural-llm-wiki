#!/usr/bin/env bash
# The fixture wiki (its origin isn't on GitHub, so it may be public), and a
# proprietary guide in ../incoming/.
set -euo pipefail
"$(dirname "${BASH_SOURCE[0]}")/../_fixture/wiki.sh"
mkdir -p ../incoming
cat > ../incoming/vendor-guide.md <<'MD'
# Vendor retry guide

Copyright Vendor Inc. All rights reserved. No part of this guide may be reproduced.

## Retries

Retry at most three times, waiting longer each time.
MD
