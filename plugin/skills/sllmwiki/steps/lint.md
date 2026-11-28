# lint: check narratives against their sources, the code and each other

## 1. Scope

- **A narrative:** its slug. **A tag:** the narratives `sllmwiki reading-plan list --primary <tag>` lists. **A description:** `sllmwiki search narratives "<keywords>"`.
- Inside a run (`build`, or a rework of an open pull request), lint that run's narratives. Alone, a narrative in an open pull request is linted on it (`sllmwiki publish resume <slug>`); otherwise it's a run of its own (`SKILL.md`).

## 2. Read each section once

For each narrative, `sllmwiki cited-sections <slug>` prints every section it cites, once, with the claims citing it; a code source's lines come numbered. Read those, not whole sources. A target it lists as missing, as a whole file or as the page's title is a finding.

For consistency, read the Abstract and Terminology of each narrative sharing its tags (`sllmwiki reading-plan list --primary <its tags>`), and the paragraphs on the terms they share.

## 3. Check

| Category | Look for |
|---|---|
| Accuracy | a claim its section doesn't support, overstates or gets a number wrong; a picture showing what its caption's citations don't support; a quotation not word for word; a number computed from a cited formula, or a term's definition, marked `[→]` instead of cited; a hedge stronger or weaker than its source's; thin evidence (one machine, a vendor's own benchmark, one source) not called thin; evidence against the answer that a cited source gives, left out |
| Code | a symbol, file or line that isn't there; design intent presented as current behavior |
| Consistency | within the narrative, one thing called by two names, or an example stated in more than one place (consolidate it, below); a contradiction, a different term, or one word with two meanings across narratives sharing tags; a concept another narrative covers, explained again, described in a way that contradicts it, or mentioned without a link to it |
| Language | grammar, spelling and wording wrong for the narrative's language (its Metadata's `Language`); a sentence left in another language, other than a quotation |
| Annotations | a reader's annotation that no longer fits what its section says: remove it, and list it, with its text, in the summary's decisions so it can be restored; one the sources contradict: rework it with its reader, or remove and list it the same way |
| Reasoning | in each section that reasons or computes, the audit below finds: a step the narrative skips; a rule or number given without the arithmetic that produces it ("by calculus", "the rule is"); a quantity without its unit, or a rate presented as the effect of a whole step; a method explained with the one it replaces; a later sentence that contradicts an earlier one or a worked check |
| Reader | the whole: an Abstract the finished body doesn't match; summarize each section in one sentence and read them in order; flag one that doesn't follow from the one before, a section the spine doesn't need, and a subject that isn't the actor of its steps; a concept introduced before one it is built from (check it against the narrative's concept plan, tables, pictures and maps included: a link to a narrative not read first explains nothing), several such cases meaning the sections need reordering or regrouping, not a clause at each use; a term used unexplained that another narrative explains, which isn't a prerequisite, and a prerequisite it never uses (`sllmwiki prerequisites propose <slug>` lists both); a concept or paragraph arriving without why the reader needs it here; one thing in different colors, or one color for different scopes or kinds, across a narrative's pictures, or no legend; a new name inside an explanation, a term never defined; a "why" before the narrative has described how it works; a big picture missing from the top of what it maps; a step list mixing parts, setup, failures or recaps, or out of real time order; a step restating where it sits, or bringing in more than two new concepts; an example set up only by reference to another narrative; a question as a heading (`QUESTION_HEADING`); a case or number in the example that its scene did not set up, an assumption not called out, a worked value named by a bare letter, a claim of the narrative's own about how a system behaves with no check behind it; English that isn't plain (each `SENTENCE_*`, `ABBREV_*` and `PASSIVE_SHARE` warning; a passive, nested or noun-stacked sentence; a paragraph whose point isn't its first sentence; a number with no baseline or meaning; three or more numbers outside a table; reasoning in a list: rewrite it as the guide's Plain sentences says); a chart without its point in the caption, axis units or a legend for several series (`CHART_*` for mermaid); anything that breaks the wiki's audience profile (each item of its Checklist), the template's guide or `shared-guide.md` (`sllmwiki narrative-format --guide <template>`, already loaded when this run wrote the narrative), and content that doesn't serve the question |

**Consolidate each example.** A narrative may have several examples; for each, when it, or part of it, is stated in more than one place, in text, a table or a picture, merge it into one place: where it is first set up, holding every part, value and unit the narrative later uses of it, in the narrative's one name for each. Then replace each other statement with a reference to it plus only what that section adds or changes. Fix it, as a small finding (M), whatever the number of places.

**Audit the reasoning, slowly.** For each section with logical or mathematical reasoning (a derivation, a worked example, a chain of "so" and "therefore", a table of computed values), think it through at full effort: rebuild it yourself from only what the narrative has said up to that point, writing out every step, and recompute every number in code. Each step you had to supply is a finding (M, or H when a number or conclusion is wrong); fix it by writing the step into the narrative, never by cutting the reasoning. Then reread the section as fixed: a fix can contradict what was there.

Formatting, links and numbering, figure captions included, are `sllmwiki narrative-format`'s and `sllmwiki wiki-check`'s, and tags are `sllmwiki tag-tree review --new <the narratives' tags>`'s (misplaced tags, and narratives using a tag's subject without it): run them, don't check by hand. A figure's caption and alt text say what it shows; open its file only to check its numbers against the source.

## 4. Grade the aim

Each template's guide names its aim, a few axes, and says what each axis means; `sllmwiki narrative-format --templates` lists every template's axes, the wiki's own included. Grade each narrative on each axis of its template's aim: **met**, **partly** or **missed**, with the evidence in a line. `sllmwiki narrative-format <file> --stats` gives the numbers: the body against its budget, the words, citations and markers in each section (for depth, the core sections' share; for faithful, what is cited and what is ours), and citations by the authority of what they cite. An axis partly met or missed is an M finding: fix what a sentence fixes, and report the rest as a decision.

## 5. Fix the small, report the big

- **Small** (a sentence, a number, a link, a term, a tag a narrative uses without it): fix it, then `sllmwiki finish-narrative <slug> --bump minor --note "Lint: <what changed>"`, with `--supporting <its supporting tags>,<tag>` for a tag.
- **Big** (a missing or wrong section, a changed answer, a source to re-ingest, a tag to move or reorder, unless the run's tree review takes it, `steps/tags.md` §4): don't fix it; it's a decision for the owner.
- Number the findings by severity: H for a wrong or unsupported claim, M for a misleading or inconsistent one or a missing link, L for wording and reader aids: H1, H2, M1, L1, …

## 6. Summary and commit

`sllmwiki publish commit lint --tags <tags> --json '{...}' --pr`, one commit, with:
- `title`: "Lint: " and what this lint checked, so a later lint in the same run keeps its own section;
- `checklist`: "Lint: every H finding fixed or decided";
- `decisions`: each big finding, with its number;
- `body`: the aim grades, a table of narrative and each axis of its aim, met, partly or missed, with the evidence; then a table of number, narrative and line, finding, and fixed or left as a decision.
