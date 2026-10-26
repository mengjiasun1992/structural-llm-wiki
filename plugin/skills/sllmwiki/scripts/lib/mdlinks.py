"""Links between the wiki's files: splitting a link into its file and anchor,
resolving it from the linking file, and checking that both exist."""

import functools
import os
import posixpath
import urllib.parse

from . import numbering, plaintext
from .util import read_text


def split(target):
    """(path, anchor) of a link target; anchor is '' without one."""
    path, _, frag = target.partition('#')
    return urllib.parse.unquote(path.split('?')[0]), urllib.parse.unquote(frag)


def resolve(from_rel, path):
    """The repository-relative path a link in from_rel points to; None when it leaves the repository."""
    joined = posixpath.normpath(posixpath.join(posixpath.dirname(from_rel), path))
    return None if joined == '..' or joined.startswith('../') else joined


@functools.lru_cache(maxsize=256)
def _anchors(path, mtime):
    return set(numbering.anchors(read_text(path)))


def anchors_of(root, rel):
    """The anchors of a markdown file in the repository."""
    path = os.path.join(root, rel)
    return _anchors(path, os.path.getmtime(path))


def problem(root, from_rel, target):
    """What's wrong with a link from from_rel, or None: a missing file, or an anchor the file doesn't have."""
    path, frag = split(target)
    rel = resolve(from_rel, path) if path else from_rel
    if rel is None or not os.path.isfile(os.path.join(root, rel)):
        return f'{target}: no such file'
    if frag and rel.endswith('.md') and plaintext.LINES.match(frag):
        return None if plaintext.lines(read_text(os.path.join(root, rel)), frag) is not None else f'{target}: {rel} has no code lines #{frag}'
    if frag and rel.endswith('.md') and frag not in anchors_of(root, rel):
        return f'{target}: {rel} has no section #{frag}'
    return None
