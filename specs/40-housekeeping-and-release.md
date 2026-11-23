# 40. Housekeeping and the first release

Combines [23 cleanup](23-cleanup.md), [12 name](12-project-name.md), [18 type-check fixes](18-type-check-fixes.md), [25 code review](25-full-code-review.md), [02 untested checks](02-untested-checks.md), [21 fresh machine test](21-fresh-machine-test.md) and [19 GitHub release](19-github-release-app.md) into one worktree (`housekeeping-and-release-specs`), with one plan, one review and one merge. Those specs keep the details. **Where this spec differs, this one is newer** (re-checked 2026-11-23).

Left for later: [14 folder structure](14-folder-structure.md) and [15 format, lint, CI](15-format-lint-ci.md) (both change almost every file), and 19's automatic release builds.

## 1. Summary
Get the app ready for its first public download:
1. Free disk space and tidy the repo (23).
2. Keep the name "Panelyze" and add a tagline (12).
3. Fix the type-checker errors (18), then review the whole app and fix the real bugs (25, a lighter version).
4. Build the Mac app, check the untested parts (02), and try it as a brand-new user (21).
5. Publish `v1.0.0` on GitHub (19).

## 2. Is it doable?
Yes. Only 18 and 25 change real code. The rest is commands, one README line, a ~15-line self-test check and manual checks. Rough time: 1–2 sessions for 18 + 25, plus about 2 hours of building and manual testing.

## 3. What's changed since the specs were written (checked 2026-11-23)
| Spec | Claim | Now |
|---|---|---|
| 23 | Sizes: `testing-output/` 17 GB, `venv-py310-old/` 1.3 GB, `dist/` 1.3 GB, `build-assets/pack/` 199 MB, 2 old stashes | ✅ Same. `.git` is 685 MB. |
| 23 | Delete the old `~/Documents/Panelyze` test folders | ✅ Already done: only `01-translate-japanese-pages/` is there |
| 23 | `NGROK_AUTH_TOKEN` line in `.env` | ⚠️ The user deleted `panelyze-main/.env` (2026-11-23): keys are typed in the app's Settings, not a file. But Azure voice still reads `.env` as a fallback (`TextToSpeech.py:265-269`), `tests/test_e2e.py` reads the Azure key from it, DEVELOPING.md mentions it, and CLAUDE.md's worktree setup copies it. Spec 01's `translate.py` also calls `utils_load_dotenv`, so that helper and `python-dotenv` stay until spec 01 drops them. |
| 12 | Update the git remote and the old `manga-panel-splitter` links | ⚠️ Mostly done already: the remote is `curlos/panelyze.git`, and only the old Colab notebook (`experiments/colab/`) still links to `manga-panel-splitter` |
| 12 | Tagline mentions "translate" | ⚠️ Translation (spec 01) isn't merged yet, so leave it out for now |
| 18 | 88 errors in the app code, 16 in the tests, 75 in `magi_model/` | ⚠️ Now **79 in the app code and 74 in the tests** (Pyright 1.1.414, standard mode). Most of the new test errors are from spec 17's tests. |
| 18 | Exclude `magi_model/` and `experiments/` | ⚠️ Also exclude **`comix_downloader/`** (copied third-party code from spec 17, 25 errors), and add it to `extraPaths` so its `src.*` imports resolve (22 "missing import" errors otherwise) |
| 18 | The config goes in #15's `pyproject.toml` | ⚠️ 15 is postponed: make a new `pyproject.toml` with only `[tool.pyright]`. 15 adds Ruff to it later. |
| 18 | "Do it after #15's formatting commit" | ⚠️ Not any more: 18 comes first, and 15's formatting later only re-wraps lines |
| 18 | Examples (`gui.py` `theme_mode = "dark"`, `ft.VerticalAlignment.CENTER` ×2, `Image.LANCZOS`, `Option(int)`, `os.startfile`, `tile_size` unbound) | ✅ All still there (line numbers moved). The `EmotionAnalyzer.py` errors are gone. New: `utils.py:160` `sum` of `int | None`, `JobView`/`MagiPanelByPanelView` attributes assigned on `PickInputAndOutputDirectories`, `download_from_comix.py:413`. |
| 25 | About 7,850 lines of app code and 3,590 of tests, 203 fast tests | ⚠️ Now **11,191 app lines, 8,300 test lines, 513 fast tests** (14.9 s) |
| 25 | 6 areas | ⚠️ Add a **downloaders** area: spec 17 added `download_from_comix.py`, `download_pages_from_url.py`, comic file import and `comix_downloader/`'s patches |
| 25 | After #15, #18 and #14 | ⚠️ Only after 18 now |
| 02 | The self-test has 5 checks, the new Best check makes 6 | ⚠️ It has **7** now (spec 17 added comic files and comix.to), so **8** with the Best check |
| 02 | `dist/Panelyze.app` is out of date (Nov 17) | ✅ Still the Nov 17 build. The build script now has `--collect-all=spandrel` and `--collect-all=coremltools`. |
| 02 | 27 GB free | ⚠️ **34 GB** free |
| 19 | Repo public, 0 releases, README's "Download for Mac" link goes nowhere | ✅ Still true (repo `curlos/panelyze`) |
| 21 | A new macOS user account for the app test | ⚠️ **Not doing it** (user, 2026-11-23): it needs an admin password, and Claude shouldn't make accounts. Instead: **one GitHub Actions workflow on a clean `macos-15` runner** (free for this public repo) that installs from `requirements.txt`, runs the fast tests and the self-test (which downloads the 2 GB Magi model for real), and builds and self-tests the app. It only needs to show that it works, even if slow (no GPU there). It doesn't need #15. The user still opens the draft zip once in Safari ("Open Anyway"). No Docker or VM. |

