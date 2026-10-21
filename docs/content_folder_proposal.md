# Proposal: a content folder, `sllmwiki/`

- **Status:** decided (§5) and implemented

## 1. Goal

Put a wiki's knowledge in one folder, `sllmwiki/` by default, and keep the
files that run the wiki (agent instructions, settings, templates, CI) and the
GitHub-only files at the repository root:

```text
<wiki-repo>/
├── README.md               GitHub front door
├── SLLMWIKI_INDICES.md     GitHub map of topics and narratives (generated)
├── AGENTS.md  CLAUDE.md    instructions for agents
├── Config.toml             settings, including where the content folder is
├── templates/              narrative templates (tooling, not knowledge)
├── .github/  .claude/      CI, plugin settings
└── sllmwiki/               the knowledge, and nothing else
    ├── tags/               tags.yaml and a page per tag (Obsidian add-on)
    ├── groomed/            narratives and their manifest
    ├── ingested/           sources, their manifest and images
    └── .obsidian/          the vault's settings (the vault is sllmwiki/)
```

## 2. Why

| | Today: content at the root | With `sllmwiki/` |
|---|---|---|
| **Obsidian** | the vault is the whole repository: agent files, the README, templates and the index appear in the graph and need filtering; `.obsidian/` sits among repository files | the vault is `sllmwiki/`: only knowledge appears, and only sources need a filter (`show_sources`) |
| **Books** ([book proposal](book_add_on_proposal.md)) | staging picks content out of the repository | the build's source is `sllmwiki/`; staging only adds the generated pages |
| **CI and checks** | lint and ignore patterns name each content path | one folder to include or exclude |
| **People and agents** | knowledge and tooling share the root | everything in `sllmwiki/` is knowledge; everything outside runs the wiki |

### 2.1 The index stays at the root

`SLLMWIKI_INDICES.md` is GitHub's map: GitHub has no navigation of its own.
Elsewhere it isn't needed, and it gets in the way:

- **Obsidian:** the graph and the tag pages are the map. The index, linking
  every narrative, becomes a hub in the middle of the tag tree.
- **Books:** Sphinx and mdBook generate their own tables of contents and
  sidebars from the tag tree. The index would duplicate them, and its
  diagram's links point at GitHub.

So it stays at the repository root, next to the README, outside the content
folder. It is still generated and checked by `wiki-check --fix-index`.

### 2.2 What stays as it is

- **`groomed/` and `ingested/`.** Clearer names were considered (`narratives/`,
  `sources/`), but the skill's documentation, manifests and checks use these
  words as concepts throughout; renaming them is a large change for little
  gain, and each wiki's README explains them.
- **Manifests inside their folders.** Obsidian doesn't show YAML.
- **`templates/` at the root.** Templates are tooling: they belong in neither
  the graph nor a book.
- **One repository is one wiki.**
- **Links between content files.** Everything in the content folder moves
  together, so narratives' links to sources (`../ingested/…`) and tag pages'
  links stay the same.

## 3. Design

### 3.1 The content root in `Config.toml`

A new path, `content`, the content folder, relative to the repository root.
The content paths are relative to it; the others stay relative to the
repository root:

```toml
[structural-llm-wiki-paths]
content = "sllmwiki"                       # the content folder: the Obsidian vault and the books' source
ingested = "ingested"                      # in the content folder: sources
ingested_manifest = "ingested/manifest.yaml"
groomed = "groomed"                        # in the content folder: narratives
groomed_manifest = "groomed/manifest.yaml"
tags = "tags/tags.yaml"                    # in the content folder
index = "SLLMWIKI_INDICES.md"              # from the repository root: GitHub's map
templates = "templates"                    # from the repository root: tooling
```

- **New wikis** get `content = "sllmwiki"`.
- **Existing wikis:** `init` adds `content = "."` to a `Config.toml`
  that lacks it, which keeps every path's meaning, so nothing moves until the
  wiki opts in.
- **Moving into the folder** is then one edit: set `content = "sllmwiki"` and
  rerun `init`. It moves the content (with `git mv`) and rewrites what
  points at it, as it does for any path change today.
- **`Layout`** (`lib/config.py`) resolves each content path through the
  content root, so scripts keep using `L.ingested`, `L.groomed` and the rest
  as paths from the repository root. `wiki-check --paths` prints both forms.
- **Validation** (decision 1, errors): `content` is a folder inside the
  repository (`.` allowed). Content paths are relative and stay inside it (no
  `..`). `index` and `templates` must be outside the content folder, unless
  `content = "."`.

### 3.2 The Obsidian vault: a setting of its own

The vault is the folder you open in Obsidian, and Obsidian keeps its settings
in `.obsidian/` at the top of that folder; which folder that is doesn't follow
from where the knowledge lives. So it is a setting of the Obsidian add-on
(decision 2):

```toml
[structural-llm-wiki-settings.addons.obsidian]
vault = "content"   # the folder you open in Obsidian: "content" (the folder the content path names) or "root"
```

- `"content"` (the default) means the folder `content` names in
  `[structural-llm-wiki-paths]`: `sllmwiki/` by default, and it follows if
  that is renamed. `"root"` means the repository root.
- The add-on writes `.obsidian/graph.json` in the vault, with a filter for
  that vault: with `"content"`, only sources (unless `show_sources`); with
  `"root"`, also the index, README, AGENTS.md, CLAUDE.md and `templates/`.
- `init` moves `.obsidian/` only when the vault changes (all of it,
  each person's files too), never because the content folder moved.
- `.gitignore` follows the vault: `<vault>/.obsidian/*` ignored, except
  `<vault>/.obsidian/graph.json`.
- Skill runs ignore `.obsidian/` changes when they check for a clean working
  tree (`publish.sh`): Obsidian rewrites `graph.json` whenever the graph view
  changes (zoom, layout), and that shouldn't block a run.

### 3.3 Everything else that names paths

- **CI** (`src/actions/wiki-checks`): markdownlint and `check-yaml` skip the
  configured sources folder and templates folder, resolved through the
  content root.
- **`init`'s moves** rewrite the links in the README, AGENTS.md and the
  index, the manifests' file lists and `tags.yaml`, as today. Links from
  content files to repository files outside the content folder would also be
  rewritten (mengjia-sllmwiki has none).
- **Book builds** use the content folder as their source (book proposal §3).
- **Documentation:** the workflows and steps keep writing `ingested/`,
  `groomed/` and `tags.yaml` as names and say they live in the content
  folder; `SKILL.md` and the design doc describe `content`.

## 4. Options considered

| Option | Why not |
|---|---|
| Keep everything at the root, filter Obsidian's graph | Works for the graph, but every tool keeps picking content out of the repository; the split between knowledge and tooling stays implicit |
| `content/` or `src/` | `src/` reads as code (the mdBook convention, not a wiki's); `content/` is generic. `sllmwiki/` names what is inside and matches the index's name |
| Content paths stay relative to the repository root (each set to `sllmwiki/...`) | Works today with `--set`, but moving the folder means changing every path, and nothing records which folder is the vault or the books' source |
| The index inside the content folder | A hub in Obsidian's graph and a second table of contents in books (§2.1) |

## 5. Decisions

1. **Content paths outside the content folder:** an error (`CONFIG_INVALID`),
   as are `index` or `templates` inside it.
2. **`.obsidian/`:** not tied to the content folder. The vault is its own
   setting, `vault` in the Obsidian add-on's table, defaulting to the content
   folder (§3.2).
