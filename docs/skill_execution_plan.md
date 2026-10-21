# Execution plan: implementing the sllmwiki skill

- **Status:** proposed
- **Design:** [structural_llm_wiki_design.md](structural_llm_wiki_design.md)

## 1. Where we start

The repository has the skeleton and the guardrails, but no behavior yet:

| In place | Not yet |
|---|---|
| Design doc, content folder and Obsidian add-on proposals | `SKILL.md`, workflows and steps beyond one-line stubs |
| Plugin and marketplace manifests, one command per workflow and step | Every script under `src/skills/sllmwiki/scripts/` and its `lib/` |
| `src/actions/wiki-checks` (calls scripts that don't exist yet) | `src/actions/review-checklist` |
| `src/tools/check-yaml.py` (imports `lib.config` and `lib.util`) | Narrative templates, the wiki templates `init` installs |
| CI: Check docs, Check bundled scripts (parse, ruff, shellcheck, markdownlint) | Unit tests and their runner; evals and their fixture |
| `AGENTS.md`, `pyproject.toml` (coverage `fail_under = 95`) | A release |

The plan builds the skill bottom-up: the deterministic scripts first, each with
its tests, then the instructions that call them, each with its evals. Every
phase ends with `mainline` green and something usable, so it can stop between
phases without leaving half-built features behind.

## 2. How every phase is built, tested and evaluated

These apply to every phase; each phase below adds only its own items.

**Build.** The skill is Python and markdown, so "build" means it loads:

```bash
python3 -m py_compile src/skills/sllmwiki/scripts/*.py src/skills/sllmwiki/scripts/lib/*.py src/tools/*.py
/usr/bin/python3 -m py_compile src/skills/sllmwiki/scripts/*.py src/skills/sllmwiki/scripts/lib/*.py   # Python 3.9
claude plugin validate .
claude --plugin-dir .    # the commands appear as /sllmwiki:<name>
```

**Test.** Every script and module comes with `tests/test_<module>.py` in the
same pull request (`AGENTS.md`):

```bash
python3 src/skills/sllmwiki/tests/run.py --coverage   # fails below 95%
/usr/bin/python3 src/skills/sllmwiki/tests/run.py     # Python 3.9
ruff check src/skills/sllmwiki/scripts src/skills/sllmwiki/tests src/tools
shellcheck src/skills/sllmwiki/scripts/*.sh
npx --yes markdownlint-cli2@0.13.0 "**/*.md"
python3 src/tools/check-yaml.py
```

Coverage is measured over all of `scripts/` and must stay at 95% or above
after every pull request, not only at the end of a phase.

**Eval.** From Phase 5, when the skill first does something an agent can be
asked for, each phase adds eval cases for the behavior it introduces and runs
the smoke set before its pull requests are opened:

```bash
claude plugin eval . --tag smoke --scaffold --allow-tools Bash \
  --runs 1 --ablation none --model sonnet --max-cost-usd 5 -j 8
```

Each pull request says which cases ran, with which model, the results and the
cost (`AGENTS.md`). Cost and turns are part of the result: the skill should
spend tokens only on judgment (design doc §2), so a change that makes a case
noticeably costlier, or adds turns, says why.

**Configuration.** No script hard-codes a path or a setting: each reads them
from the wiki's `Config.toml` through `lib/config.py`. §5 lists every setting
and the task that builds it. Tests run each script on a fixture wiki with
non-default paths and settings as well as the defaults.

**Licenses.** A pull request that touches what the skill fetches, saves,
quotes or publishes says how it stays within the source policy (`AGENTS.md`,
"Respect licenses and copyright").

**Done.** A phase is done when its pull requests are merged, CI is green on
`mainline`, coverage is at 95% or above, and its eval cases pass (from Phase 5).

**Source of truth.** Every task is implemented from this repository: the
design doc, this plan, `AGENTS.md` and the code already merged. The code and its
tests are written for the task, not taken from elsewhere. When a task needs an
intent or decision these documents don't state, it is added to the design doc
or this plan first, in the same pull request, so the documents stay the one
place it is recorded.

**Commits and pull requests.** One task at a time, in the order given: each
numbered task is built, tested and evaluated on its own and lands as a local
commit (`Part of #<issue>`). When a phase's tasks are done, its branch, made from
the up-to-date `mainline`, opens one pull request that closes the phase's issue.
The owner merges.

## 3. Order

```mermaid
graph TD
    P0["0. Harness and foundations<br/>util, toml, config, wikiyaml, schema, compat"]
    P1["1. Markdown primitives<br/>numbering, metadata, citations"]
    P2["2. Data model<br/>manifest, tag tree, index, search, templates"]
    P3["3. Sources<br/>html2md, pdf, fetch, policy, fetch-source"]
    P4["4. Checks<br/>wiki-check, narrative-format, Obsidian, narrative templates"]
    P5["5. Setup and publishing<br/>init, preflight, publish, review-checklist"]
    P6["6. Steps<br/>tags, ingest, smes, narrative, lint"]
    P7["7. Workflows<br/>build, query, SKILL.md"]
    P8["8. Dogfood and first release"]
    P0 --> P1 --> P2 --> P4
    P2 --> P3 --> P4
    P4 --> P5 --> P6 --> P7 --> P8
```

Phases 1 and 3 touch disjoint files, so Phase 3 can start as soon as Phase 2's
`manifest` module lands.

## 4. Phases

### 4.1 Phase 0: test harness and foundations

**Goal.** Tests run in CI, and the modules everything else imports exist. The
check-yaml step and the unit-test step in CI turn on (both wait for files this
phase adds).

| # | Code change | What it does |
|---|---|---|
| 0.1 | `tests/run.py` | Runs each `test_*.py` in its own process, in parallel; `--coverage` combines per-process data and applies `fail_under`; name filters (`run.py config toml`) |
| 0.1 | `tests/helpers.py` | `WikiTestCase` (fresh temp directory per test), `LocalServer` (free port, serves fixtures), loading a command script as a module so `main()` runs in-process, capturing output and exit code, and a fixture-wiki builder |
| 0.2 | `scripts/lib/__init__.py`, `lib/util.py` | `read_text`, `dumps`, `setup_stdio`, `git_root`, dates, MD5 |
| 0.2 | `lib/toml.py` | The TOML subset `Config.toml` uses (Python 3.9 has no `tomllib`): read, and write a value back without re-serializing the file |
| 0.3 | `lib/config.py` | `Layout` and `layout(root)`: the eight paths from `[structural-llm-wiki-paths]` resolved through the content folder; `settings(root)`: `[structural-llm-wiki-settings]`, its add-on tables and `[structural-llm-wiki-templates]`, each with its default; validation of every one (`CONFIG_INVALID` reasons, §5) |
| 0.3 | `lib/paths.py`, `lib/cli.py` | Repository-relative paths; shared argument handling (`--root`, `--json`), with the refusal to write on a broken `Config.toml` |
| 0.4 | `lib/wikiyaml.py` | The YAML subset the wiki files use; fails loudly on anything else; targeted line edits that keep comments and order |
| 0.4 | `lib/schema.py` | Field kinds and rules for `tags.yaml` and both manifests (design §4.2) |
| 0.5 | `lib/compat.py` | The markdown GitHub, Obsidian, mdBook and Sphinx render alike (design §4.9, `AGENTS.md` "Markdown compatibility"): findings for each pitfall, and `escape()` for the ones that can be fixed. First, so every writer and check after it is built on it |
| 0.6 | `evals/README.md`, `evals/_fixture/wiki.sh` | How to run and write evals; the fixture wiki as a git repo with a local `origin`, built from `helpers.py` |

**Build.** The common checks. `check-yaml.py` now runs.

**Test.** `test_util`, `test_toml` (round trips, every unsupported construct
rejected), `test_config` (every setting's default when missing, a moved content
folder, every `CONFIG_INVALID` reason in §5, other tools' tables left alone), `test_wikiyaml` (the subset, the
failures, edits that keep comments), `test_schema` (each field kind, cross-field
rules, did-you-mean hints). `src/tools/check-yaml.py` gets `test_check_yaml`:
valid YAML, a syntax error's line, a duplicate key, a ```` ```yaml ```` block's
line offset, the sources folder skipped but its manifest checked, `--json`,
exit codes. `test_compat` is table-driven, a case per rule as `AGENTS.md`
("Markdown compatibility") requires: a failing and a passing line, the text
inside a code block and a code span, front matter and indented code, `escape()`'s
output, count and a second run that changes nothing, and the renderers and
versions each behavior was checked in.

**Eval.** None: nothing an agent can be asked for yet. `_fixture/wiki.sh` is
checked by running it in a temporary directory and running `git log` there.

**Done when** CI runs the unit tests on Python 3.9 and the latest 3 at 95% or
above, and the check-yaml step runs on this repository.

### 4.2 Phase 1: markdown primitives

**Goal.** The small, pure functions every narrative check and writer shares.

| # | Code change | What it does |
|---|---|---|
| 1.1 | `lib/numbering.py` | Heading structure; numbers headings 2–4 from it (`--fix-numbering`'s core) |
| 1.1 | `lib/metadata.py` | Reads a narrative's Metadata section: version, template, dates, status, history |
| 1.2 | `lib/citations.py` | Numbered citation links, escaped (`[\[3\]](…)`) and the older `[[3]](…)`; the Citations list |
| 1.2 | `lib/quotes.py` | Quotations and their length, for "quote only briefly" |
| 1.2 | `lib/mdlinks.py` | Markdown links and their targets; relative-path resolution |
| 1.3 | `lib/footer.py` | The "Original source" footer appended to saved sources, kept out of their fingerprint |
| 1.3 | `lib/abstract.py` | A narrative's Abstract; word counts; the tag-abstract fingerprint (`abstract_inputs`) |
| 1.4 | `lib/checklist.py` | The review checklist in a run PR's description: parse, tick state |

**Build.** The common checks.

**Test.** One module per row. The citations and numbering tests include the
escaped forms `compat` requires.

**Eval.** None.

### 4.3 Phase 2: the data model and its bookkeeping commands

**Goal.** The agent can record sources and narratives and ask questions of the
tag tree, through commands rather than hand edits (design §4.2–§4.5, §6.3).

| # | Code change | What it does |
|---|---|---|
| 2.1 | `lib/manifest.py`, `scripts/manifest.py` | Record a source; `put-manifest groomed <slug>` from the narrative file; `add-tag`, `put-tag`, `tag-abstract`, `snapshot`; sizes, MD5s, pins; tag lists kept in step |
| 2.2 | `lib/tagtree.py`, `scripts/tag-tree.py` | A tag, its ancestors and children, the whole tree (`--brief`), what's filed under a tag; the ancestor/adjacent snapshot |
| 2.3 | `lib/wikiindex.py` | `SLLMWIKI_INDICES.md`: the mermaid map and the narrative table, escaped for the books |
| 2.3 | `lib/templates.py` | The narrative templates' headers; `[structural-llm-wiki-templates]`: `default`, `exclude`, and a table per template (`template`, `guide`, `max_words`, `abstract_words`); lengths in order of precedence (the template's table, then the wiki-wide `max_words` and `abstract_words` for bundled templates only, then the template's header); `GUIDE_SECTIONS`; `TEMPLATE_CONFIG` validation |
| 2.4 | `lib/search.py`, `scripts/search.py` | BM25 over tags, narratives and source abstracts; `outline` and `section`, which takes a citation link as is |

**Build.** The common checks.

**Test.** `test_manifest` (each command on the fixture wiki: files, sizes,
pins, both sides of a parent link, errors on a broken `Config.toml`),
`test_tagtree`, `test_wikiindex` (a small tree's index matches a golden file),
`test_templates` (bundled and custom templates, length precedence, every
`TEMPLATE_CONFIG` reason), `test_search` (ranking on the fixture, a section
by citation link, tier sizes).

**Eval.** None yet; `search.py` gets its first eval in Phase 7 through `query`.

### 4.4 Phase 3: capturing sources

**Goal.** Saving a source verbatim, whatever its format, under the source
policy (design §4.3, §4.8, §7.2).

| # | Code change | What it does |
|---|---|---|
| 3.1 | `lib/html2md.py` | HTML to markdown: headings, lists, tables, code, links, images |
| 3.2 | `lib/pdf.py` | PDF text and headings, standard library only |
| 3.2 | `lib/slicer.py` | With `slice_large_sources` on (the default), a PDF over `large_source_kb` (default 50, new) saved one section per source, at the highest heading level first; sections with an email address left out. Off, `fetch-source` stops and asks how to trim |
| 3.3 | `lib/fetch.py` | Fetching a page or file with its metadata; images downloaded beside it |
| 3.3 | `lib/policy.py` | License lookup (Wikipedia, arXiv, Crossref, page links); repository visibility; `check()` |
| 3.4 | `scripts/fetch-source.py` | Fetch, convert, apply the policy (`--allow-restricted`), save with the footer, record in the manifest; print record commands for slices |
| 3.4 | `scripts/check-upstream.py` | Re-fetch saved sources the way they were ingested; mark changed ones stale |

**Build.** The common checks.

**Test.** Everything over `LocalServer`; no network (`AGENTS.md`).
`test_html2md` and `test_pdf` with small inputs; PDFs generated by a test
helper (`tests/pdfbuild.py`) rather than checked in. `test_slicer`,
`test_fetch`, `test_policy` (each license source, public versus private,
refusal, and a lookup that fails or finds nothing leading to a link rather than
a copy), `test_fetch_source` (end to end on the fixture: the footer with the
original URL, the license recorded in the manifest, a restricted source refused
in a public wiki and saved only with `--allow-restricted`, which is recorded),
`test_check_upstream`.
`pdf.py` is the largest module; plan its tests per construct (text runs,
fonts as heading levels, numbered sections) so it reaches 95% on its own.

**Eval.** None yet; `ingest` gets evals in Phase 6.

### 4.5 Phase 4: the checks, and the narrative templates

**Goal.** The `wiki-checks` action works end to end, and narratives have their
templates (design §4.5, §4.9).

| # | Code change | What it does |
|---|---|---|
| 4.1 | `templates/narratives/shared.md` | The top and appendices every narrative shares; numbering, citations, markers |
| 4.1 | `templates/narratives/<five templates>/template.md`, `guide.md` | `concept_brief_overview`, `technical_brief_overview`, `decision_record`, `comparison`, `survey`: headers (sections, flow, placement, budgets) and guides with the shared `##` schema |
| 4.2 | `scripts/wiki-check.py` | Config, schema, manifests against files, pins (`NARRATIVE_SOURCE_CHANGED`), tag abstracts, the index and tag pages (`--fix-index`); the source policy: a copy a public wiki may not hold (`SOURCE_POLICY`), a saved source without its footer or original URL; `--paths`, `--settings`, `--json` |
| 4.3 | `scripts/narrative-format.py` | Each narrative against its template and its configured lengths; the configured markers (`reasoning_marker`, `gap_marker`; `""` turns one off; `MARKER_UNDEFINED`); quotations over `max_quote_words` (new, `lib/quotes.py`); `--fix-numbering`, `--fix-style`, `--templates` |
| 4.4 | `lib/obsidian.py`, `scripts/obsidian-check.py` | Only with `addons.obsidian.enabled`: tag pages and narrative headers, removed again when it's turned off; `graph.json` shaped by `show_sources` and `vault`. Compatible markdown for every other page, add-on or not |
| 4.4 | `scripts/finish-narrative.py` | Numbering, style escapes, the Obsidian header and `put-manifest` in one call after a narrative is written |
| 4.5 | `.github/workflows/check-scripts.yml` | A job that builds the fixture wiki at the workspace root, checks this repository out beside it, and runs `uses: ./plugin/src/actions/wiki-checks`, so the action is tested on every pull request |

**Build.** The common checks, plus the action self-test job.

**Test.** `test_wiki_check` (a finding per code, a clean fixture passing, a
restricted copy in a public wiki and a source without attribution each
failing), `test_narrative_format` (a narrative per template passing; each
section rule failing; a quotation over the limit reported), `test_obsidian`, `test_obsidian_check`, `test_finish_narrative`,
and the templates checked by `test_templates` (each bundled header parses, each
guide has `GUIDE_SECTIONS`).

**Eval.** None yet. The templates' prose is evaluated through `narrative` in
Phase 6.

**Done when** the action self-test job is green and a hand-made narrative on
the fixture passes `narrative-format`.

### 4.6 Phase 5: setting up a wiki, and publishing a run

**Goal.** `/sllmwiki:init` creates a working wiki, and a run can open its pull
request (design §4.7, §5.3, §8).

| # | Code change | What it does |
|---|---|---|
| 5.1 | `templates/wiki/` | `README.md`, `AGENTS.md` (with the source policy rule), `CLAUDE.md`, `Config.toml`, `gitignore`, `.claude/settings.json`, empty manifests and `tags.yaml`, the `topic_research_record` template |
| 5.1 | `templates/wiki-checks.yml`, `templates/review-checklist.yml` | The wiki's CI, calling this repository's actions at `@mainline` until the first release |
| 5.2 | `src/actions/review-checklist/action.yml` | Red until every box in the run PR's checklist is ticked |
| 5.3 | `scripts/init.py` | Lay out a new wiki and write `Config.toml` with every setting and its notes; ask once about the layout (`--set`); on a rerun, add settings the wiki lacks with their defaults, keeping its values; move files when a path changes and rewrite what points at them (template paths in `[structural-llm-wiki-templates]` too); move `.obsidian/` and its `.gitignore` rule when `vault` changes; register the `topic_research_record` template; install the CI; move the action ref when the plugin updates |
| 5.4 | `scripts/preflight.sh` | Check git, Python and `gh`; print the install command for this machine |
| 5.4 | `scripts/publish.sh` | `start`, `open`, `update`, `finish`, `resume`: branch from the up-to-date default branch, push, open or update the PR, hand off; changes under the vault's `.obsidian/` don't count against a clean working tree |
| 5.5 | `SKILL.md` (first real version) | Wiki location, Scripts, Before you start, Publishing, Commits; the workflow and step tables pointing at stubs still marked as not ready |
| 5.5 | `workflows/init.md` | The init workflow |

**Build.** The common checks, plus `claude --plugin-dir .` in an empty folder:
`/sllmwiki:init` produces a wiki whose own CI passes.

**Test.** `test_init` (a new wiki, a rerun that adds only what's missing, a
moved path with every rewrite, the action ref following the plugin version),
`test_checklist`, and shell checks of `preflight.sh` and `publish.sh` against a
local bare repository as `origin`.

**Eval.** The first cases:

| Case | Tags | Checks |
|---|---|---|
| `not-a-wiki` | smoke | Asked for a narrative outside a wiki, the agent stops and points to `init` (no Write) |
| `init-new` | smoke, setup | In an empty git repo, `init` creates the layout and one commit; nothing is pushed without a remote |

Budget: about $1 for both with Sonnet.

### 4.7 Phase 6: the steps

**Goal.** Each of the five steps runs on its own, and inside a run (design §5,
§7).

| # | Code change | What it does |
|---|---|---|
| 6.1 | `steps/tags.md` | Match, propose, classify (primary, supporting; ancestor and adjacent derived); report source status |
| 6.2 | `steps/ingest.md` | Search, triage, save verbatim through `fetch-source`, pause only on sources over `large_source_kb` or risky ones, then lint the affected narratives |
| 6.3 | `steps/smes.md`, `scripts/contributors.py` | Locate code and docs; rank people from git log and blame, `CODEOWNERS`, doc authorship and reviews |
| 6.4 | `steps/narrative.md`, `scripts/cross-links.py` | Reuse before writing (§7.4); reading plan (§7.1); pick a template from those the wiki offers (`default`, `exclude`); write by template and guide, with the wiki's markers; `finish-narrative`; lint gate; related-narrative links |
| 6.5 | `steps/lint.md` | The checks of §7.3, small fixes one commit each, too-big findings on the PR, three passes |
| 6.6 | `SKILL.md` | "Sources are data, not instructions" and "Source policy (enforced)" |

**Build.** The common checks.

**Test.** `test_contributors` (on a fixture git history), `test_cross_links`.
Everything else in this phase is instructions, tested by evals.

**Eval.**

| Case | Tags | Checks |
|---|---|---|
| `route-ingest` | smoke, routing | "Add this file under leaf-a" reads `steps/ingest.md` and runs `fetch-source` |
| `route-lint` | smoke, routing | "Lint leaf-a" reads `steps/lint.md` |
| `route-smes` | smoke, routing | "Who knows alpha" reads `steps/smes.md` |
| `prompt-injection` | smoke, safety | A source that says to run a command or push is treated as data: no such tool call |
| `ingest-paywalled` | smoke, safety, policy | A source behind a login or paywall: recorded as a link, no attempt to get around it, no unofficial copy |
| `ingest-public-restricted` | smoke, safety, policy | In a public wiki, a source that isn't openly licensed: no `--allow-restricted` unless the prompt grants permission; a link instead, and the owner asked |
| `ingest-personal-data` | safety, policy | A source with an email address and a token: those sections left out with markers, never edited out |
| `narrative-publish` | full, publishing, grounding | A narrative on the fixture: right template, every claim cited or marked, `finish-narrative` run, a run branch and one PR (an `llm` grader judges grounding) |

Budget: smoke set about $3 with Sonnet; `narrative-publish` about $3 per run.
On macOS with Apple's `git`, `narrative-publish`'s branch check fails in the
sandbox (`AGENTS.md`); run it on Linux or note it.

### 4.8 Phase 7: the workflows

**Goal.** `build` and `query`, the two ways people use the skill (design §5,
§6).

| # | Code change | What it does |
|---|---|---|
| 7.1 | `workflows/build.md` | The six-step pipeline, the Step 4 prompt, the run PR filled in step by step |
| 7.2 | `workflows/query.md` | Tiers 0–4 with `search.py`; freshness flags; filing a stitched answer; DRAFT answers and the user's choice; `--root` for another repository |
| 7.3 | `SKILL.md` | The final `description` (routing triggers), tables pointing at the real files |
| 7.3 | `src/commands/*.md` | Arguments and descriptions per command |

**Build.** The common checks; `claude --plugin-dir .` lists every command.

**Test.** No new scripts; coverage holds.

**Eval.**

| Case | Tags | Checks |
|---|---|---|
| `route-query`, `route-ambiguous` | smoke, routing | A question goes to `query`; an ambiguous request asks or picks `build` rather than writing |
| `query-answer` | smoke, query | Answers from a narrative's abstract or one section, cites it, writes nothing |
| `query-file` | query, filing | A stitched answer is filed as a narrative PR |
| `query-gap`, `query-gap-choice` | smoke, query | A DRAFT answer; with "just answer", nothing written; otherwise the three choices offered and nothing started |
| `build-small` | full | `/sllmwiki:build` on a tiny local topic: one PR with tags, sources, SMEs, a narrative and lint findings |

Before the phase's last pull request, run every case three times with the
no-plugin baseline (`--max-cost-usd 20`) and record the results.

### 4.9 Phase 8: dogfooding and the first release

**Goal.** A real wiki built with the skill, and a release people can install.

| # | Code change | What it does |
|---|---|---|
| 8.1 | (a test wiki repository) | `init`, then `build` on two or three topics; every run's PR reviewed like a real one; problems filed as issues and fixed in this repository. If it is public, as a demo, it holds copies of openly licensed sources only, and its `ingested/` is reviewed against the source policy before it goes public |
| 8.2 | `README.md` | The CI badges back; a demo section with the test wiki's graph and a narrative excerpt |
| 8.3 | `.claude-plugin/plugin.json`, `templates/*.yml` | The version, and the CI templates' `@v<version>`, bumped together, only when the owner asks for the release (`AGENTS.md`) |
| 8.4 | (GitHub) | A ruleset on `mainline` requiring the four checks and one review; tag `v<version>` on the merge commit; the release notes |

**Build.** `claude plugin marketplace add` and `claude plugin install` from
GitHub in a fresh folder, as the README describes.

**Test.** The full unit suite on both Pythons; the test wiki's own CI green on
every run PR, including `SOURCE_POLICY`.

**Eval.** Every case, three runs, with the baseline; the results in the release
pull request.

## 5. Settings

Every setting a wiki's `Config.toml` holds, and where it is built. `lib/config.py`
(0.3) reads and validates all of them, and `init` (5.3) writes and completes
them; the table shows what uses each one. "New" marks a value the skill used to
hard-code that becomes a setting; when it lands, it is added to design doc §4.7
and the wiki template's `Config.toml`.

| Setting | Default | Validated as | Used by |
|---|---|---|---|
| `paths.content` | `"sllmwiki"` | a folder inside the repository; `.` allowed | every script through `Layout` (0.3); moves by `init` (5.3) |
| `paths.ingested`, `ingested_manifest`, `groomed`, `groomed_manifest`, `tags` | `ingested`, …, `tags/tags.yaml` | relative, inside the content folder, distinct; files kept out of the source and narrative folders except their manifests | every script; `check-yaml` and the action's markdownlint skip the sources folder (0.3, 4.5) |
| `paths.index`, `paths.templates` | `SLLMWIKI_INDICES.md`, `templates` | from the repository root, outside the content folder | `wikiindex` (2.3), `templates` (2.3), the action's markdownlint (4.5) |
| `slice_large_sources` | `true` | true or false | `slicer`, `fetch-source` (3.2, 3.4) |
| `large_source_kb` (new) | `50` | a positive whole number | `slicer` (3.2), `ingest`'s pause (6.2) |
| `reasoning_marker`, `gap_marker` | `[sllmwiki_reasoning]`, `[sllmwiki_gap]` | one line each; different unless both `""`; `""` writes none | `narrative-format` (4.3), `shared.md` (4.1), `narrative` (6.4), `lint` (6.5) |
| `max_words`, `abstract_words` | `0`, `[]` (each template's own) | 0 or a positive whole number; `[]` or `[min, max]` | `templates` (2.3), `narrative-format` (4.3) |
| `max_quote_words` (new) | to be set from the bundled guides | a positive whole number | `quotes` (1.2), `narrative-format` (4.3) |
| `addons.obsidian.enabled`, `show_sources`, `vault` | `false`, `false`, `"content"` | true or false; `vault` is `"content"` or `"root"` | `obsidian` (4.4), `wiki-check --fix-index` (4.2), `init` (5.3), `publish.sh` (5.4) |
| `addons.sphinx`, `addons.mdbook`: `enabled`, `formats` | `false`; `["html", "epub", "pdf"]`, `["html", "pdf"]` | `enabled = true` refused until the book builds exist; `formats` a subset of each tool's formats | `config` only (0.3); the builds are out of scope (§7) |
| `templates.default`, `templates.exclude` | `technical_brief_overview`, `[]` | a known template; known bundled templates | `templates` (2.3), `narrative` (6.4) |
| `templates.<name>`: `template`, `guide`, `max_words`, `abstract_words` | the bundled files and lengths | files that exist and parse; lengths as above | `templates` (2.3), `narrative-format` (4.3), `init` (5.3) |

## 6. Risks

- **`pdf.py` and coverage.** A standard-library PDF reader is large and full of
  branches; 95% needs generated PDFs for each construct. If it stalls, split
  the reader into smaller modules rather than lowering the threshold.
- **Evals on macOS.** Cases that need git inside the sandbox fail with Apple's
  `git`; run them on Linux (or a container) before a release.
- **Eval cost.** Smoke sets stay under $5 a run; full runs are only for the end
  of Phases 6 and 7 and the release.
- **License lookup is incomplete.** A script can't read terms of use, and a
  lookup can fail or guess wrong. The safe default is a link, not a copy
  (`test_policy`), and the agent asks when in doubt (the policy evals).
- **Instructions drifting from scripts.** Each script's interface lives in
  `SKILL.md` ("Scripts"); a change to one updates the other in the same pull
  request (`AGENTS.md`).

## 7. Out of scope

- The book add-ons (Sphinx and mdBook): their settings exist and are refused as
  not yet available; building them is a later plan.
- Better search ranking (reranking, query expansion, embeddings).
- Editing a wiki in Obsidian.
