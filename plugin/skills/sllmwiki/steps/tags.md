# tags: map questions to tags

1. **See the tree:** `sllmwiki tag-tree tree --brief`, and `sllmwiki search context "<keywords>"` for the closest tags.
2. **Choose, per question:**
   - **primary:** the most specific tags the question is about;
   - **supporting:** tags whose content it needs for context;
   - never a parent tag as supporting, since parents are noted, not read.
3. **Add what's missing** with `sllmwiki manifest add-tag <tag> --description "<one line>" --parent <tag>`:
   - kebab-case, as specific as the question needs;
   - under the closest existing parent;
   - a new root only for a new field.
4. **Review the tree,** at the end of a run that added a tag, once its narratives are written (`build` §8), or right after adding when run on its own: `sllmwiki tag-tree review` shows the whole tree and the tags a reader may not expect where they are. For each new tag and each finding, check its parent against its siblings and its narratives' subjects: would a reader new to the area look for it there? Move one another parent fits better with `sllmwiki manifest move-tag <tag> --parent <tag>` (or `--no-parent`). When the roots don't run from foundations to what builds on them, order them with `sllmwiki manifest order-tags <root> <root> …`. Commit with `sllmwiki publish commit tags --json '{"title": "Tag tree review", ...}'`, listing each move and why, and each finding kept and why.
5. **Summary:** `sllmwiki publish commit tags --json '{...}'`, which commits any new tags, with:
   - `title`: "Tags";
   - `checklist`: one item per question, naming its tags, for the owner to confirm;
   - `body`: a table of question, primary and supporting tags, with the new tags marked new.

Run on its own (asked which tags a topic belongs to), reply with that table instead; add tags only when the user confirms.
