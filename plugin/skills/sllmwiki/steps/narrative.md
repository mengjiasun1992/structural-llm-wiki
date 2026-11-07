# narrative: write or update the narrative answering one question

Inside a run (`build`, a filed query, or a rework), write within it; asked for alone, it's a run of its own (`SKILL.md`).

## 1. Reuse or expand first

Inside `build`, its step 1 has decided this: use that. Otherwise, `sllmwiki search narratives "<keywords>"`. If a narrative already asks this question, or one close to it, update it rather than writing a second. Write a new narrative only for a genuinely different question, and link it to the closest one. A narrower question that a narrative only touches in passing, such as how a mechanism works where "What is X?" defines it, is different: it gets its own narrative, since "What is X?" stays at definition level. Say which you chose, and why, in the summary.

## 2. Plan the reading

1. `sllmwiki reading-plan list --primary <tags> --supporting <tags>` lists the candidates.
2. Grade each saved source in a JSON file outside the wiki, in a temporary folder: `{"<slug>": {"relevance": "high|medium|low", "authority": "A|B|C"}}`. A source that defines the subject is high relevance even when the rest of it is about something else. Grade each existing narrative by relevance only, `{"<slug>": {"relevance": "high"}}`: high when this narrative builds on it, relying on its definition or linking to what it explains.
3. `sllmwiki reading-plan order --primary <tags> --supporting <tags> --grades <file>` prints the plan, even for one source.

Read in that order, each source once, and only what the plan says: whole sources for high and medium relevance (or the sections that matter, with `sllmwiki search section`), and abstracts only for low.

## 3. Write

- **Template:** pick one with `sllmwiki narrative-format --templates`, by its use_when, and start from `sllmwiki narrative-format --skeleton <template>`. When none fits the subject, take the closest.
- **Language:** write in the wiki's language (Config.toml's `language`, English by default), or in the one the user asks for: pass it as `--skeleton <template> --language <tag>`, which writes it into Metadata, puts the headings in that language and names the pack's Writing rules to follow. Sources stay in theirs.
- **Where:** save the narrative as `sllmwiki/narratives/<question-slug>.md`.
- **What to follow:** the three guides `sllmwiki narrative-format --guide <template>` prints: the template's, `shared.md` and `shared-guide.md`.
- **Updating:** keep the narrative's version history and say what changed.

## 4. Finish

1. Run `sllmwiki finish-narrative <slug> --primary <tags> --supporting <tags> --read <the slugs read in full> --grades <file>`, with the grades file from §2.
   - On an update, add `--bump minor --note "<what changed>"`, or `major` for a new answer.
2. Fix every error it reports, by editing the narrative, then run it again until none are left.

## 5. Summary

`sllmwiki publish commit narrative --tags <its primary tags> --json '{...}'` with:
- `title`: the question;
- `checklist`: `"<the question>: answers it, every claim cited or marked, reads well"`;
- `body`:
  - reuse, expand or new, and why;
  - the template, and why it fits the subject; or, when none fits, that none does, the closest taken, what it leaves out, and how to add one: ask `make a template for <this kind of answer>`;
  - the reading plan's table;
  - the narrative's outline, with a link to it.
