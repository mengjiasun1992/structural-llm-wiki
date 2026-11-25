# Design: reviewing the tag tree

- **Status:** proposed and built in this pull request, for the owner to check (issue #204)
- **Wiki design:** [structural_llm_wiki_design.md](structural_llm_wiki_design.md) §4.2
- **Companions:** #205 (prerequisites), #206 (reading paths in the index)

## 1. Problem

The owner reads the wiki to learn a new area and gets lost: the tag tree
doesn't show what to read first. Each run adds tags under whichever parent fits
that run, and nothing looks at the whole tree afterwards. So tags sit under the
wrong root (`gpu-cloud-providers` under `machine-learning`), a root stands apart
from the one it builds on (`large-language-models`), and roots appear in the
order they were made. What to read first across trees is #205 and #206; this is
only about the tree being right.

## 2. Decisions

| Question | Decision | Why |
|---|---|---|
| When is the tree reviewed? | At the end of a run that added a tag, once its narratives are written (`steps/tags.md` §4, called from `build` §8) | A new tag's narratives show where it belongs |
| What does the script do, and what does the agent do? | `sllmwiki tag-tree review` shows the whole tree and lists the findings; the agent judges each new tag and each finding | Placing a tag is judgment; finding the suspects is counting |
| Which tags are suspect? | `TAG_NO_PRIMARY`: a leaf that no narrative has as primary. `TAG_OTHER_ROOT`: a tag most of whose narratives have their other primary tags under one other root | These are the issue's two rules. A parent with no narratives of its own isn't flagged, since it groups its children |
| What about a root added before the field it belongs to? | `TAG_BUILDS_ON_ROOT`: a tag most of whose subtree's narratives link to, build on or need narratives under another root, reported on the highest such tag. The tags step also looks down when it adds a tag | The owner's dry run: `large-language-models` and `ml-workload-math` weren't caught by primary tags alone, because narratives written before a tag existed never got it |
| What about narratives written before a tag existed? | `tag-tree review --new <tags>` lists, for each new tag, the narratives not filed under it that link to its narratives or name it (`TAG_RETAG`); the agent adds the tag, at least as supporting | So `TAG_OTHER_ROOT` doesn't keep reading stale tags |
| Which ones does `wiki-check` report? | Only `TAG_OTHER_ROOT`, as a warning | A tag with sources and no narrative yet is normal partway through a run |
| How is a tag moved? | `sllmwiki manifest move-tag <tag> --parent <tag> \| --no-parent`, children included | Never by hand. It refuses to move a tag under itself |
| How are roots ordered? | `sllmwiki manifest order-tags <tag> …` writes `order` on the siblings named; they come first, the rest follow in file order | The owner sets it. It applies to any siblings, so the tag pages and `tag-tree` follow it too |

## 3. For the owner to weigh

1. **Where the order lives:** an `order` field in `tags.yaml` (chosen, since it's
   part of the tree), or a list of roots in `Config.toml`.
2. **Ordering children too:** the order works for any siblings, not only roots.
   The alternative is limiting it to roots, as the issue asks.
3. **Deriving the order from prerequisites:** left to #206, where a root whose
   narratives need another root's comes after it, and ties keep this order.
