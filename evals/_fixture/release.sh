#!/usr/bin/env bash
# The fixture wiki ready for a release (the release-* cases): a GitHub remote
# served from the local bare origin, the release workflow installed, HTML on, a
# published release v2026.10.01 and a narrative added since. A stand-in gh in
# .eval/ answers release.py (the case sets EVAL_SLLMWIKI_GH=.eval/gh) and logs
# each call to .eval/gh.log. Usage: release.sh CHECKS BUILD, CHECKS passing or
# failing (the default branch's), BUILD success or failure (the book's).
set -euo pipefail
checks="${1:-passing}"
build="${2:-success}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$here/wiki.sh"
origin="$(git remote get-url origin)"
git remote set-url origin git@github.com:o/wiki.git
git config "url.$origin.insteadOf" git@github.com:o/wiki.git
mkdir -p .github/workflows
printf 'name: Book\n' > .github/workflows/release-book.yml
printf '[structural-llm-wiki-release]\nhtml_book = true\n' > sllmwiki/Config.toml
git add -A && git commit -q -m "install the release workflow"
git tag v2026.10.01
tests="$(cd "$here/../../src/skills/sllmwiki/tests" && pwd)"
PYTHONDONTWRITEBYTECODE=1 python3 -c 'import os, sys; sys.path.insert(0, sys.argv[1]); import helpers
helpers.add_narrative(os.getcwd(), "how-does-beta-work", "How does beta work?", primary=("leaf-b",))' "$tests"
git add -A && git commit -q -m "a narrative on beta"
git push -q origin mainline --tags
git remote set-head origin mainline
mkdir -p .eval
python3 - "$checks" "$build" > .eval/responses.json <<'PY'
import datetime, json, sys
checks, build = sys.argv[1], sys.argv[2]
version = 'v' + datetime.datetime.now(datetime.timezone.utc).date().strftime('%Y.%m.%d')
assets = [{'name': f'wiki-{version}.html', 'size': 84546, 'url': f'https://github.com/o/wiki/releases/download/{version}/wiki-{version}.html'}]
print(json.dumps({
    'api repos/o/wiki/commits/': {'check_runs': [{'name': 'wiki-checks', 'status': 'completed',
                                                  'conclusion': 'success' if checks == 'passing' else 'failure'}]},
    'release list': [{'tagName': 'v2026.10.01', 'publishedAt': '2026-10-01T09:00:00Z', 'isDraft': False}],
    'release create': f'https://github.com/o/wiki/releases/tag/{version}',
    'run list': [{'databaseId': 1, 'status': 'completed', 'conclusion': build, 'headBranch': version, 'url': 'https://github.com/o/wiki/actions/runs/1'}],
    'release view': {'url': f'https://github.com/o/wiki/releases/tag/{version}',
                     'body': 'Notes.' if build == 'success' else 'Notes.\n\n### Known issues\n\n- html: Sphinx failed: Extension error',
                     'assets': assets if build == 'success' else []},
}))
PY
cat > .eval/gh <<'PY'
#!/usr/bin/env python3
import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
args = ' '.join(sys.argv[1:])
with open(os.path.join(here, 'gh.log'), 'a') as f:
    f.write(args + '\n')
responses = json.load(open(os.path.join(here, 'responses.json')))
key = max((k for k in responses if args.startswith(k)), key=len, default=None)
if key is None:
    print('gh: unexpected call: ' + args, file=sys.stderr)
    sys.exit(1)
answer = responses[key]
print(answer if isinstance(answer, str) else json.dumps(answer))
PY
chmod +x .eval/gh
