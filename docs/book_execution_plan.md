# Execution plan: the wiki as a book

- **Status:** proposed
- **Design:** [book_design.md](book_design.md)

## 1. Approach

The riskiest parts are proved first, on a throwaway spike, before anything
ships: that Sphinx reads the staged wiki with GitHub's anchors, that headless
Chrome turns diagrams and math into SVG that every format shows, and how long
a build takes. Then the book is built in the order its formats depend on each
other: staging (which every format and the pull request check use), the HTML
(which the PDF is printed from), the release flow, the PDF, the EPUB, and last
the pull request check for diagrams and math.

Every phase ends with `mainline` green and the skill usable, and each
`Config.toml` key arrives in the phase that makes its format work, so no
setting names something that isn't there. One pull request per item, or per
small group of items in the same files.

## 2. How every phase is tested and evaluated

**Unit tests,** as for every script (`AGENTS.md`): a `tests/test_<module>.py`
per module in the same commit; coverage of `scripts/` at 95% or above; the
tests pass on Python 3.9; ruff 0.8.4 is clean. Staging and the release
script are standard-library Python and fully unit-tested on the fixture wiki
in `tests/helpers.py`, which gains what a book needs: two tags with parts,
a `built_on` chain, a figure, a diagram, inline and display math, a `[?]`
marker, and a Chinese narrative with its language pack.

**A book build in this repository's CI** (`.github/workflows/check-book.yml`,
from Phase 2): on every pull request that touches the book's code, build the
fixture wiki with the pinned Sphinx, MyST-Parser, mermaid.js, MathJax and
fonts, and run `src/tools/check-book.py` on the outputs:

| Check | How |
|---|---|
| Every internal link and anchor resolves | parse the HTML; every `href="#…"` has its `id` |
| Nothing is left unrendered | no ```` ```mermaid ````, `$…$` or `<script>` in the output; one SVG per diagram and formula in `book.json` |
| Self-contained | no `src` or `href` to `http(s)://` except the original-source links in Appendix A |
| The PDF | page count within a range; every font embedded (`pdffonts`); the Chinese chapter's text extracts as Chinese (`pdftotext`), not empty boxes |
| The EPUB | `epubcheck` with 0 errors |
| Time and size | the build within its budget (§5) |

**Behavior evals** for `/sllmwiki:release` (`evals/`, `claude plugin eval`),
with a stub `gh` on `PATH` that records its calls and a fixture wiki with a
previous release tag:

- it picks the version and writes notes naming the narratives that changed;
- it refuses on a red default branch, and releases when told "release anyway",
  saying what was failing;
- it reports the files' links when the workflow succeeds, and what failed
  when it doesn't.

**Real releases.** Each phase's evaluation ends with a release of the demo
wiki and of the owner's wiki. The owner reads the result against the rubric
in §6 and files what's wrong. A phase is done when the rubric passes on both.

## 3. Order

```text
B0 spike ─► B1 stage + PR check ─► B2 pre-render + HTML ─► B3 release flow ─► B4 PDF ─► B5 EPUB ─► B6 diagram and math PR check
```

B4 and B5 are independent of each other once B3 lands, and can swap.

## 4. Phases

### 4.1 Phase B0: spike

**Goal.** Prove the three risky assumptions on the demo wiki, in a branch that
is thrown away, and fix the versions everything is pinned to.

