# Structural LLM Wiki — Design

## 1. Overview

### The problem

Most of what a team knows about its systems isn't written down in one place. Design docs drift from the code, decisions get buried in chat threads and code reviews, and the rest lives in the heads of a few people. New engineers rebuild the same understanding from scratch, and experienced ones answer the same questions again and again.

AI assistants help, but only for the moment: an answer from a chat session is gone when the session ends, nobody can easily check where it came from, and nothing tells you when it stops being true. The team's understanding doesn't accumulate.

### The approach

The structural LLM wiki gives that knowledge a durable home: a git repository the coding agent maintains and the team reviews. The work happens in five moves:

1. **Collect.** For a topic, the agent searches docs, code, and discussions and saves the useful sources into the wiki verbatim, so they can be checked later.
2. **Organize.** Every source is attached to hierarchical topic tags. The tags form a graph that connects sources, narratives, and the people who know each area.
3. **Answer.** For each question, the agent uses that graph to choose what to read, then writes a narrative that answers it, with every claim traced to a source and a list of experts to ask.
4. **Verify.** Lint checks each narrative against its sources, the code, and every related narrative, fixing small issues and flagging conflicts. When a source changes, the narratives that depend on it are checked again.
5. **Use.** A person or another agent asks the wiki a question and gets a cited answer, read from the smallest thing that answers it: a tag summary, a narrative abstract, one section, one cited source section. When nothing covers the question, the answer comes back marked DRAFT and the gap is filed as a draft narrative for review, to be grounded in sources later.

Each run arrives as a single pull request against the default branch, so people stay in control of what enters the wiki without having to do the research. Over time the wiki builds up instead of decaying: answers stay linked to their evidence, new findings are reconciled with old ones, and the history shows how the team's understanding evolved.

This document covers the architecture and the decisions behind it. The skill's files are the source of truth for step-by-step behavior: `src/skills/sllmwiki/workflows/` and `src/skills/sllmwiki/steps/`.

**One skill: two workflows made of five steps.** The skill has two workflows: `build` builds knowledge (§5) and `query` uses it (§6), plus a one-time `init`. They are made of five steps: `tags`, `ingest`, `smes`, `narrative` and `lint`. Each step also runs on its own when only that part is needed. They all share one data model, one set of scripts and one set of rules (wiki location, preflight, publishing), so they live in a single skill: `SKILL.md` holds what is shared and routes to a workflow or step file, which the agent reads only when it runs. Separate skills would each need their own copy of the scripts, since an installer copies one skill folder at a time and a skill can rely only on files inside it.

## 2. Principles

- **The wiki is a dedicated git repository.** All paths are relative to its root. Git provides history, review, and rollback.
- **Sources are ground truth.** Ingested sources are saved verbatim, never summarized or edited. Narratives are built from them and checked against them.
- **Every claim is traceable.** A claim in a narrative cites a source, or is explicitly marked as the narrative's own reasoning (`[sllmwiki_reasoning]`) or a gap (`[sllmwiki_gap]`), both configurable in `Config.toml`, and the narrative defines each marker it uses in its Terminology. Citations are numbered links, each after a space (`claim. [\[3\]](../ingested/<file>.md#<section>)`; the brackets are escaped so Obsidian doesn't read `[[3]]` as a wikilink, and older narratives' `[[3]](…)` is still read, with a warning), that open the cited section of the saved source in one click, listed under `### Citations` at the end of the narrative. (GitHub footnotes were the first style; GitHub draws a ↩ back-link on each, so they were replaced.)
- **Tags index; the user's words carry intent.** Tags locate content. The original question or topic is carried through every step and decides what is relevant.
- **Runs are unattended; review happens on one pull request.** Runs commit as they go and open a single PR per run against the default branch; the user merges it. Mid-run pauses are reserved for decisions that are costly to get wrong. An answered query changes nothing.
- **Build on what exists.** One narrative per question. Before writing, look for a narrative that already covers the question, and reuse it, expand it (a new version) or ground it if it's a draft. A new narrative is written only when the question is genuinely different (§7.4).
- **Readable where people read.** The wiki is plain markdown that renders the same on GitHub and in Obsidian, so it can be browsed page by page or explored as a graph of tags, narratives and sources (§4.9), with no export step and no second copy.
- **Unverified is labeled.** Whatever the sources don't support is marked `[sllmwiki_reasoning]` where it appears. A whole answer the wiki can't ground is a DRAFT, marked in the text, in the manifest and in the index, until a later run grounds it (§6.2).
- **Tool-neutral.** The workflows name capabilities (docs search, code search, page fetch, git history) rather than specific tools, so they work with whatever the agent has.

## 3. Layout

**This package** (`sllmwiki`):

```text
sllmwiki/
├── .claude-plugin/
│   ├── plugin.json                        # Claude Code plugin manifest
│   └── marketplace.json                   # makes this repo a plugin marketplace
├── src/                                   # the plugin: what installs and runs
│   ├── skills/sllmwiki/                   # the one skill
│   │   ├── SKILL.md                       # what the wiki is, shared rules, the workflow and step tables
│   │   ├── workflows/                     # read when the workflow runs
│   │   │   ├── build.md                   # build knowledge
│   │   │   ├── query.md                   # use knowledge
│   │   │   └── init.md                   # one-time init
│   │   ├── steps/                         # read when a workflow (or the user) runs the step
│   │   │   ├── tags.md
│   │   │   ├── ingest.md
│   │   │   ├── smes.md
│   │   │   ├── narrative.md
│   │   │   └── lint.md
│   │   ├── scripts/                       # the deterministic scripts, one copy (wiki-check, manifest, tag-tree, search, …)
│   │   │   └── lib/                       # shared modules (YAML reader, schema, tag tree, search, HTML converter, PDF reader)
│   │   └── templates/                     # narratives/ (narrative templates); wiki/ and the CI workflows init installs
│   ├── commands/                          # Claude Code commands, one per workflow and step
│   ├── actions/                           # GitHub actions a wiki's CI calls
│   └── tools/                             # CI-only tools outside the skill (check-yaml)
└── docs/
    └── structural_llm_wiki_design.md      # this file
```

**A wiki repository** (created by `init`):