## 4. Recommended approach
| Part | Recommended | Not doing (why) |
|---|---|---|
| 23 Cleanup | Delete `venv-py310-old/`, `dist/`, `build-assets/pack/`, `testing-output/` and `__pycache__` folders, drop the 2 old stashes, `git gc --prune=now`. Stop using `.env`: Azure's key and region come only from Settings. | `git clean -fdX` (it would delete `venv/` and the Magi weights) |
| 12 Name | Keep "Panelyze", replace the README's first line with a tagline, fix the Colab link | A rename (about 150 places plus users' data folders) |
| 18 Types | Exclude the 3 copied folders, fix the app code to 0 errors as spec 18 says (the `SettingsBase` helper for `page`, the right enums, `| None`, guards), and **fix all 74 test errors too** (user, 2026-11-23: `assert x is not None`, `cast(...)` for the fakes) | `basic` mode, or turning rules off for the app code or the tests (hides real ones) |
| 25 Review | 7 read-only Claude agents (one per area), merge the findings, check each "high" one by hand, fix only confirmed bugs (a failing test first), then one full real run | CodeRabbit (needs a GitHub app and PRs; the agents cover it). Fixing style or "nice to have" findings. |
| 02 Checks | Add `check_best_upscaler_libraries` to `self_test.py`, build with `./build_mac_app.sh`, then the first-time download and no-Core-ML checks from scratch scripts | A "Use Core ML" setting (code for a one-off test) |
| 21 New machine | `.github/workflows/clean-mac-check.yml`, started by hand (`workflow_dispatch`). It's added in this branch, so it **first runs after the merge** (user's pick, 2026-11-23: GitHub only sees `main`). The release stays a draft until it passes. The user also opens the draft's zip once in Safari. | A new macOS user account (needs admin, user said no), pushing the branch to run it before the merge, a macOS VM (too much disk), Docker (no Mac GPU), running it on every push (a build takes a while; this is a release check) |
| 19 Release | After the merge: publish the draft as `v1.0.0`, unsigned, with the README's "Open Anyway" steps | Signing ($99/year), Intel, Windows (spec 32), CI builds (later, with 15) |

