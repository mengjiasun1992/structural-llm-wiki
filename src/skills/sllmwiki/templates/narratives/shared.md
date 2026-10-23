# What every narrative shares

A narrative answers one question, for the reader its template's guide names. It starts from `narrative-format.py --skeleton <template>`, which joins this skeleton to the template's sections, and keeps them in that order.

## The top and the appendices

- **Title:** the question, exactly as asked.
- **Abstract:** one sentence on the problem and who has it, the answer in two or three, then 3-5 key takeaways, each a line the reader should remember; all within the template's word range, so a reader can stop there.
- **Terminology:** only the terms the whole narrative leans on, and every abbreviation it uses, one line each. Define any other term in a clause where it's first used, and put it in the Appendix's Glossary when a reader may need it again.
- **Appendix** (when needed): what a reader may want but doesn't need to follow the answer: the Glossary, a derivation, an example beyond the key ones, a table of values, a lesser variant. Each item is a ### subsection that still serves the question, and the body links to it where it's relevant.
- **SMEs** (when known): who to ask, the evidence, and one specific question each.
- **References:** the sources read in full, then the Citations list, which gives each citation number its target once.
- **Metadata:** version, template, model, dates, history and the reading plan. `finish-narrative.py` keeps it.

## Other narratives

When the narrative mentions a concept another narrative covers, say it in a sentence consistent with that narrative and link to it there, to its section where one fits, instead of explaining it again. The reading plan names the related narratives.

## Citations

Every claim a source makes is cited, after a space, with a numbered link to the section that makes it:
`Retries back off exponentially. [\[3\]](../sources/<slug>.md#<section>)`. Numbers run 1, 2, 3 in order of first use; the brackets stay escaped so Obsidian doesn't read them as a wikilink. Cite the section, never just the file: a reader checks one section, not a whole source. In a code source, cite the lines: `#L10-L20`.

## What the sources don't say

Write it as yours, marked, never as a source's. When markers are on (the default), put the marker where a citation would go, after the statement (a sentence, a list item or a table cell):

- `[→]`: your own conclusion, comparison, grouping, worked example or reconstruction, which no cited source states: `Both trade latency for consistency. [→]`;
- `[?]`: something the question needs that the sources don't answer. Say what's missing; never fill it with a guess.

A number you compute from a cited formula, with its inputs shown, isn't your own reasoning: cite the formula's section after it. Mark at the level the reasoning spans: a section that is all yours (applying the ideas, a constructed scenario) marks its heading once, `## 8. Applying them [→]`, not each sentence. A statement is cited or marked, never both. With `markers = false` in Config.toml, leave markers out: an uncited sentence is then your own, and a gap is said in words ("the sources don't say …").

## Quoting

Explain in your own words. Quote only a definition or one key sentence, in quotation marks, with its citation, never longer than the wiki's `max_quote_words` (50 unless Config.toml says otherwise). Never copy tables, figures or long passages.

## Formatting

Write plain markdown, with no heading numbers and no Obsidian-only syntax (wikilinks, highlights): `finish-narrative.py` numbers, escapes and records the narrative, and `narrative-format.py` reports the rest.
