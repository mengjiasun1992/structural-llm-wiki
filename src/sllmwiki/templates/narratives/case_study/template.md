---
description: One real, documented case of a concept or domain, followed to its causes, and what it teaches
use_when: 'One real, documented instance that a concept or domain is known by, an incident, a production system or a design decision, rather than how something works in general: "What happened in <incident>, and what does it teach?", "Why did <system> choose <design>?", "Case study: <decision> at <organization>"'
max_words: 1500
abstract_words: [80, 150]
---

## 3. Context

<The orientation, for a reader who doesn't know the system: what it does, its scale, how it normally behaves, and the goals or constraints it works under; and the records the case rests on, saying so when there is only one.>

## 4. The problem

<An incident: what went wrong, and its impact. A design decision: the constraints, and why the obvious approach fails.>

## 5. What happened

<The case in order, each event cited. An incident: the timeline from trigger through spread and detection to recovery. A design decision: the options considered, and the choice.>

```mermaid
%% <a sequenceDiagram or timeline for an incident; a flowchart of the options for a design decision>
```

## 6. Why

<The causal chain, each link cited or marked as ours. An incident: the trigger, the contributing causes, and why the defenses didn't hold. A design decision: why the choice works, and what it gives up.>

## 7. The ideas at work

<One ### subsection per idea the case shows: the idea in a sentence, linked to its own narrative, then the step of the chain it explains.>

## 8. Outcome (optional)

<What resulted, as recorded: the fixes and what changed, or the results, measured, with their conditions.>

## 9. Lessons

<What carries over to other systems: each lesson tied to an idea at work, with the conditions it holds under and where it stops holding; and what would have changed the outcome, marked as ours.>

## 10. Where to go next (optional)

<The questions this opens, each a narrative of its own: linked when it exists, named when it doesn't.>
