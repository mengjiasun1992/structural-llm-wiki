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
4. **Report stale sources:** `sllmwiki wiki-check` lists SOURCE_UPSTREAM_CHANGED for the chosen tags' sources.
5. **Summary:** `sllmwiki publish summary tags --json '{...}'` with:
   - `title`: "Tags";
   - `checklist`: one item per question, naming its tags, for the owner to confirm;
   - `body`: a table of question, primary and supporting tags, with the new tags marked new.

Run on its own (asked which tags a topic belongs to), reply with that table instead; add tags only when the user confirms.
