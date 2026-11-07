# build: research questions and add the answers

The input is one or more questions. When the request names only a topic, propose two or three questions in one message and wait for the choice; after that, don't pause.

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

Follow `steps/ingest.md` for the questions and their tags. Then `sllmwiki publish commit ingest --tags <tags> --subject "ingest sources for: <topic>"` and `sllmwiki publish pr` to open the pull request.

## 5. SMEs

When the topic has code or authored docs in a local clone, follow `steps/smes.md` for its tags.

## 6. Narratives

For each question that isn't a reuse, follow `steps/narrative.md`. After each, `sllmwiki publish commit narrative --tags <its primary tags> --subject "<the question>"` and `sllmwiki publish pr` to update the description.

## 7. Lint

Follow `steps/lint.md` for the narratives this run wrote or updated, inside this run: its one commit and its findings go on this pull request. Never skip it, however short the narratives or sure the writing: it is the only check of each claim against the section it cites.

## 8. Hand off

Run `sllmwiki wiki-check`; fix what it reports, committing again if anything changed, then `sllmwiki publish pr`. Reply with the pull request's link, the questions answered and reused, and the decisions left for the owner.
