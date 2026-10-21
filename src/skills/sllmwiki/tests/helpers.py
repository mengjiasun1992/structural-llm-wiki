"""Shared test helpers: import paths, running command scripts in-process,
fixture wikis, and a local HTTP server (tests never use the network)."""

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
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
sys.dont_write_bytecode = True


@functools.lru_cache(maxsize=None)
def load_script(name):
    """A command script (such as 'wiki-check') imported as a module, so its
    main() runs in-process and counts toward coverage."""
    path = os.path.join(SCRIPTS, f'{name}.py')
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Result:
    def __init__(self, code, out, err):
        self.code, self.out, self.err = code, out, err

    def __repr__(self):
        return f'Result(code={self.code}, out={self.out[:300]!r}, err={self.err[:300]!r})'


def run(name, argv, cwd=None):
    """Run a command script's main(argv) in-process; returns Result(code, out, err).
    A SystemExit (from usage errors) becomes the exit code."""
    module = load_script(name)
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
    return Result(code if code is not None else 0, out.getvalue(), err.getvalue())


def md5(data):
    return hashlib.md5(data).hexdigest()


def write(root, rel, text, binary=False):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'wb' if binary else 'w', **({} if binary else {'encoding': 'utf-8', 'newline': ''})) as f:
        f.write(text)
    return path


def read_bytes(root, rel):
    with open(os.path.join(root, rel), 'rb') as f:
        return f.read()


def read(root, rel):
    with open(os.path.join(root, rel), encoding='utf-8', newline='') as f:
        return f.read()


ABSTRACT = ' '.join(['word'] * 170)


def narrative_text(question, version='1.0', status=None, template=None, sources=None, extra_metadata=''):
    """A narrative that passes narrative-format with the technical_brief_overview template.
    sources: list of (slug, file) cited as numbered citations."""
    sources = sources or []
    cites = ''.join(f' [\\[{i}\\]](../{f})' for i, (_, f) in enumerate(sources, 1))
    banner = '\n> **DRAFT** — not yet grounded.\n' if status == 'draft' else ''
    meta = ['- **Created:** 2026-10-01', '- **Last modified:** 2026-10-02', f'- **Version:** {version}']
    if status:
        meta.insert(0, f'- **Status:** {status}')
    if template:
        meta.append(f'- **Template:** {template}')
    citations = '\n'.join(f'{i}. Source {slug} — [source](../{f}).' for i, (slug, f) in enumerate(sources, 1))
    return f'''# {question}
{banner}
## 1. Abstract

{ABSTRACT}

## 2. Terminology

| Term | Definition |
|------|-----------|
| **Node** | A computer. |

## 3. Background

Background text.{cites}

## 4. What is X?

X is a thing.

## 5. How does it work?

### 5.1 North star overview

Overview.

### 5.2 End-to-End Flow

```mermaid
graph TD
    A --> B
```

1. **A** sends to B.

## 6. Key Challenges and Trade-offs

| Challenge | Trade-off |
|-----------|-----------|
| One | Two |

## 7. Risks and Limitations

1. A limit.

## 8. SMEs

| Person | Expertise | Suggested question |
|--------|-----------|-------------------|
| **Ann** | X | Y? |

## 9. References

### 9.1 Primary sources (read in full)

None.
{('### 9.2 Citations' + chr(10) + chr(10) + citations + chr(10)) if sources else ''}
## 10. Topic tags

- Primary: leaf-a

## 11. Metadata

{chr(10).join(meta)}
{extra_metadata}'''


TAGS_YAML = '''# Hierarchical topic tags.

root-topic:
  description: "The root topic"
  parent: null
  sub_tags: [leaf-a, leaf-b]
  ingested: []
  groomed: []
  smes: []

leaf-a:
  description: "First leaf about alpha systems"
  parent: root-topic
  sub_tags: []
  ingested:
    - ingested/alpha-doc.md
  groomed:
    - groomed/what-is-alpha.md
  smes:
    - "Ann — alpha author"

leaf-b:
  description: "Second leaf about beta caching"
  parent: root-topic
  sub_tags: []
  ingested:
    - ingested/beta-doc.md
  groomed: []
  smes: []
'''