| # | Item | Answers |
|---|---|---|
| B0.1 | Sphinx and MyST-Parser on a hand-staged copy of the demo wiki, with `myst_heading_slug_func` set to `numbering.anchor` | Do GitHub-style anchors, including CJK ones, resolve? Which MyST settings does the wiki need? |
| B0.2 | Headless Chrome with mermaid.js and MathJax 3 producing SVG for the demo's diagrams and formulas, inserted as inline SVG | Does inline math align on the text line? Do the SVGs survive `singlehtml`, Chrome's print and the EPUB builder? |
| B0.3 | `singlehtml` with its images and stylesheet inlined into one file; Chrome printing it; the EPUB builder; `epubcheck` | Does each output come out right? What does the print stylesheet need? |
| B0.4 | The whole spike as a workflow run on GitHub | Build time cold and cached; file sizes; which versions of Sphinx, MyST-Parser, mermaid.js (close to GitHub's), MathJax and the Noto fonts to pin |

**Evaluate.** A short write-up in the B1 pull request: what worked, what
didn't, measured times and sizes, and the pinned versions. If an assumption
fails (inline SVG in EPUB, say), the design changes before B1, in
`book_design.md`.

**Done when** the three outputs of the demo wiki exist, open correctly, and
the design matches what the spike found.

### 4.2 Phase B1: staging and the pull request check

**Goal.** The book's content, as plain Markdown, from any wiki, checked on
every pull request. No Sphinx yet, and no setting.

| # | Code change | What it does |
|---|---|---|
| B1.1 | `lib/book.py`: the model | Parts from `tags.yaml`; each narrative under its primary tag; chapter order (`built_on` topologically, then template, then question); the sources each chapter cites |
| B1.2 | `lib/book.py`: rewriting | A label unique across the book before every heading (design §6.2); citations to Appendix A entries; links to sections and chapters to their labels; links to tag pages and the index to parts; figures copied; Metadata reduced to a version line |
| B1.3 | `lib/book.py`: generated pages | Cover and front page (§9 of the design, in the wiki's language through its language pack); parts' opening pages; Appendix A (sources), B (glossary, grouped by term) and C (open questions) |
| B1.4 | `scripts/book.py stage <out>` | Writes the folder and `book.json` (order, anchors, diagrams and formulas to render, problems) |
| B1.5 | `wiki-check.py`, which the `wiki-checks` action runs | Run staging's model and rewriting on every pull request, writing nothing; report `BOOK_LINK` (a link or anchor the book can't resolve), `BOOK_CYCLE` (a `built_on` cycle) and `BOOK_FIGURE` (a missing figure), unless the wiki's own checks already report that link |
| B1.6 | Language packs | The book's labels (Contents, Part, Appendix, Sources, Glossary, Open questions, the front page) in `en.md` and `zh-Hans.md` |

**Test.** Order: a chain, a cycle, ties broken by template then question.
Rewriting: every link kind, a citation to a link-only source, an anchor with
CJK characters. Generated pages: the glossary with one term defined
differently in two narratives; a source cited by two chapters; a `[?]` on a
heading and on a statement. The PR check: each code on the fixture, and none
on the demo wiki.

**Evaluate.** Stage the demo wiki and the owner's wiki and read the folder on
GitHub: is the order a sensible reading path, does every citation land on its
source, is the glossary useful? Record the problems the check finds on the
owner's wiki, and fix them in the wiki, not by loosening the check.

**Done when** both wikis stage with no problems and the owner agrees with the
chapter order.

### 4.3 Phase B2: pre-render and the HTML book

**Goal.** A single self-contained HTML file, built in CI and on a developer's
computer.

| # | Code change | What it does |
|---|---|---|
| B2.1 | `scripts/book.py render` | Headless Chrome with the pinned mermaid.js and MathJax (vendored in the action) turns everything in `book.json` into SVG, with its source as alt text; cached by content hash |
| B2.2 | `templates/book/conf.py`, `templates/book/_static/book.css` (the skill's, so `book.py build` works anywhere) | Sphinx and MyST settings (the hook that makes staging's labels the section ids, alerts as admonitions, the wiki's language, `version` and `copyright`); the `basic` theme with one stylesheet |
| B2.3 | `scripts/book.py build --formats html` | Stage, render, `sphinx-build -b singlehtml`, then inline the stylesheet and images into `<wiki>-<version>.html`, drop the theme's navigation and scripts, and rewrite `#document-<doc>#<id>` links to `#<id>` |
| B2.4 | `src/actions/release-book/action.yml` | Install the pinned tools and fonts (cached), run `book.py build`, upload the result as an artifact (previews only, for now) |
| B2.5 | `.github/workflows/check-book.yml`, `src/tools/check-book.py` | Build the fixture wiki on pull requests that touch the book, and check the output (§2) |

**Test.** `render` with a stub browser (the unit tests don't need Chrome) and,
in `check-book`, with the real one. `check-book.py` has its own tests, on a
good and a broken output.

**Evaluate.** Build the demo and the owner's wiki with `workflow_dispatch`.
Open each HTML file offline: rubric items 1 to 7 (§6).

**Done when** both HTML books pass the rubric and `check-book` is green.

### 4.4 Phase B3: the release flow

**Goal.** `/sllmwiki:release`, or *Publish* on GitHub, produces a release with
the HTML book attached.

| # | Code change | What it does |
|---|---|---|
| B3.1 | `lib/config.py`, `templates/wiki/Config.toml` | The `[structural-llm-wiki-release]` table with `html_book` (default `false`) |
| B3.2 | `templates/release-book.yml`, `init.py` | The release workflow (`release: published`, `workflow_dispatch`), installed and refreshed by `init` |
| B3.3 | The action | Build each format that's on, `gh release upload` it, append warnings and failures to the release notes; a failing format doesn't stop the others |
| B3.4 | `scripts/release.py plan, create, wait` | Check the default branch and its checks; pick the version; draft notes from the manifests at the last release's tag and now; create the release; follow the run and report |
| B3.5 | `workflows/release.md`, `src/commands/release.md`, `SKILL.md` | The workflow and its routing row, within the instruction budgets |
| B3.6 | The README and the wiki's README template | How to release, and a "Read the book" link to `/releases/latest` |

**Test.** `release.py` against a fixture repository with tags and a stub `gh`:
versions on a first release, a second the same day, and a new day; the notes'
content; refusals. `init` installs and refreshes the workflow. The evals in §2.

**Evaluate.** Release the demo and the owner's wiki with `/sllmwiki:release`:
the time from command to links, and whether the notes say what changed
correctly (checked against the merged pull requests).

**Done when** both releases work from the command and from GitHub's *Publish*,
and the evals pass 3 runs in 3.

### 4.5 Phase B4: the PDF

| # | Code change | What it does |
|---|---|---|
| B4.1 | `book.css` print rules | Cover page; a new page per part and chapter; page numbers and a running header (Chrome's header and footer templates); no table or diagram split across pages where it fits on one |
| B4.2 | `book.py build --formats pdf` | Chrome prints the single-file HTML to `<wiki>-<version>.pdf` |
| B4.3 | The action | Install Noto Sans, Noto Sans CJK and Noto Sans Math |
| B4.4 | `Config.toml` | `pdf_book`, default `true` |

**Test.** `check-book` on the fixture: page count, embedded fonts, the Chinese
chapter extracts as Chinese.

**Evaluate.** Release both wikis with the PDF; print a few pages. Rubric items
1 to 9.

**Done when** both PDFs pass the rubric.

### 4.6 Phase B5: the EPUB

| # | Code change | What it does |
|---|---|---|
| B5.1 | `book.py build --formats epub` | Sphinx's EPUB 3 builder from the same staged, pre-rendered folder; the cover image; the navigation document from the contents |
| B5.2 | `book.css` small-screen rules | Wide tables scroll; diagrams and display math fit the width |
| B5.3 | `check-book` | `epubcheck` on the fixture's EPUB |
| B5.4 | `Config.toml` | `epub_book`, default `false` |

**Test.** `epubcheck` with 0 errors on the fixture.

**Evaluate.** Open both wikis' EPUBs in Apple Books, Calibre and Kindle (Send
to Kindle) on a phone and a tablet. Rubric items 1 to 8 and 10.

**Done when** the EPUBs pass the rubric in all three readers.

### 4.7 Phase B6: the diagram and math check on pull requests

| # | Code change | What it does |
|---|---|---|
| B6.1 | `scripts/book.py parse` | Headless Chrome parses only the diagrams and formulas a pull request changed (`mermaid.parse`, MathJax's TeX input) |
| B6.2 | `wiki-checks` action | Run it when a pull request changes a ```` ```mermaid ```` block or math; report `DIAGRAM_SYNTAX` and `MATH_SYNTAX` with the line and the parser's message |

**Test.** The fixture with a diagram that has a `;` in a message (the design
doc's own bug) and a formula with an unknown macro.

**Evaluate.** Run on the owner's wiki's history: how many past pull requests
would it have failed, and were those real errors?

**Done when** it flags real errors only, in under 30 seconds.

## 5. Fixed values

| What | Value | Revisit |
|---|---|---|
| Sphinx, MyST-Parser | 9.1.0 and 5.1.0, pinned in the action | each quarter, with a `check-book` run |
| mermaid.js | 12.2.0, GitHub's in October 2026, vendored | when GitHub's changes |
| MathJax | 3.2.2 (`tex-svg-full.js`), vendored; GitHub's version not yet confirmed | when B6 or GitHub shows a difference |
| epubcheck | 5.3.0, on the runner's Java 17 | each quarter |
| Fonts | Noto Sans, Noto Sans Math (notofonts), Noto Sans CJK SC (noto-cjk, OTF) | when a language pack needs another script |
| Build time, a few dozen narratives | under 4 minutes cold, 3 cached | if a real wiki exceeds it |
| PR check time | staging under 10 seconds; diagram and math parse under 30 | the same |
| File size, the demo wiki | PDF under 10 MB; EPUB and HTML under 5 MB | the same |

## 6. The rubric for a real book

Read by the owner for each phase's evaluation:

1. The cover shows the wiki, the version, the date and the commit.
2. The contents and parts follow the tag tree, and the chapter order is a
   sensible reading path.
3. Every diagram is drawn and legible; none is left as code.
4. Every formula is typeset, inline math sits on its line, and none is left
   as TeX.
5. Every citation goes to its source in Appendix A, and that entry links to
   the original.
6. Every link between chapters, and to a section of another chapter, works.
7. The glossary and the open questions read well, and nothing in them is
   wrong.
8. A Chinese chapter reads as Chinese, with Chinese labels.
9. The PDF: page breaks at parts and chapters, page numbers, nothing cut at
   the margins.
10. The EPUB: text reflows, tables and diagrams fit or scroll, the table of
    contents works.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Inline SVG behaves differently across e-readers | `epubcheck` passes (B0); B5's reading in Apple Books, Calibre and Kindle decides; fall back to SVG images (`<img>`) for diagrams, keeping inline SVG for math |
| A wide left-to-right diagram, scaled to the page, has text too small to read in the PDF | B4: a minimum scale, and a wide diagram on a landscape page or across the full page width |
| GitHub's mermaid or MathJax version moves, and a diagram GitHub draws doesn't parse in the book | pin close to GitHub's; B6's check uses the same versions as the book, so a mismatch shows on a pull request |
| Sphinx warns on something the wiki considers valid | the warning goes to the release notes; recurring ones become a staging rewrite or a compat rule |
| Releases cost more Actions minutes than expected | the cache; only the formats that are on are built |
| A private skill repository blocks the wiki's workflow from calling the action | the access setting in the README; it ends when the repository is public |