```text
<wiki-repo>/
├── README.md                 # what this wiki is and how to use it
├── SLLMWIKI_INDICES.md       # generated map of topics and narratives (click a narrative to open it)
├── AGENTS.md                 # rules for agents working in this repo
├── CLAUDE.md                 # imports AGENTS.md for Claude Code
├── .gitignore
├── .claude/settings.json     # offers the sllmwiki plugin to teammates
├── .github/workflows/        # review-checklist.yml: red until a run PR's review boxes are ticked
├── Config.toml               # where the wiki keeps the files below (§4.7)
├── templates/                # the wiki's own narrative templates (configured in Config.toml, §4.5)
│   └── topic_research_record/  # the wiki's own example template
└── sllmwiki/                 # the content folder (§4.7): the knowledge, Obsidian's vault, the books' source
    ├── tags/
    │   ├── tags.yaml         # hierarchical topic tags
    │   └── <tag>.md          # a page per tag, with the Obsidian add-on
    ├── ingested/             # sources, saved verbatim (flat)
    │   ├── manifest.yaml     # source registry
    │   └── images/
    └── groomed/              # narratives, one per question
        └── manifest.yaml     # narrative registry
```

These are the default names; `Config.toml` can give each of them another path (§4.7). A repository is a wiki if its tags file exists; everything else stops and points to `init` otherwise.

## 4. Data model

### 4.1 Topic tags

A **topic tag** connects sources, narratives, and people.

- One source → many tags; one narrative → many tags (a question can span topics); one tag → many sources, narratives, and SMEs.
- Tags form a hierarchy: a parent tag contains sub-tags.
- Sources and narratives attach to the **most specific tag they are about**. A parent holds what covers it as a whole (an overview source, a comparison across its sub-tags), and its sub-tags hold the specific ones. Parents roll up their sub-tags' content at narrate time, so nothing is listed twice up the tree. Giving a tag a child moves nothing. (An earlier rule allowed sources only on leaf tags. It forced a tag's general sources and narratives onto a sub-tag as soon as the tag got a child, so it was dropped.)

For a given question, each tag has a class:

| Class | Determined by | Role in reading |
|---|---|---|
| **primary** | Proposed by tag resolution | Core topic. Sources read in full, last (highest attention) |
| **supporting** | Proposed by tag resolution | Related context. Sources read in full, before primary |
| **ancestor** | Derived: parent chain of primary/supporting tags | Not read. Recorded in the narrative for lint |
| **adjacent** | Derived: siblings of primary/supporting tags | Not read. Recorded in the narrative for lint |

`tags` asks the user to confirm primary and supporting tags when run on its own; inside the pipeline and in `narrative`, the classification is applied automatically and recorded on the PR. A parent tag is an ancestor, never "supporting". Ancestor and adjacent tags are a snapshot of the tree at generation time, stored in the narrative file rather than the manifests, so lint can detect when the tree has changed.

### 4.2 `tags.yaml`

```yaml
request-handling:
  description: "Top-level category for components that receive, route, and serve requests"
  parent: null
  sub_tags: [gateway, load-balancer, rate-limiter, routing]
  ingested: []
  groomed: []
  smes: []
  abstract: "Request handling covers how a request reaches a backend: … (150–250 words, rolled up from the sub-tags' abstracts)"
  abstract_inputs: 9f8e7d6c5b4a...   # written by manifest.py tag-abstract

gateway:
  description: "Gateway service — routes incoming API requests to the appropriate backend"
  parent: request-handling
  sub_tags: []
  ingested:
    - ingested/gateway-design-doc.md
    - ingested/gateway-arch-diagram.png
  groomed:
    - groomed/what-is-gateway.md
  smes:
    - "@alice (design doc author, 45% of router.go)"
    - "@bob (30 commits in last 3 months)"
  contact_channels:            # optional; only channels found in a source
    - "Chat: #gateway-dev"
    - "Owning team: @example-org/gateway-team"
  abstract: "The gateway is the single entry point for API requests: … (150–250 words, from its narratives' abstracts)"
  abstract_inputs: 1a2b3c4d5e6f...
```

**Schema.** `tags.yaml` and both manifests have a schema, in `lib/schema.py`: for every field, its kind (string, whole number, ISO date, MD5, quoted version, kebab-case name, repository path, one of a set of values, list, mapping) and whether it is required or may be null, plus rules across fields (a `link` source has no `file`; `abstract_inputs` needs an `abstract`). `wiki-check` validates every entry against it and reports missing fields, unknown fields with a did-you-mean hint, wrong types and bad values as errors, so the wiki's CI fails the pull request.

**Tag abstracts.** Every tag that has a narrative, or a sub-tag with an abstract, carries an `abstract` of 150–250 words: what the topic is and what the wiki knows about it, written from its narratives' Abstracts and its sub-tags' abstracts. `manifest.py tag-abstract <tag> --abstract "…"` writes it together with `abstract_inputs`, a fingerprint of those inputs. When a narrative is added or changed, its tag's fingerprint no longer matches and `wiki-check` warns `TAG_ABSTRACT_STALE` (or `TAG_ABSTRACT_MISSING`); rewriting that tag's abstract then makes its parent stale, so the update rolls up to the root. `narrative` and `lint`, the steps that add or change narratives, re-abstract the flagged tags, deepest first, before they commit.

