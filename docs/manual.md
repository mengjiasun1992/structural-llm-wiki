# Structural LLM Wiki: the manual

Everything about using the `sllmwiki` plugin, after [the README](../README.md)'s setup. How it's built, and why: [the design](structural_llm_wiki_design.md).

**The big picture.** A wiki is a git repository that answers questions from saved sources. The agent saves each source verbatim, with its URL and license. For each question, the agent writes a narrative: the answer, with every claim cited to a source. Tags sort sources and narratives into a tree of topics. Each tag page also lists the people who know its topic, the SMEs. Lint checks each narrative against its sources. Every run that changes the wiki ends in one pull request, and nothing lands until you merge it. Where each part lives: [§3](#3-whats-in-your-wiki).

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

For everything else, ask in your own words. The skill runs the step your request needs; `build` runs them all for you.

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

Each run's pull request starts with a checklist (tags, sources, each narrative), then the decisions the agent left to you, then what the run cost. Tick each box as you check it. The wiki's "Review checklist" check turns green when all are ticked. To ask for changes, leave comments, then ask the agent to "apply the review comments on PR #12". The agent reworks the same pull request. Nothing lands until you merge. [The demo's PR #22](https://github.com/mengjiasun1992/sllmwiki-demo/pull/22) is one run's pull request, checklist and all.

## 3. What's in your wiki

Your wiki is its own git repository, plain Markdown and YAML you can read anywhere:

| Content | Where | What it is |
|---|---|---|
| **Sources** | `sllmwiki/sources/` | Verbatim copies of the docs, web pages, papers, books and code the answers rest on, saved as markdown and never edited, each with its URL, date, license and a short abstract |
| **Narratives** | `sllmwiki/narratives/` | One per question: the facts and claims that answer it, told in order, opening with an abstract, every claim cited; the figures a narrative draws in `figures/` |
| **Tags** | `sllmwiki/tags/` | A tree of topics, each with a page listing its narratives, sources and the people who know it |
| **Index** | `sllmwiki/.SLLMWIKI_INDICES.md` | A clickable map of the topics, for GitHub |
| **Your templates** | `sllmwiki/.templates/` | Optional: your own kinds of narratives, language packs, and `audience.md`, who the wiki is written for |
| **Settings** | `sllmwiki/Config.toml` | The source policy, markers, language, the book's formats, title and author |
| **Books** | the repository's Releases | The wiki as a PDF, EPUB or HTML file, attached to each release; never committed |

The index and the templates have dot names, so Obsidian hides them and the book leaves them out. The demo wiki has each: [sources](https://github.com/mengjiasun1992/sllmwiki-demo/tree/main/sllmwiki/sources), [narratives](https://github.com/mengjiasun1992/sllmwiki-demo/tree/main/sllmwiki/narratives), [tags](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/tags/tags.yaml) and [the index](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/.SLLMWIKI_INDICES.md).

Sources are ranked by relevance, then authority (code, specifications and original papers first), then date. They're saved as the most faithful text that can be checked: markdown, HTML, PDF (by its outline), EPUB (by its table of contents), LaTeX and code; large books are sliced by chapter.

## 4. Narratives and templates

Each kind of answer comes from a template, which the agent picks by the question's subject. Each template comes with a writing guide, written for a reader new to the topic. It also has an aim, which lint grades its narratives on.

| Template | For | Shape | Example |
|---|---|---|---|
| `concept_brief_overview` | "What is X?" | In short, then rigorously, and its edge cases | [What is a distributed system?](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-is-a-distributed-system.md) |
| `technical_brief_overview` | "How does X work?" | One real example, walked through with its numbers | [What is an EWMA?](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-is-an-ewma-exponentially-weighted-moving-average-and-how-does-it-work.md) |
| `comparison` | "X or Y?" | Every common option compared, and the rule for when each wins | [EWMA or other moving averages?](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/when-should-software-use-an-ewma-instead-of-other-moving-averages.md) |
| `survey` | "What are the principles of X?" | The field mapped first, then each idea in brief | [Design tenets of distributed systems](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-are-the-common-design-tenets-and-principles-for-distributed-systems.md) |
| `case_study` | "What happened, and what does it teach?" | The timeline, the chain of causes, and the lessons | |

**Your own templates.** For a kind of answer the five don't fit, describe it: "make a template for postmortems of our incidents". The agent starts from the closest bundled template and shapes its sections, writing guide and aim from your description. The agent checks the result and opens a pull request. The template lives in `sllmwiki/.templates/<name>/` as two files:

- `template.md`: a short header and the sections every answer needs;
- `guide.md`: its reader, aim, style and checklist.

You can also write these files by hand. From then on, the agent picks the template for the questions its header says it fits, and lint grades its narratives on its aim. A template named like a bundled one replaces the bundled one. To change only a length, set `max_words` in `Config.toml` instead. The demo has one: [`skim_read`](https://github.com/mengjiasun1992/sllmwiki-demo/tree/main/sllmwiki/.templates/skim_read), a ten-minute primer on a long paper for someone deciding whether to read it, and [a narrative made with it](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-does-keeping-calm-argue-and-is-it-worth-reading-in-full.md). How templates work: [the design, §4.5.5](structural_llm_wiki_design.md#455-a-wikis-own-templates).

When no template fits a question, the agent uses the closest one and says so in the pull request, with the request to make one.

**Who your wiki is written for.** The guides write for a reader from a technical or research field who is new to the topic. If your readers are someone else, describe them once, in the audience file. `init` creates the file empty, in `sllmwiki/.templates/audience.md`. The `audience` setting in `Config.toml` can move the file anywhere in the repository outside the Obsidian vault, or turn it off with `""`. To fill it, ask "write this wiki for our product managers: no code, the decision first", or edit it yourself, in at most 1000 words. From then on, every narrative and answer follows the audience file before the skill's and the guides' own rules. The audience file never overrides the source policy or the review of each pull request. How it works: [the design, §4.5.7](structural_llm_wiki_design.md#457-the-wikis-audience).

## 5. Citations and markers

As in a paper, a claim's numbered citations sit inside its sentence, before the period, separated by commas: `… exponentially [3], [6].` Each links to the section of the saved source that supports it, and quotations are checked word for word.

Two markers flag what no citation covers:

- `[→]` marks the narrative's own reasoning, which no source states.
- `[?]` marks a gap, something the sources don't answer. A gap is never filled with a guess.

A marker goes where a citation goes, or once on a heading for a whole section; each narrative defines the ones it uses ([an example](https://github.com/mengjiasun1992/sllmwiki-demo/blob/main/sllmwiki/narratives/what-is-an-ewma-exponentially-weighted-moving-average-and-how-does-it-work.md)). Turn them off with `markers = false`.

With `reader_annotations = true`, a narrative can also hold your own annotations: tell the agent your view of a section. Once you agree on what it means, the agent adds a quote block at the section's end, apart from the cited text: `> [* <date> <your github username>] …`. Lint removes an annotation once its section no longer fits it, and lists it on the pull request so you can restore it. How it works: [the design, §4.10.1](structural_llm_wiki_design.md#4101-readers-annotations).

## 6. Keeping it true

Each narrative records the source versions it read and the narratives it builds on. To update a topic, ask the agent to refresh its sources ("refresh the gateway sources"). The agent re-saves the sources that changed where they came from. The wiki's checks then flag exactly the narratives built on those sources. A lint ("lint the gateway narratives") rechecks just those narratives against the new version. A narrative that builds on another is flagged when that one changes, too.

## 7. Books and releases

Turn on the formats you want in `Config.toml` (`init` asks). `/sllmwiki:release` publishes a dated release of the wiki on GitHub (`v2026.10.24`), with notes on what changed since the last one. The wiki's release workflow then attaches the wiki as a book, in each format the `[structural-llm-wiki-release]` table turns on: a PDF to print and share, an EPUB for e-readers and phones, one HTML file for a browser.

The book has a cover, a contents page and a part per topic. Each part gives each chapter's summary and reading time, then the narratives in teaching order. Appendices hold the sources, a glossary and open questions. Its diagrams and math are drawn as they are on GitHub, and the file works offline. It carries each source's abstract, license and link, never its saved copy, and never the SMEs.

GitHub's *Releases → Draft a new release* does the same without the agent. `/sllmwiki:release --preview` builds the book from a branch as a workflow artifact. A diagram or formula that wouldn't draw, or a link the book couldn't follow, fails the pull request that brings it, long before a release. The demo's [latest release](https://github.com/mengjiasun1992/sllmwiki-demo/releases/latest) has all three formats. How it works: [the book's design](book_design.md).

## 8. Settings

`sllmwiki/Config.toml` holds the wiki's settings. `init` writes it with the defaults and the answers you gave. Change any of them at any time:

```toml
[structural-llm-wiki-settings]
source_copies = "allow"     # or "links-only": keep no copies, only links
visibility = ""             # "private" or "public", for when GitHub can't say who sees the wiki
audience = "sllmwiki/.templates/audience.md"  # who the wiki is written for; "" for none
max_quote_words = 50        # the longest quotation a narrative may take
smes_exclude = []           # never listed as SMEs, such as the wiki's owner or bots
markers = true              # false: no reasoning or gap markers
reader_annotations = false  # true: your own annotations, quote blocks at a section's end
picture_formats = ["mermaid", "svg", "png"]  # the kinds of picture a narrative may use
max_pictures = 5            # pictures in one narrative, at most; 0: none
max_image_kb = 100          # an SVG or PNG figure's size, at most
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

Narratives are written in the wiki's `language`. A narrative can name its own: `- **Language:** zh-Hans` in its Metadata, or ask for a language when you ask the question. Sources stay in the language they were written in, and a quotation keeps its source's words, translated after it.

Headings come from a language pack: `languages/<tag>.md`, in the package's or your wiki's templates. A pack can also carry its language's writing rules. The skill ships three packs, each for a language it has evaluated:

- English;
- Simplified Chinese (`zh-Hans`);
- Traditional Chinese (`zh-Hant`, in Taiwan usage; `zh-TW` and `zh-HK` find it too).

For another language, copy [the English pack](../src/sllmwiki/templates/languages/en.md) into your wiki's `sllmwiki/.templates/languages/` and fill in the translations. The skill then writes in that language, and says it hasn't evaluated the pack. Without a pack, headings stay English around prose in your language. Word budgets stay in words; Chinese and Japanese text counts its characters at 1.6 to a word.

## 10. Obsidian

Set `obsidian = true` and rerun `/sllmwiki:init`. Then open `sllmwiki/` as a vault: its graph shows tag pages in gold and narratives in indigo. Sources are gray, and the graph hides them until you clear its filter (`-path:sources`). To hide them from search and the quick switcher as well, add `sllmwiki/sources/` to your own *Settings → Files and links → Excluded files*. `init` writes the graph's settings once, and the wiki owns them from then on.

## 11. Teams, updates and other agents

**Join a wiki.** Clone it and start Claude Code inside. Trust the folder, and accept the `sllmwiki` plugin the repository offers. `init` records the plugin in the wiki's `.claude/settings.json`. The wiki's README, which `init` writes, says what to run when no offer appears and how other agents join. Your first `sllmwiki` command installs the plugin's code.

**Update the plugin.** `/sllmwiki:init` checks for a newer release and offers to upgrade. On a yes, it runs `claude plugin marketplace update structural-llm-wiki && claude plugin update sllmwiki@structural-llm-wiki`; then restart. After a plugin update, rerun `/sllmwiki:init`: it brings the wiki's layout, CI checks and release workflow up to date in a pull request, and keeps the wiki's own files.

**Other agents.** Codex, Cursor, Copilot and other agents that support [Agent Skills](https://agentskills.io) install the skill with the [`skills` CLI](https://skills.sh): `npx skills add mengjiasun1992/structural-llm-wiki -g`. They install the code it runs with `pipx install sllmwiki==<version>`, the version its `SKILL.md` names. These agents have no commands: ask for what you want in your own words ("lint the gateway narratives").

## 12. Licenses, sources and your responsibility

A wiki holds other people's work next to text an LLM wrote, so it's worth knowing who owns what and who answers for it.

- **The skill** is open source, copyright 2026 Mengjia Sun ([NOTICE](../NOTICE)). Its code is under the [GNU General Public License, version 3 or later](../LICENSE), so a modified version someone distributes stays open too. Its templates (what `init` puts in your wiki, the narrative templates, the book's stylesheet) are under [MIT-0](../src/sllmwiki/templates/LICENSE), with no conditions, so your wiki and its books owe the skill nothing. Running the skill, even on private code, triggers no GPL obligation; distributing a modified copy of its code does. Versions up to 1.2.0 were released under Apache 2.0.
- **Your wiki is yours.** The skill picks no license for it. What your narratives may be shared under is your call. A wiki made from your company's code and docs falls under your company's rules.
- **Sources stay their authors'.** Copyright stays with each source's authors, and every saved source keeps its URL and license. Narratives quote only briefly, at most `max_quote_words` words, and cite the rest.
- **Copies follow a source policy.** A private wiki keeps reference copies unless a source's terms forbid sharing. A public wiki keeps only openly licensed ones, and its CI fails on a copy it may not hold. GitHub says who can see the wiki. When GitHub can't say (the wiki is hosted elsewhere, or GitHub is unreachable), the wiki counts as public unless you set `visibility = "private"`. With `source_copies = "links-only"` it keeps no copies at all. Review `sllmwiki/sources/` before you make a private wiki public.
- **Fair access only.** The skill never gets around a login, paywall or anti-bot protection, and uses no unofficial copies. When it may not keep a copy, it records a link instead. When in doubt, it asks.
- **No personal data or secrets** go into the wiki, even when a source contains them.
- **Your model provider sees what your agent reads.** Questions and sources go to the model your agent runs on, under that provider's terms. Ingest only what you may share with it.
- **Narratives are written by an LLM.** Every claim cites its source, and what no source states is marked, but a narrative can still be wrong. Review each pull request before you merge it, and check a claim's source before you rely on it.

The scripts enforce what they can. These rules are a cautious default, not legal advice: for anything that matters, ask your own counsel. What the plugin does with your data: [Privacy](../PRIVACY.md).

## 13. FAQ

**Does the wiki have to be on GitHub?** No, but its CI checks and the book run on GitHub Actions, and `gh` opens the pull requests. Without a remote, a run keeps its commits on its branch, with the pull request's description beside them.

**What does the plugin install?** Its code, the [`sllmwiki` package](https://pypi.org/project/sllmwiki/), from PyPI, once per version, into a virtual environment in the plugin's own data folder; nothing global changes. If you already have `sllmwiki` of that version on your PATH (`pipx install sllmwiki==<version>`), it uses that instead. Behind a proxy or offline, pip's own settings apply.

**What if `gh` isn't installed?** Every run checks for `gh` and git, and installs what's missing with your machine's package manager. You run yourself any command that needs `sudo` or a sign-in. Without `gh`, a run prints the link to open its pull request yourself.

**Can I edit a narrative by hand?** Yes: a narrative is Markdown in git, and the wiki's checks run on your pull request like on any other. Never edit a saved source, `tags.yaml`, a `manifest.yaml`, the index or a tag page. Ask the agent instead: its scripts keep these files in step.

**How do I remove a source or a narrative?** Ask the agent ("remove the retry-policy source") in a run, so its scripts keep the manifests in step. Git history keeps the removed file until you rewrite that history.

**Can it read our private code and docs?** Yes, anything your agent can read: repositories you point it at, files, and pages you can open without getting around a login. Their content goes to your agent's model provider, as with any work in your agent.

**What does a run cost?** Each pull request records what its run took: its time, and its turns and tokens. In the demo, a run that saved three sources and wrote one 1,800-word narrative took 10 minutes and 6.0M tokens, almost all of them cached ([PR #22](https://github.com/mengjiasun1992/sllmwiki-demo/pull/22)). [The README](../README.md) has more.

**Can I make my wiki public?** Yes, once its saved sources are all openly licensed: a public wiki's CI fails on a copy it may not hold. Review `sllmwiki/sources/` first, or set `source_copies = "links-only"`.

**Who are the SMEs, and how do I keep someone off the list?** The people behind a topic's code and docs, ranked by evidence from git history, code owners and authorship, each with a question to ask them. Add anyone, such as yourself or a bot, to `smes_exclude` in `Config.toml`.
