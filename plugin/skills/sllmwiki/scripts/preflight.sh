#!/usr/bin/env bash
# preflight: are the tools a run needs here? git and Python 3.9+ are required;
# gh, signed in, is recommended (without it, a run prints the link to open
# its pull request). Prints what's missing with the command that installs it
# on this machine, from its package manager. Exit code: 0 ready, 1 something required is missing.
set -u
missing=0

# Where to get a tool when no package manager is known.
download() {
  case "$1" in git) echo "https://git-scm.com/downloads" ;; python) echo "https://www.python.org/downloads/" ;; gh) echo "https://cli.github.com" ;; esac
}

# The command that installs a tool here, with this machine's package manager:
# install_hint <git|python|gh>. A command starting with sudo, the owner runs.
install_hint() {
  local sudo=""
  [ "$(id -u 2>/dev/null)" = 0 ] || sudo="sudo "
  case "$(uname -s)" in
    Darwin)
      if command -v brew >/dev/null 2>&1; then
        case "$1" in git) echo "brew install git" ;; python) echo "brew install python" ;; gh) echo "brew install gh" ;; esac
      else
        case "$1" in
          git|python) echo "xcode-select --install (Apple's command line tools: git and Python 3.9+)" ;;
          gh) echo "install Homebrew (https://brew.sh), then: brew install gh" ;;
        esac
      fi ;;
    Linux)
      local pm="" pkg="$1"
      for candidate in apt-get dnf yum pacman zypper apk; do
        if command -v "$candidate" >/dev/null 2>&1; then pm="$candidate"; break; fi
      done
      case "$pm:$1" in
        pacman:python) pkg=python ;;
        *:python) pkg=python3 ;;
        pacman:gh|apk:gh) pkg=github-cli ;;
      esac
      case "$pm" in
        apt-get) echo "${sudo}apt-get install -y $pkg" ;;
        dnf|yum|zypper) echo "${sudo}$pm install -y $pkg" ;;
        pacman) echo "${sudo}pacman -S --noconfirm $pkg" ;;
        apk) echo "${sudo}apk add $pkg" ;;
        *) download "$1" ;;
      esac ;;
    MINGW*|MSYS*|CYGWIN*|Windows_NT)
      case "$1" in git) echo "winget install -e --id Git.Git" ;; python) echo "winget install -e --id Python.Python.3.13" ;; gh) echo "winget install -e --id GitHub.cli" ;; esac ;;
    *) download "$1" ;;
  esac
}

# Run git, not just find it: macOS's /usr/bin/git is a stub that fails when it
# can't reach the real one (in a sandbox, or without the developer tools).
if git_version="$(git --version 2>/dev/null)"; then
  echo "ok       git $(echo "$git_version" | awk '{print $3}')"
elif command -v git >/dev/null 2>&1; then
  echo "missing  git (required): \`git --version\` fails here; install a working git ($(install_hint git)) or allow the sandbox to run it"
  missing=1
else
  echo "missing  git (required): $(install_hint git)"
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
  echo "missing  Python 3.9 or later (required): $(install_hint python)"
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
  echo "warning  gh (recommended, to open pull requests): $(install_hint gh)"
fi

exit "$missing"
