# Writing guide: every narrative

Each template's guide holds its own reader, structure and style; this one holds what every narrative's style shares. The reader is from a technical or research field but new to this topic: define the topic's own terms, not general computing ones. When two rules pull apart, the earlier one wins.

## Context first

Set clear context before anything the reader must interpret, so nothing reads ambiguously: the narrative opens with the problem and who has it, even in the Abstract, before its answer; each section, scenario, comparison, formula or piece of pseudocode opens with what it's about and why the reader needs it here; each term is defined before its first use. Depth comes after context, never instead of it.

## Ideas first, sources second

Say each idea in your own words, then cite it. Name a source in the prose only when who said it matters: a definition, a landmark paper, a disagreement, a measurement. Never tally who agrees ("X says …, Y agrees, Z adds …"): give the idea once, with all its citations after it.

## Map before details

Show the whole before its parts: what the narrative covers and how its parts fit, then each part. When a list runs past five to seven items, group it under a few named areas, each with a sentence on what holds it together, so the reader holds a few groups rather than many items.

## Examples

One or two key examples carry the whole narrative, never more. The first is the running example: introduce it once, where the template says, with its scene set for a reader who doesn't know it, in a few plain sentences: what the system does, the problem it has, what goes wrong without the answer, and what each quantity means in it. Then come back to it in each section that explains something, so the reader never switches context to follow a point. A second key example is only for what the first can't show. Any other example goes in the Appendix, or is named in a sentence with a link.

For anything computed, work the running example with numbers, step by step, in a small table where it helps: a reader follows three numbers faster than one formula.

## The shape fits the content

A template's sections are where content goes, not a form to fill. When an optional section or a part of an item's shape has nothing real to say for this subject, leave it out rather than fill it: an example that isn't one, or a "why" that only repeats the "what", costs the reader more than its absence.

## Detail in its place

The body holds what the reader needs to follow the answer; what they may want but don't need goes in the Appendix, linked from where it's relevant. The budget is a ceiling, not a target: stop once the question is answered. Over it, move a secondary example or variant to the Appendix; never cut context.

## Diagrams

Most narratives need at least one diagram, of the flow or how the parts relate; add more only where each shows something new. Each is the type that shows its idea best, not always a flowchart: `sequenceDiagram` for messages between parties, `stateDiagram-v2` for states and transitions, `timeline` for history, `quadrantChart` for trade-offs on two axes, `mindmap` for a field's parts, `flowchart` for a process or how parts connect. Color what carries meaning (a group, the failure path, the recommended choice) with `classDef` fills light enough for dark text in light and dark themes. Keep labels plain text (`s_t`): not every renderer draws math in a diagram.

**Captions.** After each diagram or figure, on a line of its own, its caption: `*Figure 5-1: <what it shows; what each color means>.*`, numbered by its ## section and its place there. Say what a picture shows once, in its caption: no sentence before it describes it again. The text names it by its label where the reader should look ("the groups in Figure 4-1"). With the alt text, the caption spares an agent opening the image. `finish-narrative.py` keeps the numbers in order.

## Figures

When a mermaid diagram can't show an idea well (a curve or measured data with annotations, geometry, a layout drawn to scale, many series at once) and the wiki's `images` setting is on (the default), draw a figure instead. Compute it from the narrative's own formulas or from numbers it cites, and cite their source; never trace or copy a source's figure.

- **Format:** SVG, written yourself or by a short script: every renderer shows it, it stays sharp, and its diff is readable. PNG only for what SVG can't hold, such as a dense heatmap.
- **Where:** `sllmwiki/narratives/figures/<slug>/<name>.svg`, shown with `![<what it shows>](figures/<slug>/<name>.svg)` on a line of its own.
- **Readable in dark themes:** start the SVG with a light `<rect>` the size of the figure, dark text on it, and a generic font (`font-family="sans-serif"`).
- **Small:** an SVG under 40 KB: no more points than the eye can tell apart (a couple of hundred per curve), coordinates rounded to one decimal, styles shared in one `<style>`, no metadata, comments or embedded images. A PNG under 150 KB and 1600 px wide. Self-contained: no scripts or links.

With `images = false`, use mermaid only.

## Pseudocode

Pseudocode, in a ```text block, explains an algorithm or a procedure step by step, under the same rule: where it shows what the prose and diagrams don't, never repeating them. Write it yourself in the narrative's notation, and cite the source it follows in the sentence before it; don't copy a source's code.

## Math

Write formulas and their symbols as TeX: `$x_t$` inline, and a display formula between `$$` lines of its own, one equation per block (GitHub's renderer changes `&` and `\\` inside one). Define each symbol in Terminology, or, when it's used in one section only, in the sentence before its formula.
