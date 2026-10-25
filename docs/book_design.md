# Design: the wiki as a book

- **Status:** proposed
- **Execution plan:** [book_execution_plan.md](book_execution_plan.md)
- **Wiki design:** [structural_llm_wiki_design.md](structural_llm_wiki_design.md)

## 1. Goal

A wiki is written and reviewed on GitHub, and explored in Obsidian. Neither
gives you something to hand to a colleague, read on a plane, or keep as a
record of what the group knew on a given day. The book does: at each release,
the wiki becomes a PDF, an EPUB or a single HTML file, attached to a GitHub
Release, dated and versioned.

Three book formats, each turned on separately, because most people want only one:

| Format | Setting | For |
|---|---|---|
| PDF | `pdf_book` | sharing, printing, reading anywhere with the same layout |
| EPUB | `epub_book` | e-readers and phones: text that reflows, adjustable type, offline |
| HTML, one file | `html_book` | a browser: searchable, clickable, wide tables and diagrams at full size |

**Not goals:** a hosted website (GitHub Pages for a private repository needs a
paid plan and is public on most of them), a reference site with indices and
"cited by" panels (a later direction, §11), and building books on a computer
without GitHub (possible for developers, not promised to users, §8.4).

## 2. What it's like to use

### 2.1 Turning it on

The first time `init` runs, `Config.toml` gets a release table:

```toml
[structural-llm-wiki-release]
pdf_book = true      # a PDF: share, print, read anywhere
epub_book = false    # an EPUB: e-readers and phones
html_book = false    # one self-contained HTML file, for a browser
title = ""           # the book's title; empty: the repository's name
author = ""          # its author; empty: the title
```

`init` also installs the release workflow, which does nothing until a release
exists. A wiki that never releases never pays for it. To change the formats,
edit the table, or ask the agent ("also make an EPUB"), which changes it in a
pull request like any other setting.

### 2.2 Making a release

```text
You:    /sllmwiki:release
Agent:  Releasing v2026.10.24 from mainline (adef3db).
        Since v2026.10.01: 4 new narratives (consistent hashing), 2 updated,
        12 new sources; 1 open question marked [?].
        Building the PDF… done in 2 min 40 s.

        Release: https://github.com/<you>/<wiki>/releases/tag/v2026.10.24
        PDF:     mengjia-sllmwiki-v2026.10.24.pdf  (84 pages, 3.1 MB)
        Notes:   the release page lists what changed; the book had no warnings.
```

What happens behind it:

1. The agent checks the default branch is up to date and its checks pass. If
   they don't, it says which and stops: a book of a broken wiki is a broken
   book. ("Release anyway" wins, and the notes say what was failing.)
2. It picks the version: the date, `v2026.10.24`, or `v2026.10.24.2` for a
   second release that day.
3. It writes the release notes from what changed since the last release:
   narratives added and updated (with their questions and versions), sources
   added, open questions, and the formats being built.
4. It creates the release (`gh release create`). The release workflow starts,
   builds each format that's on, and attaches the files.
5. It waits for the workflow and replies with the links, or with what failed.

People who don't use the agent can do the same from GitHub: *Releases → Draft
a new release*, a tag, *Publish*. The workflow builds the books either way.

### 2.3 Previewing without releasing

`/sllmwiki:release --preview` (or *Actions → Book → Run workflow* on a branch)
builds the same files from the current branch and uploads them as a workflow
artifact, kept for 90 days, without creating a release. For checking a big
change before it's published.

### 2.4 Reading the book

Every format has the same content (§5):

- a **cover** titled with sllmwiki's braces, `{mengjia-sllmwiki 📖}`, what made it ("Made by sllmwiki
  and Claude Opus 5.5, from mengjia-sllmwiki", linking to this skill and to
  the wiki's repository), the version, date and commit;
- a **front page** saying whose work is whose (§9), and how to read the
  citations and the `[→]` and `[?]` markers;
- **contents** by topic, then **parts** following the tag tree, each opening
  with the topic's description and a map of its chapters and sections, each
  chapter followed on its line by the first paragraph of its Abstract (a
  section by its description), so a part can be skimmed;
- **chapters**, the narratives, in teaching order within each part;
- above the title of every part, chapter and appendix, one quiet line saying
  **where it is**: the book's `{mengjia-sllmwiki 📖}` (to the cover) › each
  part above it, all links, with **Contents** at the right; under a chapter's
  title, only its version and date;
