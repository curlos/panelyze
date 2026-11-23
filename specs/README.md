# Specs

One plan per [ROADMAP.md](../ROADMAP.md) item, written in Nov 2026 for future work (see [PROGRESS.md](PROGRESS.md) for which are done). Every spec has the same 9 sections: summary, is it doable, what's already true (roadmap claims checked ✅ / ⚠️), recommended approach, files to change, steps, how to test, size/risks/open questions, sources.

Speed numbers in some specs were measured while other jobs ran on the same Mac, so the specs say which ones to re-measure.

| # | Spec | Doable? | Size | Value | Recommended approach |
|---|---|---|---|---|---|
| 1 | [Translate raw Japanese pages](01-translate-japanese-pages.md) | Yes | Large | High | Magi finds boxes, manga-ocr reads them, a vision LLM (Claude default, Gemini cheap, Ollama free) translates the whole page with the image + a series glossary; color fill or manga-LaMa to erase; Comic Neue lettering |
| 2 | [Check the untested things](02-untested-checks.md) | Yes | Small | High | 3 checklists: rebuild the app (the current `dist/` is out of date), first-time model download into a scratch folder, Core ML turned off |
| 3 | [Whole-series runs](03-whole-series-runs.md) | Yes | Small–Medium | High | "Skip chapters already done" checkbox; batches by volume; needs #8 first (only 26 GB free) |
| 4 | [Magi on the Neural Engine](04-magi-neural-engine.md) | Partly | Small–Medium | Low alone, Medium with #3 | One fixed 1333×800 padded model (not one per page shape: 140 shapes found); try plain padding on the GPU first |
| 5 | [Faster "Best" for color](05-faster-best-color.md) | Yes | Small | Medium–High | Switch to IllustrationJaNai V3 SPAN: runs on the Neural Engine, about 12× faster per tile |
| 6 | [Upscale to video size](06-upscale-to-video-size.md) | Yes | Small | None at 2×, Medium at 4× | Fit the real video frame; only worth it for 4× upscales |
| 7 | [Highlight text boxes on the fast path](07-page-reading-highlight-boxes.md) | Yes | Small–Medium | Medium | Save each text box as fractions of its panel in `panel-text.json` |
| 8 | [Smaller files](08-smaller-files.md) | Yes | Small | Medium–High | Lossy WebP q90 (waifu2x's "webp" is lossless) + "keep only comic files" option |
| 9 | [Blurry scans](09-blurry-scan-upscaling.md) | Partly | Small | Low | No blurry manga found; an optional "shrink if nothing is lost" check, only after a test |
| 10 | [AMD gaming PC](10-amd-gaming-pc.md) | Probably | Small code, 1–2 h setup | Low–Medium | Windows + AMD TheRock nightly (now lists gfx1031 as tested) |
| 11 | [Smaller ideas](11-smaller-ideas.md) | Yes | Small | Low | 2 fps video without highlighting; launcher script; per-chapter timing line; close the GPU outlier |
| 12 | [Project name](12-project-name.md) | — | — | — | Keep "Panelyze", add a tagline; no clashes in manga |
| 13 | [Fit small panels to the screen](13-fit-small-panels-to-screen.md) | Yes | Small–Medium | Medium | Per-panel ratio to fill a target box (iPad by default), then resize exactly |
| 14 | [Folder structure](14-folder-structure.md) | Yes | Medium (mechanical) | Medium | `panelyze/` package with core / tools / gui; `gui.py` stays in the root |
| 15 | [Format, lint, CI](15-format-lint-ci.md) | Yes | Small | High | Ruff + Pyright + pre-commit + GitHub Actions |
| 16 | [More MangaDex options](16-mangadex-options.md) | Yes | Small | Medium–High | "Chapters" box (`1-5, 7-10`), Volumes box, cover option |
| 17 | [More sources for pages](17-second-downloader.md) | Yes (import, page URL, comix.to, Internet Archive) | Medium | High | Import .cbz/.zip/.epub/.pdf + "Download pages from a URL" (e.g. DC preview pages), then a comix.to downloader (headless browser) and a public-domain Internet Archive downloader; first test of American, Western and French comics |
| 18 | [Type-check fixes](18-type-check-fixes.md) | Yes | Small–Medium | Medium | 88 real-code errors, about 20 real bugs; about 60 one-line edits |
| 19 | [Downloadable app on GitHub](19-github-release-app.md) | Yes | Small | High | Rebuild, test, `gh release create` unsigned; CI builds later |
| 20 | [Optional free NVIDIA GPU](20-optional-nvidia-gpu.md) | Yes | Small | Low–Medium | A Kaggle/Colab notebook that runs Magi on uploaded chapters |
| 21 | [Fresh machine test](21-fresh-machine-test.md) | Yes | Small | High | New macOS user account (packaged app) + GitHub Actions macOS runner (from source) |
| 22 | [Panel reader](22-panel-reader.md) | Yes | Tiny | Medium | Use the Panels app with the .cbz the app already makes; docs only |
| 23 | [Cleanup](23-cleanup.md) | Yes | Tiny | High (disk) | About 2.8 GB safe now; ask about `testing-output` (17 GB) and old git stashes (about 600 MB) |
| 24 | [Non-manga upscale test](24-non-manga-upscale-test.md) | Yes | Small | Low | Scratch comparison; "Best" drops transparency today |
| 25 | [Full code review](25-full-code-review.md) | Yes | Medium | High | 6 Claude subagents by area (+ free CodeRabbit on PRs), after #23 → #15 → #18 → #14 |
| 26 | [Colorize B&W manga (experimental)](26-colorize-manga.md) | Partly | Medium | Low–Medium | Magi v2 names characters from reference pictures (works on the M1); coloring via Gemini image API (~$0.80/chapter), keeping the original lines. Start with a <$2 test, no app code |
| 27 | [Pick the reading direction automatically](27-reading-direction-from-mangadex.md) | Yes | Small–Medium | High | MangaDex has no direction field, so: user pick → "Long Strip" tag (webtoon) → "4-Koma" tag (right strip first if Japanese, else left) → language (ja = right to left, else left to right) → image checks |
| 28 | [Join floating speech bubbles to their speaker's panel](28-floating-bubbles-join-panel.md) | Yes | Medium | Medium–High | Add Magi's tiny speaker/tail/dialogue heads (~2 MB) to the fast model; split bubble-only panels per bubble and attach each to its speaker's panel, within size limits |
| 29 | [Less memory for webtoons](29-webtoon-memory.md) | Yes | Medium | Medium | A "lazy strip" that builds only the part each window or crop needs, instead of one 282,000 px image (3.2 GB peak) |
| 30 | [Skip first/last images (optional)](30-skip-intro-credit-pages.md) | Yes | Small | Low | Two number settings, 0 by default; no automatic credit detection (not reliable) |
| 31 | [Test the untested formats](31-format-testing-followups.md) | Yes | Small | Medium | Spreads, Western comics, more 4-koma, webtoon upscaling and video text: measure only |
| 32 | [Downloadable Windows app](32-windows-app.md) | Yes (A), Probably (B) | Medium (A), Medium–Large (B) | High | (A) one Windows zip with CPU PyTorch (waifu2x still uses the GPU), built by a new `build_windows_app.ps1`; then (B) Magi and "Best" on ONNX Runtime + DirectML, for any GPU from a small download |
| 35 | [Show every speech bubble once, and closer shots](35-panels-without-repeats-and-closer-shots.md) | Probably (A), Yes but experimental (B) | Small–Medium (A), Medium–Large (B) | Medium (A), Low–Medium (B) | Draft, not researched: (A) measure overlapping panels, then give each shared bubble to one panel and trim or merge the other within limits; (B) a camera move to each speaker inside big panels in the video |
| 36 | [Better text reading](36-better-text-reading.md) | Yes | Medium | Medium–High | Draft, not researched: keep Magi for finding text boxes, read them again with a second OCR (Apple Vision, PaddleOCR, a vision LLM...) and check the words against a dictionary and the sentence |
| 37 | [Better voices](37-better-voices.md) | Yes, in steps | Medium–Large | High (videos) | Draft, not researched: a voice per character, a narrator for captions, shouting/whispering, emotion from the text and from the character's face; compare newer engines (OpenAI, ElevenLabs, Kokoro, XTTS...) |
| 38 | [Character sheets (experimental)](38-character-sheets.md) | Probably | Medium–Large | Low–Medium alone, High with 26 and 37 | Draft, not researched: the user's pictures of each character; Magi v2 names them, for coloring (26), voices (37) and name tags |
| 39 | [Highlighter-style highlighting](39-highlighter-text-highlighting.md) | Yes | Small | Medium | Draft, not researched: a Style option (Box / Highlighter / Spotlight) for "Highlight Text Boxes In Images" |
| 40 | [Housekeeping and the first release](40-housekeeping-and-release.md) | Yes | Medium | High | Specs 23, 12, 18, 25, 02, 21 and 19 in one worktree, one plan and one review; 14 and 15 later |

## Suggested order
Top to bottom. The spec numbers are IDs, not the order, so they never change.

1. **New sources and comic types:** 17 (American, Western and French comics, like Webtoon mode was for webtoons)
2. **Panel-By-Panel polish:** 27 → 28 → 29 → 31 → 30
3. **Quick wins:** 12 → 22 → 23 → 05 → 08 → 16 (any order)
4. **Code health:** 15 → 18 → 14 → 25 (in this order)
5. **Ship the app:** 02 → 21 → 19 (in this order)
6. **Bigger features:** 13 → 07 → 03 → 01 (03 needs 08 and 16 first)
7. **Later / experimental:** 11, 24, 06, 09, 04, 10, 20, 26 (any order)
8. **Videos people would watch (drafts, research first):** 35 → 39 → 36 → 37 → 38 (38 goes well with 26 and 37)

Which specs are done: [PROGRESS.md](PROGRESS.md).
