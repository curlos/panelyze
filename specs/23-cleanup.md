# 23. Cleanup: folders and files that look unneeded

Related: [#14 folder structure](14-folder-structure.md) · [#15 format, lint and CI](15-format-lint-ci.md) · [#18 type-check fixes](18-type-check-fixes.md) · [#25 full code review](25-full-code-review.md)

**Nothing has been deleted. This is a list for the user to decide on.**

## 1. Summary
The repo folder takes about **21 GB on disk, and only about 1 MB of it is tracked code**. Almost all of the rest is git-ignored test output (17 GB), an old Python 3.10 venv (1.3 GB), an old app build (1.3 GB), and **two old git stashes holding about 600 MB of build files** inside `.git`. The "old scripts" (`copy_panels_to_one_level_directory.py`, `DrawBoxCoords.py`) turned out to be **still used by the app**, so they stay.

## 2. Is it doable?
Yes. Deleting ignored folders doesn't touch git history, and none of them are needed to run, test or build the app (they're all rebuilt when needed). Only the test output and the stashes need the user's OK, because they might hold something the user wants.

## 3. What's already true (checked 2026-11-19 with `du -sh`, `git check-ignore`, `git ls-files`, and `grep` over code, tests and docs)

| Path | Size | In git? | Referenced by | Verdict |
|---|---|---|---|---|
| `testing-output/` | **17 GB** (of which `outputs/One Piece (Official Colored)` is 13 GB) | Ignored | Only `.gitignore`, `.vscode/settings.json`, and package.json `dev --ignore-dirs`. No code or tests use it. | 🟡 **Ask user.** Old outputs from Dec 2024 to Jul 2025 (One Piece, Dragon Ball, Frieren, TTS/WPM tests, "medals", "soccer-trophies"). Delete, or move what's worth keeping to `~/Documents/Panelyze`. |
| `venv-py310-old/` | 1.3 GB | Ignored (`venv-*/`) | Only package.json `dev --ignore-dirs` | ✅ **Safe to delete.** Python 3.10.16 venv from Jan 2025. The app uses `venv/` (3.12). |
| `dist/` (`Panelyze/` 688 MB + `Panelyze.app` 690 MB) | 1.3 GB | Ignored | `build_mac_app.sh` writes it | ✅ **Safe to delete.** Built Nov 17, before spandrel/coremltools were added, so it's out of date. There's no zip, so nothing was released from it. `./build_mac_app.sh` rebuilds it. |
| `build-assets/pack/` | 199 MB | Ignored | `build_mac_app.sh` (deleted and rebuilt every build) | ✅ Safe to delete |
| `build-assets/waifu2x/` | 46 MB | Ignored | `build_mac_app.sh` (downloads it again if missing) | 🟢 Keep (saves a download per build). Deleting it is safe. |
| `build-assets/Panelyze.icns`, `.iconset/` | 0.6 MB | Ignored | Rebuilt every build | Keep (tiny) |
| `.git` loose objects: **2 stashes** "BUNCH OF SHIT I CHANGED TO TRY TO GET THIS TO WORK…" (Aug 2025) | about **600 MB** of the 647 MB `.git` (they hold `dist/main` 188 MB ×2, `build/main/main.pkg` 187 MB, …) | Local only (not on GitHub) | Nothing | 🟡 **Ask user.** `git stash drop` ×2, then `git gc --prune=now` would shrink `.git` from 647 MB to a few MB. It's not urgent. Not reversible. |
| `__pycache__/` (root 276 KB, `gui_classes/` 320 KB, `tests/` 632 KB, `magi_model/` 92 KB) | 1.3 MB | Ignored | Python makes them | ✅ Safe to delete any time. Do it after #14, so stale `.pyc` files can't hide a missed import. |
| `.pytest_cache/` | 36 KB | Ignored | pytest makes it | ✅ Safe |
| `.DS_Store` (root 16 KB, and in `test-chapter-cache/`, `testing-output/`) | KBs | Ignored | macOS makes them | ✅ Safe (they come back) |
| `storage/` (`data/`, `temp/`, both empty) | 0 B | Ignored | **`flet run` makes it** (`flet_cli/commands/run.py:196-199` sets `FLET_APP_STORAGE_DATA/TEMP`) | 🟢 Keep. It comes back every `npm run dev`. |
| `test-chapter-cache/` | 2.1 MB | Ignored | `tests/test_e2e.py`, DEVELOPING.md | 🟢 **Keep**: the cached Dragon Ball ch. 93 pages that the e2e tests reuse |
| `experiments/` (README + 1 Colab notebook) | 24 KB | **Tracked** | Only package.json `--ignore-dirs`. The README explains it. | 🟢 Keep (documented, tiny). Ruff and Pyright should exclude it (#15). |
| `magi_model/panels_fp16.safetensors` | 83 MB | Ignored | `magi.py` (built once), `build_mac_app.sh` | 🟢 **Keep.** Needed. It would take a 2 GB download to rebuild. |
| `copy_panels_to_one_level_directory.py` | 3 KB | Tracked | **`magi.py:19,698`** (used for grouped-by-page output), `tests/test_copy_panels.py` | 🟢 **Keep: still used.** It could be renamed later (#14). |
| `DrawBoxCoords.py` | 8 KB | Tracked | **`VideoCreatorFromImages.py:17,81`** (highlight text boxes), `tests/test_video.py` | 🟢 **Keep: still used** |
| `EmotionAnalyzer.py`, `SpeechTextParser.py` | 4–5 KB | Tracked | `TextToSpeech.py:305`, `VideoCreatorFromImages.py:16` | 🟢 Keep: used |
| `assets/no-face.png` | 34 KB | Tracked | `build_mac_app.sh` (app icon) | 🟢 Keep |
| `.env` | – | Ignored | `utils.utils_load_dotenv` (Azure key, region, endpoint), plus `NGROK_AUTH_TOKEN` (only for the unused Colab experiment) | 🟢 Keep. The `NGROK_AUTH_TOKEN` line could be removed (ask user). **It holds a real Azure key: never print it.** |
| `.envrc` | – | Ignored | direnv (`source ./venv/bin/activate`) | 🟢 Keep (handy) |
| `.gitignore` lines `outputs`, `*.wav`, `build/`, `*.spec`, `*.app` | – | – | Nothing creates `outputs/`, `*.wav` or `build/` in the root now (`flet pack` runs inside `build-assets/pack`) | 🟢 Keep. They're harmless guards, and cheap protection if an old script runs. |
| `benchmarks/images/`, `benchmarks/panel-cropping.md`, `tests/test_panel_growth.py` | – | **Untracked (new work)** | – | 🟢 Not junk: the current uncommitted session's work. The user decides when to commit it. |

**Outside the repo (for completeness, also not deleted):**

| Path | Size | Verdict |
|---|---|---|
| `~/Documents/Panelyze/` test folders (Panel Crop Limits 25 ch 4.3 GB and 7 ch 1.8 GB, Upscale Comparison Shachou 1.3 GB and One Piece 895 MB, Best Upscale Test 585 MB, Speed Tests 387 MB, Panel Crop Comparison 448 MB, Pipeline 208 MB, MangaDex Downloads 465 MB, Videos 56 MB) | about 10 GB | ✅ **User decision (2026-11-21): delete them.** Each spec downloads what it needs again into the spec's own folder (`~/Documents/Panelyze/<worktree-folder>/`) (the specs that used these folders now say so). `Speed Test 2…` was the only copy of the Shachou ch. 3 pages; it can be downloaded again from `https://mangadex.org/chapter/f54fb875-d732-42d2-9926-b25767ee4cda`. |
| `~/Library/Application Support/Panelyze/upscale-models` | 314 MB | 🟢 Keep (the "Best" models) |
| `~/.cache/huggingface/hub/models--ragavsachdeva--magiv2` | 1.9 GB | 🟢 Keep (full Magi, for the video text) |

## 4. Recommended approach + rejected alternatives
| Option | Verdict | Why |
|---|---|---|
| **Delete the ✅ items now (about 2.8 GB). Ask about `testing-output/`, the stashes and the `~/Documents` test folders.** | ✅ | It frees space with zero risk, and the user's own files stay their call |
| Delete everything ignored (`git clean -fdX`) | ❌ | It would also delete `venv/`, the Magi weights, `test-chapter-cache/` and `.env` |
| Rewrite git history to shrink `.git` | ❌ Not needed | The big blobs are only in 2 local stashes, not in the pushed history. Dropping them and running `gc` is enough. |
| Move `testing-output/` to an external drive | 🟡 | A fine middle path if the user wants to keep old outputs |

## 5. Files to change + what's reused
| File | Change |
|---|---|
| `package.json` `dev` script | After deleting: drop `venv-py310-old` (and `testing-output`, if deleted) from `--ignore-dirs`. Optional, since missing folders are harmless. |
| `.vscode/settings.json` | Optional: remove the matching excludes. They're harmless if left. |
| No code changes | – |

## 6. Steps
- [ ] User answers the open questions below.
- [ ] `rm -rf venv-py310-old dist build-assets/pack` (about 2.8 GB).
- [ ] `find . -name __pycache__ -not -path "./venv/*" -exec rm -rf {} +` and `rm -rf .pytest_cache` (best after #14).
- [ ] If OK'd: delete or move `testing-output/` (17 GB).
- [ ] If OK'd: `git stash list` (check it's the same 2), `git stash drop` ×2, `git gc --prune=now` (`.git` goes from about 647 MB to a few MB).
- [ ] Delete the older `~/Documents/Panelyze` test folders (user OK'd on 2026-11-21; leave any spec's own folder that's still being reviewed). Keeping `Speed Test 2 - Shachou Ch 3 Full Pipeline` is optional.
- [ ] Optional: tidy `--ignore-dirs` in package.json.

## 7. How to test it
| Check | Expected |
|---|---|
| `npm run test` | 203 passed |
| `npm run self-test` | Passes |
| `npm run dev` | The app opens. `storage/` comes back, which is normal. |
| `npm run test:all` | The e2e tests still find `test-chapter-cache/` |
| `./build_mac_app.sh` (next time) | Rebuilds `dist/` and `build-assets/pack` |
| `du -sh .` | About 21 GB → about 1.2 GB if everything is OK'd (`venv/` is 865 MB of that) |
| `git status` | Unchanged (only ignored files were removed) |

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | Tiny: a few commands, no code |
| Value | Medium: about 20 GB freed. Faster `flet run -r` file watching, Spotlight and backups. Clearer folder. |
| Risk | Losing old outputs the user cares about. That's why `testing-output/` and the stashes are "ask". |
| Open question | Delete `testing-output/` (17 GB), move it, or keep part of it (e.g. `medals`, `soccer-trophies`, `videos`)? |
| Open question | Drop the 2 Aug-2025 stashes (about 600 MB, local only)? |
| Decided | Delete the older `~/Documents/Panelyze` test folders (user, 2026-11-21). Specs download what they need again. |
| Open question | Remove `NGROK_AUTH_TOKEN` from `.env` (only the unused Colab experiment needs it)? |

## 9. Sources
- Local checks: `du -sh`, `git check-ignore -v`, `git ls-files`, `git count-objects -vH`, `git rev-list --objects --all | git cat-file --batch-check` (the largest blobs), `git stash list`, and a `grep` for each name across code, tests, docs and configs
- Flet's `storage/` folder: `venv/lib/python3.12/site-packages/flet_cli/commands/run.py` lines 196–199, 304–305
