# lint: check narratives against their sources, the code and each other

## 1. Scope

- **A narrative:** its slug. **A tag:** the narratives `reading-plan.py list --primary <tag>` lists. **A description:** `search.py narratives "<keywords>"`.
- Inside a run (`build`, or a rework of an open pull request), lint that run's narratives. Alone, a narrative in an open pull request is linted on it (`publish.py resume <slug>`); otherwise start a run (`publish.py start lint-<slug>`).

## 2. Read each section once

For each narrative, `cited-sections.py <slug>` prints every section it cites, once, with the claims citing it; a code source's lines come numbered. Read those, not whole sources. A target it lists as missing or as a whole file is a finding.

For consistency, read the Abstract and Terminology of each narrative sharing its tags (`reading-plan.py list --primary <its tags>`), and the paragraphs on the terms they share.

## 3. Check

| Category | Look for |
|---|---|
| Accuracy | a claim its section doesn't support, overstates or gets a number wrong; a quotation not word for word; a number computed from a cited formula marked `[→]` instead of cited |
| Code | a symbol, file or line that isn't there; design intent presented as current behavior |
| Consistency | a contradiction or a different term across narratives sharing tags; a concept another narrative covers, explained again, described in other words than that narrative's, or mentioned without a link to it |
| Reader | the template's guide and `shared-guide.md`: a term used before it's defined, notation that changes, a section, scenario or formula without its context first, the same context said twice across the Abstract, the orientation and a scene, more than two key examples in the body or one whose scene isn't set, prose that tallies sources instead of stating the idea, a long list not grouped, a slot filled with filler, detail the Appendix should hold, content that doesn't serve the question |

Formatting, links and numbering, figure captions included, are `narrative-format.py`'s and `wiki-check.py`'s: run them, don't check by hand. A figure's caption and alt text say what it shows; open its file only to check its numbers against the source.

## 4. Fix the small, report the big

- **Small** (a sentence, a number, a link, a term): fix it, then `finish-narrative.py <slug> --bump minor --note "Lint: <what changed>"`.
- **Big** (a missing or wrong section, a changed answer, a source to re-ingest): don't fix it; it's a decision for the owner.
- Number the findings by severity: H for a wrong or unsupported claim, M for a misleading or inconsistent one or a missing link, L for wording and reader aids: H1, H2, M1, L1, …

## 5. Summary and commit

`publish.py summary lint --json '{...}'` with:
- `title`: "Lint: " and what this lint checked, so a later lint in the same run keeps its own section;
- `checklist`: "Lint: every H finding fixed or decided";
- `decisions`: each big finding, with its number;
- `body`: a table of number, narrative and line, finding, and fixed or left as a decision.

Then one commit, `publish.py commit lint --tags <tags> --subject "Lint: <narratives>"`, and `publish.py pr`.
