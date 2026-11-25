# Writing guide: technical brief overview

## Audience and purpose

**Takeaway:** a reader who didn't know the solution or design has learned it by the end.

**Aim:** concise, authoritative, depth over breadth. Depth: the core idea and how it works carry at least half the body: why it works, how exactly it behaves on the running example, and its edge cases. Breadth is held back: the variants, decisions and limitations the running example needs, a few each; the rest is named under the Appendix's Where to go next. Authoritative: how it works rests on the code, the specification or the original paper.

An engineer, a researcher or an agent, new to this solution or design, who needs to understand how it works well enough to use it, change it or debug it. Every passage serves that; the history of the field, related systems and how the narrative was written are left out. A neighboring topic worth its own explanation becomes its own question, linked from here.

## Voice and tone

Present tense, second person where it helps ("you configure …"). No hype.

## Structure

- **Background:** the orientation, then the problem through the running example, then what the reader must know before the mechanism. A long one is split into subsections, its assumptions before the numbers that use them.
- **How it works, worked:** a numbered walkthrough, one step per arrow or transition of the diagram, each on the running example.
- **The subject is the main actor:** when the question is about a tool, service or system, introduce it right after the example's problem: what it is, its parts at a glance by what each does, and what it automates. Each step then leads with its part ("NVSentinel's monitor, on each tray, reads …"), then the supporting systems' response; where it helps, what an operator would do without it.
- **Each step is a handoff:** who acts and where it runs, what it reads, what it does, and what it produces for whom. Its first sentence starts from the step before's output.
- **Several new concepts: build up from a toy.** When the mechanism brings more than two concepts new to the reader, first build it on a toy small enough to compute by hand, in an ideal setting. Add one concept per step, in the concept plan's order; then take the same steps to the real running example, with a table from toy to real.
- **Who does what, at each level:** a system with several levels (node, CPU, GPU, switch) gets a short table of each level's actions, in the body.
- **The data on each path:** what crosses each path, how much per unit of work, and what isn't on it. Every rate says whether it is each way or both directions added.
- **The basic form first;** each variant is named as a variant of it.
- **Parameters come with rules of thumb:** a typical value, how to choose it, and what goes wrong when it's too high or too low.

## Examples

| Section | The running example's part |
|---|---|
| Background | its scene: what the system does, its problem, what goes wrong without the answer |
| The core idea | the idea applied to it, in a sentence |
| How does it work? | each step worked on it, with its numbers |
| Variants | the variant it needs, or the one it doesn't |
| Design decisions and trade-offs | the parameter values it uses, and why |
| Limitations and failure modes | where it breaks |

A second key example only for a variant or a limit the first doesn't show.

## Evidence

How it works is cited to the code, the specification, the original paper or the system's own docs; secondary sources serve illustrations and rules of thumb. When the docs and the code disagree, say so and cite both.

## Length

Spend the budget on the core idea worked in full on the running example; a neighboring question goes under the Appendix's Where to go next.

## Checklist

- [ ] The core idea and how it works carry at least half the body.
- [ ] The core idea is in plain words before its formula and diagram.
- [ ] The walkthrough matches the diagram, step for step, on the running example.
- [ ] A tool or system the question is about is introduced upfront and leads every step; each step is a handoff from the one before.
- [ ] Each parameter has a rule of thumb.
- [ ] With several levels, a table says what each does; each path says what data crosses it, how much, and each rate's direction.
- [ ] With several new concepts, a toy is built up one concept at a time before the real case.
