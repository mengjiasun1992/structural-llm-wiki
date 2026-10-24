"""Shared test helpers: the scripts on the import path, command scripts run
in-process, a fixture wiki in the fixed layout, git, and a local HTTP server
(tests never use the network)."""

import contextlib
import functools
import hashlib
import http.server
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # src/skills/sllmwiki
SCRIPTS = os.path.join(SKILL_DIR, 'scripts')
REPO = os.path.dirname(os.path.dirname(os.path.dirname(SKILL_DIR)))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
sys.dont_write_bytecode = True


@functools.lru_cache(maxsize=None)
def load_script(path):
    """A command script imported as a module, so its main() runs in-process and
    counts toward coverage. path is relative to scripts/ (wiki-check.py) or absolute."""
    full = path if os.path.isabs(path) else os.path.join(SCRIPTS, path)
    name = os.path.splitext(os.path.basename(full))[0].replace('-', '_')
    spec = importlib.util.spec_from_file_location(name, full)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Result:
    def __init__(self, code, out, err):
        self.code, self.out, self.err = code, out, err

    def __repr__(self):
        return f'Result(code={self.code}, out={self.out[:300]!r}, err={self.err[:300]!r})'


def run(path, argv, cwd=None):
    """Run a command script's main(argv) in-process, from cwd; a Result. A
    SystemExit becomes the exit code."""
    module = load_script(path)
    out, err = io.StringIO(), io.StringIO()
    old = os.getcwd()
    try:
        if cwd:
            os.chdir(cwd)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = module.main(list(argv))
            except SystemExit as e:
                code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    finally:
        os.chdir(old)
    return Result(0 if code is None else code, out.getvalue(), err.getvalue())


def md5(data):
    return hashlib.md5(data).hexdigest()


def write(root, rel, data):
    """Write text (str, kept byte for byte) or bytes to root/rel, making folders; the path."""
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    if isinstance(data, bytes):
        with open(path, 'wb') as f:
            f.write(data)
    else:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(data)
    return path


def read(root, rel):
    with open(os.path.join(root, rel), encoding='utf-8', newline='') as f:
        return f.read()


def git(root, *args, check=True):
    """Run git in root with a fixed identity and no user or system config."""
    env = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@example.com', GIT_COMMITTER_NAME='t',
               GIT_COMMITTER_EMAIL='t@example.com', GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
    return subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, check=check, env=env)


def git_init(root):
    git(root, 'init', '-q', '-b', 'mainline')
    git(root, 'add', '-A')
    git(root, 'commit', '-q', '-m', 'init')


# The fixture wiki: a root tag with two leaves, three sources (two saved, one
# link) and one narrative, in the fixed layout (design doc §3-§4.4).
FOOTER = '\n\n<!-- sllmwiki:original-source -->\n## Original source\n\n- URL: <{url}>\n- License: {license}\n'
ALPHA = '# Alpha\n\nAlpha systems retry failed requests.\n\n## Details\n\nEach retry waits twice as long as the last.\n'
BETA = '# Beta\n\nBeta caching keeps hot data close to readers.\n'
ABSTRACT = ' '.join(['word'] * 120)

TAGS_YAML = '''# The tag tree: each tag's description, parent and SMEs.

root-topic:
  description: The root topic
  parent: null

leaf-a:
  description: First leaf, about alpha systems
  parent: root-topic
  smes:
    - "@ann: wrote the alpha doc"

leaf-b:
  description: Second leaf, about beta caching
  parent: root-topic
'''


def narrative_text(question='What is alpha?', cites=(('alpha-doc', 'details'),), extra=''):
    """A narrative on the technical_brief_overview template that passes narrative-format,
    citing sections of saved sources."""
    marks = (' ' + ', '.join(f'[\\[{i}\\]](../sources/{slug}.md#{anchor})' for i, (slug, anchor) in enumerate(cites, 1))) if cites else ''
    listed = '\n'.join(f'{i}. [{slug}: {anchor}](../sources/{slug}.md#{anchor})' for i, (slug, anchor) in enumerate(cites, 1))
    read = '\n'.join(f'- [{slug}](../sources/{slug}.md): how alpha retries' for slug in dict(cites))
    return f'''# {question}

## 1. Abstract

{ABSTRACT}

## 2. Terminology

| Term | Definition |
|---|---|
| **Retry** | Sending a failed request again. |

## 3. Background

Requests fail, and alpha systems send them again.

## 4. The core idea

Wait longer after each failure.

```mermaid
graph LR
    A[Request fails] --> B[Wait, then retry]
```

*Figure 4-1: A failed request waits, then retries.*

## 5. How does it work?

Alpha systems retry, each time waiting twice as long{marks}.

1. A request fails, so the client waits and retries.
{extra}
## 6. Design decisions and trade-offs

Waiting longer each time spares a struggling server.

## 7. Limitations and failure modes

Retries add load when many clients fail at once.

## 8. References

### 8.1 Sources read

{read}

### 8.2 Citations

{listed}

## 9. Metadata

- **Version:** 1.0
- **Template:** technical_brief_overview
- **Created:** 2026-10-01
- **Last modified:** 2026-10-02
- **History:**
  - 1.0 (2026-10-01): First version.
'''