## 5. Files to change
| File | Change | From |
|---|---|---|
| `package.json` | Drop `venv-py310-old` (and `testing-output` if deleted) from `--ignore-dirs` | 23 |
| `README.md` | Tagline; maybe the `xattr` footnote for "Open Anyway" | 12, 19 |
| `TextToSpeech.py`, `tests/test_text_to_speech.py` | Azure's key and region only from Settings (drop the `.env` fallback and its test patch) | 23 |
| `tests/test_e2e.py` | The Azure e2e test takes the key from the `AZURE_SUBSCRIPTION_KEY` / `AZURE_REGION` environment variables, and skips without them | 23 |
| `DEVELOPING.md`, `HANDOFF.md` | Drop the `.env` mentions | 23 |
| `CLAUDE.md` (on `main`, done) | The worktree setup no longer copies `.env` | 23 |
| `experiments/colab/*.ipynb` | The one old `manga-panel-splitter` link | 12 |
| `pyproject.toml` (new) | `[tool.pyright]`: standard mode, `exclude` the 3 copied folders, `extraPaths = ["comix_downloader"]`, relaxed rules for `tests/` | 18 |
| About 30 app files | The type fixes listed in spec 18 §5 | 18 |
| Files the review names | Only the lines a confirmed bug needs, each with a test | 25 |
| `self_test.py` | `check_best_upscaler_libraries` (~15 lines) and a test for it | 02 |
| `.github/workflows/clean-mac-check.yml` (new, ~30 lines) | Manual trigger. `macos-15`, Python 3.12, `pip install -r requirements.txt`, `python -m pytest`, `python gui.py --self-test`, `./build_mac_app.sh` (which self-tests the built app). Upload the logs if it fails. | 21 |
| `DEVELOPING.md` | One line: what the workflow checks and how to start it | 21 |
| `build_mac_app.sh` | Only if the built app's version is still `0.0.0`: one `plutil` line | 19 |
| `specs/PROGRESS.md`, this spec | Tick the steps | — |

Disk-only (no git change): the deletions in 23, the build in `dist/`.

## 6. Steps
**A. Housekeeping (23, 12)**
- [x] User answers the open questions in 8.
- [ ] In `panelyze-main/` (disk only, nothing tracked changes): `rm -rf venv-py310-old dist build-assets/pack testing-output`. `git stash list` (check it's the same 2 "BUNCH OF SHIT…" entries), `git stash drop` ×2, `git gc --prune=now`. `__pycache__` folders in the worktree.
- [ ] Delete the worktree's `.env` copy. Drop the `.env` fallback for Azure, update its tests and the docs.
- [ ] `package.json` `--ignore-dirs`, README tagline, Colab link.

**B. Type fixes (18)**
- [ ] `pyproject.toml` with `[tool.pyright]`. Check: about 79 app errors and 74 test errors, 0 in the copied folders.
- [ ] Fix the wrong enums and `Option(str(...))` (check the upscale ratio and noise level are still remembered after a restart).
- [ ] `| None` signatures, variables set before `if`/loops, `JobView` return type and the attributes it sets on `PickInputAndOutputDirectories`.
- [ ] Guards or asserts with clear messages for the real `None` cases.
- [ ] The `SettingsBase` helper for `page`, used in the views.
- [ ] `Image.Resampling.LANCZOS`, then named `# pyright: ignore[rule]` on the library-type lines.
- [ ] The 74 test errors: `assert x is not None`, `cast(...)` for the fakes, a named ignore only where a test passes a wrong type on purpose.
- [ ] `npx --yes pyright@1.1.414 --pythonpath venv/bin/python` → 0 errors. Fast tests pass.

**C. Code review (25)**
- [ ] 7 read-only agents, one per area: Magi and panels · Upscale · Video and voice · Core and settings · Downloaders (MangaDex, comix.to, page URL, comic import, `comix_downloader` patches) · GUI and Pipeline · Tests. Each uses spec 25's "look especially at" list and writes a findings table.
- [ ] Merge and sort the findings; check every "high" one by reading the code or writing a failing test.
- [ ] Show the user the list. Fix the confirmed bugs, each with a test that failed first. Fast tests after each area, e2e (`-m e2e`) after Magi, upscale or video fixes.

**D. Build and check (02)**
- [ ] `check_best_upscaler_libraries` in `self_test.py` → `venv/bin/python gui.py --self-test` shows 8 PASS.
- [ ] `./build_mac_app.sh` in the worktree → `SELF-TEST PASSED` in the built app. Note the app and zip sizes and the `Info.plist` version.
- [ ] Open the built app: upscale 2–3 Dragon Ball ch. 93 panels with Fast, Better and Best (one color image too); the log says Core ML was used.
- [ ] Scratch script: first-time "Best" download into an empty scratch folder (592 MB). Then the no-Core-ML run (`janai.can_use_coreml = lambda: False`). Compare the images and times.

**E. New machine (21) and release (19)**
- [ ] Write `.github/workflows/clean-mac-check.yml` and the DEVELOPING.md line. Check the file's syntax locally (it can't run before the merge).
- [ ] Ask the user, then upload the zip to a **draft** release (`gh release create v1.0.0 --draft ...`, private until published).
- [ ] User downloads the zip from the draft in Safari, unzips, drags it to Applications, follows the README's "Open Anyway" steps, and checks the window opens and one short job runs.
- [ ] Review agent, then the user's review and the merge (CLAUDE.md "Finish").
- [ ] After the push: start the workflow (`gh workflow run clean-mac-check.yml`) and watch it. If it fails, fix in a small follow-up (with the user), rebuild, replace the draft's zip.
- [ ] When it passes, with the user's OK: publish the draft. Click the README's "Download for Mac" link and check it reaches the zip.

