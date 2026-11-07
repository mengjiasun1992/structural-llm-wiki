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
| Accuracy | a claim its section doesn't support, overstates or gets a number wrong; a picture showing what its caption's citations don't support; a quotation not word for word; a number computed from a cited formula marked `[→]` instead of cited |
| Code | a symbol, file or line that isn't there; design intent presented as current behavior |
| Consistency | a contradiction or a different term across narratives sharing tags; a concept another narrative covers, explained again, described in a way that contradicts it, or mentioned without a link to it |
| Language | grammar, spelling and wording wrong for the narrative's language (its Metadata's `Language`); a sentence left in another language, other than a quotation |
| Reader | anything that breaks the template's guide or `shared-guide.md` (`sllmwiki narrative-format --guide <template>`, already loaded when this run wrote the narrative), and content that doesn't serve the question |

Formatting, links and numbering, figure captions included, are `sllmwiki narrative-format`'s and `sllmwiki wiki-check`'s: run them, don't check by hand. A figure's caption and alt text say what it shows; open its file only to check its numbers against the source.

## 4. Grade the aim

Each template's guide names its aim, a few axes, and says what each axis means; `sllmwiki narrative-format --templates` lists every template's axes, the wiki's own included. Grade each narrative on each axis of its template's aim: **met**, **partly** or **missed**, with the evidence in a line. `sllmwiki narrative-format <file> --stats` gives the numbers: the body against its budget, the words, citations and markers in each section (for depth, the core sections' share; for faithful, what is cited and what is ours), and citations by the authority of what they cite. An axis partly met or missed is an M finding: fix what a sentence fixes, and report the rest as a decision.

## 5. Fix the small, report the big

- **Small** (a sentence, a number, a link, a term): fix it, then `sllmwiki finish-narrative <slug> --bump minor --note "Lint: <what changed>"`.
- **Big** (a missing or wrong section, a changed answer, a source to re-ingest): don't fix it; it's a decision for the owner.
- Number the findings by severity: H for a wrong or unsupported claim, M for a misleading or inconsistent one or a missing link, L for wording and reader aids: H1, H2, M1, L1, …

## 6. Summary and commit

`sllmwiki publish summary lint --json '{...}'` with:
- `title`: "Lint: " and what this lint checked, so a later lint in the same run keeps its own section;
- `checklist`: "Lint: every H finding fixed or decided";
- `decisions`: each big finding, with its number;
- `body`: the aim grades, a table of narrative and each axis of its aim, met, partly or missed, with the evidence; then a table of number, narrative and line, finding, and fixed or left as a decision.

Then one commit, `sllmwiki publish commit lint --tags <tags>`, and `sllmwiki publish pr`.
