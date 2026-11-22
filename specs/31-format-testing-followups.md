# 31. Test the formats that haven't been tested yet

Related: [benchmarks/panel-cropping.md](../benchmarks/panel-cropping.md) · [benchmarks/webtoons.md](../benchmarks/webtoons.md) · [benchmarks/upscaling.md](../benchmarks/upscaling.md) · [#02 untested checks](02-untested-checks.md)

New item, not on the roadmap yet. This is a plan only: no app code was changed. Researched 2026-11-20.

## 1. Summary

Panel-By-Panel was tested on 25 manga chapters, 10 webtoons and Bleach ch. 336. A few formats and steps were never tested. This spec is **testing and measuring only**. App code changes only if a test finds a real problem, and then only after the user agrees.

| # | Item | Question |
|---|---|---|
| A | Two-page spreads (manga) | Are multi-panel spreads split into panels, and single-image spreads kept whole? How do they look on a phone? |
| B | Western comics (left to right) | No test chapter yet: is the panel order right? |
| C | More 4-koma | Only Bocchi ch. 2 was tested |
| D | Upscaling a webtoon | How long do "Best" and "fast" take on an all-color webtoon chapter? |
| E | Webtoon videos | How much slower is reading the text for Images To Video on a webtoon? |

## 2. Is it doable?

Yes, all of it is running existing features on new chapters.

## 3. What's already true (checked 2026-11-20)

| Claim | Check | Status |
|---|---|---|
| Spreads appear in the tests | Chainsaw Man and Gachiakuta had up to 3 two-page spreads per chapter (wide pages) | ✅ |
| Magi splits panels on a spread | Expected: a spread is just a wide page to Magi. Not checked by eye. | ⚠️ |
| Left-to-right order exists | `reorder_page_result_left_to_right` in `magi.py`, with tests on fake pages | ✅ (no real comic tested) |
| Webtoon text for video | Panel-By-Panel doesn't save `panel-text.json` for webtoons (the strip is too tall to read in one go), so Images To Video reads the text from each panel instead | ✅ (not timed) |
| "Best" color upscaling is slow | IllustrationJaNai runs on the GPU, not the Neural Engine: about 1.5 s per panel on One Piece | ✅ |

## 4. Recommended approach + rejected alternatives

| Item | How |
|---|---|
| A. Spreads | Download a One Piece chapter that has a spread (MangaDex's official colored One Piece; the user expects these in every big series), plus re-check Chainsaw Man ch. 3 and Gachiakuta ch. 174. Make a sheet of every wide page with its panels drawn on it. The user's preference: **single-image spreads stay whole**. Only suggest an option (e.g. rotate 90° for phones) if the sheet shows a clear problem. |
| B. Western comics | Find a left-to-right comic that downloads from MangaDex (original language `en`, or a flipped release), run it with "Left to right", and check the order on 3–4 pages by eye |
| C. 4-koma | Another Bocchi chapter plus one more 4-koma series (Japanese, and a non-Japanese one if [#27](27-reading-direction-from-mangadex.md) is done) |
| D. Upscaling a webtoon | Time fast and Best on one webtoon chapter's panels (e.g. Eleceed ch. 2, 140 panels), in a fresh process each; add a row to `benchmarks/upscaling.md` |
| E. Webtoon videos | Time Images To Video's text reading on Eleceed ch. 2 vs a manga chapter of similar length. If it's much slower, a follow-up could read the text from the same windows used for panels (not in this spec). |

**Rejected:** changing any code "just in case". Measure first.

## 5. Files to change + what's reused

| File | Change |
|---|---|
| `benchmarks/panel-cropping.md` | Spreads, Western comics, 4-koma results |
| `benchmarks/upscaling.md` | Webtoon upscaling times |
| `benchmarks/webtoons.md` | Webtoon video text timing |
| Reused | The MangaDex downloader command used for the test chapters, `get_panels_for_chapter`, the upscale and video views |

## 6. Steps

- [ ] A: download + run, make the spreads sheet, show the user.
- [x] B: find a downloadable Western comic, run, check the order. Done in #17 (2026-11-20): Absolute Batman preview, Pepper&Carrot, Pirates Comics, all in the right order. See `benchmarks/panel-cropping.md` Step 10.
- [ ] C: one more Bocchi chapter + another 4-koma.
- [ ] D: time fast and Best upscaling on Eleceed ch. 2.
- [ ] E: time the video text reading on Eleceed ch. 2.
- [ ] Write the results into the benchmark docs. List any real problems found as new specs, not fixes.

## 7. How to test it

| Check | Pass |
|---|---|
| Each item | Has a measured result (numbers or a checked sheet) in the docs |
| Any problem found | Written up with an example image, for the user to decide on |

## 8. Size, value, risks, open questions

| | |
|---|---|
| Size | Small each; about one session for all five |
| Value | Medium: finds problems before users do |
| Risk | Some series may not be downloadable from MangaDex (many big series were taken down); pick what's available |
| Open question | Which One Piece chapter has a good single-image spread and a multi-panel spread? |

## 9. Sources

- This project's test runs (`benchmarks/panel-cropping.md`, `benchmarks/webtoons.md`).
- Code: `magi.py` (`reorder_page_result_left_to_right`, `get_four_koma_panel_order`, `get_panels_using_local_cpu`), `VideoCreatorFromImages.py` (`panel-text.json` fallback).
