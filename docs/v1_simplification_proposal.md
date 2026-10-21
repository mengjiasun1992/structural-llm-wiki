# Proposal: a simpler v1

- **Status:** proposed; decisions open in §7
- **Changes:** [structural_llm_wiki_design.md](structural_llm_wiki_design.md) and [skill_execution_plan.md](skill_execution_plan.md), once decided

## 1. Why now

The design describes a system that grew one need at a time: a configurable
layout and the moves that change it, a migration rule for older wikis, five
templates with a three-level precedence for their lengths, drafts with their own
states, an Obsidian add-on, two book add-ons that exist only to be refused. Each
was reasonable when it was added. Together they put most of the plan's effort
into machinery around the core loop, and they push the first time an agent can
do anything useful to Phase 5, and the first full run to Phase 7.

Nothing depends on that machinery yet: no wiki runs on this repository's code,
and Phase 0 (#18) isn't merged. This is the cheapest moment to cut back to what
v1 needs, and to build the core loop first.

## 2. What the skill is for

The design's own overview names the value: a team's knowledge kept in git, where
every answer traces to its evidence, people review every change, and the wiki
stays current instead of decaying. Five mechanisms deliver that, and v1 keeps
all five:

| Mechanism | Why it can't go |
|---|---|
| Sources saved with their URL, date and hash | Without them nothing can be checked, and nothing knows when it's stale |
| A tag tree linking sources, narratives and people | It's how a run chooses what to read and how a query finds an answer |
| Narratives whose claims cite a source's section | The answer, and its evidence, in one place |
| One pull request per run | People stay in control without doing the research |
| Checks: deterministic scripts, and lint for judgment | What keeps the wiki honest as it grows |

Everything else is judged by one question: does v1 need it for these five to
work? If not, it waits until real use asks for it.

## 3. Principles for the cut

1. **Core loop first.** One thin path through init, ingest, narrative, query and
   publish, running end to end, before any part is made deep.
2. **One way to do each thing.** A setting is a second way; add one only when
   two real wikis need different answers.
3. **No migrations.** v1 has no older wikis to carry forward; a rule that exists
   for an older layout or format is removed.
4. **Defer, don't half-build.** A feature that isn't in v1 isn't in the code,
   the config or the docs, not even as a refused setting.
5. **Store what you can check.** A saved copy is either byte for byte, or the
   original file; conversions that can't be verified are kept to what's needed.

## 4. Keep, simplify, defer, cut

### 4.1 Layout and configuration

| Today's design | v1 | Why |
|---|---|---|
| Eight configurable paths in `Config.toml`, validated, with `init` moving files and rewriting links, manifests and fingerprints when one changes, and reading older `Config.toml` versions from git | **Cut.** One fixed layout: `sllmwiki/tags/`, `sllmwiki/ingested/`, `sllmwiki/groomed/` (each manifest in its folder), `templates/` at the root | The largest piece of `config.py` and `init.py`, and every script resolving paths, exist for this. One layout is easier to read, document and test |
| A `Config.toml` without `content` means the repository root | **Cut** | A migration rule (principle 3) |
| Settings: `slice_large_sources`, `large_source_kb`, two markers, wiki-wide `max_words` and `abstract_words`, `max_quote_words`, and add-on tables | **Simplify** to two: `large_source_kb` and `max_quote_words` | Each is a real per-wiki choice (how big a source to accept, how much to quote). Markers and lengths become fixed or per template (§4.3, §4.5) |
| Sphinx and mdBook settings, refused until built | **Cut**; the books are a later proposal | Principle 4. The markdown compatibility rules stay: they're cheap, done, and protect every renderer |

### 4.2 Sources

| Today's design | v1 | Why |
|---|---|---|
| Markdown and text saved byte for byte | **Keep** | Exact, and checkable by hash |
| HTML converted to markdown | **Keep**, with a small converter covering headings, paragraphs, lists, tables, code and links | Web pages are the most common source; section citations need headings |
| PDFs converted to markdown by a standard-library reader, and sliced per section above a size | **Simplify:** save the original PDF in `ingested/files/` with its manifest entry, and cite pages (`file.pdf#page=3`) | The reader would be the plan's largest and riskiest module, and its markdown isn't a verbatim copy anyway. GitHub and Obsidian open PDFs at a page, and agents read PDFs directly |
| License lookup from Wikipedia, arXiv, Crossref and page links | **Simplify:** the agent records the license it finds (`--license`); the script checks the repository's visibility and refuses a copy a public wiki may not hold | The judgment was always the agent's; the script enforces the part that can be checked. Lookups can come back as helpers |
| Images downloaded beside a source | **Defer** | A link to the original image keeps attribution without copying |
| `check-upstream` and hash pins | **Keep** | Staleness is core |

### 4.3 Narratives

| Today's design | v1 | Why |
|---|---|---|
| Five bundled templates | **Simplify** to two: `concept_brief_overview` ("What is X?") and `technical_brief_overview` ("How does X work?") | Most questions are one of these. Add the others when narratives show the need |
| A template header schema (titles, `required`, `flow`, `right_after`, numbering start, budgets) | **Simplify:** the skeleton is the schema: its headings are the required sections, in order, and a heading marked `(optional)` may be left out; the header keeps only `description`, `use_when` and the word budgets | One file to read instead of a schema and a skeleton that must agree |
| Wiki templates through `[structural-llm-wiki-templates]` tables: default, exclude, per-template files and lengths, with precedence over wiki-wide settings | **Simplify:** a wiki's own template is a folder in `templates/` with `template.md` and `guide.md`, found by the folder, with its budget in its header | Three levels of precedence become one: the template's own header |
| Configurable markers, defined in each narrative's Terminology (`MARKER_UNDEFINED`) | **Simplify:** fixed markers, `[sllmwiki_reasoning]` and `[sllmwiki_gap]`, explained once in the wiki's README | A reader learns them once; every narrative stops repeating them |
| Ancestor and adjacent tags snapshotted in each narrative, to detect tree drift | **Cut**; lint derives them from the current tree | Stored derived data that can only go stale |
| Drafts: a banner, `status: draft`, version `0.x`, `DRAFT` in the index, `[DRAFT]` pull requests, grounding to 1.0 | **Defer**; a gap is answered as a labeled draft in the reply, and the user can run `build` | Many states for one outcome; the gap still gets an answer and a next step |
| Heading numbering, numbered escaped citations, the Abstract, References and Metadata | **Keep** | Scripts already own them, and they make narratives checkable |

### 4.4 Tags and navigation

| Today's design | v1 | Why |
|---|---|---|
| A tag tree in `tags.yaml`, primary and supporting tags per narrative | **Keep** | Core |
| Tag abstracts, fingerprinted and rewritten up to the root whenever a narrative changes | **Cut**; a tag keeps its one-line description, and `query` starts from narrative abstracts | Every narrative change rippled to the root in every pull request. Narrative abstracts already answer "what does the wiki know about X" |
| `SLLMWIKI_INDICES.md`: a mermaid map and a table; with the Obsidian add-on, a page per tag too | **Simplify:** always generate a page per tag, and a short index listing the top-level tags | Tag pages serve GitHub and Obsidian alike, so one generated map replaces two |
| The Obsidian add-on: a setting, tag pages, a header on each narrative, `graph.json`, a `vault` setting that moves `.obsidian/` | **Simplify:** no add-on and no settings. Tag pages are always there; `init` writes `sllmwiki/.obsidian/graph.json` once | The graph needs only markdown files and links, which v1 now has |

### 4.5 Workflows and review

| Today's design | v1 | Why |
|---|---|---|
| `build`: tags, ingest, SMEs, questions, narrative, lint, one pull request | **Keep**, with SMEs optional | The core loop |
| `query`: tiers 0–4, filing a stitched answer automatically, drafts on a gap | **Simplify:** tiers from narrative abstracts to one section to the cited source; a stitched answer is *offered* for filing, not filed | Writing to the wiki from a question is a surprise; asking keeps the user in control |
| Reuse before writing (reuse, expand, ground, new) | **Simplify:** reuse or expand an existing narrative, else new | Grounding goes with drafts |
| Attention-aware reading order | **Keep**, as one paragraph of instructions | It costs only words |
| The review-checklist action, red until every box is ticked | **Defer**; the pull request's description keeps the checklist | A required review already blocks merging |
| SMEs from git history, `CODEOWNERS` and reviews (`contributors.py`) | **Keep**, after the core loop | Valuable, not needed for the first answer |
| Cross-links between narratives (`cross-links.py`) | **Defer**; lint suggests links | Lint already reads neighbors |

### 4.6 What stays exactly as it is

The source policy and its CI check; one pull request per run, merged by the
owner; the commit message format; standard-library Python 3.9; the markdown
compatibility rules and their tests; YAML manifests read by a narrow subset
reader; BM25 search over abstracts; `publish.sh` and `preflight.sh`.

## 5. What it saves

Roughly, against the current plan: no PDF reader or slicer, no path moves or
history, no template-table precedence, no tag-abstract roll-up, no draft states,
no add-on settings. That removes about half the planned script code and most of
the settings validation, and with it the tests and docs that would describe it.
The plan's §5 settings table shrinks from twelve rows to two.

## 6. The plan, reordered

| Phase | Builds | First evals |
|---|---|---|
| 0. Foundations | Test harness; `util`, `toml`, a small `config` (the fixed layout and two settings), `wikiyaml`, `schema`, `compat`; eval fixture | none |
| 1. The core loop, thin | `init` (layout, AGENTS.md, README, CI); `fetch-source` for markdown, text and HTML; `manifest` (record a source, put a narrative); the two templates and `narrative-format`; `wiki-check`; `search`; `publish.sh`, `preflight.sh`; `SKILL.md` with `build` (tags, ingest, narrative, one PR) and `query` | `not-a-wiki`, `init-new`, `route-query`, `query-answer`, `narrative-publish` |
| 2. Dogfood | A real wiki built with it; what breaks becomes issues | the smoke set, three runs |
| 3. Verification | `lint`; staleness (`check-upstream`, pins); source policy checks; quotation length; PDFs saved as files | `prompt-injection`, the policy cases |
| 4. Breadth | Tag pages and `graph.json`; SMEs (`contributors.py`); `smes` and `tags` as steps on their own | `route-smes`, `route-lint`, `route-ingest` |
| 5. First release | Version, CI pinned to it, README demo | every case, three runs, with the baseline |

Phase 0's code (#18) is rewritten under these rules: `config.py` loses
the configurable paths, the migration rule and most settings; the rest stays.

## 7. Decisions for the owner

1. **Fixed layout** (§4.1): no configurable paths in v1?
2. **PDFs as files** (§4.2): save the original and cite pages, instead of converting?
3. **Two templates** (§4.3): concept and technical overview only in v1?
4. **Tag abstracts** (§4.4): cut, with `query` starting from narrative abstracts?
5. **Drafts** (§4.3, §4.5): defer, answering a gap in the reply only?
6. **Obsidian** (§4.4): no add-on; tag pages always, `graph.json` once?
7. **Filing** (§4.5): offer to file a stitched answer instead of filing it?
8. **Order** (§6): the core loop first, then dogfood, then deepen?

Each answer updates the design doc and the plan in one pull request, and Phase 0
is redone to match.
