"""A release of the wiki and its book (docs/book_design.md §2.2, §6.7): its version,
what changed since the last release, whether the default branch's checks pass,
and the notes the agent reviews before the release is made."""

import datetime
import re

from . import language, layout, markers, metadata, wikiyaml
from .gitrepo import git

FAILED = ('failure', 'timed_out', 'cancelled', 'action_required', 'startup_failure', 'stale')
WORKFLOW = '.github/workflows/release-book.yml'
FORMAT_NAMES = {'html': 'HTML', 'pdf': 'PDF', 'epub': 'EPUB'}


def version(taken, today=None):
    """The release's version: the date, vYYYY.MM.DD, then .2, .3 for later releases that day."""
    base = 'v' + (today or datetime.datetime.now(datetime.timezone.utc).date()).strftime('%Y.%m.%d')
    if base not in taken:
        return base
    n = 2
    while f'{base}.{n}' in taken:
        n += 1
    return f'{base}.{n}'


def checks(runs):
    """('passing'|'failing'|'pending'|'none', [names of the failing or unfinished checks]) for a
    commit's check runs ([{name, status, conclusion}], GitHub's check-runs API)."""
    if not runs:
        return 'none', []
    failing = sorted({r['name'] for r in runs if r.get('status') == 'completed' and r.get('conclusion') in FAILED})
    if failing:
        return 'failing', failing
    pending = sorted({r['name'] for r in runs if r.get('status') != 'completed'})
    return ('pending', pending) if pending else ('passing', [])


def _read(root, rev, path):
    return git(root, 'show', f'{rev}:{path}') if rev else ''


def _narratives(root, rev):
    """{slug: text} of the narratives at rev ({} without one)."""
    if not rev:
        return {}
    names = git(root, 'ls-tree', '--name-only', f'{rev}:{layout.NARRATIVES}').split('\n')
    return {n[:-3]: _read(root, rev, f'{layout.NARRATIVES}/{n}') for n in names if n.endswith('.md')}


def _sources(root, rev):
    text = _read(root, rev, layout.SOURCES_MANIFEST)
    try:
        return set(wikiyaml.parse(text)) if text else set()
    except wikiyaml.YamlError:
        return set()


def changes(root, previous, commit):
    """What changed in the wiki from the previous release's tag (None for a first release) to commit:
    {'added': [(question, version)], 'updated': [(question, old, new)], 'removed': [question],
     'sources': [new source slugs], 'narratives': n, 'source_count': n, 'open_questions': n}."""
    before, after = _narratives(root, previous), _narratives(root, commit)

    def q(text, slug):
        return metadata.title(text) or slug

    def v(text):
        return metadata.read(text)['version'] or '?'
    out = {
        'added': sorted((q(after[s], s), v(after[s])) for s in after if s not in before),
        'updated': sorted((q(after[s], s), v(before[s]), v(after[s])) for s in after if s in before and after[s] != before[s]),
        'removed': sorted(q(before[s], s) for s in before if s not in after),
        'narratives': len(after),
    }
    now = _sources(root, commit)
    out['sources'] = sorted(now - _sources(root, previous))
    out['source_count'] = len(now)
    out['open_questions'] = sum(1 for text in after.values() for _, _, m in markers.uses(text) if m == '[?]')
    return out


def notes(found, previous, formats, pack=None, failing=()):
    """The release notes the agent reviews: what changed since the previous release, the open
    questions, the book's formats; with failing, the checks that failed (a release made anyway)."""
    pack = pack or language.ENGLISH
    t = pack.t
    out = []
    if failing:
        out += ['> [!WARNING]', f'> {t("Released while these checks failed:")} {", ".join(failing)}', '']
    if previous:
        out += [f'## {t("Since")} {previous}', '']
    else:
        out += [f'## {t("First release")}', '', f'{found["narratives"]} {t("narratives")}, {found["source_count"]} {t("sources")}.', '']
    for title, rows in ((t('New narratives'), [f'- {qq} ({vv})' for qq, vv in found['added']]),
                        (t('Updated narratives'), [f'- {qq} ({a} → {b})' for qq, a, b in found['updated']]),
                        (t('Removed narratives'), [f'- {qq}' for qq in found['removed']])):
        if rows and (previous or title != t('New narratives')):
            out += [f'**{title}:**', ''] + rows + ['']
    if previous:
        out += [f'**{t("New sources")}:** {len(found["sources"])}' + (f' ({", ".join(found["sources"])})' if found['sources'] else ''), '']
        if not (found['added'] or found['updated'] or found['removed'] or found['sources']):
            out += [t('Nothing in the wiki changed since the last release.'), '']
    out += [f'**{t("Open questions")}:** {found["open_questions"]} [?]', '']
    book = ', '.join(FORMAT_NAMES.get(f, f) for f in formats)
    out += [f'**{t("Book")}:** ' + (book if book else t('none: turn a format on in Config.toml\'s [structural-llm-wiki-release]')), '']
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(out)).strip() + '\n'
