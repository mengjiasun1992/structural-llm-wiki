# English

The language narratives are written in by default, and the model for every
other pack. To add a language, copy this file to your wiki's
`templates/languages/<tag>.md`, named by its BCP 47 tag (such as `zh-Hans.md`),
change the heading to the language's name, and fill in the right column. A row
left blank stays English. Metadata's fields are never translated. A pack may end
with a `## Writing` section of rules for writing in its language, as a list:
the narrative step follows it.

## Headings

| English | Translation |
|---|---|
| Abstract | |
| Terminology | |
| Appendix | |
| Glossary | |
| SMEs | |
| References | |
| Sources read | |
| Citations | |
| Metadata | |
| Context | |
| The problem | |
| What happened | |
| Why | |
| The ideas at work | |
| Outcome | |
| Lessons | |
| Where to go next | |
| The choices | |
| When to choose which | |
| At a glance | |
| Dimensions to think through | |
| Pitfalls | |
| Overview | |
| Definition | |
| In short | |
| Precisely | |
| Key ideas | |
| Boundaries | |
| The map | |
| The main items | |
| Tensions and trade-offs | |
| Classic case studies | |
| Applying them | |
| Background | |
| The core idea | |
| How does it work? | |
| Variants | |
| Design decisions and trade-offs | |
| Limitations and failure modes | |
| Misconceptions | |

## Labels

The words the skeleton and the scripts write around a narrative's content: the
mark of an optional section, table headers, the start of a figure's caption,
and the markers' Terminology rows.

| English | Translation |
|---|---|
| (optional) | |
| Key takeaways | |
| Term | |
| Person | |
| Why them | |
| Ask them | |
| Dimension | |
| Figure | |
| Our own reasoning, after a statement or on a section's heading: a conclusion, comparison or example no cited source states. | |
| A gap, after a statement or on a heading: something the question needs that the sources don't answer. | |

## Book

The words a release's book adds around the narratives (docs/book_design.md
§5): its contents, front page, appendices and cover. Keep `{tool}`, `{models}`
and `{source}` as they are: the book puts the links and names there.

| English | Translation |
|---|---|
| Contents | |
| About this book | |
| See also | |
| Appendix A: Sources | |
| Appendix B: Glossary | |
| Appendix C: Open questions | |
| Version | |
| Date | |
| Commit | |
| License | |
| Published | |
| Cited by | |
| Known issues | |
| Original | |
| The narratives in this book are the wiki owner's work. Every source belongs to its authors: the book links to it and quotes it briefly, but never copies it. | |
| The narratives were written by an LLM and reviewed by the owner. | |
| This book is a snapshot of the wiki at the commit on its cover. | |
| A number in brackets, such as [3], is a citation: it links to the source's entry in Appendix A, which links to the original. | |
| Made by {tool} and {models}, from {source}. | |
| Made by {tool}, from {source}. | |
