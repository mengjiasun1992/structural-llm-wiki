# {📖} Structural LLM Wiki

![Structural LLM Wiki. You ask your agent one question, "How does the gateway retry?", and your agent does the rest: 1, it finds and saves the sources, a paper, code, a web page, a design doc; 2, it writes the answer, an open book in braces, every claim tied by a thread to its source; 3, it opens one pull request on project-foobar-sllmwiki.git; 4, you review and merge. The repository is git, which your group and their agents clone, share and grow. Ask your agent a question; get an answer that teaches; every claim tied to its source; reviewed like code; kept in git for your group.](docs/images/hero.svg)

[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-d97757.svg)](#setup)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](#requirements)

**Your group's knowledge, researched by your coding agent, cited to the exact source, and reviewed like code.**

**What it is.** Structural LLM Wiki is a set of agent skills, packaged as a Claude Code plugin, that turns a git repository into a wiki your coding agent researches and keeps up to date. You give it questions. It finds the sources that answer them (design docs, code, specifications, papers, web pages), saves them in the repository, and writes one *narrative* per question: a short document that teaches the answer, with every claim linked to the section of a saved source that supports it. Topic tags tie the sources, the narratives and the people who know each area together, and every run arrives as one pull request you review.

- **For builders,** it's living documentation of your own systems, grounded in their code and design docs, with the exact lines cited and the people who know each area.
- **For tech leads,** it's onboarding that stays current, with every change reviewed and the reasons behind the design kept next to it.
- **For researchers,** it's a structured, cited review of a field: definitions taken from the sources that state them most rigorously, and every claim one click from its evidence.

Unlike an answer in a chat session, the knowledge stays: narratives build on and link to each other, and when a source changes, exactly the narratives built on it are flagged for review.

**See one.** [sllmwiki-demo](https://github.com/mengjiasun1992/sllmwiki-demo) is a wiki built with this skill, on distributed systems and moving averages: start at [its index](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/SLLMWIKI_INDICES.md), read [What is a distributed system?](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-is-a-distributed-system.md), and see [the pull request](https://github.com/mengjiasun1992/sllmwiki-demo/pull/6) that wrote its narratives.

## Why it's different

- **Answers you can check, claim by claim.** Every claim cites the exact section of a source saved in the wiki, so checking it is one click. What no source states is marked as the narrative's own reasoning (`[→]`), and what the sources don't answer as a gap (`[?]`). Quotations are verified word for word against their source.
- **Written to be learned.** The answer's shape fits its subject: a concept is defined in short to set the intuition, then rigorously from the source that defines it best; a mechanism is worked through one running example, with real numbers and diagrams; a field is mapped before its parts; a choice compares every common candidate; a case is followed to its causes. Each of the five templates has an aim, and lint grades every narrative against it.
- **Knowledge that compounds.** One narrative per question, built on and linked to the ones before it. Each records the source versions it read and the narratives it builds on, so a change upstream flags exactly what it affects.
- **Research-grade sourcing.** Sources are chosen for the question, then ranked by relevance, by authority (code, specifications and original papers first) and by date; each narrative records its reading plan and the model that wrote it. Licenses are respected, and logins and paywalls are never bypassed.
- **Reviewed like code.** Each run is one pull request: a review checklist on top, the decisions it couldn't make next, and what it cost. Nothing merges until you do.
- **Frugal and repeatable.** Scripts do everything mechanical; the agent reads the smallest thing that answers and nothing twice, so your tokens go to judgment.
- **Yours, in plain files.** Markdown and YAML in git: browse it on GitHub, open it as an Obsidian vault, keep it ready to build as a book, and run it from any agent that supports [Agent Skills](https://agentskills.io).

Inspired by Andrej Karpathy's [LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), where an LLM builds and maintains a persistent, interlinked markdown wiki from raw sources. Structural LLM Wiki adds what a group needs on top: topic tags that link sources, narratives and people; every claim traced to a section of a saved source; templates that teach; and every change reviewed.

## What it's like to use

![Three moments, from your side. Ask anything: an answer in seconds, each claim cited, and who to ask. Grow it by asking: it researches while you're away, and you review one pull request; nothing lands till you merge. It stays true: when a source changes, exactly the answers that rest on it are flagged, and the rest stay untouched.](docs/images/three-moments.svg)

**Ask anything, any time.** `/sllmwiki:query` answers from what the wiki already knows, reading as little as it can, so most answers come back in seconds. Every claim cites the narrative or source it came from, and the answer names the people who know the area. If the wiki doesn't cover the question yet, you still get an answer, clearly labeled DRAFT, and an offer to research it properly.

**Grow it by asking questions.** `/sllmwiki:build` takes the questions you want answered and does the research unattended: it reuses what the wiki already answers, finds and saves the sources the rest need, writes a narrative per question and checks every claim against its source. You come back to one pull request, opening with a checklist and the few decisions it left you. Comment on anything and the agent reworks the same pull request; nothing enters the wiki until you merge.

**It stays true.** Every answer records the source versions it was built from and the answers it builds on. When a source changes, or an answer is rewritten, exactly the answers that depend on it are flagged, so you recheck those and nothing else.

![Every kind of question gets the shape that teaches it. What is X? In short, then rigorously, and its edge cases. How does X work? One real example, walked through with its numbers. Principles of X? The field mapped first, then each idea in brief. X or Y? Every option compared, and the rule for when each wins. What happened? The timeline, the chain of causes, and the lessons.](docs/images/answer-shapes.svg)

### What's in your wiki

Your wiki is its own git repository, plain files you can read anywhere. Its knowledge lives in `sllmwiki/`:

| Content | Where | What it is |
|---|---|---|
| **Narratives** | `sllmwiki/narratives/` | One answer per question, opening with an abstract, every claim cited; the figures a narrative draws in `figures/` |
| **Sources** | `sllmwiki/sources/` | The docs, web pages, papers and code the answers rest on, saved as markdown, each with its URL, date, license and a short abstract |
| **Tags** | `sllmwiki/tags/` | A tree of topics, each with a page listing its narratives, sources and the people who know it |
| **Index** | `SLLMWIKI_INDICES.md` | A clickable map of the topics, for GitHub |

The demo wiki has each: [narratives](https://github.com/mengjiasun1992/sllmwiki-demo/tree/main/sllmwiki/narratives), [sources](https://github.com/mengjiasun1992/sllmwiki-demo/tree/main/sllmwiki/sources), [tags](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/tags/tags.yaml) and [the index](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/SLLMWIKI_INDICES.md).

How it's built, and why: [the design](docs/structural_llm_wiki_design.md).

## Setup

### Requirements

| Tool | Needed for | |
|---|---|---|
| An agent that runs [Agent Skills](https://agentskills.io), such as [Claude Code](https://docs.claude.com/en/docs/claude-code) | running the skill | required |
| git | history, branches and commits | required |
| Python 3.9 or later | the skill's scripts (standard library only) | required |
| [`gh`](https://cli.github.com), signed in | creating the wiki's remote and opening pull requests; without it, the skill prints the link to open each one yourself | recommended |

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

3. Run `/sllmwiki:init`. It lays out the wiki, installs its CI checks and makes the first commit. Rerun it after a plugin update: it brings the wiki up to date in a pull request.

   > [!NOTE]
   > The wiki's CI calls this repository's GitHub actions. While this repository is private, until the first release, they're reachable only from its owner's repositories, so it's set to allow them (Settings → Actions → General → Access: "Accessible from repositories owned by the user"). A wiki elsewhere fails with "Unable to resolve action … repository not found" until this repository is public.
4. Ask your first questions: `/sllmwiki:build "How does our gateway route requests? Why does it retry?"`

### Join a wiki

Clone it and start Claude Code inside. Trust the folder, and accept the `sllmwiki` plugin the repository offers.

### Other agents

Codex, Cursor, Copilot and other agents install the skill with the [`skills` CLI](https://skills.sh): `npx skills add mengjiasun1992/structural-llm-wiki -g`. There are no commands there; ask for what you want in your own words ("lint the gateway narratives").

## Usage

| I want to… | Run |
|---|---|
| Get an answer from the wiki | `/sllmwiki:query "How does the gateway retry failed backends?"` |
| Research questions and add the answers | `/sllmwiki:build "How does the gateway route requests?"` |
| Answer one question from sources already saved | `/sllmwiki:narrative "Why does the gateway retry failed backends?"` |
| Add a source, or refresh changed ones | `/sllmwiki:ingest gateway "the retry policy design doc"` |
| Check a narrative, or a whole topic | `/sllmwiki:lint gateway` |
| Find who to ask | `/sllmwiki:smes gateway` |
| See which topics a question belongs to | `/sllmwiki:tags "gateway vs load balancer"` |
| Release the wiki, with its book | `/sllmwiki:release` (`--preview` builds the book without releasing) |

**Reviewing.** Each run's pull request starts with a checklist (tags, sources, each narrative). Tick each box as you check it; the wiki's "Review checklist" check turns green when all are ticked. Leave comments, and ask the agent to "apply the review comments on PR #12". [The demo's PR #6](https://github.com/mengjiasun1992/sllmwiki-demo/pull/6) is one run's pull request, checklist and all.

**Narrative templates.** Each kind of answer above comes from a template, picked by the question's subject: `concept_brief_overview` ("What is X?", [example](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-is-a-distributed-system.md)), `technical_brief_overview` ("How does X work?", [example](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-is-an-ewma-exponentially-weighted-moving-average-and-how-does-it-work.md)), `comparison` ("X vs Y", [example](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/when-should-software-use-an-ewma-instead-of-other-moving-averages.md)), `survey` ("What are the principles of X?", [example](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-are-the-common-design-tenets-and-principles-for-distributed-systems.md)) or `case_study` ("What happened in this incident, and what does it teach?"). Each comes with a writing guide for a reader new to the topic, and an aim lint grades it on.
 Bring your own by adding a folder with a `template.md` and a `guide.md` to the wiki's `templates/`; a folder named like a bundled template replaces it.

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
html_book = false           # true: a release attaches the wiki as one HTML file
```

**Books.** `/sllmwiki:release` publishes a dated release of the wiki on GitHub (`v2026.10.24`), with notes on what changed since the last one, and the wiki's release workflow attaches the wiki as a book in each format the `[structural-llm-wiki-release]` table turns on: a cover, a contents page, a part per topic with each chapter's summary, the narratives in teaching order, and appendices of sources, a glossary and open questions. Its diagrams and math are drawn as they are on GitHub, and the file works offline. GitHub's *Releases → Draft a new release* does the same without the agent; `--preview` builds the book from a branch as a workflow artifact. The book carries each source's abstract, license and link, never its saved copy. How it works: [docs/book_design.md](docs/book_design.md).

**Languages.** Narratives are written in the wiki's `language`, and one can name its own (`- **Language:** zh-Hans` in its Metadata, or ask for a language when you ask the question). Sources stay in the language they were written in, and a quotation keeps its source's words, translated after it. Headings come from a language pack, `templates/languages/<tag>.md`: the skill ships English and Simplified Chinese (`zh-Hans`), each one it has evaluated, and a pack can carry its language's writing rules. For another language, copy [the English pack](src/skills/sllmwiki/templates/languages/en.md) into your wiki's `templates/languages/` and fill in the translations; the skill writes in it, and says it hasn't evaluated it. Without a pack, headings stay English around prose in your language. Word budgets stay in words; Chinese and Japanese text counts its characters at 1.6 to a word.

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

## Design

[docs/structural_llm_wiki_design.md](docs/structural_llm_wiki_design.md) has the architecture and the decisions behind it; [docs/skill_execution_plan.md](docs/skill_execution_plan.md), how it's being built.

## Developing

```text
src/
├── skills/sllmwiki/   the skill: SKILL.md, workflows/, steps/, scripts/, templates/, tests/
├── commands/          Claude Code commands, one per workflow and step
├── actions/           the GitHub actions a wiki's CI calls
└── tools/             CI tools outside the skill (check-yaml)
evals/                 behavior evals, kept outside the skill so they never ship with it
docs/                  the design, the plan, and their figures
```

`AGENTS.md` has the rules for changing this repository: tests with every logic change and coverage at 95% or above, instruction word budgets, evals for behavior changes. Run the tests, and try the plugin from a checkout:

```bash
python3 -m pip install "coverage[toml]==7.6.10"
python3 src/skills/sllmwiki/tests/run.py --coverage
claude --plugin-dir .
```

## License

Copyright 2026 Mengjia Sun. Licensed under the [Apache License, Version 2.0](LICENSE); see [NOTICE](NOTICE).
