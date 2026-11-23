# 02 — Check the things that aren't tested yet

> **Being built as part of [spec 40](40-housekeeping-and-release.md)** (2026-11-23). Where they differ, spec 40 is newer.

Roadmap #2. Researched 2026-11-19. Planning only: nothing here has been run yet.

## 1. Summary
Three things were never tried for real: (a) building the Mac app now that `spandrel` and `coremltools` are in it, (b) a real first-time download of the "Best" upscale models, (c) the "Best" upscaler on a Mac without Core ML. Each one is a short manual checklist. Only one small code change is suggested: add a "Best" check to the self-test so the build catches a broken Core ML bundle by itself.

## 2. Is it doable?
Yes. About 1–2 hours in total, most of it waiting for the build (the stale build took about 1–2 min to package plus the self-test) and the 592 MB download.

## 3. What's already true (claims checked)
| Claim (ROADMAP / HANDOFF) | Check | Status |
|---|---|---|
| The packaged app hasn't been built with spandrel/coremltools | `dist/Panelyze.app` is from **Nov 17 20:26**; the commit that added them (`ad09573`) is Nov 19. The bundle has no `coremltools` or `spandrel` folder. | ✅ verified |
| The build bundles the `upconv_7` ("Fast") model | The **stale** `dist/` app and `build-assets/waifu2x/` only have `models-cunet`. The script re-downloads waifu2x when `models-upconv_7...` is missing, so the next build should fix it. | ⚠️ true in the script, not in the current `dist/` (the app there would fail "Fast", the default) |
| `build_mac_app.sh` runs the self-test and zips | Yes (steps 5–6). No zip exists in `dist/` yet. | ✅ |
| The self-test would catch a broken Core ML bundle | `self_test.py` has 5 checks (Magi panels, waifu2x, video, MangaDex, TTS). **None touches janai/spandrel/coremltools.** A mis-packaged coremltools would pass the build. | ⚠️ gap |
| Models download from MangaJaNai GitHub releases, "about 600 MB of zips, 240 MB kept" | Both URLs answer today: MangaJaNai 1.0.0 zip **433 MB**, IllustrationJaNai 2.0.0 zip **159 MB** = **592 MB**. The current folder is **314 MB** (it also holds 3 converted `.mlpackage`s). | ✅ |
| Only the zip handling was tested, with a fake zip | `tests/test_janai.py` uses a fake zip. | ✅ |
| "Macs without Core ML" use the PyTorch fallback | `janai.can_use_coreml()` is False when not `darwin`+`arm64`, or coremltools can't import. `get_upscaler` also falls back if the Core ML conversion throws. There is **no setting** to turn Core ML off. | ✅ (no switch exists) |
| Which real users hit the fallback | The app is arm64-only, and every Apple Silicon Mac has Core ML. So in the app, only a failed conversion falls back. Running **from source** on Intel Macs, Linux or Windows always falls back. | ✅ (narrower than the roadmap implies) |
| A local Core ML check can run offline | Throwaway check in the scratchpad: converting and running a tiny 16×16 conv model with `coremltools 8.1` took **0.6 s**, no internet. | ✅ |
| torch 2.5.1 untested by coremltools | It still prints the warning; it works. | ✅ |
| Free disk | **27 GB free** on the M1 (460 GB disk). Enough for a build (~700 MB app + ~350 MB zip). | ✅ |

