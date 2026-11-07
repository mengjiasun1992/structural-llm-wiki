"""sllmwiki: the Structural LLM Wiki's commands.

  sllmwiki <command> [<args>]   run one; sllmwiki <command> --help explains it
  sllmwiki --version            this package's version, the plugin's too
"""

import importlib
import sys

from sllmwiki import __version__
from sllmwiki.lib.util import setup_stdio

COMMANDS = ('book', 'check-upstream', 'cited-sections', 'contributors', 'fetch-source', 'finish-narrative', 'init', 'manifest',
            'narrative-format', 'publish', 'reading-plan', 'release', 'review-checklist', 'search', 'tag-tree', 'wiki-check')


def main(argv=None):
    """Run `sllmwiki <command> <args>`; its exit code. 2 for an unknown command."""
    argv = sys.argv[1:] if argv is None else list(argv)
    setup_stdio()
    if argv[:1] == ['--version']:
        print(f'sllmwiki {__version__}')
        return 0
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__.strip() + '\n\ncommands: ' + ', '.join(COMMANDS))
        return 0 if argv else 2
    if argv[0] not in COMMANDS:
        print(f"sllmwiki: no command {argv[0]!r}; the commands: {', '.join(COMMANDS)}", file=sys.stderr)
        return 2
    module = importlib.import_module('sllmwiki.commands.' + argv[0].replace('-', '_'))
    return module.main(argv[1:])
