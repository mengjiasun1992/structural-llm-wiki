# Writing guide: technical brief overview

## Audience and purpose

**Takeaway:** a reader who didn't know the solution or design has learned it by the end.

An engineer, a researcher or an agent, new to this solution or design, who needs to understand how it works well enough to use it, change it or debug it. Every passage serves that; anything that doesn't (the history of the field, related systems, how the narrative was written) is left out. A neighboring topic worth its own explanation becomes its own question, linked from here.

## Voice and tone

Plain, direct and specific: active voice, present tense, second person where it helps ("you configure …"). Concrete numbers over adjectives. No hype, no hedging beyond what the sources hedge.

## Structure

- **Context before mechanics.** Background opens with the problem, through the running example, then the prerequisites.
- **The core idea before any detail:** in plain words first (what it does, as you'd say it to a colleague), then the one rule or formula, then the diagram that shows it.
- **How it works, worked:** a numbered walkthrough, one step per arrow or transition of the diagram, each on the running example.
- **One notation throughout.** Define each symbol once, with its meaning; write step-by-step quantities with an index ($x_t$, $x_{t+1}$), and never switch to another name for the same thing. A source's own notation is translated, not adopted.
- **The basic form first;** each variant then in Variants, named as a variant of it. A variant few readers need goes in the Appendix.
- **Parameters come with rules of thumb:** a typical value, how to choose it, and what goes wrong when it's too high or too low.

## Examples

One running example, a system the reader can picture, carries the narrative:

| Section | The running example's part |
|---|---|
| Background | its scene: what the system does, its problem, what goes wrong without the answer |
| The core idea | the idea applied to it, in a sentence |
| How does it work? | each step worked on it, with its numbers |
| Variants | the variant it needs, or the one it doesn't |
| Design decisions and trade-offs | the parameter values it uses, and why |
| Limitations and failure modes | where it breaks |

A second key example only for what the first can't show, such as a variant it doesn't use. Others go in the Appendix.

## Evidence

Cite the section that says it. Prefer the code, specifications and the system's own docs; when the docs and the code disagree, say so and cite both. Mark what is yours as reasoning.

## Length

The template's budget is a ceiling, not a target. If the answer needs more, the question is probably several: answer the core one and name the others as next questions.

## Checklist

- [ ] Background shows the problem through the running example before any mechanism.
- [ ] The core idea is in plain words before its formula and diagram.
- [ ] The walkthrough matches the diagram, step for step, on the running example.
- [ ] At most two key examples; any other is in the Appendix.
- [ ] Each parameter has a rule of thumb.
- [ ] Every claim is cited to a section, or marked.
- [ ] Nothing in the body is there for any reason but the reader's understanding.
