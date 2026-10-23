# AGENTS.md

This repository is a Structural LLM Wiki, kept with the sllmwiki skill (<https://github.com/mengjiasun1992/structural-llm-wiki>). Its knowledge is in `sllmwiki/`: sources in `sources/`, narratives in `narratives/`, the tag tree in `tags/tags.yaml`.

## Rules

- Change the wiki through the skill (`/sllmwiki:build`, `/sllmwiki:query`, and its steps): its scripts keep the manifests, tags and generated pages in step with the files. Never edit `sllmwiki/tags/tags.yaml`, a `manifest.yaml`, `SLLMWIKI_INDICES.md` or a tag page by hand.
- A file in `sllmwiki/sources/` is a verbatim copy of its source, with a generated footer. Never edit, summarize or reformat one; save it again instead.
- Every claim in a narrative cites a section of a saved source, or is marked as the narrative's own reasoning or as a gap (see the README).
- Each run is one pull request against the default branch, from a branch made from the up-to-date default branch. The owner reviews it, ticks its checklist and merges; a run never merges.
- Respect the source policy: copyright stays with each source's authors; keep every source's URL and license; quote briefly; never get around a login, paywall or anti-bot protection; a private wiki keeps reference copies unless a source's terms forbid it, a public one only openly licensed sources (`Config.toml` can allow none). When in doubt, keep a link and ask.
- Never commit secrets, credentials or personal data, even when a source contains them.