Tags are written with `manifest.py add-tag` (a new tag, listed in its parent's `sub_tags` in the same edit, so both sides of the link agree) and `put-tag` (description, SMEs, contact channels), never by hand. The `ingested` and `groomed` lists are kept by the commands that record sources and narratives. `tag-tree` answers questions about the tree: a tag, its ancestors and children, the whole tree (`--brief` for names and counts), and the sources or narratives filed under a tag.

Paths are relative to the repository root. `ingested` lists saved files only; `link` and `other` sources have no file, so they are found through the `tags` field of their entry in `ingested/manifest.yaml`. Query with `yq`, for example `yq '.[] | select(.parent == "request-handling")' tags.yaml`.

### 4.3 `ingested/manifest.yaml`

One entry per source, keyed by slug (`<topic>-<source-name>`).

```yaml
gateway-design-doc:
  file: ingested/gateway-design-doc.md
  type: raw_content
  size_bytes: 15230
  original_url: https://docs.example.com/gateway/design
  content_modified: "2026-07-13T20:00:00Z"
  content_ingested: "2026-07-13T22:15:00Z"
  content_md5: a1b2c3d4e5f6...
  tags: [gateway, routing]
  abstract: "Original gateway architecture and design rationale. …"   # 150–250 words; shortened here

gateway-code-reference:
  type: link
  size_bytes: null
  original_url: https://github.com/example-org/gateway/blob/main/src/routing/router.go
  content_modified: "2026-07-10T14:00:00Z"
  content_ingested: "2026-07-13T22:15:00Z"
  content_md5: null
  tags: [gateway, routing]
  abstract: "Core routing implementation — read for call flow details."
```

| Type | Stored |
|---|---|
| `raw_content` | Full content, verbatim, as markdown in `ingested/`; images downloaded to `ingested/images/` |
| `image` | The image file in `ingested/images/` |
| `link` | Pointer only (live code, dashboards, large repos) |
| `other` | Pointer only (videos, spreadsheets) |

A source is **stale** when `content_modified > content_ingested`. The `abstract` (150–250 words: the source's own abstract, verbatim, when it has one) and `size_bytes` fields let `narrative` triage and size its reading plan without opening files.

### 4.4 `groomed/manifest.yaml`

One entry per narrative, keyed by question slug.

```yaml
what-is-gateway:
  file: groomed/what-is-gateway.md
  question: "What is the gateway and how does it work?"
  size_bytes: 4195
  version: "1.0"
  created: "2026-07-13"
  last_modified: "2026-07-13"
  tags:
    primary: [gateway]
    supporting: [routing]
  sources_read_full:
    gateway-design-doc: a1b2c3d4e5f6...   # MD5 of the version read
  sources_abstract_only: [load-balancer-overview]
  abstract: "The gateway is the single entry point … (the narrative's Abstract)"
  # status: draft    # only on a draft narrative from query (§6.2)
```

A narrative's entry is written by `manifest.py put-manifest groomed <slug>`, never by hand: the question, version, dates and draft status are read from the narrative's title and Metadata section, its Abstract from its Abstract section, and the size and pins are computed, so the manifest mirrors the file (`wiki-check` warns `NARRATIVE_METADATA_MISMATCH` otherwise). `sources_read_full` pins each source to the MD5 of the version the narrative was built from (written by `put-manifest`, or `manifest.py snapshot` to re-pin). When a source is re-ingested, its MD5 changes and `wiki-check` reports `NARRATIVE_SOURCE_CHANGED` for every narrative pinned to the old version, so exactly those narratives are re-checked.

### 4.5 Narratives

One question per file in `groomed/`. The question is the title, unchanged.

**Templates.** A narrative follows one of the templates in `src/skills/sllmwiki/templates/narratives/`, one folder per kind of narrative holding `template.md` and its writing guide `guide.md` (or one of the wiki's own; see Customizing templates below). Each `template.md` has a header that says what the template is for (`description`, `use_when`) and which sections a narrative from it must have: per section, a title pattern, whether it's required, whether it needs a diagram and walkthrough (`flow`), and placement (`right_after`), plus its appendices, where numbering starts, its word budget (`max_words`) and its Abstract's range (`abstract_words`, 150–250 words when left out). The body is the template the narrative step follows. Narrate picks a template from the list (`narrative-format.py --templates`) and records it in the narrative's Metadata (`- **Template:** <name>`). `narrative-format` checks each narrative against its own template, so adding a kind of narrative means adding a folder (or, in a wiki, two files and a table in `Config.toml`), with no code change. Every template shares the Abstract, numbered citations and the Metadata appendix.

There are five templates, one per kind of question:

| Template | For | Body sections (optional ones in brackets) | Budget |
|----------|-----|-------------------------------------------|--------|
| `concept_brief_overview` | "What is X?" about an idea or a field | Definition (authoritative, quoted), [Why it matters], Key ideas, [Boundaries], [Where to go next] | 900 words |
| `technical_brief_overview` (default) | "How does X work?" about a system | Background, [What is X?], How does it work? (overview, a mermaid flow and a numbered walkthrough, per-component detail), Design decisions and trade-offs, Limitations and failure modes, [FAQ] | 1,800 words |
| `decision_record` | "Why X?", "Should we X?" (after ADR and MADR) | Context, [Decision drivers], Options considered, Decision, Consequences | 1,000 words |
| `comparison` | "X vs Y" | What each is, At a glance (a criteria table), Key differences, [What they share], When to choose which, [FAQ] | 1,200 words |
| `survey` | "What are the principles / patterns of X?" | Scope, At a glance (a table of items), In detail, How they relate, Spectrum (three to five routes to go deep, 100–200 words each), [Applying them], [FAQ] | 2,200 words |

Every narrative has the same top and appendices (`shared.md`): the **Abstract**, 150–250 words like a paper's abstract (`manifest.py put-manifest` copies it into the narrative's `abstract` in the groomed manifest, and `wiki-check` warns `ABSTRACT_OUT_OF_SYNC` when they drift); then a **Terminology** table defining every term the template's reader needs before its first use; and the appendices **SMEs**, **References** (sources read in full, code references as links, related narratives, citations), **Topic tags** (with the ancestor/adjacent snapshot) and **Metadata** (version, template and history). The budget counts the numbered sections only; `narrative-format` warns `BODY_LENGTH` above it.

**What `shared.md` holds, and what it leaves to templates.** `shared.md` holds only what is the same for every narrative: the top and appendices, heading numbering, citations and the markers. It sets no reader, purpose or tone; those belong to each template's guide, so a wiki that writes its own template decides them for itself.

- **Markers.** `shared.md` is the one place that says how to mark what the sources don't state, so no guide repeats it. The reasoning marker (`[sllmwiki_reasoning]` by default) flags the narrative's own conclusions, recommendations, groupings, relations and reconstructions; the gap marker (`[sllmwiki_gap]`) flags what the sources don't answer, which is marked, never filled with a guess. A wiki can change them or turn them off (`""`) in `Config.toml` (§4.7). `narrative-format` warns `MARKER_UNDEFINED` when a narrative uses one that its Terminology doesn't define.
- **Writing for newcomers** lives in the guides that teach. The technical brief overview's guide has a "Writing for a reader new to the topic" section, learned from user review of early narratives: every passage serves learning, so meta content stays out; context comes before mechanics (the problem with an example, the prerequisites, then the core idea in numbers); every scenario states its goal first; one notation runs throughout, each symbol defined with its type and step-by-step quantities written with subscripts; the basic form comes before its variants; and parameters come with rules of thumb. The concept guide, written for newcomers too, keeps the parts that fit it. The other guides keep only "every passage serves the purpose", with no meta content.

**Markdown that renders the same on GitHub and in Obsidian**, and the Obsidian add-on that puts the tags in its graph: §4.9.

Every heading of level 2 to 4 is numbered: `## 1. Abstract`, `## 2. Terminology`, then the body and the appendices continue the sequence, with subsections under their section (`### 5.1`, `#### 5.1.1`). `narrative-format --fix-numbering` rewrites the numbers from the heading structure, and the skills run it, then the check, after every edit to a narrative.

**Writing guides.** Each template comes with its own writing guide, `guide.md`, next to its `template.md` in `templates/narratives/<name>/`. Guides share one schema, the same `##` sections in the same order: Audience and purpose, Voice and tone, Structure, Formats, Evidence, Length, Checklist (`GUIDE_SECTIONS` in `lib/templates.py`; extra sections are allowed). The bundled guides follow technical documentation style (after the Google developer documentation and Microsoft style guides), tuned to each kind: the concept guide writes for a newcomer at definition level, the technical guide for an engineer who needs the mechanism, the decision guide stays neutral between options, the comparison guide gives each side the same depth and vocabulary, and the survey guide keeps items parallel. `narrative` writes by the guide and goes through its checklist; `lint` checks against it.

**Customizing templates.** A wiki configures its templates in `Config.toml` (§4.7), under `[structural-llm-wiki-templates]`: which template is the default, which bundled ones it doesn't offer, and one table per template it customizes. Paths are from the repository root, like every path in `Config.toml`. `init` registers one template of the wiki's own there, `topic_research_record` (research question, sources consulted with their authority, findings with confidence, open questions), and copies its `template.md` and `guide.md` into the templates folder as a working example:

```toml
[structural-llm-wiki-templates]
default = "technical_brief_overview"   # for narratives that name no template
exclude = ["comparison"]               # bundled templates not offered for new narratives

[structural-llm-wiki-templates.survey]          # a bundled template with this wiki's own guide
guide = "templates/survey/guide.md"

[structural-llm-wiki-templates.technical_brief_overview]   # a bundled template with this wiki's lengths
max_words = 3000
abstract_words = [150, 300]

[structural-llm-wiki-templates.runbook]         # a template of the wiki's own: both files
template = "templates/runbook/template.md"
guide = "templates/runbook/guide.md"
max_words = 800
```

**Lengths** (`max_words`, `abstract_words`): a template's table wins. For the skill's own `template.md` (a bundled template, guide replaced or not), the wiki-wide `max_words` and `abstract_words` in `[structural-llm-wiki-settings]` come next, then the bundled header. For the wiki's own `template.md`, its header comes next, and the wiki-wide values don't apply.

A file left out comes from the bundled template of the same name, and without tables the bundled templates are used as they are. Excluded templates still check the narratives that name them. `narrative-format` validates the configuration and every template and guide it names (`TEMPLATE_CONFIG`), so a broken customization shows as a red check; meanwhile narratives fall back to the bundled templates. The wiki's markdownlint skips `templates/`, whose skeletons are full of `<placeholder>` text by design.

The templates are configured in `Config.toml`, not in a file of their own, so that one file holds all of a wiki's configuration.

Updating a narrative for the same question bumps its version and adds a history entry rather than creating a new file. Each template holds the section-by-section instructions, its guide the style, and the `narrative` step the evidence and citation rules shared by all.

**Drafts.** A narrative written by `query` for a question nothing covered (§6.2) is a draft:
- a `> **DRAFT** — …` banner under its title, and `- **Status:** draft` in its Metadata;
- version `0.x`;
- every claim its few sources don't support marked `[sllmwiki_reasoning]`;
- a `Sources to ingest` list under References.

`put-manifest` records `status: draft`, `SLLMWIKI_INDICES.md` lists it as `DRAFT: <question>`, and `narrative-format` requires the banner on drafts and only on drafts. Grounding a draft (an `build` or narrate run on the same question) cites real sources, removes the banner and status, and makes it version 1.0.

### 4.6 Why YAML

| Format | Pros | Cons |
|---|---|---|
| **YAML** (chosen) | Human- and LLM-readable, grep-friendly, `yq` queryable, clean git diffs | Slower than a database at thousands of entries |
| Markdown | Best for browsing | Hard to query by attribute; error-prone for LLM edits at scale |
| JSONL | Fastest to query with `jq` | Not human-readable |
| SQLite | Indexed queries | Binary: no git diff, LLM can't read it directly |

YAML fits the expected scale (tens to low hundreds of sources). Migrate to a database if search becomes slow.

### 4.7 Wiki layout: Config.toml

Where a wiki keeps its files is set in `Config.toml` at the repository root, which `init` creates with the defaults:

```toml
[structural-llm-wiki-paths]
content = "sllmwiki"                        # the content folder; "." is the repository root
ingested = "ingested"                       # in the content folder: sources (images/ and files/ inside)
ingested_manifest = "ingested/manifest.yaml"
groomed = "groomed"                         # narratives
groomed_manifest = "groomed/manifest.yaml"
tags = "tags/tags.yaml"                     # its folder also holds the tag pages (Obsidian add-on)
index = "SLLMWIKI_INDICES.md"               # from the repository root: GitHub's map
templates = "templates"                     # from the repository root: the files of the wiki's own templates

[structural-llm-wiki-settings]  # settings for the skill
slice_large_sources = true                # save a PDF over 50 KB one section per source
reasoning_marker = "[sllmwiki_reasoning]" # marks a narrative's own reasoning; "" writes no marker
gap_marker = "[sllmwiki_gap]"             # marks what the sources don't answer; "" writes no marker
max_words = 0                             # every bundled template's body budget; 0 keeps each template's own
abstract_words = []                       # every bundled template's Abstract range; [] keeps each template's own

[structural-llm-wiki-settings.addons.obsidian]   # the Obsidian add-on (§4.9)
enabled = false                           # tag pages, narrative headers, default graph settings
show_sources = false                      # the default graph shows sources, in grey; false hides them

[structural-llm-wiki-settings.addons.sphinx]     # the book with Sphinx + MyST-Parser (docs/book_add_on_proposal.md)
enabled = false                           # planned: true is CONFIG_INVALID until it exists
formats = ["html", "epub", "pdf"]         # any of html, epub, pdf

[structural-llm-wiki-settings.addons.mdbook]     # the book with mdBook
enabled = false                           # planned: true is CONFIG_INVALID until it exists
formats = ["html", "pdf"]                 # any of html, pdf

[structural-llm-wiki-templates]           # the narrative templates (§4.5)
# default = "technical_brief_overview"
# exclude = ["comparison"]

[structural-llm-wiki-templates.technical_brief_overview]  # a bundled template's lengths, over the two above
max_words = 3000
abstract_words = [150, 300]

[structural-llm-wiki-templates.topic_research_record]     # the wiki's own template: its files and lengths
template = "templates/topic_research_record/template.md"
guide = "templates/topic_research_record/guide.md"
max_words = 1500
abstract_words = [150, 250]
```

- **The content folder** ([proposal](content_folder_proposal.md)). `content` names the folder that holds the knowledge: the tags, narratives and sources, which is also the Obsidian vault and the books' source. `ingested`, `ingested_manifest`, `groomed`, `groomed_manifest` and `tags` are relative to it; `index` (GitHub's map) and `templates` (tooling) are from the repository root and must be outside it. `Layout.paths` resolves everything to paths from the repository root, so the scripts don't change; `Layout.raw` keeps what `Config.toml` says. New wikis get `content = "sllmwiki"`. A `Config.toml` without `content` means `"."`, and `init` writes that in, so an existing wiki keeps its layout until it sets `"sllmwiki"` and reruns `init`, which moves the knowledge (the tags file's folder whole, with the tag pages), commits `Config.toml` with the move, and rewrites what points at it. The README's layout tree is generated from the layout.
- **Reading it.** Every script reads it through `lib/config.py` (a TOML subset reader in `lib/toml.py`, since Python 3.9 has no `tomllib`), and a wiki without it uses the defaults. The paths must be relative, inside the repository, distinct, and keep files out of the source and narrative folders (except each folder's own manifest). `wiki-check` reports a broken file as `CONFIG_INVALID`, and the other read-only scripts fall back to the defaults meanwhile; the scripts that write (`fetch-source`, `manifest.py`, `init`) refuse to run. `wiki-check --paths` prints the paths and `wiki-check --settings` the settings. A marker must be one line, the two must differ unless both are off, and `""` turns one off. `max_words` (0, or a positive whole number) and `abstract_words` (`[]`, or `[min, max]`) set every bundled template's lengths. A `[structural-llm-wiki-templates.<name>]` table sets one bundled template's lengths and wins over them. A wiki's own templates set theirs in their own tables, and the wiki-wide values don't apply to them (§4.5). The workflows' docs use the default names and tell the agent to use the configured ones.
- **Choosing it.** On a new wiki, `init` shows the default layout once and asks whether to keep it; other names are passed as `--set <key>=<path>` (a folder's manifest follows its folder unless set too).
- **Changing it.** After the wiki has content, a path changes by `--set`, or by editing `Config.toml` and rerunning `init`. It moves each file or folder whose configured path doesn't exist from where an earlier commit's `Config.toml` (or the default) had it, with `git mv`, then rewrites what points at it: the file lists in the manifests and `tags.yaml`, the narratives' relative links and their recorded sizes, path mentions in `README.md` and `AGENTS.md`, and the fingerprints of tag abstracts that were current. Sources are never edited; their images move with them. It is one commit, `[sllmwiki][init] Move <old> to <new> as Config.toml sets`.
- **CI.** The wiki checks read `Config.toml` too: markdownlint and `check-yaml` skip the configured sources folder (and markdownlint the templates folder).
- **Tables.** The tables are prefixed with the project's name (`[structural-llm-wiki-paths]`, and `[structural-llm-wiki-settings]` for the skill's settings), so `Config.toml` can also hold other tools' tables, which the scripts leave alone.
- **Settings.** `slice_large_sources` (default `true`): `fetch-source` saves a PDF over 50 KB one section per source (`lib/slicer.py`). It splits at the highest heading level first and goes deeper only inside a piece still over the limit; a heading's level counts its section-number depth, since PDF font sizes often put "2" and "2.1" at the same markdown level. Short introductions join the next piece, sections holding an email address are left out, and each piece gets the `--start`/`--end` markers that reproduce it. Recording each section needs its own abstract, so `fetch-source` prints the record commands instead of recording. Add-ons are optional features, each with its own table under `[structural-llm-wiki-settings.addons.<name>]`, off by default; `settings(root)['addons'][<name>]` holds each. The Obsidian add-on (§4.5) has `[structural-llm-wiki-settings.addons.obsidian]`: `enabled` (default `false`) turns it on, and `show_sources` (default `false`) sets whether its default graph shows sources, in grey. The book add-ons build the wiki as a book at release time ([proposal](book_add_on_proposal.md)): `[structural-llm-wiki-settings.addons.sphinx]` (Sphinx and MyST-Parser, issue #37) and `[structural-llm-wiki-settings.addons.mdbook]`, each with `enabled` (default `false`) and `formats` (what a build produces). They are planned, so `enabled = true` is `CONFIG_INVALID` (`NOT_YET` in `lib/config.py`) until each build exists. Add-on settings are typed like their defaults (true/false, or a list), and `init` adds a missing one with its notes. Settings are validated like paths (`CONFIG_INVALID`).
- **Narrative templates** are configured here too, under `[structural-llm-wiki-templates]` (§4.5). When the templates folder moves, `init` rewrites the template paths in these tables.

### 4.8 Source policy

The wiki keeps verbatim copies, so the skill enforces a source policy ("Source policy (enforced)" in `SKILL.md`):
- **Copyright** stays with each source's authors. A copy transfers no rights, the wiki's own license never covers `ingested/`, and narratives are original writing with brief, attributed quotations.
- **Attribution:** every source keeps its original URL (footer and manifest) and, when found, its license; narratives cite every claim and link the originals.
- **Access controls are never bypassed:** no logins, paywalls, registration walls or anti-bot protection, and no unofficial copies.
- **Licenses and terms decide what may be copied.** A private repository (or a wiki with no remote) keeps reference copies unless a source's terms forbid sharing; a public one keeps only openly licensed sources. Everything else is a `link`.
- **No personal data or secrets,** whatever the license; sections that hold them are left out with markers, never redacted by editing.

`lib/policy.py` holds the checkable part:
- **License lookup:** Wikipedia's known license, the license link on an arXiv abstract page, Crossref's record for a DOI, or a license link in the page itself.
- **Repository visibility:** `gh`, else GitHub's public API.
- **Decision:** `check()`.

`fetch-source` applies it before saving, records the license in the manifest (`license`), and refuses a restricted source in a public wiki unless the user confirms permission (`--allow-restricted`, recorded in `license`). `wiki-check` reports `SOURCE_POLICY` for any saved copy a public wiki may not hold, so the wiki's CI catches it. `init` adds the policy rule to each wiki's `AGENTS.md`. Terms of use can't be read by a script; judging them is the agent's job, and when in doubt it records a link and asks.

### 4.9 Reading in Obsidian

A wiki is read in two places: on GitHub, page by page, and in [Obsidian](https://obsidian.md), as a graph of everything it knows. Obsidian opens a folder of markdown as a vault and draws every file as a node and every link as an edge, so a wiki that links its tags, narratives and sources is already most of a knowledge graph. Two pieces make it whole: markdown that both render alike, and an add-on that puts the tags in the graph.

**Compatible markdown.** A wiki can be opened as an Obsidian vault ([proposal](obsidian_add_on_proposal.md)), so narratives use only markdown both render alike (`shared.md`). `lib/compat.py` defines it: markdown links, never wikilinks or embeds, with paths relative to the linking file and spaces written `%20` (Obsidian also resolves from the vault root or by note name, and reads a raw space; GitHub does neither); no highlights, `%%` comments, block IDs or inline `#tags`; only GitHub's five alerts as callouts; a blank line after a bold line; escaped citation brackets; `$$` math where GitHub renders it unchanged. The same rules keep a wiki ready for the books ([proposal](book_add_on_proposal.md)), checked by rendering with mdBook 0.5.4 and Sphinx 9.1 with MyST-Parser 5.1: URLs as links, never bare (the books don't link them); escapes for what a book reads as its own syntax (a `%` starting a line is a MyST comment, a `{…}` ending a heading is mdBook's id, a `$` before a number starts MyST math, single tildes strike through on GitHub and mdBook only, and `{{#include …}}` is expanded even in code); no emoji shortcodes or MyST syntax; headings that skip no level; and links to files, not folders. What configuration can settle, the book adapters settle instead (§3 of the proposal). `narrative-format --fix-style` writes the escapes, and the generated tag pages and index are written with them. `narrative-format` checks narratives, and `obsidian-check` every other markdown file outside the sources (which stay verbatim); the wiki's CI runs both.

**The Obsidian add-on** (`enabled = true` in `[structural-llm-wiki-settings.addons.obsidian]`; `lib/obsidian.py`). Obsidian's graph has one rule: every markdown file is a node and every link an edge. Narratives and sources are already nodes, linked by citations, but tags live in `tags.yaml`, which Obsidian doesn't graph. So the add-on generates, from `tags.yaml` and the manifests:

- **A tag page per tag**, next to `tags.yaml` (by default `tags/<tag>.md`, which is why the tags file moved into `tags/`): the tag's description and abstract, a breadcrumb up to its root, its subtags, its narratives (primary and supporting), its sources (flagging those no narrative read yet), and its SMEs and channels as text. The links put the tag tree in the graph, with each tag's narratives and sources around it, and on GitHub each page is a topic to browse. `wiki-check --fix-index` writes them with the index; a hand-written file is never touched (the pages carry a generated marker).
- **A header on each narrative**: its tags as Obsidian tags (full paths, such as `algorithms/moving-averages/ewma`), its version and its last update. `finish-narrative` writes it from the manifest and Metadata, so Obsidian's tag pane, `tag:` searches and property views cover narratives. The marker is a property, not a `#` comment, which tools would read as the title.
- **The default graph settings**, `.obsidian/graph.json` in the vault, written once by `init`: color groups for tag pages, narratives and sources, and sources filtered out unless `show_sources = true` (then grey). The vault is the content folder by default (`vault = "content"`), so only the knowledge appears; `vault = "root"` makes it the repository, and the filter then also hides the README, agent files, index and templates. `.obsidian/` moves when the vault's folder changes; `.gitignore` shares only its `graph.json`; `publish.sh` ignores `.obsidian/` changes when it checks for a clean working tree. The wiki owns the file from then on.

Sources are never changed: they get their edges from citations and tag pages. Tags inside sources would add `tag:` search over them, but a header that changes with the tags would break their fingerprints (`content_md5`), so it would need the treatment the footer gets; that is left for later. Turning the add-on off removes the pages and headers it generated and keeps `.obsidian/`.

## 5. Building knowledge: `build` and review

### 5.1 The pipeline (`build`)

| # | Step | What happens | Commit |
|---|---|---|---|
| 1 | `tags` | Match the topic to existing tags, propose new ones, classify, flag stale sources | — |
| 2 | `ingest` | Search, ingest new sources, refresh stale ones | ✓, then open the run PR |
| 3 | `smes` | Rank people for the tags; update `tags.yaml` | ✓ |
| 4 | — | Ask which question(s) to answer; for each, look for a narrative that already covers it and propose reuse, expand, ground a draft, or new (§7.4) | — |
| 5 | `narrative` | One narrative per question, linted before saving | ✓ |
| 6 | `lint` | Check the new narrative against sources and neighbors; fix small issues | ✓ if fixes |

Steps 5–6 repeat for each question that isn't a reuse: expand and ground update the existing narrative, and new writes one. The topic description is passed to every step.

### 5.2 Human involvement

| When | What | Blocking |
|---|---|---|
| Step 2 | Confirm or skip a source only if it is over 50KB or risky (confidential, restricted, unclear provenance) | Only when flagged |
| Step 4 | Provide the question(s), and confirm reuse / expand / new where the wiki already covers one (one combined prompt) | Always |
| End of run | Review and merge the PR; decide pending items (for example, too-big lint findings) listed at its top | No |

### 5.3 Review model

- Each run works on its own branch (`sllmwiki/<slug>`), created from the up-to-date default branch, never from another run's branch. A run stops if the local default branch doesn't match the remote's (for example, a clone made before a rename).
- **Under the orchestrator**, the steps only commit. The orchestrator opens one PR after Step 2 and, after every later step, pushes the new commit and appends that step's summary to the PR description. The description carries every summary block in full (tag classification, source table, SME tables, reading plan, lint findings), because it is the record of the unattended run.
- **Run on its own**, a step opens its own PR. Lint runs triggered by `ingest` or `narrative` share the caller's branch and PR.
- **`query`** opens nothing when one narrative answers. A stitched answer (§6.1) opens a normal narrative PR. On a gap (§6.2), the user's choice opens either `build`'s run PR or a `[DRAFT] <question>` PR on `sllmwiki/draft-<slug>`. A repeated or similar question reuses an existing draft and its PR instead of opening another.
- **The user merges the PR.** Runs never merge their own PRs; at the end they hand off the PR link and summary, with pending decisions listed at the top of the description. PRs are opened with `gh` when available, otherwise through the link `git push` prints. With no remote, commits stay on a local branch and the summary is printed.
- If the user's request asks for a different flow ("merge it for me", "use branch X"), that request wins.
- Feedback and decisions are applied by rerunning on the same branch; the existing PR is updated, never replaced.

### 5.4 Commit messages

| Action | Format |
|---|---|
| Setup | `[sllmwiki][init] Set up LLM wiki repository` |
| Ingestion | `[sllmwiki][ingest][<tags>] ingest new raw sources related to topic: <topic>` (or `modify existing raw sources…` for refreshes) |
| Tags | `[sllmwiki][tags][<tags>] <summary>` |
| SMEs | `[sllmwiki][smes][<tags>] <summary>` |
| Narrative | `[sllmwiki][narrative][<tags>] <question>` (a draft: `[sllmwiki][narrative][<tags>] [DRAFT] <question>`) |
| Lint | `[sllmwiki][lint][<tags>] <finding id> <summary>`, one commit per fix |

Commit bodies carry the step's summary, so each commit is reviewable on its own.

## 6. Using knowledge: `query`

### 6.1 Answering from the smallest thing that answers

An agent, possibly working in another repository (`--root` points the scripts at a wiki clone), asks a question. `query` turns it into keywords, resolves tags (the whole tree with `tag-tree list-tree --brief` for a small wiki, otherwise `search.py tags`), and works down tiers, **stopping at the first that answers**:

| Tier | Reads | Tool |
|---|---|---|
| 0 | the tag's abstract ("what is X") | `search.py tags` |
| 1 | narrative abstracts; most questions stop here | `search.py narratives --tags …` |
| 2 | one section of a narrative | `search.py outline` / `section` |
| 3 | the cited source section, by passing the narrative's citation link as is | `search.py section "<link>"` |
| 4 | sources no narrative covers yet, by abstract | `search.py sources --tags …` |
| gap | nothing: a DRAFT answer, then the user chooses (§6.2) | `build`, or the narrative step in draft mode |

The answer cites narrative and source sections, flags freshness (a narrative built on sources re-ingested since, `built_on_changed_sources`; a stale source), states what isn't covered, names the tags' SMEs, and says which tiers it read and roughly how much. A narrative with `status: draft` may be used, but the answer is then a DRAFT too.

**Filing a stitched answer.** When one narrative answers, `query` changes nothing. When the answer had to be stitched together, from **two or more narratives** or from **sources no narrative covers** (tier 4), it answers and then files the answer as a new narrative, without asking. Otherwise that synthesis would be lost when the session ends, which runs against Karpathy's pattern of filing good answers back. It runs the narrative step with the question and its findings (the tags, narratives and source sections it read), which become the core of narrate's reading plan. The result is a normal, grounded narrative in one PR with the lint gate, not a draft. A tier-3 read that only confirms a narrative's claim doesn't count, since that's not new synthesis. Filing is skipped when an existing narrative or open PR already asks the question, or when the user says "read-only". The answer reports the PR, or why it wasn't filed, on a **Filed:** line.

### 6.2 When nothing covers it: drafts

A question with no answer in the wiki still gets one, so the asker isn't left empty-handed. Then the user decides what happens to it:

1. **Check for an existing draft** on a similar question, as a narrative or an open `[DRAFT]` PR. If there is one, answer from it, and offer to expand it rather than open another.
2. **Answer now**, labeled **DRAFT**: built from the wiki's related sources where they help (cited) and the agent's own knowledge for the rest (each claim marked as inference). The agent doesn't search the web; finding and vetting new sources is the job of ingestion.
3. **Let the user choose**, in a **Next:** section, and wait:
   - **Go deeper**, when the draft isn't good enough: the `build` workflow runs on the topic, with the question passed as its Step 4 question so it isn't asked again. It ingests sources, finds SMEs and writes a grounded narrative in one PR, grounding an existing draft for the question rather than duplicating it.
   - **File the draft**, when the answer is good enough or workable: the narrative step writes the draft narrative (§4.5), runs the lint gate, and opens a `[DRAFT]` PR. The reviewer keeps it as a draft, grounds it later, or closes the PR.
   - **Leave it:** nothing changes.

`query` never starts `build` on its own: that is a research run (searching, ingesting, possibly pausing on large sources, asking the user), not a reply. With no user to ask (another agent called `query`), the draft is filed, so the gap is on record. If the user or calling agent says not to change the wiki, nothing that writes is offered. A filed draft is grounded later by `build` or narrate on the same question (§7.4), which turns it into version 1.0.

### 6.3 Retrieval design

`search.py` ranks with BM25 over short fields (tag names, descriptions and abstracts; narrative questions and abstracts; source abstracts). It's deterministic, uses only the standard library, and needs no index to maintain, because the abstracts the wiki already keeps are what make ranking cheap. It matches words, not meanings, so the workflow has the agent pass keywords with synonyms and judge the top results itself. Issue #31 evaluates better ranking (agent reranking, query expansion, embeddings) against a question set.

On mengjia-llmwiki, typical answers read about 5 KB (tier 1) to 11 KB (tier 2), where the narratives involved are 13–24 KB; a tier-3 lookup reads a 3 KB section of a 37 KB source; and a gap costs under 1 KB to detect.

## 7. Key mechanisms

### 7.1 Attention-aware reading

`narrative` plans its reading so the most relevant, most authoritative and newest content is read last, where the model's attention is strongest at generation time. It sorts by three keys, in order: relevance, authority, date.

1. **Triage by abstract.** Rank every primary and supporting source as high, medium, or low relevance from its manifest `abstract`, and grade its authority: A (the code, specs and standards, original papers or creators, official docs), B (textbooks, encyclopedic references), C (practitioner write-ups, blogs, threads).
2. **Read existing narratives** on overlapping tags first, as background.
3. **Read medium-relevance sources** next, for wider context.
4. **Read high-relevance sources last.**
5. **Within each tier, sort by authority, then date:** less authoritative first and most authoritative last (C → B → A); among equals, oldest to newest by original date (`content_modified` for sources, `created` for narratives), so the newest material lands last and later findings take precedence over what they revise.
6. **Skip** low-relevance sources (abstract only), links, images, and anything under ancestor or adjacent tags.

The plan is executed without an approval gate and recorded in the narrative's References and on the PR, so reviewers can see what was read deeply, skimmed, or skipped. Without it, walking from a leaf tag to the root would pull most of the wiki into context.

### 7.2 Staleness and refresh

- `check-upstream` re-fetches saved sources the way they were ingested and compares them with the saved copies; when an original changed, it marks the source stale (`content_modified`). It uses the network, so `tags` and `lint` run it on request rather than on every check.
- Re-ingesting a source updates its file, hash, and timestamps. Narratives pinned to the old hash are then reported by `wiki-check` (`NARRATIVE_SOURCE_CHANGED`), so exactly those are re-checked.
- After ingesting, `ingest` lints every narrative attached to the changed tags (and their parents) so new knowledge can't silently contradict old answers. The number refreshed per run is capped, and any left over are listed.
- Lint flags stale sources; re-ingestion is always a separate `ingest` run.
- Rebuilding a narrative is never automatic. If new sources change the story, lint hands it to the human, who reruns `narrative`.

### 7.3 Lint

Lint takes a narrative file, a tag (its narratives and sub-tags), or a description (resolved to tags first). Its checks:

| Category | Catches |
|---|---|
| Accuracy | Claims a source doesn't support, misrepresented sources, narratives built on stale sources |
| Code | Fabricated symbols, wrong locations or line links, design intent presented as current code, conflated call paths |
| Consistency | Contradictions, conflicting architecture claims, inconsistent terminology, overlapping scope, missing cross-links between narratives that share tags |
| Bookkeeping | Orphan sources, tag mismatches, stale SMEs, tree drift (the recorded ancestor/adjacent snapshot no longer matches `tags.yaml`) |
| Cleanup and format | Redundancy, buried key points, stale "TBD"s, section order and numbering, broken markdown, tables, or mermaid |

Findings are numbered by severity (H1, M1, L1, …) so reviewers can refer to them on the PR.

**Resolve loop.** Each pass reruns lint from scratch, which re-verifies the previous pass's fixes:

- **Small fixes** (a sentence, a number, a link, a symbol name, formatting) are applied automatically, one commit each.
- **Too-big findings** (a wrong or missing section, a changed thesis, anything multi-section, anything needing re-ingestion) are handed to the human.
- Lint never pauses mid-run. It applies small fixes and records too-big findings as pending decisions. They are listed at the top of the PR (the run PR, under the orchestrator) for the user to decide.
- The loop stops after 3 passes.

`narrative` always runs lint on what it wrote before publishing: no narrative reaches a PR unlinted. On a draft, lint checks the citations it has and that every uncited claim is marked as inference; it doesn't demand sources.

### 7.4 Reuse before writing

New narratives for questions the wiki already answers would split its knowledge and make answers disagree, so every narrative is written against what exists:

- **`build` Step 4:** for each question, `search.py narratives` over the whole wiki finds same or overlapping narratives. The workflow proposes one of the following, in the same prompt that asks for the questions:
  - **reuse:** answer from the existing narrative, recorded in the PR, with no new narrative;
  - **expand:** a wider scope or new sources, giving a new version of the same narrative;
  - **ground a draft:** rewrite a draft from real sources, as version 1.0;
  - **new:** only for a genuinely different question, linked to the closest existing one.
  Reuse or expand is the default.
- **`narrative` on its own:** a same or overlapping narrative is expanded by default, without pausing. The PR says so, and the user can ask there for a separate narrative.
- **`query`:** a similar draft or open draft PR is reused before a new draft is filed (§6.2).

## 8. Workflows and steps

| Workflow | Input | Does | Writes |
|---|---|---|---|
| `build` | `<topic>` | Runs the steps (§5), with reuse before writing (§7.4), and manages the run PR | Through its steps |
| `query` | `<question> [wiki path]` | Answers from existing knowledge by tiers (§6.1) and files a stitched answer as a narrative; on a gap, a DRAFT answer, then the user's choice: go deeper with `build`, file the draft, or leave it (§6.2) | Nothing, a narrative PR, or (on the user's choice) a draft narrative PR or an `build` run |
| `init` (one-time) | `[repo name]` | Turns the current directory into a wiki repo; asks before using a repo with unrelated content; offers to create the remote; checks the local default branch matches the remote's | Layout, README, `AGENTS.md`, `CLAUDE.md`, `.gitignore`, `.claude/settings.json`; first commit |

| Step | Input | Does | Writes |
|---|---|---|---|
| `tags` | `<description>` | Matches tags, proposes new ones, classifies, reports source status (refresh / skip / new-ingest). Fetches nothing | New tags in `tags.yaml` |
| `ingest` | `<tags> [description]` | Searches docs, code, and chat (3–5 good candidates beat 15 weak ones); saves verbatim; delegates to specialized ingestion skills or connectors when available; then lint-refreshes affected narratives | `ingested/`, `ingested/manifest.yaml`, `tags.yaml` |
| `smes` | `<tags> [description]` | Locates the code and docs behind the tags, then ranks people by git log/blame, `CODEOWNERS`, doc authorship, and PR reviews (breadth, depth, recency, authority). Labels people likely active or possibly moved, never drops them; lists external authors separately | `smes` and `contact_channels` in `tags.yaml` |
| `narrative` | `<question>` | Checks for an existing narrative first (§7.4), classifies tags, plans reading (§7.1), writes or updates the narrative (§4.5), self-reviews, runs lint. Draft mode for `query` (§6.2) | `groomed/`, `groomed/manifest.yaml`, `tags.yaml` |
| `lint` | `<narrative \| tag \| description>` | Checks and fixes (§7.3) | Narrative fixes |

## 9. Distribution

- The skill uses the [Agent Skills](https://agentskills.io) format, so any compatible agent can load it.
- For Claude Code, this repo is both a plugin (`sllmwiki`) and a marketplace (`structural-llm-wiki`, named like the repository) that lists itself. Each workflow and step is also a command, `/sllmwiki:<name>` (`src/commands/`).
- The plugin is installed at **project scope** in each wiki repo, and `init` writes the same `extraKnownMarketplaces` and `enabledPlugins` entries to `.claude/settings.json`. Teammates who clone the wiki and trust the folder are offered the plugin automatically.
- Other agents install with `npx skills add mengjiasun1992/structural-llm-wiki`, which installs the `sllmwiki` skill; there are no commands, so users ask for a workflow or step in their own words.
- Installing needs read access to this repository on GitHub.
