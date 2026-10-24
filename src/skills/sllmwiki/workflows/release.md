# release: a release of the wiki, with its book attached

A release is a dated snapshot of the wiki on GitHub. The wiki's release workflow builds the book in the formats `Config.toml`'s `[structural-llm-wiki-release]` turns on and attaches the files. A release changes no file in the wiki and isn't a pull request. `release.py` does every mechanical step; you review the notes and report.

## A preview

When the owner asks for a preview, run `release.py preview` from the branch to preview, pushed first, and reply with the run's link and its artifact. Nothing is released. Stop there.

## A release

1. Run `release.py plan`. When it refuses:
   - **The default branch's checks failed or haven't finished:** name them, and stop. Release anyway (`release.py plan --anyway`) only when the owner said so, in this request or in reply.
   - **The release workflow isn't installed:** offer to rerun `workflows/init.md`, then stop.
   - **No GitHub remote, or `gh` isn't signed in:** say so, and stop.
2. Review the notes it drafted, in `.git/sllmwiki/release/notes.md`. They come from the manifests, so the facts are right. Read them as the release page's reader will: fix wording that is unclear or isn't in the wiki's language, and keep them short. Add nothing the notes' lists and the wiki don't support. Edit the file in place.
3. When no book format is on, the release has notes and no files: say so, and say how to turn one on (a `Config.toml` change, in a pull request). Release only if the owner still wants it.
4. Run `release.py create`, then `release.py wait`.
5. Reply with the version, the release's link, each file with its size, and the notes' Known issues, if any. If the build failed, say what failed and link the run.

Never delete or edit a published release, and never move its tag; a fix is the next release.
