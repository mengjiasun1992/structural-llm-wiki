#!/usr/bin/env python3
"""pypi-readme: point a README's relative links and images at GitHub, for PyPI's page.

Usage: python3 pypi-readme.py --repo OWNER/NAME --ref REF [--write] README.md

pyproject.toml makes README.md the package's long description, which PyPI shows
on the project's page. The README refers to its images and pages by paths
relative to the repository, which work on GitHub and in a checkout but lead
nowhere on PyPI (issue #168). This rewrites each relative target, at the ref
the package is built from, so an old release's page keeps that release's files:

  - an image (.svg, .png, .jpg, .jpeg, .gif, .webp) becomes
    https://raw.githubusercontent.com/OWNER/NAME/REF/<path>
  - a folder (a path ending in /) becomes https://github.com/OWNER/NAME/tree/REF/<path>
  - anything else becomes https://github.com/OWNER/NAME/blob/REF/<path>, its #section kept

It reads markdown links and images, reference definitions ([x]: path) and HTML
src and href attributes, and leaves alone URLs with a scheme (https:, mailto:),
links within the page (#…), and code (fenced blocks and code spans).

It prints the rewritten README, or with --write saves it over the file. The
publish workflow runs it on the release checkout before building the package;
the README in the repository keeps its relative paths.

Exit code: 0 = rewritten, 1 = a relative target it can't point anywhere (one
that leaves the repository with ../), named on stderr, 2 = usage error.
"""

import sys

sys.dont_write_bytecode = True

import argparse  # noqa: E402
import posixpath  # noqa: E402
import re  # noqa: E402

IMAGES = ('.svg', '.png', '.jpg', '.jpeg', '.gif', '.webp')
SCHEME = re.compile(r'[A-Za-z][A-Za-z0-9+.-]*:')
FENCE = re.compile(r'\s{0,3}(`{3,}|~{3,})')
CODE_SPAN = re.compile(r'(`+)(?:.+?)\1')
INLINE = re.compile(r'(\]\(\s*<?)([^)\s>]+)')  # [text](target "title") and ![alt](target)
REFERENCE = re.compile(r'(\A\s{0,3}\[[^\]]+\]:\s*<?)([^\s>]+)')  # [label]: target
HTML = re.compile(r'(\b(?:src|href)\s*=\s*["\'])([^"\']+)')


def is_relative(target):
    return not (SCHEME.match(target) or target.startswith(('#', '//')))


def absolute(target, repo, ref):
    """The URL for a relative target, or None when it leaves the repository."""
    path, hash_, fragment = target.partition('#')
    folder = path.endswith('/')
    path = posixpath.normpath(path.lstrip('/'))
    if path == '..' or path.startswith('../'):
        return None
    if path.lower().endswith(IMAGES):
        return f'https://raw.githubusercontent.com/{repo}/{ref}/{path}'
    kind = 'tree' if folder or path == '.' else 'blob'
    path = '' if path == '.' else path
    return f'https://github.com/{repo}/{kind}/{ref}/{path}' + (hash_ + fragment)


def rewrite(text, repo, ref):
    """(the text with its relative targets made absolute, [the targets it couldn't])."""
    unresolved = []

    def fix(m):
        target = m.group(2)
        if not is_relative(target):
            return m.group(0)
        url = absolute(target, repo, ref)
        if url is None:
            unresolved.append(target)
            return m.group(0)
        return m.group(1) + url

    def prose(part):
        part = INLINE.sub(fix, part)
        part = REFERENCE.sub(fix, part)
        return HTML.sub(fix, part)

    out, fence = [], None
    for line in text.split('\n'):
        m = FENCE.match(line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = None
            out.append(line)
            continue
        if m:
            fence = m.group(1)
            out.append(line)
            continue
        pieces, last = [], 0
        for span in CODE_SPAN.finditer(line):
            pieces += [prose(line[last:span.start()]), span.group(0)]
            last = span.end()
        out.append(''.join(pieces) + prose(line[last:]))
    return '\n'.join(out), unresolved


def main(argv):
    p = argparse.ArgumentParser(prog='pypi-readme.py', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--repo', required=True, help='OWNER/NAME on GitHub')
    p.add_argument('--ref', required=True, help='the tag or commit the package is built from')
    p.add_argument('--write', action='store_true', help='save the result over the file instead of printing it')
    p.add_argument('readme')
    args = p.parse_args(argv)
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', args.repo):
        p.error(f'--repo must be OWNER/NAME, not {args.repo!r}')
    with open(args.readme, encoding='utf-8') as f:
        text, unresolved = rewrite(f.read(), args.repo, args.ref)
    if unresolved:
        print('pypi-readme: these targets leave the repository, so nothing on GitHub can stand for them:',
              *unresolved, sep='\n  ', file=sys.stderr)
        return 1
    if args.write:
        with open(args.readme, 'w', encoding='utf-8') as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
