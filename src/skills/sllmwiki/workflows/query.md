# query: answer from the wiki

Answer a question from what the wiki already knows, reading as little as possible. Never change the wiki.

1. **Find.** Turn the question into keywords with synonyms, then `search.py context "<keywords>"`: the matching tags and the top narratives' abstracts.
2. **Answer from the smallest thing that answers,** stopping as soon as you can:
   1. a narrative's abstract;
   2. one section: `search.py outline <narrative>`, then `search.py section "<narrative>#<anchor>"`;
   3. the source section a citation points to: `search.py section "<the citation's link>"`, passed as is;
   4. sources no narrative covers yet: `search.py sources "<keywords>"`, then one section of the best.
3. **Reply** with:
   - the answer, citing each narrative or source section it rests on, as links;
   - a warning when a narrative was built on a source that has changed since (`wiki-check.py` reports it as NARRATIVE_SOURCE_CHANGED);
   - what the wiki doesn't cover;
   - who to ask: the tags' SMEs (`tag-tree.py show <tag>`);
   - what you read: which tiers, roughly how much.
4. **Offer, don't do.**
   - When the answer stitched together several narratives, or used sources no narrative covers, offer to file it as a narrative (`steps/narrative.md`).
   - When nothing covers the question, answer from what you know, labeled **DRAFT** and marked as not from the wiki, and offer to research it (`workflows/build.md`).
   - Start neither until asked. Another agent asking gets the answer and the offer.
   - Asked to file it: `publish.py start <question-slug>`, follow `steps/narrative.md` for the question, then `publish.py commit narrative` and `publish.py pr`. Asked to research it: follow `workflows/build.md`.
