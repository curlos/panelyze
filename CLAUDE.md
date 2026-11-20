1. First think through the problem, read the codebase for relevant files.
2. The plan should have a list of todo items that you can check off as you complete them.
3. Before you begin working, check in with me and I will verify the plan.
4. Then, begin working on the todo items, marking them as complete as you go.
5. Please every step of the way just give me a high level explanation of what changes you made
6. Make every task and code change you do as simple as possible. We want to avoid making any massive or complex changes. Every change should impact as little code as possible. Everything is about simplicity.
7. Finally, give me a summary of the changes you made and any other relevant information.

## Specs and git worktrees

Each spec in `specs/` is built in its own git worktree, so several specs can be worked on at once. Folders live side by side in `Github-Repos/panelyze/`:

- `panelyze-main/` is the `main` branch. Merging, pushing and cleanup happen here.
- `<id>-<spec-file-name>/` (for example `27-reading-direction-from-mangadex/`) is one spec on a branch with the same name.

Worktrees are local only. GitHub only sees `main`. Each one is about 5 MB because the big files are symlinks. Edit CLAUDE.md only on `main`.

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
3. **Test it**, saving everything to `~/Documents/Panelyze/<worktree-folder-name>/` (for example `~/Documents/Panelyze/27-reading-direction-from-mangadex/`) by passing that folder explicitly in tests and scripts. If an end-to-end test writes to the shared default folder instead, change it to use the spec's folder. If I test by hand in the GUI, I set the output folder to the spec's folder and put it back afterwards. The app's saved settings and the default `~/Documents/Panelyze` are shared by every worktree. Don't run two worktrees' end-to-end tests at the same time.
4. **Review and commit.** I review the changes in the Source Control panel and commit and push with the VS Code buttons. Never commit or push unless I ask.
5. **Finish** when I ask: from `panelyze-main/`, run `git merge <branch>`, then `git worktree remove ../<folder>` and `git branch -d <branch>`, and delete the spec's output folder in `~/Documents/Panelyze/`.
6. **Update the others.** Merge specs one at a time. After merging one, run `git merge main` in each other worktree and re-run its tests.

### Rules

- **Check where you are before editing.** Run `pwd` and `git branch --show-current` first. Only edit files inside the worktree for the spec being worked on; never touch another worktree's folder or `panelyze-main/` from a spec's session.
- **Never delete through the symlinks.** No `rm -rf venv/` or the like. Never use `--force` on `git worktree remove` or `-D` on `git branch` without asking. Remove worktrees only with `git worktree remove`.
- **The venv is shared.** A `pip install` or upgrade there changes every worktree and `main`. If a spec needs a new package, say so, add it to `requirements.txt` and `requirements-lock.txt`, and install it on purpose.
