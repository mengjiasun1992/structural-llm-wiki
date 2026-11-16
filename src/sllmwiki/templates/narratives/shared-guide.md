# Writing guide: every narrative

The reader is from a technical or research field and new to this topic: define the topic's own terms, not general computing ones. This guide holds the style every narrative shares; each template's guide adds only what its kind of narrative needs, starting with its aim, the axes lint grades it on. When two rules pull apart, the earlier one wins.

## Context, once, in layers

Never make the reader interpret something before they know what it is and why it's there. Context comes in layers, each adding what the reader doesn't have yet, none repeating another:

1. **The Abstract,** for a reader deciding whether to read on: the problem and who has it, then the answer.
2. **The first section's orientation,** for a reader who goes on, in a few sentences, before any definition or mechanism: what the subject is, where and when one meets it, who deals with it, and why it matters.
3. **Each key example's scene,** where it first appears: what the system does, its problem, and what goes wrong without the answer.
4. **Each section, scenario, formula or piece of pseudocode** opens with what it's about and why the reader needs it here.

Each term is explained before it is used: show what it does, on the example, then give its name. Depth comes after context, never instead of it.

## Tell it as a story

Explain it in the order the reader meets it, not a textbook's:

- **A job the reader cares about, with the data in hand:** a task they could face, the evidence they would have, and what goes wrong without the answer.
- **Each concept arrives as the answer to the question the reader would ask next:** what is it for, why not something simpler, where does this number come from, is it fixed or does it change. A concept no question has asked for yet waits.
- **One new concept at a time,** in its own step or paragraph, never in a clause.
- **The example is set up once, in full,** in its scene: every case and number the narrative later uses is there from the start.
- **Say what is what:** what is set by hand to teach, what someone chooses before it runs, what is learned or measured, what is fixed in use, and each assumption, where it is made, so the reader never guesses why. Where the toy behaves unlike the real system, say so there.
- **A derivation goes one link at a time:** the nearest case first, each link checked with a number, then the general rule.
- **Names come after use:** once the reader has seen a part work, give its official name; a table from the story's words to the field's terms closes the mechanism.

## Ideas first, sources second

Say each idea in your own words, then cite it. A claim of your own about how a system behaves is checked before it's written, by computing or running it, and the narrative says how. Name a source in the prose only when who said it matters: a definition, a landmark paper, a disagreement, a measurement. Never tally who agrees ("X says …, Y agrees"): give the idea once, cited. Where sources disagree, cite each view.

## Map before details

Show the whole before its parts: what the narrative covers and how its parts fit, then each part. An overview of a process names every step the body explains, so none appears later from nowhere. A list longer than five to seven items is grouped under a few named areas, each with a sentence on what holds it together.

## One or two key examples

One running example carries the narrative: its scene is set once, and each section that explains something comes back to it, so the reader never switches context to follow a point. A second only shows what the first can't. Others go in the Appendix, or are named in a sentence with a link. Pick the examples that fit this question; when a related narrative's key example fits just as well, reuse it and link to its scene. Work anything computed on the running example, with its numbers, step by step, in a small table where it helps: a reader follows three numbers faster than one formula. Name each value for what it is (`past`, `pred`), not by a bare letter.

## The shape fits the content

A template's sections are where content goes, not a form to fill. When an optional section, or a part of an item's shape, has nothing real to say for this subject, leave it out: an example that isn't one, or a "why" that only repeats the "what", costs the reader more than its absence.

## Detail in its place

The body holds what the reader needs to follow the answer; what they may want but don't need goes in the Appendix, linked from where it's relevant. The budget is a ceiling, not a target: stop once the question is answered. An answer that needs several areas new to the reader is several narratives, one question each, read in order, each saying what it needs from the one before. Over it, move a secondary example or variant to the Appendix; never cut context. The questions a reader would ask after the body can go in the Appendix as an FAQ, each answered briefly.

## Pictures

A picture earns its place when it saves the reader from building something in their head: how the parts fit, what happens in what order, how a state changes, a quantity's shape. Add one wherever it does, each teaching something new, up to `max_pictures`; none where it would only decorate. Choose the form by what it shows: boxes are no stand-in for a chart or geometry. What follows is a floor and rules of thumb, not a limit: judge each case by what helps this reader learn.

- **Where it helps most:** the map of the whole, near the start; the running example step by step, the same small diagram at each step rather than one dense one; before and after. A comparison is often clearest as a table.
- **The form:** whichever of the wiki's `picture_formats` shows this idea best; none comes first.
  - **Mermaid**, text each viewer draws: structure and flow in a standard shape, in the type that fits (`sequenceDiagram` for messages, `stateDiagram-v2` for states, `timeline` for history, `quadrantChart` for trade-offs on two axes, `mindmap` for a field's parts, `flowchart` for a process). Some viewers, GitHub's among them, clip a long node label: keep labels to a few words, or draw an SVG.
  - **An SVG** you draw controls every position: a curve, measured data, geometry, a layout to scale, or a diagram mermaid would crowd.
  - **A PNG**, only for what's raster by nature, like a heatmap.
  - Draw an image from the narrative's own formulas, numbers or structure, never traced from a source's figure: `sllmwiki/narratives/figures/<slug>/<name>.svg` or `.png`, light background, dark text, a generic font; an SVG keeps the formula and inputs it was drawn from in its `<desc>`.
- **Easy to read:** one idea per picture, about a dozen elements at most, short plain-text labels in the narrative's names (`s_t`, as not every renderer draws math). Check that no label is cut off or overlaps another. Keep each thing's color and place the same across pictures. Color only what carries meaning, with light `classDef` fills and dark text, and never by color alone: a label, a shape or a dashed line says it too.
- **A picture makes claims:** it shows nothing its caption's citations don't support.

Each picture is followed by its caption, on a line of its own: `*Figure 5-1: <its point, not just its subject; what each color means> [3].*`. Say it once, in the caption, not again before it; the text names it by its label where the reader should look. An image's alt text says what it shows. `sllmwiki narrative-format` checks the rest, the wiki's limits included.

## Pseudocode and math

Pseudocode, in a ```text block, explains an algorithm or procedure step by step, where it shows what the prose and pictures don't. Write it in the narrative's notation and cite the source it follows; don't copy a source's code.

Write formulas as TeX: `$x_t$` inline, a display formula between `$$` lines of its own, one equation per block. Use one notation throughout: define each symbol once, in Terminology or in the sentence before the formula that alone uses it, and translate a source's notation rather than adopt it.
