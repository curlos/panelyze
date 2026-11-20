# Spec 05: Faster "Best" upscaling for color

Roadmap item [#5](../ROADMAP.md#5-faster-best-upscaling-for-color). Related: [09 – Blurry scans](09-blurry-scan-upscaling.md), [13 – Fit small panels to the screen](13-fit-small-panels-to-screen.md) (needs fast 4× and 8×), [24 – Non-manga upscale test](24-non-manga-upscale-test.md).

Checked on 2026-11-19. ✅ = checked today against the code or the web, ⚠️ = an older note that's now out of date, 🟡 = not confirmed.

## 1. Summary
Switch color panels from IllustrationJaNai **V2 FDAT** (GPU only) to the new IllustrationJaNai **V3 SPAN** 2× model (released Nov 2025). SPAN is made only of convolutions, so it **runs on the Neural Engine**. In a quick test today it was about **12× faster per tile** than the current color model, and the result looked close. The change is a different file name and download URL in `janai.py`, plus `use_neural_engine=True` for color.

Side finding: the **native 4× MangaJaNai models are already in the zip the app downloads**, but the app throws them away. Keeping them makes 4× black-and-white upscales about 20% cheaper and is a 2-line change. It's optional.

## 2. Is it doable?
**Yes.** Measured today on this Mac (M1, macOS 26.4.1, coremltools 8.1):

| Color model | Runs on | Core ML conversion | Time per 256 px tile | 10 One Piece panels |
|---|---|---|---|---|
| IllustrationJaNai V2 FDAT M (now) | GPU | already converted | **0.23 s** (benchmarks/upscaling.md); 1.03 s today ⚠️ | 15 s expected; 112.8 s today ⚠️ |
| **IllustrationJaNai V3detail SPAN S** | **Neural Engine** | ✅ 15.8 s, worked first time | **0.019 s** | **2.2 s** |
| IllustrationJaNai V1 ESRGAN (2×) | Neural Engine | ✅ 105.8 s | 0.092 s | 15.8 s |

⚠️ Other Claude jobs were using the GPU and CPU during today's test, so the FDAT numbers today were about 4× slower than in the benchmarks. The Neural Engine numbers were likely less affected, but they **must be re-measured on a quiet Mac** (step 6).

Estimate for One Piece ch. 567 (96 color panels): **about 20–30 s instead of 142 s**, if the quiet-Mac numbers hold.

**Quality (one 400 px crop, One Piece panel 10):** SPAN V3**detail** looks very close to the current model and keeps a bit more of the printed dot texture. The V1 ESRGAN model is smoother and loses some thin lines and texture, so it's rejected. Average pixel difference from the current model: SPAN 5.5, ESRGAN V1 7.9 (out of 255). The test crop is in the scratchpad: `/private/tmp/claude-501/-Users-curlos-Desktop-Github-Repos-manga-panel-splitter/8ee4c6a0-1364-4871-bb81-d6088b80b372/scratchpad/compare_color.png` (left: now, middle: V1 ESRGAN, right: V3 SPAN).

## 3. What's already true (roadmap claims checked)
| Claim | Status | What's really true |
|---|---|---|
| Color is the slow part of Best: One Piece 142 s vs 10 s Fast | ✅ | benchmarks/upscaling.md. Not re-run today. |
| IllustrationJaNai can't use the Neural Engine | ✅ for V2 FDAT | `janai.py` runs color with `use_neural_engine=False`. ⚠️ **No longer true for the family**: V3 has a SPAN model that converts and runs on the Neural Engine (tested today). |
| "Try newer coremltools / macOS" | ⚠️ | coremltools **9.0** is out (Nov 10, PyTorch 2.7, macOS 26 targets). Its notes don't mention Neural Engine or attention fixes, so FDAT is unlikely to start working. The Mac is **already on macOS 26.4.1**, the newest. The app has 8.1 with torch 2.5.1. Upgrading is a separate, riskier change; not needed if SPAN works. |
| Flexible tile sizes failed for this model | ✅ | HANDOFF.md. Not needed: SPAN works with the fixed 256 px tile. |
| "A lighter color model" | ✅ found | IllustrationJaNai **V3** (release 3.0.0, 2025-11-26) has `2x_IllustrationJaNai_V3detail_SPAN_S_40k_fp16.safetensors` and `2x_..._V3denoise_SPAN_S_30k_fp16.safetensors` (8.9 MB each, 2.2 M parameters vs FDAT's 4.0 M). The author's speeds on an RTX 4090: 2× SPAN 0.08 s vs 2× FDAT M 0.3 s. They say SPAN is "good on lightly degraded images". |
| Real-CUGAN se is good on color at waifu2x cunet speed | ✅ (benchmarks) | Still needs a color/B&W split, and it's a different program. SPAN is simpler: same code path. |
| "Native 4×: use MangaJaNai's 4× models instead of two 2× passes" | ✅ the models exist | `MangaJaNai_V1_ModelsOnly.zip` (the zip the app already downloads) has **7 `4x_MangaJaNai_*` models** next to the 2× ones. `download_model_file` keeps only names starting with `2x_`, so they're thrown away. |
| Native 4× would be faster | ⚠️ only ~20% | Checked in code: the 2× MangaJaNai models shrink the image by 2 inside (pixel unshuffle, `shuffle_factor=2`) and then upscale 4×. So two 2× passes cost about 0.25 + 1.0 = 1.25 units vs **1.0** for one 4× pass. The author also says the 4× models are "higher quality but much slower" than 2× (at the same input). Most runs use 2×, so this only helps when 4× is picked (or with [#13](13-fit-small-panels-to-screen.md)). |
| Native 4× for **color** | 🟡 | The color zip the app downloads also has `4x_IllustrationJaNai_V2standard_FDAT_M_52k` (16 MB), but it's FDAT (GPU only). V3 has no 4× SPAN. For color 4×, two SPAN 2× passes on the Neural Engine will likely beat one FDAT 4× pass on the GPU. |
| spandrel loads SPAN | ✅ | spandrel 0.4.2 (installed, newest) loaded it as `SPAN` today. |
| License | ✅ | Same author, same CC BY-NC 4.0 as the current models. |

## 4. Recommended approach + rejected alternatives
| Option | Speed (color) | Change size | Verdict |
|---|---|---|---|
| **V3 SPAN 2× on the Neural Engine** | ~12× faster per tile | 3 lines in `janai.py` | ✅ **Recommended** |
| V3 FDAT M unshuffle 2× (newer FDAT) on the GPU | same as now | 2 lines | ❌ Not faster; only maybe better colors |
| V1 ESRGAN 2× on the Neural Engine | ~2.5× faster per tile | 2 lines | ❌ Slower than SPAN, softer, 106 s one-time conversion |
| Upgrade coremltools to 9.0 and retry FDAT on the Neural Engine | unknown | dependency upgrade, packaging risk | ❌ Not now; no sign it fixes FDAT |
| Real-CUGAN se for color | 25.6 s/chapter | new program + split | ❌ More code than SPAN |
| Native 4× MangaJaNai (B&W) | ~20% faster at 4× | 2–5 lines | 🟡 Optional, separate step |

Which V3 SPAN: **detail** (keeps the dot texture, closest to today's look in one crop) or **denoise** (the direct successor to V2, smoother). Test both (step 5) and pick one; ship one model only.

## 5. Files to change + functions to reuse
| File | Change |
|---|---|
| `janai.py` | `COLOR_MODEL_FILE` → `"2x_IllustrationJaNai_V3detail_SPAN_S_40k_fp16.safetensors"` (or V3denoise). `COLOR_MODEL_ZIP_URL` → `.../releases/download/3.0.0/IllustrationJaNai_V3detail.zip` (318 MB; V3denoise zip is 166 MB). In `upscale_image_with_janai`, color uses `use_neural_engine=True`. Update the docstring at the top. |
| `janai.py` (optional, native 4×) | `download_model_file`: also keep `4x_` files. A `MANGA_4X_MODEL_FILES` dict, and `upscale_in_tiles(..., scale=4, ...)` when the ratio is 4. `get_upscaler` passes the scale (today it's fixed at 2). |
| `gui_classes/SettingsUpscaleImages.py` | Only if the download size changes the "downloads about 600 MB" text: the B&W zip is 433 MB + color zip 318 MB (detail) or 166 MB (denoise). |
| `README.md`, `DEVELOPING.md`, `benchmarks/upscaling.md` | Model name, new numbers. |
| `tests/test_janai.py` | The fake-zip test checks that only `2x_` files are kept; update if 4× is added. |

Reuse as-is: `download_model_file`, `get_coreml_upscale_function` (converts and caches `*-256.mlpackage`), `get_upscaler`, `upscale_in_tiles`, `is_color_image`.

**Download size catch:** the V3 SPAN file is only sold inside a 318 MB (detail) or 166 MB (denoise) zip; the app's zip code downloads the whole zip once and keeps the `2x_` files (about 33 MB from V3detail). The old V2 color files stay on disk until deleted by hand.

## 6. Steps
- [ ] 1. On a **quiet Mac** (no other Claude jobs), time the current color model on all 96 color One Piece ch. 567 panels (fresh process). This is the "before".
- [ ] 2. In a scratch script, time V3detail SPAN and V3denoise SPAN on the same panels on the Neural Engine.
- [ ] 3. Check the Neural Engine is really used (SPAN on `CPU_AND_GPU` should be clearly slower; if not, it fell back).
- [ ] 4. Check SPAN on PyTorch (the non-Mac path) doesn't make NaNs in full precision.
- [ ] 5. Make a side-by-side page (like `Compare upscalers.html`) of now vs detail vs denoise on One Piece, Dragon Ball ch. 93 and Vagabond (painted color). The user picks one.
- [ ] 6. Change the 3 lines in `janai.py`, update the docs and benchmarks.
- [ ] 7. (Optional) Native 4× MangaJaNai: keep `4x_` files, add the 4× path, compare time and look vs two 2× passes on Shachou ch. 3.
- [ ] 8. Run the tests.

## 7. How to test it
- `venv/bin/python -m pytest -q -m "not e2e"` and `-m e2e` (the Best e2e test).
- In the app: Upscale One Piece ch. 567 with "Best". Check the time in the Progress tab and look at 5 panels next to the old output in `~/Documents/Panelyze/Best Upscale Test`.
- First-time path: point `MODELS_FOLDER` at an empty scratch folder, so the zip download and conversion run for real.

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | **Small**: about 3 lines + docs. Native 4× adds ~15 lines. |
| Value | **Medium–High**: color chapters (Dragon Ball, One Piece, Vagabond) could go from ~2.5 min to well under a minute with Best. |
| Risks | V3 is marked **pre-release** by its author. SPAN is "good on lightly degraded images", so it may be weaker on bad JPEG scans than FDAT. The detail model can "add too much noise or texture on some images". Today's timing was on a busy Mac. |
| Open questions | 1. Detail or denoise? (user picks from the comparison page). 2. Keep the old V2 FDAT as a choice? (recommend no: one model, simple). 3. Do native 4× now or wait for [#13](13-fit-small-panels-to-screen.md)? |

## 9. Sources
- MangaJaNai releases (3.0.0 V3 notes, model speeds, zip contents read today): https://github.com/the-database/MangaJaNai/releases
- coremltools releases (9.0 notes): https://github.com/apple/coremltools/releases , PyPI: https://pypi.org/project/coremltools/
- spandrel on PyPI (0.4.2 is the newest): https://pypi.org/project/spandrel/
- benchmarks/upscaling.md, HANDOFF.md, `janai.py`
- Today's test scripts: `/private/tmp/claude-501/-Users-curlos-Desktop-Github-Repos-manga-panel-splitter/8ee4c6a0-1364-4871-bb81-d6088b80b372/scratchpad/convert_check.py`
