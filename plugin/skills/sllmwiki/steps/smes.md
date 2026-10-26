# smes: find the people who know a topic

## 1. Find the code and docs behind the tags

For each tag, the files its knowledge comes from: the code its code sources were saved from, the docs and design notes the team wrote. They must be in a local clone: the wiki itself, or a repository the user names or already has checked out. Never clone or fetch a repository just for this; without one, say so in the summary and stop.

## 2. Rank the people

`contributors.py <paths> --repo <clone>` ranks the people behind them, each with evidence: commits (recent ones count more), the lines they last changed, CODEOWNERS rules, reviews, and named authors. It leaves out bots, anyone in `smes_exclude`, and the commits wiki runs made.

## 3. Choose and record

- Choose two to five per tag: the strongest recent evidence first; someone who only owns the files on paper is listed after those who changed them.
- For each, one specific question this person can answer and the sources can't.
- Record them: `manifest.py put-tag <tag> --smes "@handle: <evidence>; ask: <question>" ...`. Use their handle when the evidence gives one, else their name.

## 4. Summary

`publish.py summary smes --json '{...}'` with:
- `title`: "SMEs";
- `checklist`: "SMEs: each is someone you'd ask";
- `decisions`: a tag with no local repository to rank people from;
- `body`: a table of tag, person, evidence, and question.

Then `publish.py commit smes --tags <tags> --subject "SMEs for: <topic>"`.
