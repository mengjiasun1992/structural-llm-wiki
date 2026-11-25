# Design: reading paths that keep the tag tree

- **Status:** agreed with the owner and built in this pull request (issue #206)
- **Wiki design:** [structural_llm_wiki_design.md](structural_llm_wiki_design.md) §4.8 "Reading paths"
- **Builds on:** #205 (prerequisites), #204 (the tree review, root order)

## 1. Problem

The index and the tag pages show the tag tree. A reader finds a topic there,
but not an order to read it in. The owner wants the order without losing the
tree's structure.

## 2. Decisions

| Question | Decision | Why |
|---|---|---|
| Which path does a narrative belong to? | Its **home**: drop any primary tag that is an ancestor of another of its primary tags, then take the first that's left | The owner's rule: the most specific tag when they nest, the first when they're siblings. Depths in different trees don't compare, so unrelated tags keep the narrative's order |
| What orders a path? | Prerequisites (a topological sort). Ties go by the home's place in the tree, then template (what-is before how-does), then question | The order follows from what the writers recorded, so it's always current |
| How is a prerequisite in another root shown? | Inline, as a link to its place: "needs 2 and machine-learning 2" | The paths stay per area, and the links across areas stay visible |
| What orders the roots? | Dependency order: a root whose narratives need another root's comes after it; the owner's `order-tags` breaks ties | Foundations come first even when they were made later |
| What do tag pages show? | Their narratives numbered in the same order, primary before supporting on a tie, each naming a prerequisite filed under another tag | One order everywhere |
| Does the book follow it? | Yes. Chapters sit under their home; within a tag they come after their prerequisites, then after what they're built on. A `built_on` that a prerequisite contradicts is dropped. Parts follow the roots' order | The book, the index and the tag pages read in one order |
| A diagram per root? | Left out | The numbered lists carry the order; diagrams mattered mostly for Obsidian (the owner's call) |