- at the end of each chapter, a quiet credit, `── {📖} sllmwiki ──`, linking
  to this skill;
- each part, section and chapter on a **page of its own**: a new page in print;
  on screen, sllmwiki's mark (braces around an open book, `{📖}`) between two
  rules, which a chapter's closing credit stands in for between chapters.
- **appendices**: the sources with their abstracts, licenses and links; a
  glossary of every term the narratives define; and the open questions.

A citation in a chapter goes to its source's entry in the appendix, which
links to the original. Links between chapters work in every format.

It's set for long reading: a serif text at about 70 characters a line on a
warm off-white page, sans-serif headings sized by kind of page rather than by
depth, and a dark theme that follows the reader's system, with diagrams kept
on a light card so they stay readable.

### 2.5 When something goes wrong

- **A problem the wiki can fix** (a broken link, a diagram that doesn't parse)
  is caught on the pull request that caused it (§7), long before a release.
- **A warning at release** (an anchor Sphinx can't resolve) doesn't stop the
  book: it is listed in the release notes under *Known issues*.
- **A format that fails** doesn't block the others: the PDF is still attached
  if the EPUB fails, and the notes and the agent's reply say what failed.

## 3. Settings

```toml
[structural-llm-wiki-release]
pdf_book = true      # a PDF: share, print, read anywhere
epub_book = false    # an EPUB: e-readers and phones
html_book = false    # one self-contained HTML file, for a browser
title = ""           # the book's title; empty: the repository's name
author = ""          # its author; empty: the title
```

- **A table of its own,** read by `lib/config.py` like the others: unknown
  keys and mistyped values are `CONFIG_INVALID`, and a rerun of `init` adds
  keys the file lacks.
- **PDF on by default:** the one format everyone can open. All three off is
  valid: a release then has notes and no files.
- **Each key appears when its format works** (the execution plan's phases),
  so no setting ever names something that isn't there.
- **The title and the author** are settings: a repository's name is rarely a book's. Files keep the repository's name (`<repo>-<version>.pdf`), so a title with spaces or Chinese never lands in a link; the EPUB's author is `author`, by default the title, and its publisher sllmwiki.
- **Nothing else is configurable at first** (theme, cover, fonts, order). The
  book has to read well with no tuning (§5); a setting is added when a real
  wiki needs one, as for every setting (design doc §4.9).

## 4. Principles

1. **The wiki's format doesn't change.** Everything a book tool needs is done
   in a scratch folder at build time; nothing it produces is committed.
2. **Built by GitHub, read anywhere.** Users install nothing; the release
   workflow does the work. The files are self-contained: no network, no
   JavaScript, no fonts to fetch.
3. **One source for every format.** All three come from the same prepared
   folder and the same pre-rendered diagrams and math, so a fix lands in all
   of them at once.
4. **Sources stay their authors'.** A book carries each source's abstract,
   license and link, never its saved copy (§9).
5. **Fail late, fail small.** Structural problems fail the pull request; at
   release, warnings become notes and a failing format doesn't take the others
   down.

## 5. The book's content

### 5.1 Structure

| Part | From |
|---|---|
| Cover | the book's title (`title`, by default the repository's name) and 📖; "Made by sllmwiki and \<models\>, from \<wiki\>", the models from the narratives manifest, the wiki linked to its repository (`--source`, by default its `origin` remote); the version, the date, the commit |
| Front page | §9's text, the markers' meaning, how citations work |
| Contents | generated: a list of links to the parts, sections and chapters (a visible toctree would pull the whole book into a single-file HTML) |
| One part per top-level tag, sections per child tag | `tags.yaml`: each part opens with links up, the tag's description, and a map of its chapters (each with its Abstract's first paragraph) and sections (each with its description) |
| Chapters | the narratives, each under its **primary** tag only; its supporting tags' parts link to it |
| Appendix A: Sources | every source a chapter cites: title, URL, license, published date, abstract, and the chapters that cite it |
| Appendix B: Glossary | every Terminology row, A to Z, grouped by term: one definition, or each narrative's, side by side when they differ |
| Appendix C: Open questions | every statement or section marked `[?]`, with its chapter |

Not in the book: the saved copies of sources, `SLLMWIKI_INDICES.md` and the
tag pages (the book has its own contents), SMEs (names and handles are
personal data in a file that travels), and Metadata sections beyond a
narrative's version and date.

### 5.2 Chapter order

Within a part, chapters go in teaching order:

1. **Dependencies first:** a narrative that `built_on` another comes after it
   (a topological order of `built_on`; a cycle is a PR-time error, §7).
2. **Then by template:** concept, survey, technical, comparison, case study,
   so "what is X" comes before "how does X work" and "X or Y".
3. **Then by question,** alphabetically, so the order is stable.

### 5.3 What changes in a chapter, in the scratch folder

| In the wiki | In the book |
|---|---|
| A citation, `[\[3\]](../sources/x.md#section)` | `[3]` linking to x's entry in Appendix A; the Citations list shows the section's name and the original URL |
| A link to another narrative, `other.md#3-how-it-works` | a link to that chapter's section |
| A link to a tag page or the index | a link to that tag's part |
| ```` ```mermaid ```` blocks and `$…$`, `$$…$$` math | inline SVG, pre-rendered (§6.3), its source kept as alt text |
| A figure in `narratives/figures/<slug>/` | the same image, copied |
| The Metadata section | a line under the title: version and last-modified date |

## 6. How it's built

### 6.1 The pipeline

```text
                  ┌──────────────── release workflow (GitHub Actions) ─────────────────┐
 /sllmwiki:release│                                                                     │
  or "Publish" ───┼─► stage ─► pre-render ─► Sphinx ─┬─► single-file HTML ──► html_book │
                  │   (book.py,   (Chrome:     (MyST) │        └─► Chrome print ─► pdf_book
                  │    stdlib)    mermaid,            └─► EPUB ─────────────────► epub_book
                  │               MathJax → SVG)                                       │
                  └─────────────► attach the files and the notes to the GitHub Release ┘
```

### 6.2 Stage (`scripts/book.py stage`, `lib/book.py`)

Standard-library Python, like every script. It reads the wiki through the
existing libraries (`manifest`, `tagtree`, `metadata`, `citations`,
`numbering`, `language`) and writes a scratch folder of plain Markdown:
the cover and front page, one file per part, the chapters rewritten as in
§5.3, and the three appendices. It also writes `book.json`: the order, every
anchor, every diagram and formula to render, and any problem found. The pull
request check (§7) runs the same model and rewriting inside `wiki-check.py`,
writing nothing, and reports only what the wiki shows but the book can't: a
link already broken in the wiki is the wiki's own checks' to report.

Staging owns every anchor in the book. It gives each heading a label unique
across the book, made of its chapter and its GitHub anchor (from
`numbering.anchors`, which also numbers repeated headings as GitHub does),
written as a MyST target before the heading, and it rewrites every link (to a
section, a chapter, a source or a part) to its label. Sphinx's own section ids
can't do this job (§6.4). Diagrams are ```` ```mermaid ```` blocks; math is
`$…$`, `$$…$$` and ```` ```math ```` blocks, GitHub's three forms, never inside
code.

### 6.3 Pre-render (`scripts/book.py render`)

Headless Chrome, already on GitHub's runners, loads pinned copies of
mermaid.js and MathJax 3 (bundled in the action, not fetched) and turns each
diagram and formula listed in `book.json` into SVG. The script stays standard
library: it writes one page that renders every item, runs Chrome with
`--dump-dom` and a virtual time budget, and reads the SVGs back from the
page. A hundred items take about 3 seconds. Inline math keeps
MathJax's vertical alignment, so it sits on the text line; every SVG keeps its
source as alt text, for screen readers and copying. Results are cached by a
hash of the source and the library versions (the Actions cache), so a
release renders only what changed.

Each SVG is made to stand alone and to be valid XML, so the same markup works
in HTML, in print and in an EPUB's XHTML: mermaid draws its labels as SVG text,
not HTML (`htmlLabels: false`); MathJax writes its glyphs into each formula
(`fontCache: 'none'`), not into shared definitions; every id is prefixed by
the item, and an id mermaid repeats inside one diagram is renamed; a `rect`
gets the `width` and `height` SVG 1.1 requires; and the alt text replaces any
`role` or `aria-label` the library set. Diagrams use the book's font.

Why everything becomes SVG, for every format: EPUB readers don't run
JavaScript, and an HTML book that fetches MathJax from a CDN shows raw TeX
offline. One static rendering makes the three formats identical. mermaid.js
and MathJax are pinned close to the versions GitHub uses, so what GitHub draws
in review is what the book draws. GitHub's mermaid version can be read from its
viewer's script (`renderer.draw(…, "12.2.0", …)` in October 2026).

### 6.4 Sphinx (the release action)

Sphinx with MyST-Parser reads the staged folder, using the `conf.py` and
stylesheet in the skill's `templates/book/` (passed with `-c`, so no Sphinx
file lives in the wiki; `book.py build` sets the wiki's name, version and
language with `-D`). The vendored mermaid.js and MathJax, megabytes the skill
shouldn't carry to every install, stay in the action (`render --vendor`):

- **Ids are staging's labels:** Sphinx gives a section its own id from its
  title (`abstract` in every chapter, `id4` for a Chinese heading) and keeps a
  label as a second id. A `doctree-read` hook in `conf.py` makes the label the
  section's only id, so every id in the single-file book is unique and the
  contents and heading links use the labels too. Setting
  `myst_heading_slug_func` doesn't help: it only resolves links, and a
  function in `conf.py` can't be cached.
- **MyST extensions:** `dollarmath` is off (math is already SVG); GitHub alerts
  become admonitions (`alert`).
- **Structure:** every toctree is hidden. A single-file HTML puts a visible
  toctree's pages in its place, so the contents and each part's map of its
  chapters are lists of links staging writes.
- **Theme:** Sphinx's `basic` theme with the skill's own stylesheets, and no
  theme package to install: `book.css`, for every format, in CSS 2.1
  selectors that e-readers and `epubcheck` read; and `book-html.css`, which
  the single-file HTML and the PDF add, for what relies on their one-page
  structure (section ids, `:is()`, `:has()`) and on Chrome's printing (page
  margin boxes). The EPUB neither links nor packs it.
- **Language:** Sphinx's `language` is the wiki's `language` (Config.toml);
  generated labels (Appendix, Glossary, Sources) come from the language pack.
- **Builders:** `singlehtml` for the HTML and PDF, `epub` for the EPUB, reusing
  one doctree cache. The EPUB builder needs `version` and `copyright` set: the
  release version, and the wiki's name.

### 6.5 The three outputs

- **HTML:** the `singlehtml` output with its stylesheet and images inlined
  into one file, `<wiki>-<version>.html`. The same step drops the theme's
  navigation bars and scripts, and rewrites the links `singlehtml` writes
  between documents, `#document-<doc>#<id>`, to `#<id>`.
- **PDF:** Chrome prints that file with the print stylesheet: A4; the cover,
  the front page and the contents each on a page; each part and chapter on a
  new page; page numbers, and the book's title as a running head, from CSS
  page margin boxes (`@page { @bottom-center { … } }`, in Chrome since 131),
  so no browser driver is needed; no table or diagram split where it fits on
  a page. Fonts: the action installs the distribution's Noto fonts (Sans,
  Serif, Mono, Math, CJK, and Color Emoji for the title's 📖) when a release
  builds the PDF, so Chinese text and Unicode such as `ₜ₊₁` print correctly.
  Chrome embeds a CJK or color font as Type 3 glyphs; the text still extracts,
  which is what the check tests.
- **EPUB:** Sphinx's EPUB 3, from the same staged, rendered pages: the cover
  page first (text, as in the other formats; no cover image), the reader's
  contents from every part, section and chapter (`epub_tocscope =
  'includehidden'`, since the toctrees are hidden), inline SVG, and the small
  screen rules (narrower margins, tables that scroll, diagrams that fit).
  Sphinx doesn't declare the pages that hold inline SVG (`properties="svg"`
  in the package file), so the build adds it. Validated with `epubcheck`.

