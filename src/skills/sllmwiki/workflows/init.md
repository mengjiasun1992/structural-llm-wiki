# init: set up a wiki repository

A wiki is a git repository of its own. Run this in the repository that will hold it.

1. Run `init.py --name <repository name>`. When it reports files that aren't a wiki's, tell the owner which, and ask whether to set the wiki up here anyway or in a new, empty repository. Pass `--force` only on their yes.
2. If the repository has no remote, offer to create one on GitHub (`gh repo create <name> --private --source . --push`), private unless the owner says otherwise; a public wiki keeps copies of openly licensed sources only.
3. If it has a remote, check that the local default branch matches the remote's (`git fetch` and compare); stop and tell the owner if it has diverged.
4. Commit: `init.py --commit --prompt "<the user's request, verbatim>"`. A rerun commits only what changed. Push the default branch if there's a remote.
5. Reply with what was created or updated, and how to start: `/sllmwiki:build "<a first question>"`. Mention the optional settings in `Config.toml`, including the Obsidian add-on.

Rerun after a plugin update: it refreshes the files it owns and keeps the wiki's own.
