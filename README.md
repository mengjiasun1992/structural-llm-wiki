# {📖} Structural LLM Wiki

![Structural LLM Wiki. You ask your agent one question, "How does the gateway retry?", and your agent does the rest: 1, it finds and saves the sources, a paper, code, a web page, a design doc; 2, it writes the answer, an open book in braces, every claim tied by a thread to its source; 3, it opens one pull request on project-foobar-sllmwiki.git; 4, you review and merge; 5, each release attaches the wiki as a book, in PDF, EPUB and HTML. The repository is git, which your group and their agents clone, share and grow. Answers you can check; written to teach; knowledge that compounds; stays true as sources change; reviewed like code; kept in git, shared as a book.](docs/images/hero.svg)

[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-d97757.svg)](#setup)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](#requirements)
[![Scripts](https://github.com/mengjiasun1992/structural-llm-wiki/actions/workflows/check-scripts.yml/badge.svg?branch=mainline)](https://github.com/mengjiasun1992/structural-llm-wiki/actions/workflows/check-scripts.yml?query=branch%3Amainline)
[![Book](https://github.com/mengjiasun1992/structural-llm-wiki/actions/workflows/check-book.yml/badge.svg?branch=mainline)](https://github.com/mengjiasun1992/structural-llm-wiki/actions/workflows/check-book.yml?query=branch%3Amainline)

**Your group's knowledge, researched by your coding agent, cited to the exact source, and reviewed like code.**

**What it is?** An agent skill, packaged as a Claude Code plugin, that turns a git repository into a wiki your coding agent researches and keeps current. You ask questions. It finds and saves the *sources* that answer them: a source is a verbatim copy of existing material, such as code, a design doc, a specification, a paper or a web page. Then it writes one *narrative* per question: an account of the connected facts and claims that answer it, told in order, that says what happened or how something works. A narrative tells; it stays out of the way, and every claim links to the section of a source that supports it. Each run arrives as one pull request you review. It builds on Andrej Karpathy's [LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) and adds what a group needs: claims you can check, review before anything lands, topic tags that connect sources, answers and the people who know them, and a book at each release.

**What it saves?** Hours to days of digging, reading and writing per question become minutes of the agent's work and your review. In the demo, one unattended run wrote four cited narratives from 29 sources in 21 minutes ([PR #6](https://github.com/mengjiasun1992/sllmwiki-demo/pull/6)), and a release built the whole wiki as a PDF, an EPUB and an HTML book in about a minute. Every pull request records what its run took, so you can check.

**See one!** [sllmwiki-demo](https://github.com/mengjiasun1992/sllmwiki-demo) is a wiki built with this skill, on distributed systems and moving averages: start at [its index](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/.SLLMWIKI_INDICES.md), read [What is a distributed system?](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-is-a-distributed-system.md), see [the pull request](https://github.com/mengjiasun1992/sllmwiki-demo/pull/6) that wrote its narratives, look at [its own template](https://github.com/mengjiasun1992/sllmwiki-demo/tree/main/sllmwiki/.templates/skim_read), a ten-minute primer on one paper, with [the narrative made with it](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-does-keeping-calm-argue-and-is-it-worth-reading-in-full.md), and download its book: [PDF](https://github.com/mengjiasun1992/sllmwiki-demo/releases/download/v2026.10.25/sllmwiki-demo-v2026.10.25.pdf), [EPUB](https://github.com/mengjiasun1992/sllmwiki-demo/releases/download/v2026.10.25/sllmwiki-demo-v2026.10.25.epub) or [HTML](https://github.com/mengjiasun1992/sllmwiki-demo/releases/download/v2026.10.25/sllmwiki-demo-v2026.10.25.html), from [release v2026.10.25](https://github.com/mengjiasun1992/sllmwiki-demo/releases/tag/v2026.10.25).

## Who it's for, and what it fixes

### Builders: you need to understand a system before you change it

- What the code does is in the code, why it does it is in a design doc that drifted two releases ago, and the rest is in a chat thread you can't find. Piecing it together takes an afternoon, every time.
- Asking the one person who knows interrupts them, and the same question comes back next month from someone else.
- An AI assistant answers in seconds, but you can't tell which parts it read and which it guessed, and the answer is gone when the session ends.

**With the wiki,** you ask, and in seconds (or minutes, if the agent has to research it) the answer cites the exact lines of code and the section of the design doc it rests on, and names the people who know the area. It's saved, so the next person who asks gets the same answer, already reviewed. When the code or the doc changes, the answers that rest on them are flagged.

### Tech leads: what the group knows has to outlive who knows it

- Onboarding takes weeks, and it runs through the same few senior engineers, whose days go to explaining instead of building.
- The reasons behind a design live in reviews and meetings, and leave with the people who were there.
- Documentation nobody owns goes stale quietly, and nobody can say which pages are still true.
- AI-written docs are cheap to make and expensive to check.

**With the wiki,** the agent does the research and the writing, and your seniors review instead of writing from scratch. Questions become reviewed documents in git, with the sources and reasoning behind them and a history of how the group's understanding changed. Every change arrives as a pull request with a checklist, and nothing lands until someone merges it. Staleness is tracked, not guessed. Each release attaches the whole wiki as a book, an onboarding pack that's current as of that day.

### Researchers: the reading never ends, and summaries can't be trusted

- There are more papers than time: a close read costs hours, and an abstract is too thin to decide which ones deserve it.
- Notes lose track of where each claim came from, so a review of the field has to be redone from scratch.
- LLM summaries sound right and cite sections that don't say what they claim, or papers that don't exist.

**With the wiki,** sources are saved verbatim and every claim links to the section that supports it, with quotations checked word for word. Definitions come from the sources that state them most rigorously. A survey maps a field, a comparison weighs the candidates, and a template of your own, such as a ten-minute primer on one paper, helps you decide in ten minutes what deserves the hours. The review grows with every question instead of starting over.

## How it addresses them

- **You can check every answer, claim by claim.** Each claim cites the exact section of a source saved in the wiki, one click away. What no source states is marked as the narrative's own reasoning (`[→]`), and what the sources don't answer as a gap (`[?]`), never filled with a guess. Lint checks each claim and quotation against the section it cites.
- **Knowledge compounds instead of vanishing with the chat.** One narrative per question, kept in git. A new answer builds on and links to what the wiki already explains, and the agent extends an existing answer before writing a new one.
- **Answers stay true as things change.** Each narrative records the source versions it read and the narratives it builds on. When one changes, exactly the narratives that depend on it are flagged, so you recheck those and nothing else.
- **It teaches, so a newcomer can learn from it.** The answer's shape fits the question, as below: a concept defined in short, then rigorously; a mechanism worked through one running example with real numbers; a field mapped before its parts; a choice weighed across every common candidate; an incident followed to its causes. When none fits, describe your own, such as a postmortem or a ten-minute primer on a paper. Each kind has an aim, and lint grades every narrative against it.
- **It knows who to ask.** Each topic lists the people behind its code and docs, ranked by evidence from git history, code owners and authorship.
- **It works unattended, and nothing lands unreviewed.** The agent researches on its own and delivers one pull request: a checklist on top, the decisions it couldn't make next, and what the run cost. Nothing merges until you do.
- **A book with every release.** The whole wiki as a PDF, an EPUB or one HTML file: parts by topic, chapters in teaching order, diagrams and math drawn as on GitHub. Read it offline, or hand it to a new teammate.

Under the hood, sources are ranked by relevance, then authority (code, specifications and original papers first), then date; licenses are respected and paywalls never bypassed. Scripts do everything mechanical, so your tokens go to judgment. And it's all plain Markdown and YAML in git: browse it on GitHub, open it in Obsidian, or use it from any agent that supports [Agent Skills](https://agentskills.io).

![Every kind of question gets the shape that teaches it. What is X? In short, then rigorously, and its edge cases. How does X work? One real example, walked through with its numbers. Principles of X? The field mapped first, then each idea in brief. X or Y? Every option compared, and the rule for when each wins. What happened? The timeline, the chain of causes, and the lessons. Your own kind? A postmortem, a primer: a template you describe.](docs/images/answer-shapes.svg)

## What it's like to use

![Four moments, from your side. Ask anything: an answer in seconds, each claim cited, and who to ask. Grow it by asking: it researches while you're away, and you review one pull request; nothing lands till you merge. It stays true: when a source changes, exactly the answers that rest on it are flagged, and the rest stay untouched. Share it as a book: each release, such as v2026.10.24, attaches the whole wiki as a PDF to print and share, an EPUB for e-readers and phones, and one HTML file for a browser; read it offline, or hand it on.](docs/images/four-moments.svg)

**Ask anything, any time.** `/sllmwiki:query` answers from what the wiki already knows, reading as little as it can, so most answers come back in seconds. Every claim cites the narrative or source it came from, and the answer names the people who know the area. If the wiki doesn't cover the question yet, you still get an answer, clearly labeled DRAFT, and an offer to research it properly.

**Grow it by asking questions.** `/sllmwiki:build` takes the questions you want answered and does the research unattended: it reuses what the wiki already answers, finds and saves the sources the rest need, writes a narrative per question and checks every claim against its source. You come back to one pull request, opening with a checklist and the few decisions it left you. Comment on anything and ask the agent to apply it: it reworks the same pull request.

**It stays true.** Ask the agent to refresh a topic's sources ("refresh the gateway sources"): it re-saves the ones that changed where they came from, the wiki's checks flag the narratives built on them, and a lint ("lint the gateway narratives") rechecks just those against the new version.

**Share it as a book.** `/sllmwiki:release` makes a dated release on GitHub, with notes on what changed, and attaches the book in the formats you turned on.

### What's in your wiki

Your wiki is its own git repository, plain files you can read anywhere:

| Content | Where | What it is |
|---|---|---|
| **Sources** | `sllmwiki/sources/` | Verbatim copies of the docs, web pages, papers, books and code the answers rest on, saved as markdown and never edited, each with its URL, date, license and a short abstract |
| **Narratives** | `sllmwiki/narratives/` | One per question: the facts and claims that answer it, told in order, opening with an abstract, every claim cited; the figures a narrative draws in `figures/` |
| **Tags** | `sllmwiki/tags/` | A tree of topics, each with a page listing its narratives, sources and the people who know it |
| **Index** | `sllmwiki/.SLLMWIKI_INDICES.md` | A clickable map of the topics, for GitHub |
| **Your templates** | `sllmwiki/.templates/` | Optional: your own kinds of narratives, and language packs |
| **Settings** | `sllmwiki/Config.toml` | Optional: the source policy, markers, language, the book's formats, title and author |
| **Books** | the repository's Releases | The wiki as a PDF, EPUB or HTML file, attached to each release; never committed |

The demo wiki has each: [sources](https://github.com/mengjiasun1992/sllmwiki-demo/tree/main/sllmwiki/sources), [narratives](https://github.com/mengjiasun1992/sllmwiki-demo/tree/main/sllmwiki/narratives), [tags](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/tags/tags.yaml) and [the index](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/.SLLMWIKI_INDICES.md).

How it's built, and why: [the design](docs/structural_llm_wiki_design.md).

## Setup

### Requirements

| Tool | Needed for | |
|---|---|---|
| An agent that runs [Agent Skills](https://agentskills.io), such as [Claude Code](https://docs.claude.com/en/docs/claude-code) | running the skill | required |
| git | history, branches and commits | required |
| Python 3.9 or later | the skill's scripts (standard library only) | required |
| [`gh`](https://cli.github.com), signed in | creating the wiki's remote and opening pull requests; without it, the skill prints the link to open each one yourself | recommended |
| The wiki hosted on GitHub | its CI checks, and the book, which GitHub Actions builds at each release | for the checks and the book |

```bash
brew install git python gh                                   # macOS
winget install Git.Git Python.Python.3.13 GitHub.cli         # Windows
sudo apt-get install -y git python3 gh                       # Debian / Ubuntu
gh auth login && gh auth setup-git                           # then, everywhere
```

### Start a wiki (once, by one person)

1. Create an empty repository (for example `project-foobar-sllmwiki`), clone it and start Claude Code in it.
2. Install the plugin into it:

   ```bash
   claude plugin marketplace add mengjiasun1992/structural-llm-wiki --scope project
   claude plugin install sllmwiki@structural-llm-wiki --scope project
   ```

3. Run `/sllmwiki:init`. It asks a few preferences (the narratives' language, the source policy, the book's formats, title and author), lays out the wiki, installs its CI checks and release workflow, and makes the first commit. Rerun it after a plugin update: it brings the wiki up to date in a pull request.
4. Ask your first questions: `/sllmwiki:build "How does our gateway route requests? Why does it retry?"`

### Join a wiki

Clone it and start Claude Code inside. Trust the folder, and accept the `sllmwiki` plugin the repository offers.

### Other agents

Codex, Cursor, Copilot and other agents install the skill with the [`skills` CLI](https://skills.sh): `npx skills add mengjiasun1992/structural-llm-wiki -g`. There are no commands there; ask for what you want in your own words ("lint the gateway narratives").

## Usage

Four commands cover what you do: set up, ask, grow and publish.

| I want to… | Run |
|---|---|
| Set up a wiki (start here, in an empty repository) | `/sllmwiki:init` |
| Ask the wiki: a cited answer, or a DRAFT and an offer to research it | `/sllmwiki:query "How does the gateway retry failed backends?"` |
| Research questions unattended: sources saved, a cited answer each, one pull request to review | `/sllmwiki:build "How does the gateway route requests?" "Why does it retry?"` |
| Publish the wiki as a book (PDF, EPUB, HTML) in a dated release | `/sllmwiki:release` (`--preview` only builds it) |

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

**Reviewing.** Each run's pull request starts with a checklist (tags, sources, each narrative). Tick each box as you check it; the wiki's "Review checklist" check turns green when all are ticked. Leave comments, and ask the agent to "apply the review comments on PR #12". [The demo's PR #6](https://github.com/mengjiasun1992/sllmwiki-demo/pull/6) is one run's pull request, checklist and all.

**Narrative templates.** Each kind of answer above comes from a template, picked by the question's subject: `concept_brief_overview` ("What is X?", [example](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-is-a-distributed-system.md)), `technical_brief_overview` ("How does X work?", [example](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-is-an-ewma-exponentially-weighted-moving-average-and-how-does-it-work.md)), `comparison` ("X vs Y", [example](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/when-should-software-use-an-ewma-instead-of-other-moving-averages.md)), `survey` ("What are the principles of X?", [example](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-are-the-common-design-tenets-and-principles-for-distributed-systems.md)) or `case_study` ("What happened in this incident, and what does it teach?"). Each comes with a writing guide for a reader new to the topic, and an aim lint grades it on.

**Your own templates.** For a kind of answer the five don't fit, describe it: "make a template for postmortems of our incidents". The agent starts from the closest bundled template and shapes its sections, writing guide and aim from your description. It checks the result and opens a pull request. The template lives in your wiki's `sllmwiki/.templates/<name>/` as a `template.md` (a short header and the sections every answer needs) and a `guide.md` (its reader, aim, style and checklist), and you can also write it by hand. From then on the agent picks it for the questions its header says it fits, and lint grades its narratives on its aim. A template named like a bundled one replaces it; to change only a length, set `max_words` in `Config.toml` instead. The demo has one: [`skim_read`](https://github.com/mengjiasun1992/sllmwiki-demo/tree/main/sllmwiki/.templates/skim_read), a ten-minute primer on a long paper for someone deciding whether to read it, and [a narrative made with it](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-does-keeping-calm-argue-and-is-it-worth-reading-in-full.md). How templates work: [the design, §4.5.5](docs/structural_llm_wiki_design.md#455-a-wikis-own-templates).

**Citations and markers.** As in a paper, a claim's numbered citations sit inside its sentence, before the period, separated by commas: `… exponentially [3], [6].` What no source states is marked `[→]` (our own reasoning), and something the sources don't answer `[?]`, where a citation goes, or once on a heading for a whole section; each narrative defines the ones it uses ([an example](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-is-an-ewma-exponentially-weighted-moving-average-and-how-does-it-work.md)). Turn them off with `markers = false` (see below).

**Settings.** A wiki can keep an optional `Config.toml` (`init` writes it with the defaults):

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

**Books.** Turn on the formats you want in `Config.toml` (`init` asks). `/sllmwiki:release` publishes a dated release of the wiki on GitHub (`v2026.10.24`), with notes on what changed since the last one, and the wiki's release workflow attaches the wiki as a book in each format the `[structural-llm-wiki-release]` table turns on: a cover, a contents page, a part per topic with each chapter's summary and reading time, the narratives in teaching order, and appendices of sources, a glossary and open questions. Its diagrams and math are drawn as they are on GitHub, and the file works offline. GitHub's *Releases → Draft a new release* does the same without the agent; `--preview` builds the book from a branch as a workflow artifact. The book carries each source's abstract, license and link, never its saved copy. A diagram or formula that wouldn't draw, or a link the book couldn't follow, fails the pull request that brings it, long before a release. The demo's [release v2026.10.25](https://github.com/mengjiasun1992/sllmwiki-demo/releases/tag/v2026.10.25) has all three. How it works: [docs/book_design.md](docs/book_design.md).

**Languages.** Narratives are written in the wiki's `language`, and one can name its own (`- **Language:** zh-Hans` in its Metadata, or ask for a language when you ask the question). Sources stay in the language they were written in, and a quotation keeps its source's words, translated after it. Headings come from a language pack, `languages/<tag>.md` in the skill's or your wiki's templates: the skill ships English and Simplified Chinese (`zh-Hans`), each one it has evaluated, and a pack can carry its language's writing rules. For another language, copy [the English pack](plugin/skills/sllmwiki/templates/languages/en.md) into your wiki's `sllmwiki/.templates/languages/` and fill in the translations; the skill writes in it, and says it hasn't evaluated it. Without a pack, headings stay English around prose in your language. Word budgets stay in words; Chinese and Japanese text counts its characters at 1.6 to a word.

**Obsidian.** With `obsidian = true` and `/sllmwiki:init` rerun, open `sllmwiki/` as a vault: its graph shows tag pages in gold and narratives in indigo. Sources are gray, and the graph hides them until you clear its filter (`-path:sources`); to hide them from search and the quick switcher as well, add `sllmwiki/sources/` to your own *Settings → Files and links → Excluded files*. `init` writes the graph's settings once, and the wiki owns them from then on.

## Licenses, sources and your responsibility

A wiki holds other people's work next to text an LLM wrote, so it's worth knowing who owns what and who answers for it.

- **The skill** is open source under the [Apache License 2.0](LICENSE), copyright 2026 Mengjia Sun ([NOTICE](NOTICE)). It covers the skill's code, templates and docs, not what you put in your wiki.
- **Your wiki is yours.** The skill picks no license for it: what your narratives may be shared under is your call, and a wiki made from your company's code and docs falls under your company's rules.
- **Sources stay their authors'.** Copyright stays with each source's authors, and every saved source keeps its URL and license. Narratives quote only briefly, at most `max_quote_words` words, and cite the rest.
- **Copies follow a source policy.** A private wiki keeps reference copies unless a source's terms forbid sharing; a public wiki keeps only openly licensed ones, and its CI fails on a copy it may not hold. With `source_copies = "links-only"` it keeps no copies at all. Review `sllmwiki/sources/` before you make a private wiki public.
- **Fair access only.** The skill never gets around a login, paywall or anti-bot protection, and uses no unofficial copies; when it may not keep a copy, it records a link instead, and when in doubt it asks.
- **No personal data or secrets** go into the wiki, even when a source contains them.
- **Your model provider sees what your agent reads.** Questions and sources go to the model your agent runs on, under that provider's terms: ingest only what you may share with it.
- **Narratives are written by an LLM.** Every claim cites its source, and what no source states is marked, but a narrative can still be wrong: review each pull request before you merge it, and check a claim's source before you rely on it.

The scripts enforce what they can. This is a cautious default, not legal advice: for anything that matters, ask your own counsel.

## Your data

The plugin runs in your agent, on your machine, and its authors collect nothing: no telemetry, no server. Everything it writes goes into your wiki's repository. Data leaves your machine only to **GitHub**, through `git` and `gh` in your own account (pushes, pull requests, releases, and the wiki's Actions), and to **the sites your sources come from**, which receive only the requests that fetch them. The SMEs step reads git history (commit authors' names and emails) and records each person chosen by a handle or a name, with the evidence; personal data in a source is left out of the saved copy. Details: [Privacy](PRIVACY.md).

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
