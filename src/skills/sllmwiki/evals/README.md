# Behavior evals

Unit tests (`../tests/`) check the scripts; these evals check the skill's behavior: does a request reach the right workflow or step, and does a run follow the rules that matter most. They run with `claude plugin eval`, each run a real Claude session on the operator's account, so they cost money and CI doesn't run them. How to run and write them: "Running evals" and "Writing evals" in the repository's `AGENTS.md`.

## Cases

| Case | Checks | Tags | Threshold |
|---|---|---|---|

None yet: Phase 1 of [the plan](../../../../docs/skill_execution_plan.md) adds the first. Add a row with every case. A case passes at its threshold, never 0, so a suite summary can't count a failing case as passed.

## The fixture

Every case's `scaffold.sh` calls `_fixture/wiki.sh`, which builds the unit tests' fixture wiki (`make_wiki` in `../tests/helpers.py`) in the run's working directory: three tags, two saved sources and a link, and one narrative, committed on `mainline` with a repository-local identity, and a local bare `origin` beside it so a run can push without the network. A case then changes only what it needs. `test_eval_fixture` checks the script.

## Known limits

- **macOS and git.** With Apple's `git` (the Xcode command-line tools shim), `git` can't run inside the eval sandbox, so cases that need a branch fail there. Run them where `git` is a plain binary (Linux, or a non-Xcode `git` first on `PATH`), and say so in the pull request.
- **Variance.** One run can pass or fail by chance; for a decision, use three runs per case.