### 6.6 The release workflow and action

- `init` installs `.github/workflows/release-book.yml`, refreshed like the
  other workflows. It runs on `release: published` and on
  `workflow_dispatch` (the preview), with `contents: write`.
- It calls `src/actions/release-book` in this repository, which installs the
  pinned Sphinx and MyST-Parser (and, for the PDF, the fonts), runs
  `book.py build` for each format that's on with the libraries in its
  `vendor/` folder, and attaches the files (`gh release upload`), or uploads
  an artifact for a preview. This repository's `check-book` workflow builds
  the fixture wiki with it on every pull request that touches the book.
- Each format is its own step, and a failure in one is recorded and doesn't
  stop the others. Warnings and failures are appended to the release notes.

### 6.7 `/sllmwiki:release`

A workflow in the skill (`workflows/release.md`, `scripts/release.py`):

- `release.py plan` checks the default branch and its checks, picks the
  version, and drafts the notes from the narratives and sources manifests at
  the last release's tag and now.
- The agent reviews the draft (the notes say what changed, in the wiki's
  language), then `release.py create` makes the release.
- `release.py wait` follows the workflow run and reports the files, their
  sizes and any warnings.

## 7. When things run

| When | What runs | Cost | Catches |
|---|---|---|---|
| Every pull request | staging's model and rewriting, in `wiki-check.py` (the `wiki-checks` action) | seconds, Python only | a link that works in the wiki but not in the book (a section the narrative lacks, its Metadata, a narrative with no chapter), a `built_on` cycle |
| A pull request that changes a diagram or a formula | a parse of just those, in headless Chrome | about 20 seconds | a diagram or formula GitHub would show as an error |
| A release | the full build, for each format that's on | 2 to 3 minutes | warnings go to the release notes |
| A preview | the full build, as an artifact | the same | the same |

