#!/usr/bin/env bash
# preflight: are the tools a run needs here? git and Python 3.9+ are required;
# gh, signed in, is recommended (without it, a run prints the link to open
# its pull request). Prints what's missing with the command that installs it
# on this machine. Exit code: 0 ready, 1 something required is missing.
set -u
missing=0

install_hint() {
  case "$(uname -s)" in
    Darwin) echo "brew install $1" ;;
    Linux) echo "sudo apt-get install -y $2" ;;
    *) echo "winget install $3" ;;
  esac
}

# Run git, not just find it: macOS's /usr/bin/git is a stub that fails when it
# can't reach the real one (in a sandbox, or without the developer tools).
if git_version="$(git --version 2>/dev/null)"; then
  echo "ok       git $(echo "$git_version" | awk '{print $3}')"
elif command -v git >/dev/null 2>&1; then
  echo "missing  git (required): \`git --version\` fails here; install a working git ($(install_hint git git Git.Git)) or allow the sandbox to run it"
  missing=1
else
  echo "missing  git (required): $(install_hint git git Git.Git)"
  missing=1
fi

py=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
    py="$candidate"
    break
  fi
done
if [ -n "$py" ]; then
  echo "ok       python $("$py" -c 'import platform; print(platform.python_version())')"
else
  echo "missing  Python 3.9 or later (required): $(install_hint python python3 Python.Python.3.13)"
  missing=1
fi

if command -v gh >/dev/null 2>&1; then
  if auth="$(gh auth status 2>&1)"; then
    echo "ok       gh, signed in"
    # Over HTTPS, gh's token can't push .github/workflows/ (init's CI) without
    # the workflow scope. Tokens that don't list their scopes aren't judged.
    case "$(git remote get-url origin 2>/dev/null)" in
      https://github.com/*)
        if echo "$auth" | grep -q 'Token scopes:' && ! echo "$auth" | grep -q "'workflow'"; then
          echo "warning  gh's token lacks the workflow scope, so a push can't add or change .github/workflows/: gh auth refresh -h github.com -s workflow"
        fi ;;
    esac
  else
    echo "warning  gh isn't signed in (recommended): gh auth login"
  fi
else
  echo "warning  gh (recommended, to open pull requests): $(install_hint gh gh GitHub.cli)"
fi

exit "$missing"
