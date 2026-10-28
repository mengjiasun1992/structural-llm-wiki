# Structural LLM Wiki: the manual

Everything about using the `sllmwiki` plugin, after [the README](../README.md)'s setup. How it's built, and why: [the design](structural_llm_wiki_design.md).

- [1. Commands and requests](#1-commands-and-requests)
- [2. Reviewing a run](#2-reviewing-a-run)
- [3. What's in your wiki](#3-whats-in-your-wiki)
- [4. Narratives and templates](#4-narratives-and-templates)
- [5. Citations and markers](#5-citations-and-markers)
- [6. Keeping it true](#6-keeping-it-true)
- [7. Books and releases](#7-books-and-releases)
- [8. Settings](#8-settings)
- [9. Languages](#9-languages)
- [10. Obsidian](#10-obsidian)
- [11. Teams, updates and other agents](#11-teams-updates-and-other-agents)
- [12. Licenses, sources and your responsibility](#12-licenses-sources-and-your-responsibility)
- [13. FAQ](#13-faq)

## 1. Commands and requests

Four commands cover what you do: set up, ask, grow and publish.

| I want to… | Run |
|---|---|
| Set up a wiki (start here, in an empty repository) | `/sllmwiki:init` |
| Ask the wiki: a cited answer, or a DRAFT and an offer to research it | `/sllmwiki:query "How does the gateway retry failed backends?"` |
| Research questions unattended: sources saved, a cited answer each, one pull request to review | `/sllmwiki:build "How does the gateway route requests?" "Why does it retry?"` |
| Publish the wiki as a book (PDF, EPUB, HTML) in a dated release | `/sllmwiki:release` (`--preview` only builds it) |

**`query`** answers from what the wiki already knows, reading as little as it can, so most answers come back in seconds. Every claim cites the narrative or source it came from, and the answer names the people who know the area. If the wiki doesn't cover the question yet, you still get an answer, clearly labeled DRAFT, and an offer to research it properly.

**`build`** reuses what the wiki already answers, finds and saves the sources the rest need, writes a narrative per question and checks every claim against its source. You come back to one pull request.

Everything else, ask for in your own words; the skill runs the step it needs (`build` runs them all for you):

| I want to… | Ask |
|---|---|
| Answer one question from sources already saved | "Write a narrative answering: why does the gateway retry failed backends?" |
| Add a source, or refresh changed ones | "Save the retry policy design doc to the wiki, under gateway" |
| Check a narrative, or a whole topic | "Lint the gateway narratives" |
| Find who to ask | "Who knows the gateway?" |
| See which topics a question belongs to | "Which topics does 'gateway vs load balancer' belong to?" |
| Add a kind of answer of your own | "Make a template for postmortems of our incidents" |
| Find out what it can do, or how to do something | "What can sllmwiki do?" |

## 2. Reviewing a run

Each run's pull request starts with a checklist (tags, sources, each narrative), then the decisions the agent left to you, then what the run cost. Tick each box as you check it; the wiki's "Review checklist" check turns green when all are ticked. Leave comments, and ask the agent to "apply the review comments on PR #12": it reworks the same pull request. Nothing lands until you merge. [The demo's PR #6](https://github.com/mengjiasun1992/sllmwiki-demo/pull/6) is one run's pull request, checklist and all.

## 3. What's in your wiki

Your wiki is its own git repository, plain Markdown and YAML you can read anywhere:

| Content | Where | What it is |
|---|---|---|
| **Sources** | `sllmwiki/sources/` | Verbatim copies of the docs, web pages, papers, books and code the answers rest on, saved as markdown and never edited, each with its URL, date, license and a short abstract |
| **Narratives** | `sllmwiki/narratives/` | One per question: the facts and claims that answer it, told in order, opening with an abstract, every claim cited; the figures a narrative draws in `figures/` |
| **Tags** | `sllmwiki/tags/` | A tree of topics, each with a page listing its narratives, sources and the people who know it |
| **Index** | `sllmwiki/.SLLMWIKI_INDICES.md` | A clickable map of the topics, for GitHub |
| **Your templates** | `sllmwiki/.templates/` | Optional: your own kinds of narratives, and language packs |
| **Settings** | `sllmwiki/Config.toml` | The source policy, markers, language, the book's formats, title and author |
| **Books** | the repository's Releases | The wiki as a PDF, EPUB or HTML file, attached to each release; never committed |

The index and the templates have dot names, so Obsidian shows only the knowledge and the book leaves them out. The demo wiki has each: [sources](https://github.com/mengjiasun1992/sllmwiki-demo/tree/main/sllmwiki/sources), [narratives](https://github.com/mengjiasun1992/sllmwiki-demo/tree/main/sllmwiki/narratives), [tags](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/tags/tags.yaml) and [the index](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/.SLLMWIKI_INDICES.md).

Sources are ranked by relevance, then authority (code, specifications and original papers first), then date. They're saved as the most faithful text that can be checked: markdown, HTML, PDF (by its outline), EPUB (by its table of contents), LaTeX and code; large books are sliced by chapter.

## 4. Narratives and templates

Each kind of answer comes from a template, picked by the question's subject. Each comes with a writing guide for a reader new to the topic, and an aim lint grades it on.

| Template | For | Shape | Example |
|---|---|---|---|
| `concept_brief_overview` | "What is X?" | In short, then rigorously, and its edge cases | [What is a distributed system?](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-is-a-distributed-system.md) |
| `technical_brief_overview` | "How does X work?" | One real example, walked through with its numbers | [What is an EWMA?](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-is-an-ewma-exponentially-weighted-moving-average-and-how-does-it-work.md) |
| `comparison` | "X or Y?" | Every common option compared, and the rule for when each wins | [EWMA or other moving averages?](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/when-should-software-use-an-ewma-instead-of-other-moving-averages.md) |
| `survey` | "What are the principles of X?" | The field mapped first, then each idea in brief | [Design tenets of distributed systems](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-are-the-common-design-tenets-and-principles-for-distributed-systems.md) |
| `case_study` | "What happened, and what does it teach?" | The timeline, the chain of causes, and the lessons | |

**Your own templates.** For a kind of answer the five don't fit, describe it: "make a template for postmortems of our incidents". The agent starts from the closest bundled template and shapes its sections, writing guide and aim from your description. It checks the result and opens a pull request. The template lives in `sllmwiki/.templates/<name>/` as a `template.md` (a short header and the sections every answer needs) and a `guide.md` (its reader, aim, style and checklist), and you can also write it by hand. From then on the agent picks it for the questions its header says it fits, and lint grades its narratives on its aim. A template named like a bundled one replaces it; to change only a length, set `max_words` in `Config.toml` instead. The demo has one: [`skim_read`](https://github.com/mengjiasun1992/sllmwiki-demo/tree/main/sllmwiki/.templates/skim_read), a ten-minute primer on a long paper for someone deciding whether to read it, and [a narrative made with it](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-does-keeping-calm-argue-and-is-it-worth-reading-in-full.md). How templates work: [the design, §4.5.5](structural_llm_wiki_design.md#455-a-wikis-own-templates).

When no template fits a question, the agent uses the closest one and says so in the pull request, with the request to make one.

## 5. Citations and markers

As in a paper, a claim's numbered citations sit inside its sentence, before the period, separated by commas: `… exponentially [3], [6].` Each links to the section of the saved source that supports it, and quotations are checked word for word.

What no source states is marked `[→]` (the narrative's own reasoning), and something the sources don't answer `[?]` (a gap), never filled with a guess. A marker goes where a citation goes, or once on a heading for a whole section; each narrative defines the ones it uses ([an example](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-is-an-ewma-exponentially-weighted-moving-average-and-how-does-it-work.md)). Turn them off with `markers = false`.

## 6. Keeping it true

Each narrative records the source versions it read and the narratives it builds on. Ask the agent to refresh a topic's sources ("refresh the gateway sources"): it re-saves the ones that changed where they came from, the wiki's checks flag exactly the narratives built on them, and a lint ("lint the gateway narratives") rechecks just those against the new version. A narrative that builds on another is flagged when that one changes, too.

## 7. Books and releases

Turn on the formats you want in `Config.toml` (`init` asks). `/sllmwiki:release` publishes a dated release of the wiki on GitHub (`v2026.10.24`), with notes on what changed since the last one, and the wiki's release workflow attaches the wiki as a book in each format the `[structural-llm-wiki-release]` table turns on: a PDF to print and share, an EPUB for e-readers and phones, one HTML file for a browser.

The book has a cover, a contents page, a part per topic with each chapter's summary and reading time, the narratives in teaching order, and appendices of sources, a glossary and open questions. Its diagrams and math are drawn as they are on GitHub, and the file works offline. It carries each source's abstract, license and link, never its saved copy, and never the SMEs.

GitHub's *Releases → Draft a new release* does the same without the agent; `/sllmwiki:release --preview` builds the book from a branch as a workflow artifact. A diagram or formula that wouldn't draw, or a link the book couldn't follow, fails the pull request that brings it, long before a release. The demo's [latest release](https://github.com/mengjiasun1992/sllmwiki-demo/releases/latest) has all three formats. How it works: [the book's design](book_design.md).

## 8. Settings

`sllmwiki/Config.toml` holds the wiki's settings; `init` writes it with the defaults and the answers you gave. Change any of them at any time:

```toml
[structural-llm-wiki-settings]
source_copies = "allow"     # or "links-only": keep no copies, only links
max_quote_words = 50        # the longest quotation a narrative may take
smes_exclude = []           # never listed as SMEs, such as the wiki's owner or bots
markers = true              # false: no reasoning or gap markers
images = true               # false: diagrams in mermaid only, no generated figures
language = "en"             # the language narratives are written in, such as "zh-Hans"

[structural-llm-wiki-templates.technical_brief_overview]
max_words = 3000            # a template's word budget, over its own

[structural-llm-wiki-addons]
obsidian = false            # true: set the wiki up to open as an Obsidian vault

[structural-llm-wiki-release]
pdf_book = true             # a release attaches the wiki as a PDF
epub_book = false           # true: as an EPUB too, for e-readers
html_book = false           # true: as one HTML file, for a browser
title = ""                  # the book's title; empty: the repository's name
author = ""                 # its author; empty: the title
```

## 9. Languages

Narratives are written in the wiki's `language`, and one can name its own (`- **Language:** zh-Hans` in its Metadata, or ask for a language when you ask the question). Sources stay in the language they were written in, and a quotation keeps its source's words, translated after it.

Headings come from a language pack, `languages/<tag>.md` in the skill's or your wiki's templates: the skill ships English and Simplified Chinese (`zh-Hans`), each one it has evaluated, and a pack can carry its language's writing rules. For another language, copy [the English pack](../plugin/skills/sllmwiki/templates/languages/en.md) into your wiki's `sllmwiki/.templates/languages/` and fill in the translations; the skill writes in it, and says it hasn't evaluated it. Without a pack, headings stay English around prose in your language. Word budgets stay in words; Chinese and Japanese text counts its characters at 1.6 to a word.

## 10. Obsidian

With `obsidian = true` and `/sllmwiki:init` rerun, open `sllmwiki/` as a vault: its graph shows tag pages in gold and narratives in indigo. Sources are gray, and the graph hides them until you clear its filter (`-path:sources`); to hide them from search and the quick switcher as well, add `sllmwiki/sources/` to your own *Settings → Files and links → Excluded files*. `init` writes the graph's settings once, and the wiki owns them from then on.

## 11. Teams, updates and other agents

**Join a wiki.** Clone it and start Claude Code inside. Trust the folder, and accept the `sllmwiki` plugin the repository offers: `init` records it in the wiki's `.claude/settings.json`.

**Update the plugin.** After a plugin update, rerun `/sllmwiki:init`: it brings the wiki's layout, CI checks and release workflow up to date in a pull request, and keeps the wiki's own files.

**Other agents.** Codex, Cursor, Copilot and other agents that support [Agent Skills](https://agentskills.io) install the skill with the [`skills` CLI](https://skills.sh): `npx skills add mengjiasun1992/structural-llm-wiki -g`. There are no commands there; ask for what you want in your own words ("lint the gateway narratives").

## 12. Licenses, sources and your responsibility

A wiki holds other people's work next to text an LLM wrote, so it's worth knowing who owns what and who answers for it.

- **The skill** is open source under the [Apache License 2.0](../LICENSE), copyright 2026 Mengjia Sun ([NOTICE](../NOTICE)). It covers the skill's code, templates and docs, not what you put in your wiki.
- **Your wiki is yours.** The skill picks no license for it: what your narratives may be shared under is your call, and a wiki made from your company's code and docs falls under your company's rules.
- **Sources stay their authors'.** Copyright stays with each source's authors, and every saved source keeps its URL and license. Narratives quote only briefly, at most `max_quote_words` words, and cite the rest.
- **Copies follow a source policy.** A private wiki keeps reference copies unless a source's terms forbid sharing; a public wiki keeps only openly licensed ones, and its CI fails on a copy it may not hold. With `source_copies = "links-only"` it keeps no copies at all. Review `sllmwiki/sources/` before you make a private wiki public.
- **Fair access only.** The skill never gets around a login, paywall or anti-bot protection, and uses no unofficial copies; when it may not keep a copy, it records a link instead, and when in doubt it asks.
- **No personal data or secrets** go into the wiki, even when a source contains them.
- **Your model provider sees what your agent reads.** Questions and sources go to the model your agent runs on, under that provider's terms: ingest only what you may share with it.
- **Narratives are written by an LLM.** Every claim cites its source, and what no source states is marked, but a narrative can still be wrong: review each pull request before you merge it, and check a claim's source before you rely on it.

The scripts enforce what they can. This is a cautious default, not legal advice: for anything that matters, ask your own counsel. What the plugin does with your data: [Privacy](../PRIVACY.md).

## 13. FAQ

**Does the wiki have to be on GitHub?** No, but its CI checks and the book run on GitHub Actions, and `gh` opens the pull requests. Without a remote, a run keeps its commits on its branch, with the pull request's description beside them.

**What if `gh` isn't installed?** Every run checks for it, with git and Python, and prints the command that installs what's missing on your machine. Without `gh`, a run prints the link to open its pull request yourself.

**Can I edit a narrative by hand?** Yes: it's Markdown in git, and the wiki's checks run on your pull request like on any other. Never edit a saved source, `tags.yaml`, a `manifest.yaml`, the index or a tag page: ask the agent, whose scripts keep them in step.

**How do I remove a source or a narrative?** Ask the agent ("remove the retry-policy source") in a run, so its scripts keep the manifests in step. Git history keeps it until you rewrite that history.

**Can it read our private code and docs?** Yes, anything your agent can read: repositories you point it at, files, and pages you can open without getting around a login. Their content goes to your agent's model provider, as with any work in your agent.

**What does a run cost?** Each pull request records what its run took: its time, and its turns and tokens. In the demo, one run wrote four narratives from 29 sources in 21 minutes ([PR #6](https://github.com/mengjiasun1992/sllmwiki-demo/pull/6)).

**Can I make my wiki public?** Yes, once its saved sources are all openly licensed: a public wiki's CI fails on a copy it may not hold. Review `sllmwiki/sources/` first, or set `source_copies = "links-only"`.

**Who are the SMEs, and how do I keep someone off the list?** The people behind a topic's code and docs, ranked by evidence from git history, code owners and authorship, each with a question to ask them. Add anyone, such as yourself or a bot, to `smes_exclude` in `Config.toml`.
