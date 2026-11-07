# build: research questions and add the answers

The input is one or more questions; a request that names only a topic is asked about first (`SKILL.md`). After that, don't pause.

## 1. What already answers them

For each question, `sllmwiki search narratives "<keywords>"`. Decide, without asking:

- **reuse:** an existing narrative asks this question, not just touches it in passing (`steps/narrative.md` §1); write nothing for it, and say so in the summary;
- **expand:** one answers part of it, or has newer sources to take in; update that narrative;
- **new:** no narrative asks this question; write one.

Stop if every question is a reuse: reply with the narratives that answer them.

## 2. Start the run

`sllmwiki publish start <slug> --title "<the questions, short>" --prompt "<the user's request, verbatim>"`.

## 3. Tags

Follow `steps/tags.md` for the questions. Its summary goes into the run as `tags`.

## 4. Sources

Follow `steps/ingest.md` for the questions and their tags; its commit takes `--pr`, which opens the pull request.

## 5. SMEs

Follow `steps/smes.md` for the questions' tags; it says when there's nothing to rank.

## 6. Narratives

For each question that isn't a reuse, follow `steps/narrative.md`.

## 7. Lint

Follow `steps/lint.md` for the narratives this run wrote or updated, inside this run: its one commit and its findings go on this pull request. Never skip it, however short the narratives or sure the writing: it is the only check of each claim against the section it cites.

## 8. Hand off

Run `sllmwiki wiki-check --fix` and fix what it still reports; if anything changed, `sllmwiki publish commit lint --subject "wiki-check fixes"`. Then `sllmwiki publish pr`. Reply with the pull request's link, the questions answered and reused, and the decisions left for the owner.
