# {{name}}

A Structural LLM Wiki: this team's knowledge, kept in git by a coding agent with the sllmwiki skill (<https://github.com/mengjiasun1992/structural-llm-wiki>), and reviewed by people like code.

- **Ask it:** `/sllmwiki:query "How does the gateway retry failed requests?"` answers from what the wiki already knows, citing it.
- **Grow it:** `/sllmwiki:build "How does the gateway route requests?"` finds sources, writes an answer whose every claim is cited, and opens one pull request for you to review and merge.
- **Browse it:** [SLLMWIKI_INDICES.md](SLLMWIKI_INDICES.md) maps the topics; each opens a page of its narratives, sources and who to ask.
- **Read it as a book:** `/sllmwiki:release` publishes a release with the wiki as a book, in the formats `Config.toml`'s `[structural-llm-wiki-release]` turns on; the latest is on this repository's *Releases* page.

## What's here

| Folder | What it holds |
|---|---|
| `sllmwiki/sources/` | Sources, saved verbatim with their URL and license; `manifest.yaml` lists them |
| `sllmwiki/narratives/` | One narrative per question; `manifest.yaml` records their tags and the source versions they read |
| `sllmwiki/tags/` | The tag tree, `tags.yaml`, and a generated page per tag |
| `templates/` | This wiki's own narrative templates, if any |
| `Config.toml` | This wiki's settings |

## Reading a narrative

Every claim cites the section of a source it rests on: the number links to it. Citations sit inside the sentence, before its period, as in a paper. What no source says is marked where a citation would go, `[→]` (the narrative's own reasoning) or `[?]` (something the sources don't answer), or once on a heading for a whole section; a narrative defines the ones it uses. When `Config.toml` sets `markers = false`, there are no markers: an uncited sentence is the narrative's own.

## Joining

Clone this repository and start Claude Code in it. Trust the folder, and accept the `sllmwiki` plugin it offers.
