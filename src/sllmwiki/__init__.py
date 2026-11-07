"""sllmwiki: the Structural LLM Wiki's code. The plugin's instructions run it as
`sllmwiki <command>`; a wiki's GitHub Actions run it from this repository at the tag."""

import os

__version__ = '1.2.1'  # the plugin's version too (.claude-plugin/plugin.json); a test keeps them equal

TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')  # what init installs, the narrative templates, the book's
