# 04. Magi on the Neural Engine

Roadmap item #4. This is a plan only: nothing in the app has changed yet.

## 1. Summary

Run Magi's **detection transformer** (the part that finds panels, text boxes and characters) with Core ML on the Neural Engine instead of PyTorch on the GPU. The earlier experiment measured **0.08 s vs 0.31 s per page** for this step.

The roadmap planned **one conversion per page shape**. That doesn't hold up on real chapters: 25 downloaded chapters produced **140 different shapes**. So the plan changes to **one fixed canvas**. Every portrait page is padded to 1333×800, with a mask that tells Magi which part is padding (Magi already does this today whenever it handles several pages at once). That means **one conversion, ever** (about 27 s), cached in Application Support. Double-page spreads, and any Mac where Core ML fails, keep using the GPU exactly as now.

## 2. Is it doable?

**Yes.** The same pattern already runs in the app: `janai.py` converts the upscale models to Core ML once, caches them, and falls back to PyTorch. coremltools 8.1 is already installed, in requirements.txt, and bundled by `build_mac_app.sh`. The only real unknown is whether the converted model still gives the same boxes once the mask is an input. Step 1 of the plan checks that before anything else is built.

## 3. What's already true (claims checked)

| Claim (ROADMAP / HANDOFF / benchmarks) | Check | Status |
|---|---|---|
| Core ML on the Neural Engine: 0.08 s/page vs 0.31 s on the PyTorch GPU (3.8×), same boxes | Taken from benchmarks/magi.md; not re-measured (no heavy conversions in this task). The experiment script wasn't saved anywhere in the repo. | ⚠️ not re-checked, script lost |
| What to convert: `model.detection_transformer`, returning `last_hidden_state` + `reference_points` | `_get_predicted_bboxes_and_classes` (magi_model/modelling_magiv2.py:491) only reads those two fields. `find_panels` (magi.py:412) and `predict_detections_and_associations` (:180) both call `_get_detection_transformer_output` | ✅ |
| One converted model can serve both Panel-By-Panel and text finding | The panels model is the full model's detection parts saved in fp16 (magi.py:97). Same network, same weights. | ✅ |
| "Convert once per page shape… a series usually has only a few page shapes" | Magi resizes every page to shortest edge 800 / longest 1333 first, so a "shape" is the resized size. Measured on 593 pages in 25 chapters in `~/Documents/Panelyze/MangaDex Downloads`: **140 shapes**, **median 5 per chapter, max 38**. Scans differ by a few pixels. | ⚠️ wrong: per-shape caching would cost about 140 × 27 s ≈ 63 min of conversions to save about 2.3 min |
| Panels (all different sizes) can't use it | Still true, but it doesn't matter: Magi now finds text on pages, not panels | ✅ |
| Reading the text can't move (it writes one word-piece at a time) | Still true; this plan doesn't touch it | ✅ |
| Saves about 20–25 min on a whole series (#3) | 5,600 pages × 0.23 s ≈ **21 min** for the panel step. About as much again for text finding, but only when making a video or translating. | ✅ (math checks out) |
| coremltools 8.1 is used and bundled | `requirements.txt:28`; `build_mac_app.sh` has `--collect-all=coremltools`; installed: coremltools 8.1, torch 2.5.1, transformers 4.34.0, Python 3.12.11, macOS 26.4.1 | ✅ |
| coremltools warns that torch 2.5.1 is untested, but works | Seen again during this check ("Torch 2.4.0 is the most recent version that has been tested") | ✅ |
| The packaged app works with coremltools | Not tested yet (HANDOFF "Untested" list) | ⚠️ still untested |
| Newest coremltools | **9.0** (2025-11-10, PyTorch 2.7 support, cp310–cp313 arm64 wheels). 9.1.dev1 (2026-08-03) is only a dev build. 8.1 still works for us. | ✅ (checked on PyPI) |

**Extra facts measured for this plan:**

| | Number |
|---|---|
| Portrait vs landscape pages (after Magi's resize) | 577 vs 16 (2.7% landscape) |
| Biggest portrait page after resize | exactly 1333×800, so **every** portrait page fits a 1333×800 canvas |
| How much of that canvas a portrait page fills, on average | 89% (so padding adds about 12% work) |
| Padding changes the boxes? | It shouldn't. Magi's position encoding divides by the mask's own height and width (transformers `modeling_conditional_detr.py:454-457`), so boxes stay relative to the real page. `find_panels` already pads up to 8 pages to the same size today. |

## 4. Recommended approach and rejected alternatives

| Option | Conversions | Verdict |
|---|---|---|
| **One portrait canvas 1333×800 + mask input, on the Neural Engine. Spreads and failures stay on the GPU.** | **1, ever (about 27 s)** | ✅ **Recommended.** Simplest, and every portrait page fits. |
| One conversion per resized page shape (the roadmap's plan) | median 5 per chapter, 140 over 25 chapters | ❌ Converting costs far more than it saves |
| Two canvases (portrait + landscape 800×1333) | 2 | ❌ for now: an extra conversion and extra code for 2.7% of pages. Easy to add later. |
| One square canvas 1333×1333 | 1 | ❌ about 1.9× the pixels of a portrait page, which throws away much of the gain |
| Core ML flexible input sizes (`RangeDim`) | 1 | ❌ The Neural Engine only runs fixed sizes. Flexible sizes already failed for MangaJaNai (HANDOFF). |
| Convert at build time and bundle the `.mlpackage` | 0 for users | ❌ for now: makes the app about 90 MB bigger, and people running from source would still need first-use conversion. Could be added later. |
| Upgrade to coremltools 9.0 first | — | ❌ not needed: 8.1 already works with torch 2.5.1. Upgrading would be its own change (it also matters for #5). |
| **Cheap first test:** pad to the fixed canvas but stay on the PyTorch GPU | 0 | 🔎 **Measure in step 1.** The GPU rebuilds its programs for every new image size (benchmarks/magi.md), and chapters have about 5 sizes. A fixed size alone might win part of the time back with no Core ML at all. |

## 5. Files to change and functions to reuse

| File | Change |
|---|---|
| `magi.py` | Add about 50–70 lines: `pad_to_canvas(inputs)`, `get_coreml_detector()` (convert once, cache, load) and `get_detection_output(model, inputs)`, which tries Core ML and otherwise calls the existing `model._get_detection_transformer_output`. `find_panels` calls it instead of line 412. |
| `tests/test_magi.py` | Add tests: padding keeps the mask right, and the fallback is used when Core ML isn't available, the page is landscape, or Core ML fails |
| `self_test.py` | Optionally add one check that the panels on the test page come out the same with Core ML (no internet needed, because the panels model is bundled) |
| `benchmarks/magi.md`, `ROADMAP.md`, `HANDOFF.md` | Update with the real numbers afterwards |
| `build_mac_app.sh`, `requirements.txt` | **No change** (coremltools is already bundled and pinned) |

| Reuse | Where |
|---|---|
| `can_use_coreml()` (Apple Silicon + coremltools importable) | `janai.py:125` (`magi.py` already imports from `janai`) |
| Convert → save under a temporary `.mlpackage` name → `os.replace`; `ComputeUnit.ALL`; `FLOAT16`; `macOS13` target | `get_coreml_upscale_function`, `janai.py:137-165` |
| Fall back with a message on any Core ML error | `get_upscaler`, `janai.py:220-240` |
| GPU→CPU fallback (unchanged; still wraps everything) | `Magi.run_with_cpu_fallback`, `magi.py:371` |
| Preprocessing (resize + normalize) | `model.processor.preprocess_inputs_for_detection` (unchanged) |

**Cache location:** `~/Library/Application Support/Panelyze/magi-models/magi-detector-1333x800.mlpackage`, next to the existing `upscale-models` folder. It is outside the app bundle, so it survives app updates and is writable. The file name should include a version suffix (for example the Magi revision), so a future model change can't reuse a stale conversion.

## 6. Steps

- [ ] **1. Spike (a scratch script, not app code).** On Dragon Ball ch. 93 and Shachou ch. 3:
  - (a) Time PyTorch GPU as it is now.
  - (b) Time PyTorch GPU with every page padded to 1333×800.
  - (c) Convert the detection transformer with a `pixel_mask` input at 1333×800 and time it on the Neural Engine.
  - Compare the panels from (a), (b) and (c) (same count, corners within about 1 px). Check for NaN in fp16 from the attention mask's `finfo.min`.
  - **Stop and report to the user.** If (b) gets most of the gain, do only that (a few lines, no Core ML).
- [ ] 2. Add `pad_to_canvas` to `magi.py` (pad `pixel_values` with 0 and `pixel_mask` with 0 up to 1333×800).
- [ ] 3. Add `get_coreml_detector()`: convert once into the cache folder, using the janai pattern. Return `None` when `can_use_coreml()` is false or anything fails, and print the reason.
- [ ] 4. Add `get_detection_output()`: Core ML one page at a time for portrait pages; anything else uses the current PyTorch call. Use it in `find_panels`.
- [ ] 5. Tests in `tests/test_magi.py` (with fakes, no real model needed).
- [ ] 6. Measure a whole chapter before and after (Panel-By-Panel step time, panel count), and update benchmarks/magi.md.
- [ ] 7. *(Optional, separate OK from the user)* Use the same function for text finding in `find_and_read_dialogue`. Check first that text boxes and the speaker links (which use `last_hidden_state`) stay the same.
- [ ] 8. *(Optional)* A self-test check, then build the app once with `build_mac_app.sh` to confirm Core ML conversion works inside the bundle. That also covers the HANDOFF "untested" item.

## 7. How to test it

| Test | Pass if |
|---|---|
| `pytest tests/test_magi.py` | New fallback and padding tests pass; existing tests unchanged |
| Full `pytest` | Same results as before |
| Dragon Ball ch. 93 (default test chapter) + Shachou ch. 3, Panel-By-Panel | Same number of panels, corners within about 1 px of the GPU run, and saved panel images look the same |
| A chapter with double-page spreads (e.g. One Piece ch. 567) | Spreads still work (GPU path) |
| Timing | Panel-finding time per page goes down (target: about 0.1 s vs about 0.3 s) |
| Delete the cache folder and run again | Converts once (about 27 s, with a "getting ready" message), then reuses the cache |
| Simulate no coremltools (`can_use_coreml` returns False) | Runs on the GPU as today |
| Built app `--self-test` | Passes. No Finder windows opened. |

## 8. Size, value, risks, open questions

| | |
|---|---|
| **Size** | Small–Medium: about 60–80 lines in `magi.py` plus tests. Smaller than the roadmap's "Medium" because there's no per-shape cache. |
| **Value, one chapter (about 20 pages)** | About **4–5 s saved** in a Panel-By-Panel step of about 15–20 s. The one-time 27 s conversion pays for itself after about 6 chapters. Small. |
| **Value, whole series (#3, about 5,600 pages)** | About **21 min** saved on panels (+ about 21 min on text finding if the video step is used), in a run of about 3.5–6 h. Roughly 5–10%. Worth it only together with #3. |
| **Verdict** | Only worth doing for #3 (or as a cheap win if step 1b shows padding alone helps). Not worth doing for single chapters. |

| Risk | How it's handled |
|---|---|
| Mask + fp16 gives NaN or slightly different boxes | Step 1 checks it before any app code is written. If it fails, drop the idea. |
| The Neural Engine compiler hangs (as it did for IllustrationJaNai) | The experiment compiled this model fine at one size. If it hangs now, use `CPU_AND_GPU` or skip Core ML. |
| The first load compiles the model for the Neural Engine (system cache) | Measure the first run separately in step 6 |
| The packaged app can't trace/convert inside PyInstaller | Same risk the janai upscaler already has; step 8 covers both |
| A stale cache after a Magi model change | Version suffix in the file name |
| Uses more memory (Core ML and PyTorch copies both loaded) | The panels model is only 87 MB, so this is negligible |

**Open questions for the user**

1. Do this only together with #3 (whole-series runs), or now?
2. If step 1 shows that padding alone (staying on the GPU) wins back much of the time, is that enough? It's far simpler.
3. Also move text finding (step 7) for the video and translation paths, or panels only?
4. Is it OK that double-page spreads stay on the GPU (2.7% of pages)?
5. Keep coremltools at 8.1 (works today), or upgrade to 9.0 separately (it may also help #5)?

## 9. Sources

- benchmarks/magi.md, "Magi on the Neural Engine": the 0.31 / 0.14 / 0.08 s numbers and the 27 s conversion
- ROADMAP.md #3 and #4; HANDOFF.md (coremltools notes, the IllustrationJaNai hang, untested items)
- Code: `magi.py` (find_panels :391, find_and_read_dialogue :494, run_with_cpu_fallback :371), `magi_model/modelling_magiv2.py:460-505`, `janai.py:125-240`, `build_mac_app.sh`, `requirements.txt`, `magi_model/panels_config.json` (resize: shortest 800 / longest 1333)
- transformers 4.34.0 `modeling_conditional_detr.py:391, 430, 454-457` (mask handling)
- Page-shape count: a scratch script over `~/Documents/Panelyze/MangaDex Downloads` (593 pages, 25 chapters), run 2026-11-19
- coremltools on PyPI: https://pypi.org/project/coremltools/ (9.0, 2025-11-10; 9.1.dev1, 2026-08-03)
- coremltools releases: https://github.com/apple/coremltools/releases (9.0: PyTorch 2.7, Python 3.13, macOS 26 targets)