## 4. Recommended approach + rejected alternatives
| Item | Recommended | Rejected (why) |
|---|---|---|
| Build check | Run `./build_mac_app.sh` as is, then run "Best" in the **built** app on a real panel. Add a tiny `check_best_upscaler_libraries` to `self_test.py` (import spandrel, convert + run a 16×16 conv with coremltools). | Converting a real MangaJaNai model in the self-test (needs the 433 MB download; the self-test promises "nothing needs the internet"). |
| First-time download | From source: a scratch script that points `janai.MODELS_FOLDER` at an empty scratch folder and upscales one panel. In the built app: test it in a **new macOS user account** (fresh `~/Library`, see spec 21). | Moving the user's real `upscale-models` folder aside (risky, easy to forget to move back; the user said don't move it). An env var / setting for the folder (code change for a one-off test). |
| No Core ML | Scratch script that sets `janai.can_use_coreml = lambda: False`, then upscales one B&W and one color panel. Optional real case: the Linux Docker run in spec 21. | A "Use Core ML" setting (code + UI for something users don't need). Uninstalling coremltools from the venv (breaks the dev setup). |

## 5. Files to change + functions to reuse
| File | Change |
|---|---|
| `self_test.py` | Add one check function and add it to `CHECKS`. About 15 lines. |
| (nothing else) | Scratch scripts live in the scratchpad, not the repo. |

| Reuse | Where |
|---|---|
| `download_model_file`, `MODELS_FOLDER`, `upscale_image_with_janai`, `can_use_coreml`, `get_upscaler` | `janai.py` |
| `run_self_test`, `CHECKS`, `REPORT_FILE_PATH` | `self_test.py` |
| Self-test on the built app (`perl alarm 600`) | `build_mac_app.sh` step 5 |

## 6. Steps
**A. Packaged app build**
- [ ] Add `check_best_upscaler_libraries` to `self_test.py` (imports `spandrel`; on arm64 Macs converts and runs a 16×16 conv with coremltools; elsewhere just says "Core ML not used").
- [ ] `venv/bin/python gui.py --self-test` from source → 6 PASS.
- [ ] Ask the user, then run `./build_mac_app.sh` (needs internet for waifu2x; the Magi panels model already exists).
- [ ] Confirm the log ends with `SELF-TEST PASSED` and the 6th check passed in the **built** app.
- [ ] Confirm the bundle now has `coremltools`, `spandrel` and `waifu2x/models-upconv_7_anime_style_art_rgb`.
- [ ] Note the real sizes: app (expect ~710 MB) and zip (expect ~360 MB).
- [ ] Note the `Info.plist` version (the stale build says `0.0.0` though the script passes `--product-version 1.0.0`).
- [ ] Open the built app; upscale 2–3 panels from the Dragon Ball ch. 93 cache with **Fast**, **Better** and **Best** (one color image too). Check the log says Core ML was used, not "Using PyTorch instead".

**B. Real first-time model download (from source)**
- [ ] Scratch script: set `janai.MODELS_FOLDER` to an empty scratchpad folder; upscale one B&W panel and one color panel with `upscale_image_with_janai(..., 2)`.
- [ ] Check: 592 MB downloaded, only `2x_*` files kept (7 MangaJaNai + 1 IllustrationJaNai), no `download.zip.tmp` left, `.mlpackage` made, output is 2× size and grayscale for B&W.
- [ ] Time it and note the numbers.
- [ ] Optional: unplug Wi-Fi mid-download → the job should stop with an `OSError` message, and a retry should work.
- [ ] Delete the scratch folder.
- [ ] The packaged-app version of this check is done in the new-user-account test (spec 21).

**C. No Core ML**
- [ ] Scratch script: `janai.can_use_coreml = lambda: False`, point `MODELS_FOLDER` at the real folder (no re-download), upscale the same two panels.
- [ ] Check: no `.mlpackage` created, output looks the same as Core ML's (compare side by side), no NaN/black image for color, note the time (expect several × slower).
- [ ] Optional real case: the Linux Docker run (spec 21) runs the same thing for real.

## 7. How to test it
- `venv/bin/python -m pytest -q -m "not e2e"` still passes (184 tests) after the self-test change.
- The built app's `~/Library/Logs/Panelyze/self-test.log` shows 6 PASS.
- B and C: compare output images by eye and note times in a small table for the user.

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | Small: 1 code change (~15 lines), 3 manual checklists. |
| Value | High: the next GitHub release (spec 19) depends on A passing. |
| Risk | PyInstaller may miss a coremltools native lib (`libcoremlpython`, `libmilstoragepython`); `--collect-all=coremltools` should cover it, and the new self-test check will show it. |
| Risk | The Neural Engine compile of MangaJaNai may behave differently inside the bundle (e.g. cache paths). Only step A's manual "Best" run shows that. |
| Open | Is it OK to run the build now (it rewrites `dist/`)? |
| Open | Should the self-test check run on non-Mac (it would just test spandrel)? |

## 9. Sources
- Local: `build_mac_app.sh`, `self_test.py`, `janai.py`, `dist/Panelyze.app` (inspected read-only), `git log`.
- Download sizes measured with `curl -I` on the two MangaJaNai release URLs (2026-11-19).
- [MangaJaNai releases](https://github.com/the-database/MangaJaNai/releases)
