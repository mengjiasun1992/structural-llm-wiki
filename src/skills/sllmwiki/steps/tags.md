# tags: map questions to tags

1. **See the tree:** `tag-tree.py tree --brief`, and `search.py context "<keywords>"` for the closest tags.
2. **Choose, per question:**
   - **primary:** the most specific tags the question is about;
   - **supporting:** tags whose content it needs for context;
   - never a parent tag as supporting, since parents are noted, not read.
3. **Add what's missing** with `manifest.py add-tag <tag> --description "<one line>" --parent <tag>`:
   - kebab-case, as specific as the question needs;
   - under the closest existing parent;
   - a new root only for a new field.
4. **Report stale sources:** `wiki-check.py` lists SOURCE_UPSTREAM_CHANGED for the chosen tags' sources.
5. **Summary:** `publish.py summary tags --json '{...}'` with:
   - `title`: "Tags";
   - `checklist`: one item per question, naming its tags, for the owner to confirm;
   - `body`: a table of question, primary and supporting tags, with the new tags marked new.

Run on its own (`/sllmwiki:tags`), reply with that table instead; add tags only when the user confirms.
