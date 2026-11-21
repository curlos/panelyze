1. First think through the problem, read the codebase for relevant files.
2. The plan should have a list of todo items that you can check off as you complete them.
3. Before you begin working, check in with me and I will verify the plan.
4. Then, begin working on the todo items, marking them as complete as you go.
5. Please every step of the way just give me a high level explanation of what changes you made
6. Make every task and code change you do as simple as possible. We want to avoid making any massive or complex changes. Every change should impact as little code as possible. Everything is about simplicity.
7. Finally, give me a summary of the changes you made and any other relevant information.
8. When I ask you to work on a spec in `specs/`, go into plan mode first and review it before changing anything. Check that what the spec says is still true in the code (files, functions, numbers) and that the plan makes sense. Tell me what's wrong or out of date, and fix the spec. Only start making changes after I confirm.
9. After I confirm a spec's plan, work through every step until the feature is done. Don't stop for review between steps. I review and test everything at the end, then give you more prompts.
10. When the changes are done (and the tests pass), launch a second Claude subagent to review them before reporting back to me. It reads the whole `git diff` and the spec, and looks for bugs, edge cases, anything that contradicts the spec, weak tests, and anything more complicated than it needs to be. It only reports; it doesn't edit. Then fix what it found, re-run the tests, and in your summary list each finding and what you did about it (fixed, or left as is and why). Don't ask me before doing this; it's part of finishing.

## Specs and git worktrees

Each spec in `specs/` is built in its own git worktree, so several specs can be worked on at once. Folders live side by side in `Github-Repos/panelyze/`:

- `panelyze-main/` is the `main` branch. Merging, pushing and cleanup happen here.
- `<id>-<spec-file-name>/` (for example `27-reading-direction-from-mangadex/`) is one spec on a branch with the same name.

Worktrees are local only. GitHub only sees `main`. Each one is about 5 MB because the big files are symlinks. Edit CLAUDE.md only on `main`. Write and edit specs (`specs/`, `ROADMAP.md`) on `main` too, so I can review and commit them there; worktrees are only for building a spec. If a spec needs fixing while it's being built (rule 8), make the fix in that spec's worktree.

### Life of a spec

1. **Create the worktree** (from `panelyze-main/`, with `SPEC` = the spec file name without `.md`):

   ```bash
   git worktree add ../$SPEC -b $SPEC
   cd ../$SPEC
   ln -s ../panelyze-main/venv venv
   ln -s ../../panelyze-main/magi_model/panels_fp16.safetensors magi_model/panels_fp16.safetensors
   ln -s ../panelyze-main/test-chapter-cache test-chapter-cache
   cp ../panelyze-main/.env ../panelyze-main/.envrc .
   ```

   Use `./venv/bin/python` (it works through the symlink). Run the fast tests (`python -m pytest`) to check the setup. If the worktree already exists and is old, run `git merge main` in it first.
2. **Work on it** in its own VS Code window, following the spec's steps and the rules below. Tick off the steps in the spec file as they're done.
3. **Test it**, saving everything to `~/Documents/Panelyze/<worktree-folder-name>/` (for example `~/Documents/Panelyze/27-reading-direction-from-mangadex/`) by passing that folder explicitly in tests and scripts. If an end-to-end test writes to the shared default folder instead, change it to use the spec's folder. This applies to every tool, including the Pipeline, which has its own output folder (scripts pass the spec's folder to it too). If I test by hand in the GUI, I set the output folder of each tab I use (MangaDex Downloader, Panel-By-Panel, Upscale Images, Images To Video and Pipeline) to the spec's folder and put them back afterwards. The app's saved settings and the default `~/Documents/Panelyze` are shared by every worktree. Don't run two worktrees' end-to-end tests at the same time.
4. **Review.** I review the changes in the Source Control panel and test them. Don't commit or push before I say the spec is finished.
5. **Finish** when I say it's finished (e.g. "we're done, merge it to main"). Do all of this in one go, without asking again:
   1. In the spec's worktree: run the fast tests, then commit everything (staged and unstaged) with a short message that says what the spec added.
   2. In `panelyze-main/` (with `git -C ../panelyze-main`): `git merge <branch>`, run the fast tests there, then `git push`.
   3. Clean up: `git worktree remove ../<folder>`, `git branch -d <branch>`, and delete the spec's output folder in `~/Documents/Panelyze/`.
   4. **Update the others:** in each other worktree, `git merge main` and re-run its tests.
   Stop and tell me instead of forcing anything if a merge has conflicts, tests fail, or a push is rejected. Never commit directly on `main` (only the merge), and never force-push. Commits show only me as the author: never add a "Co-Authored-By: Claude" line or any other Claude attribution to commit messages or pull requests.
6. Merge specs one at a time.

### Rules

- **Check where you are before editing.** Run `pwd` and `git branch --show-current` first. Only edit files inside the worktree for the spec being worked on; never touch another worktree's folder or `panelyze-main/` from a spec's session, except for the git commands in step 5 (Finish).
- **Never delete through the symlinks.** No `rm -rf venv/` or the like. Never use `--force` on `git worktree remove` or `-D` on `git branch` without asking. Remove worktrees only with `git worktree remove`.
- **The venv is shared.** A `pip install` or upgrade there changes every worktree and `main`. If a spec needs a new package, say so, add it to `requirements.txt` and `requirements-lock.txt`, and install it on purpose.
