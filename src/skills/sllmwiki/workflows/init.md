# init: set up a wiki repository

A wiki is a git repository of its own. Run this in the repository that will hold it.

1. **A rerun on a wiki** (it has `sllmwiki/tags/tags.yaml`) is a run like any other, one pull request: start it with `publish.py start init-refresh --title "Bring the wiki up to date" --prompt "<the user's request, verbatim>"`. When `start` refuses because the tree isn't clean, name the files to the owner and stop; never commit or move them.
2. Run `init.py --name <repository name>`. When it reports files that aren't a wiki's, tell the owner which, and ask whether to set the wiki up here anyway or in a new, empty repository. Pass `--force` only on their yes.
3. If the repository has no remote, offer to create one on GitHub (`gh repo create <name> --private --source . --push`), private unless the owner says otherwise; a public wiki keeps copies of openly licensed sources only.
4. If it has a remote, check that the local default branch matches the remote's (`git fetch` and compare); stop and tell the owner if it has diverged.
5. Commit:
   - **First setup:** `init.py --commit --prompt "<the user's request, verbatim>"`, which stages only what it wrote, then push the default branch if there's a remote.
   - **A rerun:** `publish.py summary init --json '{...}'` with what changed, `publish.py commit init --subject "Bring the wiki up to date"` and `publish.py pr`. Never push the default branch.

   If the wiki's CI then fails with "Unable to resolve action … repository not found", the plugin's repository is private and doesn't share its actions with this wiki's owner: say so.
6. Reply with what was created or updated, and how to start: `/sllmwiki:build "<a first question>"`. Mention the optional settings in `Config.toml`, including the Obsidian add-on.

Rerun after a plugin update: it refreshes the files it owns and keeps the wiki's own.
