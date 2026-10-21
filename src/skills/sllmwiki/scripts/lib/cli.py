"""Command-line plumbing the scripts share: usage errors and failures that end
the run with an exit code (sys.exit: 2 = usage, 1 = failure), and finding the
wiki a script works on."""

import os
import sys

from .config import SettingsError, load_layout
from .util import git_root, setup_stdio


class Cli:
    def __init__(self, prog, usage):
        self.prog, self.usage_text = prog, usage

    def usage(self, msg):
        print(f'{self.prog}: {msg}\n{self.usage_text}', file=sys.stderr)
        sys.exit(2)

    def fail(self, msg):
        print(f'{self.prog}: {msg}', file=sys.stderr)
        sys.exit(1)

    def wiki(self, root=None):
        """(root, layout) of the wiki at root (default: the git repository
        around the working directory); fails when Config.toml is invalid or
        the folder isn't a wiki."""
        root = os.path.abspath(root or git_root())
        try:
            layout = load_layout(root)
        except SettingsError as e:
            self.fail(str(e))
        if not os.path.exists(os.path.join(root, layout.tags)):
            self.fail(f'{root} is not a wiki (no {layout.tags}); run /sllmwiki:init first')
        return root, layout

    def main(self, run, argv):
        """run(argv)'s exit code, with stdout and stderr set up for the scripts' output."""
        setup_stdio()
        return run(argv)


def split_list(value):
    """"a, b,,c" -> ['a', 'b', 'c']"""
    return [t.strip() for t in value.split(',') if t.strip()]
