# Design: prerequisites, what to read first

- **Status:** proposed and built in this pull request, for the owner to check (issue #205)
- **Wiki design:** [structural_llm_wiki_design.md](structural_llm_wiki_design.md) §4.4, §4.5.2
- **Companions:** #204 (the tag tree), #206 (reading paths in the index, built on this)

## 1. Problem

A reader opens a narrative without having read the one that introduces its
concepts, and misses them. Narratives end with "Where to go next", but nothing
says what to read **before**. `built_on` doesn't answer it. It records what the
writer read with high relevance, and in the owner's wiki it diverges from what
a reader needs in both directions:

- **Missing entries:** the LLM narratives record nothing, though they use
  tokens and softmax from the neural-network ones.
- **Backwards entries:** the product-names narrative builds on the NVLink one,
  but a newcomer should read the names first.
- **Cycles:** the training-step and collectives narratives point at each other.

## 2. Decisions

| Question | Decision | Why |
|---|---|---|
| Where are prerequisites kept? | `prerequisites` in the narrative's manifest entry, pinned like `built_on` | A rewrite of a prerequisite flags its dependents (`PREREQUISITE_CHANGED`), the same mechanism as `built_on` |
| Which narratives count? | Direct ones only: whose concepts it uses without explaining them | The order follows from the graph, and #206 sorts it. An indirect one listed as direct is flagged |
| Who chooses them? | The writer, after the body is written | It's judgment. `sllmwiki prerequisites propose` lists the evidence: `built_on`, links, and terms another narrative defines |
| How are they recorded? | `finish-narrative --prerequisite <slug>`, repeatable; `--no-prerequisites` clears them | The command already records everything else about the narrative. It refuses a missing narrative, itself and a cycle |
| What does a reader see? | The Appendix's first two subsections, Before you read and Where to go next, written between generated markers | The owner's preferred structure. `wiki-check --fix` and `finish-narrative` keep them current |
| What does each row say? | The question as a link, the reading time and the first key takeaway | It's deterministic and always current. The takeaway is the narrative's own one-line summary |
| What about the writer's own next reads? | They go after the region's end marker, and every rewrite keeps them | Siblings and deeper questions aren't derived from anything |
| Does the reader see them before the body? | Yes: a "Read first" link beside the reading time under the title (`*About 9 min read. Read first: [A](a.md) ([Before you read](#81-before-you-read)).*`) | The owner's comment on #205. Without a reading time, it's a line of its own |
| Does a new dependent change a narrative? | No. The generated parts, heading numbers and blank lines are left out of the hash and the word count | Otherwise every new prerequisite would flag the narratives that rely on it. Old pins still match until re-pinned |
| What happens to the templates' body "Where to go next"? | It goes: the shared skeleton's Appendix starts with `### Where to go next` | One home. `sllmwiki prerequisites migrate` moves existing sections, and the `init` rerun runs it |

## 3. Checks

- **`wiki-check`:**
  - errors: `PREREQUISITE_UNKNOWN`, `PREREQUISITE_CYCLE` and `READING_ORDER_OUTDATED` (`--fix` rewrites it);
  - warnings: `PREREQUISITE_INDIRECT` and `PREREQUISITE_CHANGED`.
- **Lint, Reader row:** a term used without explaining it that another narrative
  explains, with no prerequisite on it; a prerequisite the narrative never uses.
  `propose` lists both.

## 4. For the owner to weigh

1. **The row's one line:** the first key takeaway. The alternative is a line the
   writer passes with each `--prerequisite`, which would add a field per
   prerequisite to the manifest.
2. **The Read first line:** it lists the titles, which can be long. The
   alternative is a count with the link ("2 narratives first").
3. **Migration:** `migrate` moves the sections and only *proposes*
   prerequisites; the agent records them in the `init` rerun's pull request for
   review. The owner's `skim_read` template keeps its own section until it's
   updated on the wiki side.
