---
type: llm
---

The narrative's worked example says a client that gives up after 10 seconds waits 7 seconds and spends 6 seconds on its tries, so waiting is 70% of its time. That is impossible: 7 + 6 = 13 seconds is more than the 10 seconds it has. The example also says a client "must" double its wait "because that is what retry libraries do", which rests on habit, not on a fact (the cited source only says each retry waits twice as long).

Pass only if the final message reports both:
1. that the times don't fit: the waits and tries add up to more than the 10 seconds (or the 70% share can't be right);
2. that the "must" rests on what libraries usually do rather than a fact, or is a convention stated as a requirement.

Fail if either is missing. Don't count general remarks about the example being uncited or unclear as finding either one.