## 8. Costs, and who pays them

1. **Setup:** none beyond `init`, which every wiki runs anyway.
2. **Time:** a release takes 2 to 3 minutes, mostly installing and starting;
   each extra format adds seconds.
3. **GitHub Actions minutes,** on a private repository: a few minutes per
   release, against the free plan's 2,000 a month.
4. **No GitHub, no book:** the workflow is GitHub's. `book.py build` runs the
   same pipeline on a developer's computer when Python, Sphinx and Chrome are
   installed, for developing the book, not as a promise to users.
5. **Private repositories:** a release's files need a GitHub login to
   download; share the file itself. While this skill's repository is private,
   the wiki's workflow can only call its action with the access setting in
   the README.

## 9. Sources, licenses and responsibility

- **No saved copies in a book.** Appendix A carries what the skill wrote (the
  abstract) and the source's own metadata (URL, license, date). Sharing the
  file never redistributes anyone's work. Including copies is not offered
  (§10).
- **Quotations** stay as short as the wiki keeps them (`max_quote_words`).
- **The front page says whose work is whose:** the narratives are the wiki
  owner's; every source belongs to its authors and is linked, not copied; the
  narratives were written by an LLM and reviewed by the owner; and the book is
  a snapshot of the commit on its cover.
- **No SMEs:** names and handles stay in the wiki.

