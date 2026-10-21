# What every narrative shares

A narrative answers one question, for the reader its template's guide names. It starts from `narrative-format.py --skeleton <template>`, which joins this skeleton to the template's sections, and keeps them in that order.

## The top and the appendices

- **Title:** the question, exactly as asked.
- **Abstract:** one sentence on the problem and who has it, then the answer in brief, within the template's word range, so a reader can stop there.
- **Terminology:** every term and acronym the reader meets before its first use, one line each.
- **SMEs** (when known): who to ask, the evidence, and one specific question each.
- **References:** the sources read in full, then the Citations list, which gives each citation number its target once.
- **Metadata:** version, template, model, dates, history and the reading plan. `finish-narrative.py` keeps it.

## Citations

Every claim a source makes is cited, after a space, with a numbered link to the section that makes it:
`Retries back off exponentially. [\[3\]](../sources/<slug>.md#<section>)`. Numbers run 1, 2, 3 in order of first use; the brackets stay escaped so Obsidian doesn't read them as a wikilink. Cite the section, never just the file: a reader checks one section, not a whole source. In a code source, cite the lines: `#L10-L20`.

## What the sources don't say

Write it as yours, marked, never as a source's. When markers are on (the default), start the sentence with:

- `[sllmwiki_reasoning]`: your own conclusion, comparison, grouping or reconstruction, which no cited source states;
- `[sllmwiki_gap]`: something the question needs that the sources don't answer. Say what's missing; never fill it with a guess.

A sentence is cited or marked, never both. With `markers = false` in Config.toml, leave markers out: an uncited sentence is then your own, and a gap is said in words ("the sources don't say …").

## Quoting

Explain in your own words. Quote only a definition or one key sentence, in quotation marks, with its citation, never longer than the wiki's `max_quote_words` (50 unless Config.toml says otherwise). Never copy tables, figures or long passages.

## Formatting

Write plain markdown; `finish-narrative.py` numbers the headings, escapes what a renderer would misread, adds the markers' Terminology rows, and records the narrative. Don't number headings by hand, and don't use wikilinks, highlights or other Obsidian-only syntax: `narrative-format.py` reports them.
