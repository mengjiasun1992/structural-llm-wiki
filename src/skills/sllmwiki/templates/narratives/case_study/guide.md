# Writing guide: case study

## Audience and purpose

**Takeaway:** a reader new to the case knows what happened and why, and can apply its lessons elsewhere.

A reader who knows, or is learning, a concept or a domain, and wants to see it at work in one of the cases it's known by: a production system, an incident, a design decision. The case teaches the ideas by showing them in action; the ideas themselves are linked to their own narratives, not taught here.

## Voice and tone

Plain, concrete and factual: the case as the sources record it, in the past tense for events and the present for designs still in use. No blame: describe what the system did and why, not who erred.

## Structure

- **Context:** the orientation, for a reader who has never seen this system: what it does, its scale, its constraints. Enough to follow the case, no more.
- **The problem** before the answer: what made it hard here, not in general.
- **What happened** in order, with a diagram: a sequence for messages, a timeline for an incident, a state diagram for a protocol, a flowchart for a design.
- **The ideas at work:** each idea the case shows, named and linked, then pointed to in the case. This is where the case connects to the rest of the wiki.
- **Lessons** a reader can carry to another system, each with the conditions it holds under.

## Examples

The case is the one key example, and every section stays inside it. Another case appears only in Lessons, in a sentence, to show where a lesson stops holding.

## Evidence

Prefer the people who built or ran the system: design docs, postmortems, papers and code; then independent analyses. When accounts differ, give each, cited.

## Length

Deep on the one case, not wide: a reader should finish it in under fifteen minutes. A second case worth its own depth is its own narrative.

## Checklist

- [ ] What happened is in order, and matches its diagram.
- [ ] Every idea at work is linked to its narrative, or named as a next question.
- [ ] Each lesson says when it holds.
