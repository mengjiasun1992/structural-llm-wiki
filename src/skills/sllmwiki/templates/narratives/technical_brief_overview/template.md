---
description: How a system or mechanism works, end to end
use_when: 'A solution, an algorithm, or the design of a component or for a problem: "How does X work?", "What is X, and how does it work?", "How does X do Y?"'
max_words: 1800
abstract_words: [150, 250]
---

## 3. Background

<The problem X solves, shown with a concrete example, and what the reader needs to know before the mechanism.>

## 4. What is <X>? (optional)

<Only when the reader can't follow the mechanism without it: one paragraph.>

## 5. How does it work?

<The idea in one paragraph, then the flow.>

```mermaid
graph LR
    A[<step>] --> B[<step>]
```

<Walk through the diagram: one numbered step per arrow, each saying what happens and why.>

## 6. Design decisions and trade-offs

<Each decision: the choice, what it buys, what it costs, and when the other choice wins.>

## 7. Limitations and failure modes

<What breaks, how it shows, and what to do about it.>

## 8. FAQ (optional)

<The questions a newcomer asks next, each answered in a few sentences.>
