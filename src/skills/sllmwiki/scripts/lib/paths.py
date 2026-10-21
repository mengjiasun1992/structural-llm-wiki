"""Where a wiki keeps its files: the paths in its Config.toml
(lib/config.py), with the defaults for anything it doesn't set. Each
manifest lives in the folder it describes (by default ingested/manifest.yaml
and groomed/manifest.yaml).
"""

import os

from .config import layout


def manifest_file(root, kind):
    """The manifest's path relative to the wiki root."""
    return layout(root).manifest(kind)


def tags_file(root):
    """tags.yaml's path relative to the wiki root."""
    return layout(root).tags


def is_wiki(root):
    """Whether root is a wiki: it has its tags file."""
    return os.path.exists(os.path.join(root, tags_file(root)))
