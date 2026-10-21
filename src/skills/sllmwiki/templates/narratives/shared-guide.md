# Writing guide: every narrative

Each template's guide holds its own reader, structure and style; this one holds what every narrative's style shares.

## Context first

Set clear context before anything the reader must interpret, so nothing reads ambiguously: the narrative opens with the problem and who has it; each section, scenario, comparison, formula or piece of pseudocode opens with what it's about and why the reader needs it here; each term is defined before its first use. Depth comes after context, never instead of it.

## Examples

Context first applies most to examples. Before an example from a particular system (TCP's retransmission timer, the Linux kernel), set its scene for a reader who doesn't know that system, in a few plain sentences: what the system does, the problem the example solves there, what goes wrong without it, and what each quantity means in it. Then go as deep as the example deserves.

## Diagrams

Most narratives need at least one diagram, of the flow or of how the parts relate; add more where each shows something new, never one that repeats another's idea. Each is the type that shows its idea best, not always a flowchart: `sequenceDiagram` for messages between parties, `stateDiagram-v2` for states and transitions, `timeline` for history, `quadrantChart` for trade-offs on two axes, `mindmap` for a field's parts, `flowchart` for a process or how parts connect. Color what carries meaning (a group, the failure path, the recommended choice) with `classDef` fills light enough for dark text in light and dark themes, and say in the text what each color means. Keep labels plain text (`s_t`): not every renderer draws math in a diagram.

## Pseudocode

Pseudocode, in a ```text block, explains an algorithm or a procedure step by step, under the same rule: where it shows what the prose and diagrams don't, never repeating them. Write it yourself in the narrative's notation, and cite the source it follows in the sentence before it; don't copy a source's code.

## Math

Write formulas and their symbols as TeX: `$x_t$` inline, and a display formula between `$$` lines of its own, one equation per block (GitHub's renderer changes `&` and `\\` inside one). Define each symbol in Terminology.
