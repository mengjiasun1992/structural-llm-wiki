# smes: find the people who know a topic

## 1. Find the code and docs behind the tags

For each tag, the files its knowledge comes from: the code its code sources were saved from, the docs and design notes the team wrote. They must be in a local clone: the wiki itself, or a repository the user names or already has checked out. Never clone or fetch a repository just for this; without one, say so in the summary and stop.

## 2. List the people

`sllmwiki contributors <paths> --repo <clone>` lists the people behind them by name, each with evidence: commits and the date of the last, the lines they last changed, CODEOWNERS rules, reviews, and named authors. It leaves out bots, anyone in `smes_exclude`, and the commits wiki runs made.

## 3. Choose and record

- Choose two to five per tag who worked on the files recently and can answer what the sources can't. This says who to ask, never how good anyone's work is: don't score, rank or compare them, nor name one best, here or in an answer; keep the command's order, by name.
- For each, one specific question this person can answer and the sources can't.
- Record them: `sllmwiki manifest put-tag <tag> --smes "@handle: <evidence>; ask: <question>" ...`. Use their handle when the evidence gives one, else their name.

## 4. Summary

`sllmwiki publish commit smes --tags <tags> --json '{...}'` with:
- `title`: "SMEs";
- `checklist`: "SMEs: each is someone you'd ask";
- `decisions`: a tag with no local repository to find people in;
- `body`: a table of tag, person, evidence, and question.
