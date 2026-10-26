"""Where a wiki keeps its files (design doc §3), and the command-line plumbing
every script shares: finding the wiki, usage errors and failures.

The layout is fixed. Paths here are from the repository root; manifests record
a saved file's path from the content folder (sources/<slug>.md), which
in_content() turns into one from the root.
"""

import os
import sys

from .util import git_root, setup_stdio

SKILL_URL = 'https://github.com/mengjiasun1992/structural-llm-wiki'  # the skill's home, where a wiki or its book points to it
CONTENT = 'sllmwiki'
TAGS_DIR = f'{CONTENT}/tags'
TAGS = f'{TAGS_DIR}/tags.yaml'
SOURCES = f'{CONTENT}/sources'
SOURCES_MANIFEST = f'{SOURCES}/manifest.yaml'
NARRATIVES = f'{CONTENT}/narratives'
NARRATIVES_MANIFEST = f'{NARRATIVES}/manifest.yaml'
OBSIDIAN_GRAPH = f'{CONTENT}/.obsidian/graph.json'
# the index and the templates aren't knowledge: their dot names keep them out of Obsidian (file list, graph, search)
INDEX = f'{CONTENT}/.SLLMWIKI_INDICES.md'
TEMPLATES = f'{CONTENT}/.templates'  # the wiki's own narrative templates and language packs
CONFIG = f'{CONTENT}/Config.toml'
# where these were before 1.0: init moves them, and the settings are read at the root until it does
OLD_CONFIG = 'Config.toml'
OLD_TEMPLATES = ('templates', f'{CONTENT}/templates')
OLD_INDEX = ('SLLMWIKI_INDICES.md', f'{CONTENT}/SLLMWIKI_INDICES.md')


def in_content(rel):
    """A path a manifest records (from the content folder) as a path from the repository root."""
    return f'{CONTENT}/{rel}'


def config_path(root):
    """The wiki's Config.toml: in the content folder, or at the root while init hasn't moved it there."""
    new, old = os.path.join(root, CONFIG), os.path.join(root, OLD_CONFIG)
    return old if not os.path.isfile(new) and os.path.isfile(old) else new


def find_root(start=None):
    """The wiki's root for a folder: the git repository around it, else the folder itself."""
    start = os.path.abspath(start or os.getcwd())
    return git_root(start) or start


def is_wiki(root):
    return os.path.isfile(os.path.join(root, TAGS))


class Cli:
    """A script's name and usage, for its errors: usage() exits 2, fail() exits 1."""

    def __init__(self, prog, usage):
        self.prog, self.usage_text = prog, usage

    def usage(self, msg):
        print(f'{self.prog}: {msg}\n{self.usage_text}', file=sys.stderr)
        sys.exit(2)

    def fail(self, msg):
        print(f'{self.prog}: {msg}', file=sys.stderr)
        sys.exit(1)

    def take_root(self, argv):
        """(the --root value or None, argv without it)."""
        argv = list(argv)
        if '--root' not in argv:
            return None, argv
        at = argv.index('--root')
        if at + 1 >= len(argv) or argv[at + 1].startswith('--'):
            self.usage('--root needs a folder')
        root = argv[at + 1]
        del argv[at:at + 2]
        return root, argv

    def wiki(self, root=None):
        """The absolute root of the wiki at root (default: around the working
        directory); fails when it isn't a wiki."""
        root = os.path.abspath(root) if root else find_root()
        if not is_wiki(root):
            self.fail(f'{root} is not a wiki (no {TAGS}): run /sllmwiki:init first')
        from . import language
        language.use(root)  # a pack that doesn't parse is wiki-check's to report
        return root


def entry(main):
    """Run a script's main(argv) as the program: UTF-8 output, its exit code."""
    setup_stdio()
    sys.exit(main(sys.argv[1:]))
