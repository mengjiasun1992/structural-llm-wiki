# narrative: write or update the narrative answering one question

Inside a run (`build`, a filed query, or a rework), write within it. Alone, the step is a run of its own: `publish.py start <question-slug> --title "<the question>" --prompt "<the user's request, verbatim>"` first, and after the summary, `publish.py commit narrative` and `publish.py pr`. The pull request is how the owner reviews it, so open it without asking.

## 1. Reuse or expand first

`search.py narratives "<keywords>"`. If a narrative already asks this question, or one close to it, update it rather than writing a second. Write a new narrative only for a genuinely different question, and link it to the closest one. A narrower question that a narrative only touches in passing, such as how a mechanism works where "What is X?" defines it, is different: it gets its own narrative, since "What is X?" stays at definition level. Say which you chose, and why, in the summary.

## 2. Plan the reading

1. `reading-plan.py list --primary <tags> --supporting <tags>` lists the candidates.
2. Grade each saved source in a JSON file outside the wiki, in a temporary folder: `{"<slug>": {"relevance": "high|medium|low", "authority": "A|B|C"}}`. A source that defines the subject is high relevance even when the rest of it is about something else. Grade each existing narrative by relevance only, `{"<slug>": {"relevance": "high"}}`: high when this narrative builds on it, relying on its definition or linking to what it explains.
3. `reading-plan.py order --primary <tags> --supporting <tags> --grades <file>` prints the plan.

Read in that order, each source once, and only what the plan says: whole sources for high and medium relevance (or the sections that matter, with `search.py section`), and abstracts only for low. Keep the plan's table for the summary.

## 3. Write

- **Template:** pick one with `narrative-format.py --templates`, by its use_when, and start from `narrative-format.py --skeleton <template>`. When none fits the subject, take the closest.
- **Language:** write in the wiki's language (Config.toml's `language`, English by default), or in the one the user asks for: pass it as `--skeleton <template> --language <tag>`, which writes it into Metadata, puts the headings in that language and names the pack's Writing rules to follow. Sources stay in theirs.
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
  - the template, and why it fits the subject; or, when none fits, that none does, the closest taken, what it leaves out, and how to add one: ask `make a template for <this kind of answer>`;
  - the reading plan's table;
  - the narrative's outline, with a link to it.
