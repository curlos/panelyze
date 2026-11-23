# 25. Full code review, safe bug fixes, then an end-to-end test of the whole app

> **Being built as part of [spec 40](40-housekeeping-and-release.md)** (2026-11-23). Where they differ, spec 40 is newer.

Related: [#14 folder structure](14-folder-structure.md) · [#15 format, lint and CI](15-format-lint-ci.md) · [#18 type-check fixes](18-type-check-fixes.md) · [#23 cleanup](23-cleanup.md)

## 1. Summary
Review the whole app (about 7,850 lines of app code plus 3,590 of tests) for bugs, fix them in small checked batches, then test everything for real: fast tests, e2e tests, self-test, web-mode screenshots, and a real Dragon Ball ch. 93 run from MangaDex through every tab and the Pipeline.

Recommended:
- **Claude subagents, one per area**, as the main review.
- **CodeRabbit** (free for public repos) as a second opinion on the fix PRs.
- Order: **#15 formatting first, then #18 types, then #14 folders, then this review**, so the review sees real issues instead of style noise.

## 2. Is it doable?
Yes. The code is split into clear areas, there are 203 fast tests plus 9 e2e tests and a self-test as a safety net, and the repo is public (so CodeRabbit is free).

## 3. What's already true (checked 2026-11-19)
| Fact | Detail |
|---|---|
| Code size | Magi/upscale 1,200 lines (`magi.py` 737, `janai.py` 270, `waifu2x.py`, `copy_panels…`). Video/TTS 1,531 (`VideoCreatorFromImages.py` 781, `TextToSpeech.py` 348, `DrawBoxCoords`, `SpeechTextParser`, `EmotionAnalyzer`). Core 1,210 (`utils.py` 505, `default_settings`, `download_from_mangadex`, `self_test`, `gui.py`). GUI 3,907 (23 files in `gui_classes/`). Tests 3,588. |
| Not reviewed | `magi_model/` (vendored, kept identical to upstream) and `experiments/` |
| Safety net | `pytest`: 203 fast tests, 9.2 s. `-m e2e`: 9 real-tool tests, about 2 min (HANDOFF). `gui.py --self-test`. |
| Lint signal so far | Ruff (classic rules + bugbear): 1× E712, 9× `zip()` without `strict=`. No unused or undefined names (#15). |
| Type signal so far | 88 Pyright errors, about 20 real (#18) |
| Web-mode UI check | Works: serve with `ft.app(target=gui.GUI, view=None, port=8577)` from a scratch wrapper, and screenshot with `uv run --with playwright` (needs `fastapi==0.115.6`, already pinned). Use the shortcuts Ctrl+1..5 and Ctrl+Comma to switch tabs. Phone check at 390×760. |
| Test chapter | Dragon Ball ch. 93: `https://mangadex.org/chapter/ac33cc50-a1b2-49b0-a388-0d0ee4ebce18/14`. The e2e tests fetch only pages 1–3 and cache them in `test-chapter-cache/`. |
| CodeRabbit (pricing page, Nov 2026) | **Public repos: free reviews "forever", no setup.** Paid plans per user per month: Essentials $30 ($24 yearly), Team $60 ($48), Advanced $90 ($72). The free tier's per-hour limits for public repos aren't listed. |
| CodeRabbit's scope | It reviews **PR diffs and local changes (CLI)**, using the whole codebase as context. It doesn't do an on-demand "review the whole repo" (third-party sources, not confirmed by CodeRabbit's docs). |
| Repo visibility | `curlos/manga-panel-splitter` is **public** |

## 4. Recommended approach + rejected alternatives
**Phase A: Claude subagents review by area (read-only), each giving a findings table. Phase B: fix in small batches, one PR per area, each reviewed by CodeRabbit. Phase C: full end-to-end test.**

Area split (about 1,200–2,000 lines each, so each agent can read every line):

| Agent | Area | Files | Look especially at |
|---|---|---|---|
| 1 | Magi and panels | `magi.py`, `copy_panels_to_one_level_directory.py` | GPU→CPU fallback, batch splitting, panel growth and reading order, the 7 `zip()` calls with no length check |
| 2 | Upscale | `janai.py`, `waifu2x.py`, `gui_classes/UpscaleImagesView.py`, `SettingsUpscaleImages.py` | Model download and zip handling, hard-link temp folders, the 4K cap, waifu2x "exit 0 on failure" |
| 3 | Video and voice | `VideoCreatorFromImages.py`, `TextToSpeech.py`, `SpeechTextParser.py`, `EmotionAnalyzer.py`, `DrawBoxCoords.py`, `ImagesToVideoView.py`, `SettingsImagesToVideo.py`, `TextToSpeechAzure.py`, `HighlightTextBoxesInImages.py` | The 4-thread voice-over (locks, stop event), `full_output_directory=None`, Azure `None` results |
| 4 | Core, downloader, settings | `utils.py`, `default_settings.py`, `download_from_mangadex.py`, `self_test.py`, `gui.py` | Subprocess and `ProcessManager`, output-path overlap checks (never overwrite input), `.cbz` writing, `--run-mangadex` in the packaged app |
| 5 | GUI and Pipeline | the rest of `gui_classes/` (`PipelineView`, `JobView`, `PickInputAndOutputDirectories`, `AppBar`, `TerminalOutput`, `ProgressPanel`, `AppOutput`, …) | Running only one job at a time, cancel, `control.page == None`, `rmtree` of step folders, filling in the next tab's input |
| 6 | Tests | `tests/` | Tests that can't fail, missing cases for the bugs found by agents 1–5 |

Each agent writes a table: file:line · what's wrong · how sure (high/med/low) · how bad · the smallest fix · a test that would catch it.

| Option | Verdict | Why |
|---|---|---|
| **Claude subagents by area + CodeRabbit on the fix PRs** | ✅ | Agents can read the whole codebase now, for $0 extra. CodeRabbit is free here and gives an independent second opinion on each fix. |
| CodeRabbit alone, using an "everything" PR (an empty orphan branch as the base, so the whole repo is the diff) | 🟡 Optional extra | A known workaround. It may hit file or size limits per review (not confirmed). It's noisy without the area focus. |
| CodeRabbit CLI on the working tree | 🟡 | It only reviews uncommitted changes. Good for checking the fixes before commit, not for the first review. |
| One big Claude review of everything | ❌ | It's too much for one pass, and it misses details |
| The built-in `/code-review` skill on a diff | 🟡 | Good for reviewing each fix batch before the user commits |
| Review before #15 and #18 | ❌ | About 1,300 lines of style changes and 88 type errors would bury the real findings. Agents would waste effort on things the tools find for free. |
| Codacy or other whole-repo scanners | ❌ for now | Another account and mostly rule-based findings that overlap Ruff and Pyright |

**Recommended order across the specs:**

| Order | Spec | Why this position |
|---|---|---|
| 1 | #23 cleanup (the ✅ items only) | Frees about 2.8 GB, and stale `__pycache__` folders can't hide problems |
| 2 | #15 format + lint + CI | Turns style noise into one commit. CI then guards everything after it. |
| 3 | #18 type fixes | Fixes about 20 small real issues. CI type check becomes blocking. |
| 4 | #14 folder move | A mechanical move while the code is clean and checked (the review then uses the final paths) |
| 5 | #25 review → fixes → full E2E | Reviews the final layout, with all automated checks green |

## 5. Files to change + what's reused
| What | Where |
|---|---|
| Findings | One table per area. The user decides whether they live in chat or in a scratch file (they don't go in the repo, unless the user wants a `specs/25-findings.md`). |
| Fixes | Only the lines a finding names. Each fix comes with a test in the matching `tests/test_*.py`. |
| Existing helpers to reuse | `tests/fake_gui.py` (`make_gui`, `fake_event`, `FakeClientStorage`, `get_all_controls`). `tests/conftest.py` (blocks `open_directory`, so no Finder windows). `self_test.run_self_test`. The e2e markers `needs_internet` and `needs_waifu2x` in `tests/test_e2e.py`. |
| CodeRabbit | Install the GitHub app on the public repo. Optional `.coderabbit.yaml` with `path_filters: ["!magi_model/**", "!experiments/**", "!benchmarks/**"]`. |

## 6. Steps
**Phase A: review (read-only)**
- [ ] #15 and #18 are done (or at least #15's formatting commit), and `git status` is clean.
- [ ] Start the 6 area agents (read-only), each with this spec's "look especially at" list.
- [ ] Merge the findings into one table, remove duplicates, and sort by how bad × how sure.
- [ ] Check every "high" finding by hand (read the code, or write a failing test) before calling it a bug.
- [ ] The user picks which findings to fix.

**Phase B: fix safely**
- [ ] One area per batch. For each bug: **first a failing test, then the smallest fix, then all fast tests.**
- [ ] After each batch: `npm run test`, `uvx ruff check .`, `npx pyright` (all green), `npm run self-test`.
- [ ] The user commits each batch. Optionally open a PR, so CodeRabbit (free) reviews it. Answer or fix its comments.
- [ ] Batches that touch Magi, upscaling or video also run `npm run test:all` (e2e).

**Phase C: whole-app test**
- [ ] `npm run test` → 203+ passed. `npm run test:all` → 9 e2e passed.
- [ ] `npm run self-test` → passes.
- [ ] Web mode: serve headless on port 8577. Playwright screenshots of all 5 tabs and Settings at 1280×800 and 390×760. Compare with screenshots taken before the review.
- [ ] Real run in the desktop app (`npm run run`) on **Dragon Ball ch. 93** from MangaDex, with output in a new `~/Documents/Panelyze/Review E2E - Dragon Ball Ch 93` folder:
  - [ ] MangaDex Downloader → the pages saved under `<manga title>/Vol. … Ch. 93 …/`
  - [ ] Panel-By-Panel → panels (and a `.cbz` if turned on)
  - [ ] Upscale with Fast, then Best → images bigger, B&W saved as grayscale
  - [ ] Images To Video with edge-tts → an mp4 with a voice-over
  - [ ] Pipeline with all steps → numbered step folders, "Pipeline finished!"
  - [ ] Record the times per step in a table (compare with benchmarks/).
- [ ] Optional: `./build_mac_app.sh` (also closes the ROADMAP #2 "not tested yet" item).
- [ ] Close any Finder windows that opened, or check the tests blocked them.

## 7. How to test it
| Check | Pass |
|---|---|
| Every fixed bug | Has a test that failed before the fix and passes after it |
| Fast tests, Ruff, Pyright, CI | All green after every batch |
| e2e + self-test | Pass at the end |
| Screenshots | No layout changes that weren't intended |
| Real Dragon Ball ch. 93 run | Every tab and the Pipeline finish with no errors in Terminal Output. The log `~/Library/Logs/Panelyze/panelyze.log` has no tracebacks. |

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | Large overall. Review: 6 agents (one sitting). Fixes: depends on the findings, roughly 1–3 sessions. Full E2E: about 1 hour, including the Best upscale and the video. |
| Value | High: finds hidden bugs before whole-series runs (ROADMAP #3), and gives proof that everything works end to end |
| Risk: false positives | Agents and CodeRabbit can be wrong. Needing a failing test before each fix filters those out. |
| Risk: fixes changing behavior | Small batches, tests first, e2e after the risky areas |
| Risk: the real run | It needs MangaDex up and the internet. edge-tts is unofficial. Long Best upscales heat the Mac (run one job at a time). |
| Risk: CodeRabbit limits | The free public-repo limits aren't published. If it rate-limits, the Claude review still covers everything. |
| Open question | Use CodeRabbit at all (it needs installing a GitHub app with repo access), or Claude only? |
| Open question | Also try the "everything PR" trick for a whole-repo CodeRabbit pass? |
| Open question | Should the findings be saved as a file in `specs/`, or just shown in chat? |
| Open question | Include the packaged-app build in Phase C? |

## 9. Sources
- CodeRabbit pricing (public repos free; plan prices): https://www.coderabbit.ai/pricing
- CodeRabbit CLI (reviews local, uncommitted changes): https://docs.coderabbit.ai/cli
- CodeRabbit context across the codebase: https://coderabbit.ai/blog/how-coderabbit-delivers-accurate-ai-code-reviews-on-massive-codebases
- Third-party view that it's PR-focused: https://www.codacy.com/comparison/codacy-vs-coderabbit (vendor claim)
- Repo checks: `wc -l` per area, `gh repo view` (PUBLIC), the pytest run (203 passed in 9.2 s), DEVELOPING.md (test chapter), memory notes (web-mode testing, no Finder windows)
