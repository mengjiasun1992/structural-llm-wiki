#!/usr/bin/env python3
"""review-checklist: are all of a run's review boxes ticked? (design doc §5.2)

  review-checklist.py [--file PR_BODY.md]   (default: the PR_BODY environment variable)

Reads a pull request's description, finds its "## Review checklist" section
(publish.py writes it first), and fails while any box there is unticked. A
description without the section isn't a run's, and passes.
Exit code: 0 all ticked or no checklist, 1 boxes left, 2 usage error.
"""

import os
import re
import sys

sys.dont_write_bytecode = True

from lib.layout import Cli, entry  # noqa: E402
from lib.util import read_text  # noqa: E402

cli = Cli('review-checklist.py', 'usage: review-checklist.py [--file PR_BODY.md]')
BOX = re.compile(r'\s*[-*] \[( |x|X)\] (.*)')


def boxes(body):
    """[(ticked, item)] in the Review checklist section, or None without one."""
    lines = body.replace('\r\n', '\n').split('\n')
    start = next((i for i, line in enumerate(lines) if re.match(r'#{1,6} Review checklist\s*\Z', line)), None)
    if start is None:
        return None
    out = []
    for line in lines[start + 1:]:
        if re.match(r'#{1,6} ', line):
            break
        m = BOX.match(line)
        if m:
            out.append((m.group(1) != ' ', m.group(2).strip()))
    return out


def main(argv):
    if argv[:1] == ['--file'] and len(argv) == 2:
        body = read_text(argv[1])
    elif not argv:
        body = os.environ.get('PR_BODY', '')
    else:
        cli.usage('unknown arguments')
    found = boxes(body)
    if found is None:
        print('review-checklist: no "Review checklist" section, so not a run\'s pull request: nothing to check')
        return 0
    left = [item for ticked, item in found if not ticked]
    for item in left:
        print(f'not ticked: {item}')
    print(f'review-checklist: {len(found) - len(left)} of {len(found)} ticked')
    return 1 if left else 0


if __name__ == '__main__':  # pragma: no cover
    entry(main)