## 10. Decisions

| # | Decision | Status |
|---|---|---|
| 1 | Formats: PDF, EPUB, single-file HTML, each its own setting | made |
| 2 | Default: `pdf_book = true`, the others `false` | proposed |
| 3 | Renderer: Sphinx + MyST only (no mdBook, Quarto or LaTeX) | proposed |
| 4 | Diagrams and math pre-rendered to SVG in headless Chrome, for every format | proposed |
| 5 | Trigger: `release: published` for releases, `workflow_dispatch` for previews | proposed |
| 6 | Versions: the date, `vYYYY.MM.DD`, with `.2` for a second release that day | proposed |
| 7 | Saved copies of sources in a book: never | proposed |
| 8 | SMEs in a book: never | proposed |
| 9 | A release from a red default branch: refused, unless the owner says to | proposed |

## 11. Options set aside

| Option | Why not now |
|---|---|
| mdBook as a second renderer | a second set of quirks and tests for the same files; no PDF or EPUB without plugins. The wiki's markdown stays mdBook-safe (design doc §4.8), so it can return |
| Quarto, Typst | the best typeset PDF, but Pandoc's Markdown differs from GitHub's where the wiki relies on it, and it's the largest install |
| LaTeX PDF | several GB of TeX and fonts in CI |
| MathML instead of SVG | uneven support in e-readers (Kindle) |
| GitHub Pages | paid for private repositories, and public on most plans |
| A reference site (typed tags, sources and terms, "cited by") | a different product; a Sphinx domain on the same staging, later |
