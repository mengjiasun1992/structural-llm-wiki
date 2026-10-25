# ingest: save the sources the questions need

## 1. Find

- Look for 3-5 good sources per question; fewer good ones beat many weak ones.
- First list what the question's narrative can't miss, by its template's subject (design doc §4.5):
  - concept: the standard definition;
  - technical: the specification or paper the method comes from, and how it's used;
  - comparison: each common candidate, and every dimension the choice turns on;
  - survey: every main area of the field, and its official or classic lists.
- Search for each, the source of record first, then widen, until a source covers it or the searches show none does. Keep the searches you ran.
- Rank candidates by, in order:
  1. **Relevance:** the most relevant to the question and its tags first.
  2. **Authority,** among the sources you have access and a license to use:
     - A: the code, specifications and standards, original papers or creators, official docs;
     - B: textbooks and references;
     - C: practitioner write-ups and encyclopedias; use an encyclopedia to get oriented and to find the sources it cites.
  3. **Recency:** among equally relevant and authoritative sources, the newest, for the latest understanding of the topic.
- Skip any source already saved (`search.py sources "<keywords>"`); refresh one `wiki-check.py` reports as SOURCE_UPSTREAM_CHANGED. To find those, `check-upstream.py [<slugs>] [--tags <tags>]` fetches saved sources again and marks the changed ones.

## 2. Judge before saving

- **Read the source's license or terms.** Record what you find: an SPDX id such as CC-BY-4.0, or "proprietary", or "unknown".
- **Behind a login, a paywall or anti-bot protection:** don't fetch it any other way. Record it as a link.
- **Personal data or secrets:** save only the parts without them, and mark where you left text out.

## 3. Save

- **A copy:** `fetch-source.py <topic>-<source-name> --url <url> --tags <tags> --license <id> [--license-url <url>] [--published YYYY-MM-DD]`.
  - Add `--file <path>` for a copy you already have, or `--refresh` to save a changed source again.
  - PDFs, EPUBs and LaTeX are converted; an EPUB whose chapters are encrypted (DRM) is refused, so record a link. A LaTeX source in several files: put them in one folder and pass the main one with `--file`.
  - A table or figure a page only links to ("Full size table"): when a question needs it, save the linked page too, as its own source.
  - When it refuses (the source policy, a login, a format it can't read), record a link instead.
- **A link:** `manifest.py put-source <slug> --kind link --url <url> --license <id> --tags <tags> --abstract "<abstract>"`.

## 4. Abstract

A saved source stays in the language it was written in: never translate it. Read each saved source once, and write its abstract, in the wiki's language: 150-250 words on what it says and covers, using the source's own abstract when it has one. Save it with `manifest.py set-abstract <slug> --abstract "<abstract>"`. Note what each source says that the questions need: the narrative step reads that note instead of the whole source again.

## 5. Summary

`publish.py summary ingest --json '{...}'` with:
- `title`: "Sources";
- `checklist`: "Sources: each is one you'd trust";
- `decisions`: anything the owner must decide, such as permission to keep a copy, and each A source you couldn't use or save, with its link and why;
- `body`: what the question can't miss, each with the source that covers it or "none found"; the searches you ran; then a table of slug, kind, size, license, and why it was chosen or kept as a link.