def make_wiki(tmp, git=True):
    """A small, valid wiki in `tmp`: a root tag with two leaves, two saved
    sources (one also tagged on leaf-b), a link source, and one narrative.
    Returns the root path."""
    root = tmp
    alpha = b'# Alpha\n\nAlpha systems retry requests.\n\n## Details\n\nMore about alpha.\n\n---\n\n<!-- llm-wiki:original-source -->\n## Original source\n\n- URL: <https://example.com/alpha>\n'
    beta = b'# Beta\n\nBeta caching keeps hot data close.\n\n---\n\n<!-- llm-wiki:original-source -->\n## Original source\n\n- URL: <https://example.com/beta>\n'
    write(root, 'ingested/alpha-doc.md', alpha, binary=True)
    write(root, 'ingested/beta-doc.md', beta, binary=True)
    write(root, 'ingested/images/.gitkeep', '')
    write(root, 'tags/tags.yaml', TAGS_YAML)
    write(root, 'ingested/manifest.yaml', f'''# Source registry, keyed by slug.

alpha-doc:
  file: ingested/alpha-doc.md
  type: raw_content
  size_bytes: {len(alpha)}
  original_url: https://example.com/alpha
  content_modified: "2026-09-01T00:00:00Z"
  content_ingested: "2026-09-02T00:00:00Z"
  content_md5: {md5(alpha)}
  tags: [leaf-a]
  abstract: "Alpha systems and how they retry requests. [Authority A; 2026-09-01]"

beta-doc:
  file: ingested/beta-doc.md
  type: raw_content
  size_bytes: {len(beta)}
  original_url: https://example.com/beta
  content_modified: "2026-09-01T00:00:00Z"
  content_ingested: "2026-09-02T00:00:00Z"
  content_md5: {md5(beta)}
  tags: [leaf-b]
  abstract: "Beta caching keeps hot data close to readers."

gamma-link:
  type: link
  size_bytes: null
  original_url: https://example.com/gamma
  content_modified: "2026-08-01T00:00:00Z"
  content_ingested: "2026-09-02T00:00:00Z"
  content_md5: null
  tags: [leaf-a]
  abstract: "A pointer to gamma code."
''')
    narrative = narrative_text('What is alpha?', sources=[('alpha-doc', 'ingested/alpha-doc.md')])
    write(root, 'groomed/what-is-alpha.md', narrative)
    nbytes = narrative.encode('utf-8')
    write(root, 'groomed/manifest.yaml', f'''# Narrative registry, keyed by question slug.

what-is-alpha:
  file: groomed/what-is-alpha.md
  question: "What is alpha?"
  size_bytes: {len(nbytes)}
  version: "1.0"
  created: "2026-10-01"
  last_modified: "2026-10-02"
  tags:
    primary: [leaf-a]
    supporting: []
  sources_read_full:
    alpha-doc: {md5(alpha)}
  sources_abstract_only: [gamma-link]
  abstract: "{ABSTRACT}"
''')
    if git:
        git_init(root)
    return root


def git(root, *args, check=True):
    env = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@example.com', GIT_COMMITTER_NAME='t',
               GIT_COMMITTER_EMAIL='t@example.com', GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
    return subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, check=check, env=env)


def git_init(root):
    git(root, 'init', '-q', '-b', 'mainline')
    git(root, 'add', '-A')
    git(root, 'commit', '-q', '-m', 'init')


class WikiTestCase(unittest.TestCase):
    """A fresh fixture wiki per test, in a temporary directory."""

    git = True

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='llmwiki-test-')
        self.root = make_wiki(self.tmp, git=self.git)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def reset(self):
        """A fresh fixture wiki, for a test that checks several scenarios."""
        self.tearDown()
        self.setUp()

    def write(self, rel, text, binary=False):
        return write(self.root, rel, text, binary)

    def read(self, rel):
        return read(self.root, rel)


class LocalServer:
    """Serve a dict of path -> (status, headers, body bytes) on 127.0.0.1."""

    def __init__(self, routes):
        self.routes = routes
        routes_ref = self.routes

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - http.server API
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
