# {📖} Structural LLM Wiki

![Structural LLM Wiki. You ask your agent one question, "How does the gateway retry?", and your agent does the rest: 1, it finds and saves the sources, a paper, code, a web page, a design doc; 2, it writes the answer, an open book in braces, every claim tied by a thread to its source; 3, it opens one pull request on project-foobar-sllmwiki.git; 4, you review and merge; 5, each release attaches the wiki as a book, in PDF, EPUB and HTML. The repository is git, which your group and their agents clone, share and grow. Answers you can check; written to teach; knowledge that compounds; stays true as sources change; reviewed like code; kept in git, shared as a book.](docs/images/hero.svg)

[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-d97757.svg)](#setup)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](#setup)
[![Scripts](https://github.com/mengjiasun1992/structural-llm-wiki/actions/workflows/check-scripts.yml/badge.svg?branch=mainline)](https://github.com/mengjiasun1992/structural-llm-wiki/actions/workflows/check-scripts.yml?query=branch%3Amainline)
[![Book](https://github.com/mengjiasun1992/structural-llm-wiki/actions/workflows/check-book.yml/badge.svg?branch=mainline)](https://github.com/mengjiasun1992/structural-llm-wiki/actions/workflows/check-book.yml?query=branch%3Amainline)

**Your group's knowledge, researched by your coding agent, cited to the exact source, and reviewed like code.**

An agent skill, packaged as a Claude Code plugin, that turns a git repository into a wiki your coding agent researches and keeps current. You ask a question. It saves the *sources* that answer it, verbatim copies of code, design docs, specifications, papers or web pages, and writes a *narrative*: an account, told in order, of what happened or how something works, every claim linked to the section of a source that supports it. Each run arrives as one pull request you review. It builds on Andrej Karpathy's [LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) and adds what a group needs: claims you can check, review before anything lands, and a book at each release.

**See one.** In [the demo wiki](https://github.com/mengjiasun1992/sllmwiki-demo), one unattended run wrote four cited narratives from 29 sources in 21 minutes ([PR #6](https://github.com/mengjiasun1992/sllmwiki-demo/pull/6)). Start at [its index](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/.SLLMWIKI_INDICES.md), read [What is a distributed system?](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-is-a-distributed-system.md), or download its book as a PDF, EPUB or HTML file from [its latest release](https://github.com/mengjiasun1992/sllmwiki-demo/releases/latest).

## Setup

You need an agent that runs [Agent Skills](https://agentskills.io), such as [Claude Code](https://docs.claude.com/en/docs/claude-code), plus git and Python 3.9 or later. [`gh`](https://cli.github.com), signed in, is recommended: it opens the pull requests (without it, the skill prints a link to open each one yourself). The wiki's CI checks and its book need the wiki hosted on GitHub.

1. Create an empty repository (for example `project-foobar-sllmwiki`), clone it and start Claude Code in it.
2. Install the plugin into it:

   ```bash
   claude plugin marketplace add mengjiasun1992/structural-llm-wiki --scope project
   claude plugin install sllmwiki@structural-llm-wiki --scope project
   ```

3. Run `/sllmwiki:init`. It asks a few preferences (language, source policy, the book), lays out the wiki, installs its CI checks and makes the first commit. Rerun it after a plugin update.
4. Ask your first questions: `/sllmwiki:build "How does our gateway route requests?" "Why does it retry?"`

**Join a wiki:** clone it, start Claude Code inside, trust the folder and accept the `sllmwiki` plugin it offers. **Other agents** (Codex, Cursor, Copilot): `npx skills add mengjiasun1992/structural-llm-wiki -g` with the [`skills` CLI](https://skills.sh), then ask in your own words ("lint the gateway narratives").

<details>
<summary>Installing git, Python and gh</summary>

```bash
brew install git python gh                                   # macOS
winget install Git.Git Python.Python.3.13 GitHub.cli         # Windows
sudo apt-get install -y git python3 gh                       # Debian / Ubuntu
gh auth login && gh auth setup-git                           # then, everywhere
```

</details>

## Why use it

- **Builders** need to understand a system before they change it, but the why is in a design doc that drifted and a chat thread nobody can find, and an AI's answer can't say which parts it read and which it guessed.
- **Tech leads** need what the group knows to outlive who knows it. Onboarding runs through the same few seniors, and nobody can say which docs are still true.
- **Researchers** have more papers than time, and LLM summaries cite sections that don't say what they claim.

What the wiki does about it:

- **Every claim can be checked.** Each one cites the exact section of a saved source, one click away. What no source states is marked as the narrative's own reasoning (`[→]`) or as a gap (`[?]`), never filled with a guess. Lint checks every claim and quotation against the section it cites.
- **Nothing lands unreviewed.** The agent researches on its own and delivers one pull request: a checklist on top, the decisions it couldn't make, and what the run cost. Your seniors review instead of writing from scratch.
- **Knowledge compounds.** One narrative per question, kept in git. A new answer builds on what the wiki already explains, and the next person who asks gets the reviewed answer.
- **Answers stay true.** Each narrative records the source versions it read. When code or a doc changes, exactly the narratives that rest on it are flagged.
- **It teaches.** The answer's shape fits the question, written for a reader new to the topic; describe your own kind, such as a postmortem or a ten-minute primer on a paper.
- **It knows who to ask.** Each topic lists the people behind its code and docs, ranked by evidence from git history and code owners.
- **A book with every release.** The whole wiki as a PDF, an EPUB or one HTML file, chapters in teaching order, diagrams and math drawn as on GitHub: an onboarding pack, current as of that day.

![Every kind of question gets the shape that teaches it. What is X? In short, then rigorously, and its edge cases. How does X work? One real example, walked through with its numbers. Principles of X? The field mapped first, then each idea in brief. X or Y? Every option compared, and the rule for when each wins. What happened? The timeline, the chain of causes, and the lessons. Your own kind? A postmortem, a primer: a template you describe.](docs/images/answer-shapes.svg)

It's all plain Markdown and YAML in git: browse it on GitHub, open it in Obsidian, or use it from any agent that supports Agent Skills. Scripts do everything mechanical, so your tokens go to judgment.

## Usage

![Four moments, from your side. Ask anything: an answer in seconds, each claim cited, and who to ask. Grow it by asking: it researches while you're away, and you review one pull request; nothing lands till you merge. It stays true: when a source changes, exactly the answers that rest on it are flagged, and the rest stay untouched. Share it as a book: each release, such as v2026.10.24, attaches the whole wiki as a PDF to print and share, an EPUB for e-readers and phones, and one HTML file for a browser; read it offline, or hand it on.](docs/images/four-moments.svg)

| I want to… | Run |
|---|---|
| Set up a wiki (start here, in an empty repository) | `/sllmwiki:init` |
| Ask the wiki: a cited answer in seconds, or a DRAFT and an offer to research it | `/sllmwiki:query "How does the gateway retry failed backends?"` |
| Research questions unattended: sources saved, a cited answer each, one pull request to review | `/sllmwiki:build "How does the gateway route requests?" "Why does it retry?"` |
| Publish the wiki as a book (PDF, EPUB, HTML) in a dated release | `/sllmwiki:release` (`--preview` only builds it) |

Everything else, ask for in your own words:

| I want to… | Ask |
|---|---|
| Answer one question from sources already saved | "Write a narrative answering: why does the gateway retry failed backends?" |
| Add a source, or refresh changed ones | "Save the retry policy design doc to the wiki, under gateway" |
| Check a narrative, or a whole topic | "Lint the gateway narratives" |
| Find who to ask | "Who knows the gateway?" |
| Add a kind of answer of your own | "Make a template for postmortems of our incidents" |
| Find out what it can do | "What can sllmwiki do?" |

**Reviewing.** Each pull request starts with a checklist; the wiki's "Review checklist" check turns green when every box is ticked. Comment, then ask the agent to "apply the review comments on PR #12". [The demo's PR #6](https://github.com/mengjiasun1992/sllmwiki-demo/pull/6) shows one.

**Templates.** Each kind of answer comes from a template picked by the question: `concept_brief_overview` ("What is X?"), `technical_brief_overview` ("How does X work?"), `comparison` ("X vs Y"), `survey` ("What are the principles of X?") and `case_study` ("What happened, and what does it teach?"). Ask for your own and it lands in `sllmwiki/.templates/<name>/`, like the demo's [`skim_read`](https://github.com/mengjiasun1992/sllmwiki-demo/tree/main/sllmwiki/.templates/skim_read), a ten-minute primer on a paper ([a narrative made with it](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-does-keeping-calm-argue-and-is-it-worth-reading-in-full.md)). How they work: [the design, §4.5.5](docs/structural_llm_wiki_design.md#455-a-wikis-own-templates).

**Books.** `/sllmwiki:release` publishes a dated release (`v2026.10.24`) with notes on what changed, and the wiki's workflow attaches the book: a part per topic, the narratives in teaching order, and appendices of sources, a glossary and open questions. It carries each source's abstract, license and link, never its saved copy. How it works: [docs/book_design.md](docs/book_design.md).

**Languages.** Narratives are written in the wiki's `language`, or one you ask for; sources stay in their own. The skill ships English and Simplified Chinese (`zh-Hans`); for another, copy [the English pack](plugin/skills/sllmwiki/templates/languages/en.md) into `sllmwiki/.templates/languages/` and translate it.

**Obsidian.** With `obsidian = true` and `/sllmwiki:init` rerun, open `sllmwiki/` as a vault: its graph shows tag pages in gold and narratives in indigo, with sources hidden.

<details>
<summary>Settings (sllmwiki/Config.toml, which init writes with the defaults)</summary>

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

</details>

## What's in your wiki

| Content | Where | What it is |
|---|---|---|
| **Sources** | `sllmwiki/sources/` | Verbatim copies, never edited, each with its URL, date, license and a short abstract |
| **Narratives** | `sllmwiki/narratives/` | One per question, opening with an abstract, every claim cited; their figures in `figures/` |
| **Tags** | `sllmwiki/tags/` | A tree of topics, each with a page listing its narratives, sources and the people who know it |
| **Index** | `sllmwiki/.SLLMWIKI_INDICES.md` | A clickable map of the topics |
| **Templates** | `sllmwiki/.templates/` | Optional: your own kinds of narratives, and language packs |
| **Settings** | `sllmwiki/Config.toml` | The source policy, markers, language and the book |
| **Books** | the repository's Releases | Attached to each release; never committed |

## Licenses, sources and your responsibility

- **The skill** is open source under the [Apache License 2.0](LICENSE) ([NOTICE](NOTICE)). It covers the skill, not what you put in your wiki.
- **Your wiki is yours**, under whatever license you or your company choose.
- **Sources stay their authors'.** Each keeps its URL and license, and narratives quote at most `max_quote_words` words. A private wiki keeps reference copies unless a source's terms forbid it; a public one keeps only openly licensed ones, and its CI fails on any other. Review `sllmwiki/sources/` before making a private wiki public.
- **Fair access only.** It never gets around a login, paywall or anti-bot protection; when it may not keep a copy, it keeps a link.
- **No personal data or secrets** go into the wiki, even when a source contains them.
- **Narratives are written by an LLM.** Every claim is cited and what no source states is marked, but review each pull request before you merge it.

This is a cautious default, not legal advice.

## Your data

The plugin runs in your agent, on your machine, and its authors collect nothing. Data leaves your machine only to **GitHub**, through `git` and `gh` in your own account, to **the sites your sources come from**, and, as with any work in your agent, to **your agent's model provider**. Details: [Privacy](PRIVACY.md).

## Design

[docs/structural_llm_wiki_design.md](docs/structural_llm_wiki_design.md) has the architecture and the decisions behind it, and [docs/book_design.md](docs/book_design.md) the book a release attaches. [docs/skill_execution_plan.md](docs/skill_execution_plan.md) and [docs/book_execution_plan.md](docs/book_execution_plan.md) say how each was built.

## Developing

```text
plugin/                the plugin, and only what runs for its users
├── skills/sllmwiki/   the skill: SKILL.md, workflows/, steps/, scripts/, templates/
└── commands/          Claude Code commands: init, query, build, release
tests/                 unit tests for the scripts
src/actions/           the GitHub actions a wiki's CI calls
src/tools/             development and CI tools (eval-plugin.sh, check-yaml, check-book)
evals/                 behavior evals, run through src/tools/eval-plugin.sh
docs/                  the designs, their plans, and their figures
```

`AGENTS.md` has the rules for changing this repository: tests with every logic change and coverage at 95% or above, instruction word budgets, evals for behavior changes. Run the tests, and try the plugin from a checkout:

```bash
python3 -m pip install "coverage[toml]==7.6.10"
python3 tests/run.py --coverage
claude --plugin-dir plugin
```

## License

Copyright 2026 Mengjia Sun. Licensed under the [Apache License, Version 2.0](LICENSE); see [NOTICE](NOTICE).
