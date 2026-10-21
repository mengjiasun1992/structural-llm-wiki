# Writing guide: technical brief overview

## Audience and purpose

**Takeaway:** a reader who didn't know the solution or design has learned it by the end.

An engineer, or an agent, new to this solution or design, who needs to understand how it works well enough to use it, change it or debug it. Every passage serves that; anything that doesn't (the history of the field, related systems, how the narrative was written) is left out. A neighboring topic worth its own explanation becomes its own question, linked from here.

## Voice and tone

Plain, direct and specific: active voice, present tense, second person where it helps ("you configure …"). Concrete numbers over adjectives. No hype, no hedging beyond what the sources hedge.

## Structure

- **Context before mechanics.** Background opens with the problem, through one concrete example the reader can picture, then the prerequisites. The core idea comes next, in one paragraph, before any detail.
- **How it works, drawn.** One diagram of the mechanism (the path a request takes, the states it moves through, the messages between parties), then a numbered walkthrough, one step per arrow or transition.
- **A goal before each scenario.** Before an example or a case, one sentence says what it shows.
- **One notation throughout.** Define each symbol once, in Terminology, with its type and meaning; write step-by-step quantities with an index (x_t, x_{t+1}), and never switch to another name for the same thing.
- **The basic form first,** then its variants, each named as a variant of it.
- **Parameters come with rules of thumb:** a typical value, how to choose it, and what goes wrong when it's too high or too low.

## Evidence

Cite the section that says it. Prefer the code, specifications and the system's own docs; when the docs and the code disagree, say so and cite both. Mark what is yours as reasoning.

## Length

The template's budget is a ceiling, not a target. If the answer needs more, the question is probably several: answer the core one and name the others as next questions.

## Checklist

- [ ] Background shows the problem through an example before any mechanism.
- [ ] Every term, acronym and symbol is in Terminology before its first use.
- [ ] The diagram and the walkthrough match, step for step.
- [ ] Every scenario starts with its goal.
- [ ] Each parameter has a rule of thumb.
- [ ] Every claim is cited to a section, or marked.
- [ ] Nothing in the body is there for any reason but the reader's understanding.
