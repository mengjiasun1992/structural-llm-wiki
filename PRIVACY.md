# Privacy

The Structural LLM Wiki plugin (`sllmwiki`) runs in your coding agent, on your machine. Its authors run no server and collect nothing: no telemetry, no analytics, no accounts. Everything it writes goes into a git repository you own.

## What it reads

- **Your wiki repository**, and any repository or files you point it at.
- **Sources you ask about:** web pages, documents, papers and code. It requests them from where they're published and saves a copy in your wiki, or only a link when a copy isn't allowed.
- **Git history, for SMEs.** The SMEs step reads commit authors' names and email addresses, `git blame`, CODEOWNERS and review trailers in the repositories you name, to rank who knows an area.

## What it stores, and where

Everything is stored in your wiki repository, under your control:

- saved sources, narratives, tags and the generated pages;
- **SMEs:** the people chosen, each recorded by a handle when the evidence gives one, else a name (not an email address), with the evidence for each, on the topic's tag page. Anyone listed in `smes_exclude` in `sllmwiki/Config.toml` is never listed, and the book a release attaches never includes SMEs;
- personal data or secrets found in a source are left out of the saved copy, with a marker where they were.

Delete anything by deleting it from the repository; the git history keeps it until you rewrite that history.

## Where data goes

- **GitHub, through `git` and `gh`, in your own account:** pushing branches, opening pull requests, creating releases, and the wiki's GitHub Actions (its checks, and building the book at each release). GitHub's own terms and privacy statement apply.
- **The sites a source comes from**, which receive only the requests that fetch it.
- **Your coding agent and its model provider**, which see what the agent reads and writes, as with any work in your agent; their own terms apply. The plugin sends nothing to them itself.

Nothing goes anywhere else, and nothing is retained by the plugin's authors.

## Who it's for

The plugin isn't intended for users under 18.

## Questions

Open an issue at <https://github.com/mengjiasun1992/structural-llm-wiki/issues>.
