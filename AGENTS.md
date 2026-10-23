# AGENTS.md

This repository is the `sllmwiki` plugin: one Agent Skill (`src/skills/sllmwiki/`) with two workflows made of steps, and the deterministic scripts they run. These rules apply to any agent or person changing it. (The rules for working *in a wiki* are in each wiki's own `AGENTS.md`, which `init` writes.)

## Layout

- `src/skills/sllmwiki/`: the skill. `SKILL.md`; `workflows/` and `steps/` (instructions, read when they run); `scripts/` (the deterministic scripts, Python standard library only, one copy); `templates/` (narrative templates and what `init` installs: `wiki/` (the wiki's files) and the CI workflows); `tests/` (unit tests for the scripts, with a parallel runner).
- `evals/`: behavior evals for the skill, run with `claude plugin eval`; outside the skill, so they never ship with it (see `evals/README.md`).
- `src/commands/`: Claude Code commands, one per workflow and step.
- `src/actions/`: the GitHub actions a wiki's CI calls.
- `src/tools/`: development and CI tools outside the skill.
- `docs/`: the design doc, and proposals for larger changes.

`docs/structural_llm_wiki_design.md` describes the architecture and the decisions behind it. Read it before a change that touches the data model, the workflows or the review model.

## Rules

- **Prefer a deterministic script to an instruction.** Whenever a workflow, step, template or `SKILL.md` asks the agent to do mechanical work, anything that given the same files must always give the same result (counting, hashing, numbering, formatting, escaping, keeping YAML in sync, checking structure or syntax, building links or indexes), move it into a script with tests and have the instructions call the script. Instructions keep only judgment: choosing sources, grading relevance, writing and verifying narratives. When you add or review instructions, look for such work and propose the script, even if the change at hand doesn't need it yet.
- **Markdown renders the same on GitHub, in Obsidian, in mdBook and in Sphinx.** Everything the skill writes or checks (narratives, tag pages, the index, templates, the wiki's README) uses only the syntax the four render alike, as `lib/compat.py` defines it; see "Markdown compatibility" below.
- **Respect licenses and copyright.** Every source belongs to its authors. Never add behavior that copies, saves, shares or publishes content beyond what its license or terms allow, that gets around logins, paywalls, registration walls or anti-bot protection, or that otherwise exposes the owner or a wiki's users to legal risk. The source policy ("Source policy (enforced)" in `SKILL.md`, design doc §4.8) is the minimum. When a change touches what the skill fetches, saves, quotes or publishes, say in the pull request how it stays within the policy; when in doubt, keep a link instead of a copy and ask the owner.
- **Say each thing once.** Every rule, expectation and fact has one home, and other places point to it rather than restate it: `SKILL.md` for what all workflows and steps share, `templates/narratives/shared.md` for what all narratives share, a template's `guide.md` for its own style, the design doc for decisions and their reasons, this file for development. Before adding a rule, look for where it already lives. When you find the same expectation in several places, move it to the shared place and replace the copies with a pointer. Together with scripts over lectures, this keeps the skill concise, simple and easy to follow: an agent should get each instruction from one place, in as few words as do the job.
- **Every logic change comes with unit tests.** Any change to a script's behavior (in `src/skills/sllmwiki/scripts/` or `src/tools/`), whether a new feature, a bug fix or a changed rule, adds or updates tests in `src/skills/sllmwiki/tests/` in the same pull request. A bug fix adds a test that fails without the fix. A change to instructions only (`SKILL.md`, `workflows/`, `steps/`, templates' prose) needs no unit test, but behavior the instructions rely on does.
- **Coverage stays at 95% or above.** CI measures line coverage of `src/skills/sllmwiki/scripts/` and fails below 95% (`fail_under` in `pyproject.toml`). Don't lower the threshold, and don't exclude code from coverage to pass it; test it instead.
- **Tests are standard library only.** Use `unittest`; don't add test dependencies beyond `coverage` (CI-only, pinned). Tests never use the network: serve fixtures from a local `http.server`. They never write outside a temporary directory.
- **The scripts stay standard library only** and run on Python 3.9 or later. Run the tests on 3.9 (`/usr/bin/python3` on macOS) as well as the latest 3 before pushing.
- **Lint must pass:** ruff (rules in `pyproject.toml`) and shellcheck, as in CI.
- **Keep the docs in step:** a script's interface lives in its `--help`; when it changes, update the instructions that call it (`test_instructions` checks every script and option they name). When behavior a design decision describes changes, update `docs/structural_llm_wiki_design.md`. A larger change starts as a proposal in `docs/`.
- **Instructions stay within their word budgets** (design doc §9, checked by `test_instructions`): every run pays for them in tokens. To make room, move a rule to a script or to its one home; raise a budget only with the reason in the pull request.
- **Behavior changes get an eval check.** A change to `SKILL.md` (especially its `description`), a workflow, a step, a command or a narrative template can change how requests are routed or how runs behave, and unit tests can't see that. For such a change, run the smoke evals before opening the pull request, and add or update a case when you add behavior or fix a behavior bug. A behavior bug fix adds a case (or a grader) that fails without the fix, like a unit test for a script bug.
- **Evals cost money; keep them cheap and say what you ran.** Each eval run is a real Claude session on the operator's account, so CI doesn't run them. Always pass `--max-cost-usd`, and use `--runs 1 --ablation none` while iterating. In the pull request, say which cases you ran, with which model, the results and the cost. If you didn't run them, say so and why.
- **Don't weaken a grader to make a case pass.** When a case fails, read the trace (`--keep-temp`) to find out whether the skill or the grader is wrong. Fix the skill if it misbehaved; change a grader only when it checks the wrong thing, and say why in the pull request.
- **One pull request per change,** against `mainline`, from a branch made from the up-to-date `mainline`; the owner merges. Describe what changed, why, and how it was tested.
- **Commit messages** start with a short imperative subject, and their body quotes the owner's request that started the change, verbatim, in a `Prompt:` block. Check the staged files before committing; never commit eval results or other tool output.
- **A release bumps two places together:** `version` in `.claude-plugin/plugin.json` and the `@v<version>` the wiki CI templates (`src/skills/sllmwiki/templates/*.yml`) call the actions at, so wikis that rerun `init` after updating the plugin move to it. Merge that, then tag the merge commit `v<version>` and publish the release. Bump only when the owner asks for a release.

## Markdown compatibility

A wiki is read on GitHub, opened as an Obsidian vault, and built as a book with mdBook or with Sphinx and MyST-Parser, so its markdown has to mean the same thing in all four. `lib/compat.py` is the one definition of that common syntax, and every check and writer uses it: `narrative-format` and `obsidian-check` report what breaks it, and `escape()` (through `narrative-format --fix-style`, the tag pages and the index) fixes what can be fixed mechanically.

- **What's allowed:** markdown links with paths relative to the linking file and spaces written `%20`, to files rather than folders; GitHub's five alerts as the only callouts; `$$` math only where GitHub renders it unchanged; escaped citation brackets (`[\[3\]](…)`); URLs as links, never bare; headings that don't skip a level.
- **What's not:** wikilinks and embeds, highlights, `%%` comments, block IDs, inline `#tags`, emoji shortcodes, MyST directives, roles and targets, and anything a book reads as its own syntax unless escaped: a `%` starting a line (a MyST comment), `{…}` ending a heading (mdBook's heading attributes), `$` before a number (MyST math), single tildes (strikethrough on GitHub and mdBook only), `{{#include …}}` (expanded by mdBook even in code).
- **Verify against the renderers before changing a rule.** A rule records how each renderer actually behaves, not how its docs describe it. Check every new or changed rule in all four, at pinned versions: GitHub through the contents API (`Accept: application/vnd.github.html`, not the markdown API, which renders differently), Obsidian, mdBook 0.5.4 and Sphinx 9.1 with MyST-Parser 5.1. Say in the pull request what you rendered and what each showed, and when a renderer's version changes, recheck the rules it affects.
- **Every rule is tested from the start.** A rule doesn't land without its tests in `tests/test_compat.py`, written as a table of cases, each with:
  - a line that breaks the rule, reported with its code and line number, and a line that follows it, not reported;
  - the same text inside a fenced code block and inside a code span, not reported (except `{{#include …}}`, which mdBook expands even in code);
  - YAML front matter and an indented code block, not mistaken for markdown;
  - when the rule has a fix, `escape()`'s output, its count, a second run that changes nothing, and the escaped text no longer reported;
  - a comment naming the renderers and versions the behavior was checked in.
  A false positive is a bug: fix it with a test that fails without the fix, like any other.
- **Sources are exempt.** Files in a wiki's sources folder are verbatim copies and are never checked or escaped.

## Running the checks

```bash
# unit tests with coverage (CI fails below 95%)
python3 -m pip install "coverage[toml]==7.6.10"
python3 src/skills/sllmwiki/tests/run.py --coverage    # one process per test module, in parallel
/usr/bin/python3 src/skills/sllmwiki/tests/run.py      # the same on Python 3.9

# lint
python3 -m pip install ruff==0.8.4 shellcheck-py==0.10.0.1
ruff check src/skills/sllmwiki/scripts src/skills/sllmwiki/tests src/tools
shellcheck src/skills/sllmwiki/scripts/*.sh evals/_fixture/*.sh evals/*/scaffold.sh

# docs and plugin
npx --yes markdownlint-cli2@0.13.0 "**/*.md"
claude plugin validate .
```

## Running evals

The cases are in `evals/` at the repository's root, where `claude plugin eval` looks: outside the skill, so they never ship with it. `evals/README.md` lists them. Typical commands, from the repository root:

```bash
# smoke cases (routing, query, safety, not-a-wiki): about $1 with Sonnet
claude plugin eval . --tag smoke --scaffold --allow-tools Bash \
  --runs 1 --ablation none --model sonnet --max-cost-usd 5 -j 8

# one case, keeping its sandbox and trace to see what the agent did
claude plugin eval . --case <name> --scaffold --allow-tools Bash Write Edit \
  --runs 1 --ablation none --max-cost-usd 3 -j 8 --keep-temp

# before a release: every case, 3 runs each, with the no-plugin baseline
claude plugin eval . --scaffold --allow-tools Bash Write Edit --max-cost-usd 20 -j 8
```

- `--scaffold` is required: every case builds its fixture wiki with a scaffold script.
- Results go to `evals/results/`, which is git-ignored; never commit them.
- On macOS with Apple's `git`, `git` can't run inside the eval sandbox, so cases that need git (`init-new`, `narrative-publish`, `build-small`, the ingest cases) fail there. Run those on Linux instead: the **Evals** workflow (Actions → Evals → Run workflow) takes a tag or a case, the runs per case, a model and a cost ceiling, and keeps the report as an artifact. It needs an `ANTHROPIC_API_KEY` repository secret, costs money per run, and runs only when started by hand. Before a release, run every case three times there (`all`, 3 runs).

## Writing evals

- **One folder per case** in `evals/`: `prompt.md` (settings in the frontmatter: `max_turns`, `runs`, `tags`, `allowed_tools`), `case.yaml` (`context.scaffold_script`), `scaffold.sh`, and `graders/*.md`, one grader per file. Grader fields must match the CLI's schema; `claude plugin eval` refuses a case file it can't load and names the bad key.
- **Fixture:** `scaffold.sh` calls `../_fixture/wiki.sh`, which builds the unit tests' fixture wiki (`src/skills/sllmwiki/tests/helpers.py`) as a git repo with a local `origin` in the run's working directory, then changes only what the case needs. When a case needs new fixture content, add it to `src/skills/sllmwiki/tests/helpers.py`, so unit tests and evals keep sharing one fixture.
- **Prefer graders that check behavior over wording:**
  - which file was read, or which command ran (`tool_used` with `input_match`);
  - what must never happen (`tool_used` with `min: 0, max: 0`, for example no Write, no `git push`);
  - which files exist (`file_exists`).
  These are deterministic and free. Use an `llm` grader only for judgments the deterministic ones can't make, such as whether an answer is grounded. Write its criteria to say exactly what passes and what fails, including what not to count. It reads a produced file with `focus: {source: file, path: …}`.
- **Tags:** `smoke` for cheap cases that should pass on every behavior change, `full` for long end-to-end cases; add a topic tag (`routing`, `query`, `safety`, …) so a run can select by area.
- **Keep the case table in `evals/README.md` current** when you add or change a case.

## Writing scripts

The scripts take over mechanical work that, given the same files, must always give the same result (sizes, hashes, keeping the YAML files in sync, heading numbers, branches and PRs). Judgment stays with the agent: choosing sources, grading relevance, writing and verifying narratives. Planned scripts are tracked as GitHub issues.

- **Scripts report; the agent decides.** A check lists findings and exits non-zero. It never rewrites content on its own, except through an explicit `--fix-*` flag for purely mechanical bookkeeping.
- **No runtime dependencies:** Python 3.9 or later, standard library only. YAML is read with a reader in `scripts/lib/` that covers the subset the wiki files use and fails loudly on anything else, so a file is never misread silently. YAML is written with targeted line edits, never re-serialized, so comments and ordering survive.
- **One copy, inside the skill** (`src/skills/sllmwiki/scripts/`): every installer copies whole skill folders, and a skill can rely only on files inside its own folder.
- **Machine-readable output:** human-readable findings by default, JSON with `--json`.

## Writing tests

- The tests live in `src/skills/sllmwiki/tests/`, one file per script or module: `test_<module>.py`.
- `run.py` runs each test module in its own process, in parallel, so a module must not depend on another's state or on running alone: use a fresh temporary directory and a free port, never fixed paths or ports.
- A shared `helpers.py` puts the scripts on the import path, loads a command script as a module so its `main()` runs in-process and counts toward coverage, captures its output and exit code, and builds small fixture wikis in a temporary directory.
- Test behavior through the public functions and the commands' output and exit codes, not private details, so refactors don't break tests needlessly.
