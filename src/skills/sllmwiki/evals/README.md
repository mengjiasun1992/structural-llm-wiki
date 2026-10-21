# Behavior evals

Unit tests (`../tests/`) check the scripts. These evals check the skill's behavior: does a request reach the right workflow or step, and do runs follow the rules that matter most. They run with `claude plugin eval`, and each run is a real Claude session on the operator's account, so they cost money and CI doesn't run them.

How to run them and how to write a case: "Running evals" and "Writing evals" in the repository's `AGENTS.md`.

## Cases

| Case | Checks | Tags |
|---|---|---|

None yet: the first cases arrive with `init` (Phase 5 of `docs/skill_execution_plan.md`). Add a row here with every case.

## The fixture

Every case's `scaffold.sh` calls `_fixture/wiki.sh`, which builds the fixture wiki the unit tests use (`make_wiki` in `../tests/helpers.py`) in the run's working directory: a git repository on `mainline` with a repository-local identity, and a local bare `origin` beside it, so a run can push branches without the network. A case then changes only what it needs, for example by adding a source with an embedded instruction, or by removing the wiki. `test_eval_fixture` checks the script.

## Known limits

- **macOS and git.** With Apple's `git` (the Xcode command-line tools shim), `git` can't run inside the eval sandbox: it fails writing a cache under the system temp folder. Cases that need a git branch fail there; run them where `git` is a plain binary (Linux, or a non-Xcode `git` first on `PATH`), and note it in the pull request.
- **Variance.** A single run can pass or fail by chance. For a decision, use the default three runs per case.
