# narrative: write or update the narrative answering one question

## 1. Reuse or expand first

`search.py narratives "<keywords>"`. If a narrative already asks this question, or one close to it, update it rather than writing a second. Write a new narrative only for a genuinely different question, and link it to the closest one. Say which you chose, and why, in the summary.

## 2. Plan the reading

1. `reading-plan.py list --primary <tags> --supporting <tags>` lists the candidates.
2. Grade each saved source in a JSON file: `{"<slug>": {"relevance": "high|medium|low", "authority": "A|B|C"}}`.
3. `reading-plan.py order --primary <tags> --supporting <tags> --grades <file>` prints the plan.

Read in that order, each source once, and only what the plan says: whole sources for high and medium relevance (or the sections that matter, with `search.py section`), and abstracts only for low. Keep the plan's table for the summary.

## 3. Write

- **Template:** pick one with `narrative-format.py --templates`, by its use_when, and start from `narrative-format.py --skeleton <template>`. When none fits the subject, take the closest.
- **Where:** save the narrative as `sllmwiki/narratives/<question-slug>.md`.
- **What to follow:**
  - the template's `guide.md`, for its reader, structure and style;
  - `templates/narratives/shared.md`, for what every narrative shares: citations, markers and quoting;
  - `templates/narratives/shared-guide.md`, for the style every narrative shares: diagrams, pseudocode and math.
- **Updating:** keep the narrative's version history and say what changed.

## 4. Finish

1. Run `finish-narrative.py <slug> --primary <tags> --supporting <tags> --read <the slugs read in full> --grades <file>`, with the grades file from step 3.
   - On an update, add `--bump minor --note "<what changed>"`, or `major` for a new answer.
2. Fix every error it reports, by editing the narrative, then run it again until none are left.

## 5. Summary

`publish.py summary narrative --json '{...}'` with:
- `title`: the question;
- `checklist`: `"<the question>: answers it, every claim cited or marked, reads well"`;
- `body`:
  - reuse, expand or new, and why;
  - the template, and why it fits the subject; or, when none fits, that none does, the closest taken, and what it leaves out;
  - the reading plan's table;
  - the narrative's outline, with a link to it.
