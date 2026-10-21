#!/usr/bin/env bash
# The fixture wiki, and two documents beside it in ../incoming/ to build from,
# so a run needs no network.
set -euo pipefail
"$(dirname "${BASH_SOURCE[0]}")/wiki.sh"
mkdir -p ../incoming
cat > ../incoming/retry-budget.md <<'EOF'
# Retry budgets

A retry budget caps retries at a share of all requests, such as ten percent, so a struggling backend isn't buried in retries.

## How it works

Each client counts its requests and its retries over a sliding window, and stops retrying while retries exceed the budget.
EOF
cat > ../incoming/jitter.md <<'EOF'
# Jitter

Jitter adds a random part to each retry's wait, so clients that failed together don't retry together.

## Full jitter

Wait a random time between zero and the backoff, instead of the backoff itself.
EOF
