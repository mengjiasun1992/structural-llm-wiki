# Writing guide: technical brief overview

## Audience and purpose

**Takeaway:** a reader who didn't know the solution or design has learned it by the end.

**Aim:** concise, authoritative, depth over breadth. Depth: the core idea and how it works carry at least half the body: why it works, how exactly it behaves on the running example, and its edge cases. Breadth is held back: the variants, decisions and limitations the running example needs, a few each; the rest is named under Where to go next. Authoritative: how it works rests on the code, the specification or the original paper.

An engineer, a researcher or an agent, new to this solution or design, who needs to understand how it works well enough to use it, change it or debug it. Every passage serves that; the history of the field, related systems and how the narrative was written are left out. A neighboring topic worth its own explanation becomes its own question, linked from here.

## Voice and tone

Plain, direct and specific: active voice, present tense, second person where it helps ("you configure …"). Concrete numbers over adjectives. No hype, no hedging beyond what the sources hedge.

## Structure

- **Background:** the orientation, then the problem through the running example, then the prerequisites.
- **The core idea before any detail:** in plain words first, as you'd say it to a colleague, then the one rule or formula, then the diagram that shows it.
- **How it works, worked:** a numbered walkthrough, one step per arrow or transition of the diagram, each on the running example.
- **The basic form first;** then, in Variants, at most two, each one the running example needs or a reader is likely to meet, named as a variant of it.
- **Decisions and limitations:** those that change how the running example behaves, about three each. Parameters come with rules of thumb: a typical value, how to choose it, and what goes wrong when it's too high or too low.

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

If the answer needs more than the budget, the question is probably several: answer the core one and name the others as next questions.

## Checklist

- [ ] The core idea and how it works carry at least half the body.
- [ ] The core idea is in plain words before its formula and diagram.
- [ ] The walkthrough matches the diagram, step for step, on the running example.
- [ ] Each parameter has a rule of thumb.