## 7. How to test it
| Check | Expected |
|---|---|
| `./venv/bin/python -m pytest` | 513+ passed |
| `-m e2e` | Pass |
| Pyright | 0 errors |
| `gui.py --self-test` (source and built app) | 8 PASS |
| Web-mode screenshots of every tab and Settings | No layout changes from the type fixes |
| Real Dragon Ball ch. 93 run (from source, saving to `~/Documents/Panelyze/housekeeping-and-release-specs/`) | Every tab and the Pipeline finish, no tracebacks in the log |
| `clean-mac-check` workflow on GitHub (after the merge) | Green: install, fast tests, self-test with the real Magi download, build and the built app's self-test |
| The draft zip from Safari | Opens after "Open Anyway", one short job runs |
| `du -sh panelyze-main` | About 21 GB → about 1.5 GB |

## 8. Size, risks, open questions
| | |
|---|---|
| Size | Medium overall: most of it is 18 + 25 |
| Risk | The review's fixes are the only part that can change behavior: tests first, small batches, the e2e and real run at the end |
| Risk | Spec 01 and Windows specs (10, 32) are still open. 18 touches about 30 files, so they may get small conflicts when they merge `main` |
| Risk | The release is public and hard to take back: published only after the merge, a green workflow and the user's OK |
| Risk | The workflow first runs after the merge, so a clean-machine problem shows up then (a small follow-up fix). The runner has no GPU, 7 GB RAM and 14 GB disk: slow, but enough. |

**Decided (user, 2026-11-23):**
1. Delete `testing-output/`.
2. Drop the 2 old git stashes.
3. No `.env`: keys are typed in the app's Settings.
4. Tagline: "Panelyze: a manga toolkit for your Mac. Download, split into panels, upscale and make videos."
5. Fix all 74 test type errors.
6. Version `v1.0.0`.
7. No test macOS account. A clean GitHub Actions Mac checks it instead, first run after the merge (see 3, spec 21 row).

**For spec 01:** `translate.py` still falls back to `.env` keys through `utils_load_dotenv`. Spec 01 should drop that fallback too; then `utils_load_dotenv` and `python-dotenv` can go.

## 9. Sources
The 7 specs above, plus today's checks: `du -sh`, `git stash list`, `git remote -v`, `git grep manga-panel-splitter`, Pyright 1.1.414 with a temporary config (scratchpad results), `self_test.py` `CHECKS`, `build_mac_app.sh`, `gh release list -R curlos/panelyze` (none), `df -h`.
