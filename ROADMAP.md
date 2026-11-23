# Panelyze roadmap

Ideas and to-dos for the future, for the user and for future Claude chats. Each idea says why it's worth doing, how big it is, and what's already known. Measurements are in [benchmarks/](benchmarks/README.md), and the context of the session these came from is in [HANDOFF.md](HANDOFF.md).

**For Claude chats:** check with the user before starting any of these (see CLAUDE.md), and never commit.

**Status:** 🟢 ready to start · 🟡 needs a decision or something from the user · 🔵 idea, not planned yet · ⚪ looked into, not worth it for now

## At a glance

Every item has a detailed plan in [specs/](specs/README.md) (Nov 2026). The specs re-checked the notes below, and where they disagree, **the spec is more up to date** (e.g. #3's disk and time estimates, #4's "one model per page shape", #8's WebP sizes).

| # | Idea | Status | Size | Value | Spec |
|---|---|---|---|---|---|
| 1 | [Translate raw Japanese pages to English](#1-translate-raw-japanese-pages) | 🔨 built, being reviewed | Large | High | [01](specs/01-translate-japanese-pages.md) |
| 2 | [Check the things that aren't tested yet](#2-check-the-things-that-arent-tested-yet) | 🟢 | Small | High | [02](specs/02-untested-checks.md) |
| 3 | [Whole-series runs (e.g. all of Slam Dunk)](#3-whole-series-runs) | 🔵 needs #8 first | Small–Medium | High | [03](specs/03-whole-series-runs.md) |
| 4 | [Magi on the Neural Engine](#4-magi-on-the-neural-engine) | 🔵 worth it for whole-series runs | Small–Medium | Low–Medium | [04](specs/04-magi-neural-engine.md) |
| 5 | [Faster "Best" upscaling for color](#5-faster-best-upscaling-for-color) | 🔵 | Small | Medium–High | [05](specs/05-faster-best-color.md) |
| 6 | [Upscale only as much as the video needs](#6-upscale-only-as-much-as-the-video-needs) | ⚪ only helps at 4× | Small | Low | [06](specs/06-upscale-to-video-size.md) |
| 7 | [Page reading with "highlight text boxes"](#7-page-reading-with-highlight-text-boxes) | 🔵 | Small–Medium | Medium | [07](specs/07-page-reading-highlight-boxes.md) |
| 8 | [Smaller files by default](#8-smaller-files-by-default) | 🔵 | Small | Medium–High | [08](specs/08-smaller-files.md) |
| 9 | [Better upscaling for blurry scans](#9-better-upscaling-for-blurry-scans) | 🔵 | Small | Low | [09](specs/09-blurry-scan-upscaling.md) |
| 10 | [Run on the AMD gaming PC](#10-run-on-the-amd-gaming-pc) | 🟡 user's choice | Small (+ setup) | Low–Medium | [10](specs/10-amd-gaming-pc.md) |
| 11 | [Smaller ideas](#11-smaller-ideas) | 🔵 | Small | Low | [11](specs/11-smaller-ideas.md) |
| 12 | [Is "Panelyze" still the right name?](#12-the-name) | 🟡 keep it (recommended) | — | — | [12](specs/12-project-name.md) |
| 13 | [Upscale every panel to fit the screen](#13-upscale-every-panel-to-fit-the-screen) | 🟡 | Small–Medium | Medium | [13](specs/13-fit-small-panels-to-screen.md) |
| 14 | [Organize the Python files into folders](#14-organize-the-python-files-into-folders) | 🔵 | Medium | Medium | [14](specs/14-folder-structure.md) |
| 15 | [Auto format, lint, type check and tests + CI](#15-auto-format-lint-type-check-and-ci) | 🟢 | Small | High | [15](specs/15-format-lint-ci.md) |
| 16 | [More MangaDex options (chapter ranges, etc.)](#16-more-mangadex-options) | 🟢 | Small | Medium–High | [16](specs/16-mangadex-options.md) |
| 17 | [More sources for pages](#17-more-sources-for-pages) | 🟡 | Medium | High | [17](specs/17-second-downloader.md) |
| 18 | [Fix the type-checker (Pylance) errors](#18-fix-the-type-checker-errors) | 🟢 | Small–Medium | Medium | [18](specs/18-type-check-fixes.md) |
| 19 | [A downloadable app on GitHub](#19-a-downloadable-app-on-github) | 🟢 after #2 | Small | High | [19](specs/19-github-release-app.md) |
| 20 | [Optional free NVIDIA GPU](#20-optional-free-nvidia-gpu) | 🔵 | Small | Low–Medium | [20](specs/20-optional-nvidia-gpu.md) |
| 21 | [Test on a fresh machine](#21-test-on-a-fresh-machine) | 🟢 | Small | High | [21](specs/21-fresh-machine-test.md) |
| 22 | [How to read the panels](#22-how-to-read-the-panels) | 🟢 | Tiny | Medium | [22](specs/22-panel-reader.md) |
| 23 | [Clean up unneeded files](#23-clean-up-unneeded-files) | 🟡 user's OK | Tiny | High (disk) | [23](specs/23-cleanup.md) |
| 24 | [Upscale non-manga images (game icons)](#24-upscale-non-manga-images) | 🟡 needs the icons | Small | Low | [24](specs/24-non-manga-upscale-test.md) |
| 25 | [Full code review, fixes and a whole-app test](#25-full-code-review) | 🔵 after #15, #18, #14 | Medium | High | [25](specs/25-full-code-review.md) |
| 26 | [Colorize black-and-white manga (experimental)](#26-colorize-black-and-white-manga) | 🟡 test first | Medium | Low–Medium | [26](specs/26-colorize-manga.md) |
| — | [Looked into, not worth it for now](#looked-into-not-worth-it-for-now) | ⚪ | — | — | — |

---

## 1. Translate raw Japanese pages
**Why:** read chapters that only exist in Japanese, with the English text in the speech bubbles.

**Built (spec 01):** a **Translate** tab and Pipeline step after Download and before Panel-By-Panel, working on whole pages. Magi finds the text boxes, Hayai OCR reads the Japanese, one request per page (with the numbered page image) goes to **Ollama** (free, local, default `translategemma:12b`, with PLaMo for fast Japanese to English and models grouped for 8, 16 and 32 GB computers, downloaded and removed from the app), **Gemini**, **ChatGPT** or **Claude**, the text is erased per speech bubble (manga LaMa on artwork), and the translation is lettered in **Bubble Sans** (or one of five other free fonts). From Japanese, English or Spanish into English or Spanish. How it works: [DEVELOPING.md](DEVELOPING.md#translate). Also moved Magi's packages to torch 2.14.1 and transformers 4.57.6.

| Open items | |
|---|---|
| Known limit | Magi misses a few speech bubbles, which stay in Japanese (1 bubble in the first 5 pages of the test chapter). |
| Later | Translating sound effects (big stylized lettering on the art; hard even for the best tools). |
| Later | **Sugoi-14B** (a free translator trained on game text) now runs on Ollama on a Mac too, but it's text-only and about 9 GB; it could be tried on the gaming PC (spec 10). |
| Also possible | An English voice-over for the video from the translated text. |

## 2. Check the things that aren't tested yet
| What | Why it matters | How |
|---|---|---|
| Build the packaged Mac app | `spandrel` and `coremltools` were added. Core ML Tools has compiled parts that PyInstaller can mis-package. | Run `./build_mac_app.sh`: it builds, runs the self-test on the built app, and zips it. |
| A real first-time download of the upscale models | Only the URLs were checked, plus the zip handling with a fake zip. | Move `~/Library/Application Support/Panelyze/upscale-models` aside, then pick "Best" and upscale. |
| Macs without Core ML | That path (PyTorch fallback) is only covered by tests. | Run "Best" with Core ML turned off. |

## 3. Whole-series runs
**Why:** e.g. read all of **Slam Dunk** (about 278 chapters) by downloading and converting everything in one go.

Estimate, not measured: about 20 pages per chapter → about 5,600 pages.

| Step | Per chapter | All 278 chapters |
|---|---|---|
| MangaDex download | about 5 s | about 25 min |
| Panel-By-Panel (GPU) | about 15–20 s | about 1–1.5 h |
| Upscale, Fast | about 25 s | about 2 h |
| Upscale, Best | about 45–60 s | about 4 h |
| Small comic files | a few seconds | about 15 min |

| Things to check or build | |
|---|---|
| Test run | Start with 3 chapters of Slam Dunk, then a whole volume. |
| MangaDex | Rate limits and chapters with missing pages over a long run. |
| Disk space | Upscaled PNGs are about 2.4 MB per panel, so roughly **200+ GB** for the series. Small comic files would be about 6 GB. Consider an option to keep only the comic files (see #8). |
| Resuming | If a long run stops halfway, skip chapters that are already done. |

## 4. Magi on the Neural Engine
**Why:** Magi's box finder, converted to Core ML, ran **3.8× faster on the Neural Engine** with the same boxes: 0.08 s vs 0.31 s per page. For one chapter that only saves a few seconds, but for whole-series runs (#3) it saves about **20–25 minutes**.

| Details | |
|---|---|
| What to convert | Panel-By-Panel's panel finder (used by every run) and Magi's text finder (video and translation). Reading the text can't move: it writes one word-piece at a time. |
| Fixed sizes | The Neural Engine only runs fixed sizes: convert once per page shape (about 27 s) and cache it, falling back to the GPU for shapes not converted yet. A series usually has only a few page shapes. Panels (all different sizes) can't use it. |
| How it was tested | Trace `model.detection_transformer` (returning `last_hidden_state` and `reference_points`) for one page size, convert with `coremltools` in half precision, and run with `ComputeUnit.ALL`. Details in [benchmarks/magi.md](benchmarks/magi.md). |

## 5. Faster "Best" upscaling for color
**Why:** color is the slow part of "Best": One Piece ch. 567 takes 142 s vs 10 s with Fast. IllustrationJaNai can't use the Neural Engine (Apple's compiler gets stuck on it).

| Ideas | |
|---|---|
| Newer software | Try newer `coremltools` and macOS versions, in case the Neural Engine compiler handles FDAT later. |
| Flexible tile sizes | Core ML's conversion failed for this model. Tiles fitted to each panel weren't faster in PyTorch. |
| A lighter color model | Look for a lighter model with similar quality. Real-CUGAN se was good on color at waifu2x cunet speed (26 s), but it smears black-and-white screentone, so it would need the same color/B&W split. |
| Native 4× | For 4× upscales, use MangaJaNai's 4× models instead of two 2× passes. |

## 6. Upscale only as much as the video needs
**Why:** in a 1080p video, panels are shrunk to fit the frame anyway. Upscaling to 4K first can be wasted time.

**Idea:** when the Pipeline also makes a video, cap the upscale at the video's resolution (now a dropdown: 360p–4K). The existing 4K-cap function (`get_capped_upscale_ratio`) can take a different limit. Test first how much time it saves: Shachou's panels are small, so most still need 2×.

## 7. Page reading with "highlight text boxes"
**Why:** the Pipeline's fast path (reading text from whole pages) is turned off when the video highlights text boxes, because highlighting needs each box's position on each panel. The video step then reads every panel again, which is much slower.

**Idea:** when Panel-By-Panel reads the pages, also convert each text box's position from the page to its panel (and scale it if the panel gets upscaled). Then save it with `panel-text.json`, so highlighting can use it too.

## 8. Smaller files by default
**Why:** upscaled PNGs are huge (217 MB per chapter for Shachou, vs 22 MB as WebP).

| Ideas | |
|---|---|
| WebP by default | Default Upscale's image format to WebP at high quality: it looks the same at a fraction of the size. |
| Comic files only | An option to keep only the comic file and delete the intermediate folders, for whole-series runs (#3). |

## 9. Better upscaling for blurry scans
**Why:** waifu2x and MangaJaNai sharpen enlarged pixels, but can't fix a big image that's blurry.

| Ideas | |
|---|---|
| Shrink, then upscale | Shrink a blurry "fake 4K" image to its real level of detail, then upscale it back. |
| Real-ESRGAN | Its anime model is trained on blurry and compressed images. Testers report it can distort text, so test it on speech bubbles first. |

## 10. Run on the AMD gaming PC
**Why:** the user's PC (Radeon RX 6700 XT, 12 GB) might run Magi and the upscalers about 3–5× faster than the M1. That's an estimate.

| Option | Status |
|---|---|
| Linux (dual boot) with ROCm | The most proven route. Needs `HSA_OVERRIDE_GFX_VERSION=10.3.0`. |
| Windows with AMD's new PyTorch builds ("TheRock") | They list the card's chip (gfx1031), but they're previews. Nobody has reported testing this exact card. |
| VM or WSL2 | ❌ Can't use the card. |
| DirectML | ❌ Unmaintained, stuck on PyTorch 2.0. |

Panelyze runs from source there, not as the Mac app, and waifu2x needs its Windows or Linux download. Because AMD cards show up in PyTorch as "cuda", the GPU picker needs no code change.

## 11. Smaller ideas
| Idea | Notes |
|---|---|
| Faster video writing | Writing the video took about 48 s for a 10-minute video at 5 frames per second (used with a voice-over). Try a lower frame rate. |
| A launcher script in the repo | The one-icon Dock launcher (`~/Applications/Panelyze.app`, with Flet's window app renamed and given the Panelyze icon) was made by hand. A small script in the repo could rebuild it. |
| The unexplained GPU outlier | Finding and reading text on 6 Shachou panels (17–22) once took 50.4 s on the GPU vs 40.0 s on the CPU, though the GPU won everywhere else. |
| Heat during long runs | Benchmarks slowed down after long stretches of work. Worth knowing for whole-series runs (#3). |

## 12. The name
**Question:** the app grew from panel-by-panel into a general manga helper. Is "Panelyze" still right? **Recommendation:** keep it and add a tagline. No clashes in manga or comics; the GitHub repo is already `curlos/panelyze`.

## 13. Upscale every panel to fit the screen
**Why:** small panels look obviously smaller when reading. **Idea:** give each panel the smallest upscale (1×, 2×, 4×) that fills a target box (iPad size by default), then resize it to fit exactly. Costs about 5× the upscale time if it goes up to 4×.

## 14. Organize the Python files into folders
**Why:** all the main Python files are in the repo root. **Idea:** a `panelyze/` package with `core/`, `tools/` and `gui/`, moved in one `git mv` step; `gui.py` stays in the root so `flet run` and the build barely change.

## 15. Auto format, lint, type check and CI
**Why:** there's no formatter, no linter and no CI yet (Prettier is for JavaScript). **Idea:** Ruff (format + lint) and Pyright on every commit through pre-commit, plus GitHub Actions running them and the fast tests.

## 16. More MangaDex options
**Why:** the GUI is missing options the downloader's command line has. **Idea:** a "Chapters" box (`1-5, 7-10`), a Volumes box and a cover option. The downloader's own `--range` is turned off, so Panelyze runs one download per range.

## 17. More sources for pages
**Why:** MangaDex is the only source, has low-quality Slam Dunk scans, and almost no American, Western or French comics, which the app has never been tested on. **Idea:** import comic files (.cbz, .zip, .epub, .pdf, later .cbr), "Download pages from a URL" (e.g. DC's Absolute Batman #1 preview pages), a comix.to downloader, and a public-domain Internet Archive downloader. High priority.

## 18. Fix the type-checker errors
**Why:** red Pylance lines. Pyright finds 88 errors in the app code (about 20 are real small bugs), plus 75 in the bundled `magi_model/`, which should be excluded.

## 19. A downloadable app on GitHub
**Why:** the README's download link has no release behind it yet. **Idea:** rebuild (the current build is out of date), test it, and publish an unsigned GitHub release. Automatic CI builds and signing come later.

## 20. Optional free NVIDIA GPU
**Why:** big jobs could run faster on an NVIDIA card; the default stays the user's own Mac. **Idea:** a Kaggle or Colab notebook that runs Magi on uploaded chapters and returns a zip.

## 21. Test on a fresh machine
**Why:** prove all needed libraries install outside this Mac. **Idea:** the packaged app in a new macOS user account, plus a from-source run on a GitHub Actions macOS runner.

## 22. How to read the panels
**Idea:** read the .cbz of panels the app already makes in the Panels app (iPhone, iPad, Mac). Only docs change; a reader built into Panelyze isn't needed.

## 23. Clean up unneeded files
**Why:** the folder is about 21 GB. About 2.8 GB is safe to delete (`venv-py310-old`, `dist`, `build-assets/pack`, `__pycache__`). `testing-output` (17 GB) and two old git stashes (about 600 MB) need the user's OK.

## 24. Upscale non-manga images
**Idea:** compare the upscalers on game icons (BO7 / MW19 prestige icons, from the user). Known issue: "Best" drops transparency.

## 25. Full code review
**Idea:** Claude subagents review each area (free CodeRabbit on PRs as a second opinion), each bug gets a test and a small fix, then a full app test on Dragon Ball ch. 93. Do it after #23, #15, #18 and #14.

## 26. Colorize black-and-white manga
**Experimental.** Color B&W pages automatically. Magi v2 (already in the repo) can name characters from one reference picture each, so each page's coloring gets the right character references. Good coloring models don't fit on the M1, so the plan uses Gemini's image API (about $0.80 a chapter) and keeps the original lines. Start with a test under $2 before any app code.

---

## Looked into, not worth it for now
| Idea | Why not |
|---|---|
| Gluing several pages into one image for Magi | Finding was 2.6 s faster, but it missed 9 lines of dialogue, and reading took twice as long. |
| Upscaling pages instead of panels | Pages have more pixels than their panels (they include the gutters and margins), so it's 6–20% slower. |
| Speeding up the MangaDex download | It's about 5 s per chapter. |
| A faster video encoder preset | 3.5 s → 3.1 s on 20 panels. |
| waifu2x thread and tile settings | No faster than the defaults. |
| Real-CUGAN for black and white | Smears screentone into a waxy texture. |
| Separate comic files for phone and iPad | A tablet-sized file is only 5–25% bigger, so one "small" file covers both. |