def make_wiki(root, git=True):
    """The fixture wiki in root; returns root."""
    alpha = ALPHA + FOOTER.format(url='https://example.com/alpha', license='CC-BY-4.0')
    beta = BETA + FOOTER.format(url='https://example.com/beta', license='CC0-1.0')
    write(root, 'sllmwiki/sources/alpha-doc.md', alpha)
    write(root, 'sllmwiki/sources/beta-doc.md', beta)
    write(root, 'sllmwiki/tags/tags.yaml', TAGS_YAML)
    write(root, 'sllmwiki/sources/manifest.yaml', '''# Sources, keyed by slug.

alpha-doc:
  file: sources/alpha-doc.md
  kind: text
  url: https://example.com/alpha
  published: "2026-09-01"
  ingested: "2026-09-02"
  license: CC-BY-4.0
  tags: [leaf-a]
  abstract: Alpha systems and how they retry failed requests.

beta-doc:
  file: sources/beta-doc.md
  kind: html
  url: https://example.com/beta
  ingested: "2026-09-02"
  license: CC0-1.0
  tags: [leaf-b]
  abstract: Beta caching keeps hot data close to readers.

gamma-link:
  kind: link
  url: https://example.com/gamma
  ingested: "2026-09-02"
  license: unknown
  tags: [leaf-a]
  abstract: A pointer to the gamma code.
''')
    write(root, 'sllmwiki/narratives/what-is-alpha.md', narrative_text())
    write(root, 'sllmwiki/narratives/manifest.yaml', f'''# Narratives, keyed by question slug.

what-is-alpha:
  template: technical_brief_overview
  tags:
    primary: [leaf-a]
    supporting: []
  read:
    alpha-doc: {md5(ALPHA.encode())}
''')
    from lib import wikiindex
    wikiindex.sync(root, write=True)  # the index and tag pages, as wiki-check.py --fix writes them
    if git:
        git_init(root)
    return root


def add_narrative(root, slug, question, template='technical_brief_overview', primary=('leaf-a',), supporting=(),
                  built_on=(), cites=(('alpha-doc', 'details'),)):
    """Add a narrative and its manifest entry to a fixture wiki; built_on names other narratives."""
    write(root, f'sllmwiki/narratives/{slug}.md', narrative_text(question, cites).replace(
        '**Template:** technical_brief_overview', f'**Template:** {template}'))
    entry = (f'\n{slug}:\n  template: {template}\n  tags:\n    primary: [{", ".join(primary)}]\n'
             f'    supporting: [{", ".join(supporting)}]\n  read:\n    alpha-doc: {md5(ALPHA.encode())}\n')
    if built_on:
        entry += '  built_on:\n' + ''.join(f'    {b}: {md5(b.encode())}\n' for b in built_on)
    write(root, 'sllmwiki/narratives/manifest.yaml', read(root, 'sllmwiki/narratives/manifest.yaml') + entry)


class WikiTestCase(unittest.TestCase):
    """A fresh fixture wiki per test, in a temporary directory."""

    git = True

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='sllmwiki-test-')
        self.root = make_wiki(self.tmp, git=self.git)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, rel, data):
        return write(self.root, rel, data)

    def read(self, rel):
        return read(self.root, rel)


class LocalServer:
    """Serve {path: (status, headers, body bytes)} on 127.0.0.1, on a free port."""

    def __init__(self, routes):
        routes_ref = routes

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - http.server's name
                status, headers, body = routes_ref.get(self.path, (404, {}, b'not found'))
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()

    def url(self, path):
        return f'http://127.0.0.1:{self.server.server_address[1]}{path}'
