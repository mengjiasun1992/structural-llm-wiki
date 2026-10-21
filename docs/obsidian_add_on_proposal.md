# Proposal: reading a wiki in Obsidian

- **Status:** decided (§7) and implemented

## 1. Goal

Let a team open a wiki repository as an [Obsidian](https://obsidian.md) vault
and explore it as a graph: tags, the narratives that answer questions about
them, and the sources those narratives cite. The final goal is the graph view.

GitHub stays where the wiki is written and reviewed. Obsidian is a way to
read and explore it.

## 2. Principles

1. **GitHub rendering never changes for the worse.** No Obsidian-only syntax
   that GitHub renders differently.
2. **Everything Obsidian shows is generated.** The scripts write it from
   `tags.yaml` and the manifests, like `SLLMWIKI_INDICES.md`, so it never
   drifts and nobody edits it by hand.
3. **`tags.yaml` stays the one definition of the tag tree.** Sources stay
   verbatim, and narratives keep no YAML frontmatter.
4. **An add-on, off by default.** A wiki that doesn't use Obsidian gets no
   extra files.

## 3. How Obsidian sees a wiki today

Obsidian needs no particular structure. Its graph view has one rule: every
markdown file is a node, and every link from one markdown file to another
is an edge. Folders, frontmatter and file names don't matter.

| In the wiki | In Obsidian's graph |
|---|---|
| Narratives (`groomed/*.md`) | Nodes |
| Saved sources (`ingested/*.md`) | Nodes |
| Citations, narrative → source | Edges, but see §4.1: today they also create fake nodes |
| Related narratives, narrative → narrative | Edges |
| `SLLMWIKI_INDICES.md` | One hub node; links inside its mermaid diagram don't count |
| Tags (`tags.yaml`) | Nothing: Obsidian graphs only markdown files |
| SMEs and tag abstracts (in `tags.yaml`) | Nothing |

So the current structure almost works. What's missing is compatible syntax
in two places, and a way for the tag tree to reach the graph.

## 4. Proposal

Two parts: syntax that works in both GitHub and Obsidian for every wiki, and
an opt-in add-on that generates what the graph needs.

### 4.1 Compatible syntax (every wiki, no setting)

| Today | Problem in Obsidian | Proposed | GitHub |
|---|---|---|---|
| Citation `[[1]](../ingested/x.md#s)` | `[[1]]` is a wikilink to a note named "1": every citation shows as a broken link, and the graph fills with fake "1", "2", "3" nodes | `[\[1\]](../ingested/x.md#s)` | Renders "[1]" as a link, the same as today (checked on github.com) |
| Display formula in a `math` code block | Shown as code | A `$$ … $$` block, when the formula has no backslash before punctuation and no `*` next to a character | Renders as display math (checked on github.com, with subscripts). GitHub runs markdown over a `$$` block first, so `\\`, `\,`, `\{` lose their backslash and `x^{*}` becomes emphasis: such a formula stays a `math` block (`DOLLAR_MATH` reports one in `$$`) |

**Known limitation: some formulas.** A formula that needs a backslash
before punctuation (an `aligned` block's `\\` line breaks, `\,` spacing,
`\{`) can't be written one way for both: it stays a `math` block, correct on
GitHub and shown as code in Obsidian. Often it can be rewritten instead:
separate `$$` formulas for the lines, no thin spaces, `\lbrace` for `\{`,
`\ast` for `*`.

Both are always on: they cost nothing on GitHub, and a wiki that turns the
add-on on later has nothing to convert. `narrative-format` warns about the
old forms, `finish-narrative` rewrites them, and the templates and
`shared.md` describe the new ones. Narratives in the old form keep passing
the checks, with a warning, until they're rewritten.

**Known limitation: links to a section.** Citations point at a section by
GitHub's heading anchor (`#3-background`). Obsidian looks sections up by
heading text, so these links likely open the source at its top rather than
at the section (to confirm in Obsidian). No one link form works for both,
and GitHub is the primary surface, so the anchors stay as they are.

Sources in `ingested/` are verbatim copies and stay unchanged, even when
their text contains `[[…]]`.

### 4.2 The Obsidian add-on (opt-in)

The add-on has its own table in `Config.toml`, which turns it on and shapes its default graph:

```toml
[structural-llm-wiki-settings.addons.obsidian]
enabled = false        # true: tag pages, narrative headers, default graph settings
show_sources = false   # true: the default graph shows sources, in grey
```

`init` writes both as `false`, with notes, and does the work when one
changes (rerun it). When `enabled` is `true`:

**Tag pages, in `tags/` with `tags.yaml`.** The tags file's default path is
`tags/tags.yaml`, and its folder holds one generated page per tag,
`tags/<tag>.md`:

- a header with the tag's full path as an Obsidian tag;
- a breadcrumb to its ancestors, and its description and abstract;
- its narratives, primary and supporting, with version and date;
- its subtags;
- its sources, flagging those no narrative read yet;
- its SMEs and contact channels, as text.

The links put the tag tree in the graph, with each tag's narratives and
sources around it; on GitHub each page is a topic to browse. `wiki-check
--fix-index` writes them with the index and reports one missing, stale or
left over (`TAG_PAGE_OUTDATED`, `TAG_PAGE_ORPHAN`); a hand-written file is
never touched. A wiki that keeps `tags.yaml` at the root gets
`TAG_PAGES_NO_FOLDER` and no pages until it moves the file into a folder.

**A header on each narrative.** `finish-narrative` writes a generated header
with the narrative's tags (full paths), its version and its last update, for
Obsidian's tag pane, `tag:` searches and property views. It's the one
exception to the no-frontmatter rule, and never written by hand
(`NARRATIVE_HEADER`, `FRONTMATTER` in `narrative-format`).

**The vault.** The folder you open in Obsidian is a setting, `vault`:
`"content"` (the default) is the content folder (the
[content folder proposal](content_folder_proposal.md)), so only the knowledge
appears; `"root"` is the whole repository. `.obsidian/` lives at the top of the
vault, and `init` moves it, each person's files too, when the vault's
folder changes.

**Default graph settings, once.** `init` writes the vault's
`.obsidian/graph.json` when it is missing: color groups for tag pages,
narratives and sources; sources filtered out unless `show_sources` is `true`
(then grey); and, for a vault at the repository root, the README, agent files,
index and templates filtered out too. The wiki owns it from then on; the
skill never overwrites it, and skill runs ignore Obsidian's rewrites of it
(on every zoom or layout change) when they check for a clean working tree.

**`.gitignore`.** Setup shares only `graph.json` from the vault's `.obsidian/`
(`<vault>/.obsidian/*`, except `graph.json`): the rest is each person's
(layout, appearance, plugins, where some keep API keys). `init` also
stops reporting `.obsidian/` as unrelated content.

**Sources stay verbatim.** They get their graph edges from citations and tag
pages. Tags inside sources would add `tag:` search and property views over
them, but a header that changes with the tags breaks their fingerprints; it
would need the footer's treatment (left out of the fingerprint) and is left
for later.

Turning it off (`enabled = false`) removes the generated pages and headers, and keeps
`.obsidian/`.

### 4.3 What doesn't change

- `tags.yaml` defines the tags; the tag pages only mirror it.
- Sources stay verbatim, with no frontmatter or added links.
- Narratives keep no YAML frontmatter.
- Pull requests stay the way changes are reviewed. Editing in Obsidian is
  out of scope (§6).

## 5. Alternatives considered

1. **Nothing beyond compatible syntax.** The graph shows narratives and
   sources only, with no tag tree. Useful, but flat. This is what a wiki gets
   with the add-on off.
2. **Obsidian tags in narrative frontmatter**
   (`tags: [algorithms/moving-averages/ewma]`). The tag pane would show the
   hierarchy, and the graph's "Tags" toggle adds a node per tag. But the
   graph doesn't link a tag to its parent, so the tree is lost there. Sources
   can't carry tags, because they are verbatim. And it ends the
   no-frontmatter rule. It could come later, for the tag pane only, on top of
   the tag pages.
3. **Wikilinks (`[[note]]`) instead of markdown links.** Obsidian-native, but
   GitHub shows them as plain text. Ruled out by principle 1.

## 6. Out of scope

- **Editing in Obsidian.** Edits made there bypass the manifests and checks,
  unless they go through the skills afterwards. CI still catches the
  problems on the pull request.
- **Obsidian plugins.** Everything here works in a plain Obsidian install.
- **Changing citation anchors for Obsidian** (§4.1).

## 7. Decisions

1. **Where tag pages live:** in a `tags/` folder with `tags.yaml`, at
   `tags/tags.yaml` by default.
2. **Sources in the graph:** a setting, `show_sources`, off by
   default (the default graph hides them); on, they are grey. Anyone can
   change it in their own graph settings.
3. **Shared graph settings:** generated once into the wiki
   (`.obsidian/graph.json`), which people then edit as they like.
4. **Settings:** their own table, `[structural-llm-wiki-settings.addons.obsidian]`, with `enabled` and
   `show_sources`.
5. **Obsidian tags:** on narratives, as a generated header; not on sources,
   for now (§4.2).
