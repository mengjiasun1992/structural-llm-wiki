# Writing guide: case study

## Audience and purpose

**Takeaway:** a reader new to the case knows what happened and why, and can apply its lessons elsewhere.

**Aim:** faithful, causal, transferable; deep on one case. Faithful: the case as its records tell it, every event, time and number cited, nothing beyond them. Causal: the chain from trigger to impact, or from constraint to choice to result, each link explained. Transferable: lessons a reader can apply elsewhere, each with the conditions it holds under.

A reader who knows, or is learning, a concept or a domain, and wants to see it at work in one of the cases it's known by: an incident, a production system, a design decision. The case teaches the ideas by showing them in action; the ideas themselves are linked to their own narratives, not taught here. How something works in general is the technical template's subject, not this one's.

## Voice and tone

Plain, concrete and factual: the past tense for events, the present for designs still in use. No blame: describe what the system did and why, not who erred.

## Structure

Pick the shape by the kind of case:

| Section | An incident | A design decision |
|---|---|---|
| Context | the system, its scale, its normal behavior | the system, and its goals |
| The problem | what went wrong, and its impact | the constraints, and why the obvious approach fails |
| What happened | the timeline: trigger, spread, detection, recovery, as a sequence or timeline diagram | the options considered, and the choice, as a flowchart |
| Why | the trigger, the contributing causes, and why the defenses didn't hold | why the choice works, and what it gives up |
| Outcome | the fixes, and what changed | the results, measured |

- **Faithful:** every event, time and number in Context, The problem and What happened is cited to the record. A case that rests on one account says so in Context. Nothing beyond the record: no blame, no guessed cause; a cause the record doesn't state is marked as ours, or as a gap.
- **Causal:** Why is the heart of the narrative: each link of the chain is cited or marked, and each idea at work explains a step of it, not just names a concept.
- **Transferable:** each lesson names the idea it applies and when it holds or stops holding; one says what would have changed the outcome. The lessons stay no longer than the analysis they rest on.

## Examples

The case is the one key example, and every section stays inside it. Another case appears only in Lessons, in a sentence, to show where a lesson stops holding.

## Evidence

Prefer the people who built or ran the system: postmortems, design docs, papers and code; then independent analyses. When accounts differ, give each, cited.

## Length

Deep on the one case, not wide: a reader should finish it in under fifteen minutes. A second case worth its own depth is its own narrative.

## Checklist

- [ ] Every event, time and number in What happened is cited; a single account is said to be one.
- [ ] Why traces the whole chain, and each idea at work explains a step of it.
- [ ] Each lesson says when it holds, and one says what would have changed the outcome.
