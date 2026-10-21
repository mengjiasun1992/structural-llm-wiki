# ingest: save the sources the questions need

## 1. Find

- Look for 3-5 good sources per question; fewer good ones beat many weak ones.
- Rank candidates by, in order:
  1. **Relevance:** the most relevant to the question and its tags first.
  2. **Authority,** among the sources you have access and a license to use:
     - A: the code, specifications and standards, original papers or creators, official docs;
     - B: textbooks and references;
     - C: practitioner write-ups.
  3. **Recency:** among equally relevant and authoritative sources, the newest, for the latest understanding of the topic.
- Skip any source already saved (`search.py sources "<keywords>"`); refresh one `wiki-check.py` reports as SOURCE_UPSTREAM_CHANGED.

## 2. Judge before saving

- **Read the source's license or terms.** Record what you find: an SPDX id such as CC-BY-4.0, or "proprietary", or "unknown".
- **Behind a login, a paywall or anti-bot protection:** don't fetch it any other way. Record it as a link.
- **Personal data or secrets:** save only the parts without them, and mark where you left text out.

## 3. Save

- **A copy:** `fetch-source.py <topic>-<source-name> --url <url> --tags <tags> --license <id> [--license-url <url>] [--published YYYY-MM-DD]`.
  - Add `--file <path>` for a copy you already have, or `--refresh` to save a changed source again.
  - When it refuses (the source policy, a login, a format it can't read), record a link instead.
- **A link:** `manifest.py put-source <slug> --kind link --url <url> --license <id> --tags <tags> --abstract "<abstract>"`.

## 4. Abstract

Read each saved source once, and write its abstract: 150-250 words on what it says and covers, using the source's own abstract when it has one. Save it with `manifest.py set-abstract <slug> --abstract "<abstract>"`. Note what each source says that the questions need: the narrative step reads that note instead of the whole source again.

## 5. Summary

`publish.py summary ingest --json '{...}'` with:
- `title`: "Sources";
- `checklist`: "Sources: each is one you'd trust";
- `decisions`: anything the owner must decide, such as permission to keep a copy;
- `body`: a table of slug, kind, size, license, and why it was chosen or kept as a link.
