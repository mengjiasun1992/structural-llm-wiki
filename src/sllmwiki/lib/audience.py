"""The wiki's audience profile (design doc §4.5.7): who reads this wiki and what they need, in at most
MAX_WORDS words, in the markdown file Config.toml's audience names (sllmwiki/.templates/audience.md by
default; "" for none), outside the Obsidian vault. When it says something, it comes before the skill and
every guide: narrative-format --guide prints it first and --audience alone, and wiki-check reports one over
its budget (AUDIENCE_TOO_LONG). init writes STARTER, which says nothing until the owner fills it in.
"""

import os
import re

from . import config, language
from .util import read_text

MAX_WORDS = 800
STARTER = ('# Who reads this wiki\n\n'
           '<!-- Empty for now: the skill writes for the readers its guides describe. Say who reads this wiki, what they\n'
           'already know and what they need from an answer, in at most 800 words; it comes before the skill\'s and the\n'
           'guides\' rules on how to write. Config.toml\'s audience names this file. -->\n')
COMMENT = re.compile(r'<!--.*?-->', re.S)


def path(root):
    """The profile's path in the repository, or None when Config.toml's audience is ""."""
    return config.get(root).settings['audience'] or None


def content(text):
    """The text the profile says: without its HTML comments, and nothing when only headings are left."""
    text = COMMENT.sub('', text).strip()
    return text if any(line.strip() and not line.lstrip().startswith('#') for line in text.split('\n')) else ''


def read(root):
    """The profile's text, or None when the wiki has none: no path, no file, or a file that says nothing."""
    rel = path(root)
    if not rel or not os.path.isfile(os.path.join(root, rel)):
        return None
    return content(read_text(os.path.join(root, rel))) or None


def problems(root):
    """[what's wrong with the profile]: only its length, which is checkable; what it says is the owner's."""
    text = read(root)
    n = language.words(text) if text else 0
    if n > MAX_WORDS:
        return [f'{path(root)} has {n} words, over its {MAX_WORDS}: keep it to who reads the wiki and what they need']
    return []
