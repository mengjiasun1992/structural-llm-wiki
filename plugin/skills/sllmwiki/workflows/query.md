# query: answer from the wiki

Answer a question from what the wiki already knows, reading as little as possible. Never change the wiki. A request that names only a topic isn't a question yet: ask first (`SKILL.md`).

1. **Find.** Turn the question into keywords with synonyms, then `sllmwiki search context "<keywords>"`: the matching tags and the top narratives' abstracts.
2. **Answer from the smallest thing that answers,** stopping as soon as you can:
   1. a narrative's abstract;
   2. one section: `sllmwiki search outline <narrative>`, then `sllmwiki search section "<narrative>#<anchor>"`;
   3. the source section a citation points to: `sllmwiki search section "<the citation's link>"`, passed as is;
   4. sources no narrative covers yet: `sllmwiki search sources "<keywords>"`, then one section of the best.
3. **Reply** with:
   - the answer, citing each narrative or source section it rests on, as links;
   - a warning when a narrative was built on a source that has changed since (`sllmwiki wiki-check` reports it as NARRATIVE_SOURCE_CHANGED);
   - what the wiki doesn't cover;
   - who to ask: the tags' SMEs (`sllmwiki tag-tree show <tag>`);
   - what you read: which tiers, roughly how much.
4. **Offer, don't do.**
   - When the answer stitched together several narratives, or used sources no narrative covers, offer to file it as a narrative (`steps/narrative.md`).
   - When nothing covers the question, answer from what you know, labeled **DRAFT** and marked as not from the wiki, and offer to research it (`workflows/build.md`).
   - Start neither until asked. Another agent asking gets the answer and the offer.
   - Asked to file it: `steps/narrative.md` for the question, as a run of its own (`SKILL.md`). Asked to research it: `workflows/build.md`.
