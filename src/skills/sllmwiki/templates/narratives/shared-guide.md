# Writing guide: every narrative

Each template's guide holds its own reader, structure and style; this one holds what every narrative's style shares.

## Diagrams

Most narratives need at least one diagram, of the flow or of how the parts relate; add more where each shows something new, never one that repeats another's idea. Each is the type that shows its idea best, not always a flowchart: `sequenceDiagram` for messages between parties, `stateDiagram-v2` for states and transitions, `timeline` for history, `quadrantChart` for trade-offs on two axes, `mindmap` for a field's parts, `flowchart` for a process or how parts connect. Color what carries meaning (a group, the failure path, the recommended choice) with `classDef` fills light enough for dark text in light and dark themes, and say in the text what each color means. Keep labels plain text (`s_t`): not every renderer draws math in a diagram.

## Pseudocode

Pseudocode, in a ```text block, explains an algorithm or a procedure step by step, under the same rule: where it shows what the prose and diagrams don't, never repeating them. Write it yourself in the narrative's notation, and cite the source it follows in the sentence before it; don't copy a source's code.

## Math

Write formulas and their symbols as TeX: `$x_t$` inline, and a display formula between `$$` lines of its own, one equation per block (GitHub's renderer changes `&` and `\\` inside one). Define each symbol in Terminology.
