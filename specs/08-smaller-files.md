# Spec 08: Smaller files by default

Roadmap item [#8](../ROADMAP.md#8-smaller-files-by-default). Related: [03 – Whole-series runs](03-whole-series-runs.md) (needs this to fit on the disk) and [16 – More MangaDex options](16-mangadex-options.md).

## 1. Summary
- **WebP by default:** make Upscale's output a real, small **WebP** (lossy, quality 90) by default, instead of PNG.
- **Comic files only:** add an option to keep **only the comic files** (.cbz) after a Pipeline run.

Why: upscaled PNGs are about 200 MB per chapter, which is too much for whole-series runs on a Mac with 26 GB free.

## 2. Is it doable?
**Yes**, but with a catch the roadmap missed:
- **waifu2x's own "webp" output is lossless**, so picking "webp" in the app today only saves about 43%, not 90%.
- To get the ~10× saving, the app has to re-save each image as lossy WebP after waifu2x.

## 3. What's already true (roadmap claims checked)
| Claim | Status | What's really true |
|---|---|---|
| Upscaled PNGs are 217 MB per chapter (Shachou) vs 22 MB as WebP | ✅ for **WebP 80% made with Pillow** | That's what benchmarks/file-sizes.md measured, but it isn't what the app makes. |
| "Default Upscale's image format to WebP: same look at a fraction of the size" | ⚠️ **not with the current code** | Measured on 10 upscaled Shachou panels: PNG **21.0 MB**, waifu2x WebP **12.0 MB** (pixel difference 0.0, so lossless), Pillow WebP q80 **2.4 MB**, q90 **3.3 MB**. The waifu2x source uses `WebPEncodeLossless*` (`src/webp_image.h`). |
| The Upscale "Image Format" dropdown already has webp | ✅ | `SettingsUpscaleImages.py`: jpg, png, webp. Default `"image_format": "png"` in `default_settings.py`. |
| Best (janai.py) saves WebP lossy | ✅ | `quality: 95` (about 4.0 MB for the same 10 panels) |
| Resizes after upscaling re-save at Pillow's default | ⚠️ new finding | The 4K cap, custom height and max width call `pil_image.save(output_image)`, so WebP becomes quality 80 there: a different quality than the rest. |
| The rest of the app reads WebP | ✅ | `utils.IMAGE_EXTENSIONS` has `.webp`. Tests already cover WebP from Upscale (`tests/test_upscale.py`) and Best (`tests/test_janai.py`). Images To Video with WebP input isn't tested yet. |
| A new default only reaches new installs | ⚠️ | `set_client_storage_default_values` only fills in **empty** settings, so your stored `"png"` stays until you change the dropdown or use "Reset All Settings". |
| Small comic files take "a few seconds" per chapter | ⚠️ **0.53 s per panel** | About 51 s per 97-panel chapter. `get_small_comic_file_image` uses `method=6`, the slowest WebP setting. |

**WebP speed/size on 10 upscaled panels (1880×1074, gray):**

| Pillow WebP setting | Size (10 panels) | Time per panel | Average pixel change (0–255) |
|---|---|---|---|
| PNG (now) | 21.0 MB | 0.03 s | 0 |
| waifu2x "webp" (now) | 12.0 MB | — | 0 |
| q90, method 0 | **3.47 MB** | **0.11 s** | ~1 |
| q90, method 4 (Pillow's default) | 3.31 MB | 0.24 s | 1.0 |
| q90, method 6 | 3.27 MB | 0.81 s | 1.0 |
| q80, method 4 | 2.48 MB | 0.24 s | 1.8 |

So **q90 with method 0** costs about 11 s per 97-panel chapter and makes the files **~6× smaller** than PNG. Method 6 costs 7× more time for 1% less size.

## 4. Recommended approach
| Option | Verdict |
|---|---|
| **A. Default `image_format` to `"webp"`, and when it's webp, re-save each finished image as WebP quality 90, method 0.** Use one small helper, `save_image(pil_image, path)`, everywhere Upscale saves (the 3 existing resizes + the new re-save + janai's save). | ✅ **Recommended.** About 15 lines. |
| B. Have waifu2x write PNG, then convert it to WebP | ❌ Same result, but more code: the output file names and the "did waifu2x make it?" check would change |
| C. Quality 80 (like the benchmark) | ❌ Smaller (2.5 vs 3.3 MB), but it's the master copy that gets made into comic files and video later; 90 leaves headroom. *Your call, see questions.* |
| D. Lossless WebP (what waifu2x does now) | ❌ Only 43% smaller |
| E. AVIF/JPEG XL | ❌ Pillow 10/11 support is patchy, and comic readers (Panels, Mihon) support WebP best |

**Comic files only:**

| Option | Verdict |
|---|---|
| **A. A Settings checkbox under the comic file dropdown: "Keep only the comic files (delete the image folders once the Pipeline finishes)".** Only enabled when a comic file size is picked. At the end of a successful `run_pipeline`, delete the image folders that have a matching `.cbz` next to them in the step folders. Keep `1-mangadex-download`, so the downloader can still resume (spec 03), unless you say otherwise. | ✅ **Recommended.** About 15 lines in `PipelineView.py`. |
| B. Delete right after each chapter's comic file is made | ❌ The next step needs those images |
| C. Ask the downloader for .cbz (`--save-as cbz`) | ❌ Panel-By-Panel needs loose images |
| D. Also for the single tabs | ❌ Not now: surprising to delete a tab's output. Pipeline only. |

**Optional quick win:** in `get_small_comic_file_image`, change `method=6` to `method=4`. That makes it **~3× faster** (0.81 → 0.24 s per panel in the test above) for ~1% bigger comic files. One-word change.

## 5. Files to change
| File | Change | Reuse |
|---|---|---|
| `default_settings.py` | `"image_format": "webp"`, and new `"keep_only_comic_files": False` | — |
| `utils.py` | New `save_image(pil_image, path)`: WebP/JPG → `quality=90`, WebP `method=0`; PNG as is. *(Optional: `method=6` → `4` in `get_small_comic_file_image`.)* | — |
| `gui_classes/UpscaleImagesView.py` | In the per-image loop of `process_image_folder`: if the format is webp and the image wasn't already re-saved by a resize, open it and `save_image` it. The 3 `pil_image.save(output_image)` calls → `save_image`. | `replace_extension` |
| `janai.py` | `result.save(output_image, **save_options)` → `save_image(result, output_image)` | — |
| `gui_classes/AppSettingsView.py` | The checkbox below the comic file dropdown | `WrappingCheckbox` |
| `gui_classes/PipelineView.py` | After a successful run, delete the step image folders that have a matching `.cbz` (not step 1). The review line says so. | `get_step_output_directory`, `PIPELINE_STEP_FOLDER_NAMES` |

## 6. Steps
- [ ] Add `save_image` and use it in Upscale (waifu2x path) and janai.
- [ ] Change the default to webp, and tell you to pick webp once in the dropdown (your saved "png" is kept).
- [ ] Tests for WebP size and quality.
- [ ] Add the "keep only comic files" checkbox, and the clean-up at the end of the Pipeline.
- [ ] (Optional) `method=4` for small comic files.
- [ ] Re-measure Shachou ch. 3 (97 panels) and update benchmarks/file-sizes.md and the README.

## 7. How to test
| Test | How |
|---|---|
| Unit: WebP output is lossy and small | Fake waifu2x writes a lossless WebP → after `process_image_folder`, the file is lossy and smaller (check with Pillow) |
| Unit: resizes keep quality 90 | Existing 4K-cap/height tests with `image_format="webp"` |
| Unit: comic-only clean-up | A fake pipeline run with `save_as_cbz="small"` and the checkbox on → `.cbz` files are kept, the image folders are gone, and `1-mangadex-download` is kept |
| Unit: off = no change | The existing tests pass |
| Real | Upscale Shachou ch. 3 (Fast and Best) with webp → expect about **30 MB** instead of 193–217 MB. Open a few side by side with the PNGs. |
| Real | Images To Video with WebP input (not tested yet) |

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | **Small:** ~30 lines plus tests |
| Value | **Medium–High:** ~6× less space; needed for spec 03 |
| Risks | Lossy: an average pixel change of ~1/255 at q90 (not visible, but it's not exact). Re-encoding for the small comic file loses a little more. The existing "png" setting isn't changed automatically. |

**Open questions for you:**
1. **Quality 90 or 80?** 90 = 3.3 MB, 80 = 2.5 MB per 10 panels.
2. Should Best's WebP drop from quality 95 to 90 to match? (4.0 vs 3.3 MB)
3. Should "keep only comic files" also delete the **downloaded pages** (step 1)? That saves ~3.8 GB for Slam Dunk, but resuming would then re-download.
4. Should your saved "png" setting be switched to webp automatically once, or will you change the dropdown yourself?
5. Do the optional `method=4` speed-up for small comic files? (~3× faster)

## 9. Sources
- waifu2x WebP encoder (lossless): https://github.com/nihui/waifu2x-ncnn-vulkan/blob/master/src/webp_image.h
- Pillow WebP options (`quality`, `method`): https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#webp
- [benchmarks/file-sizes.md](../benchmarks/file-sizes.md)
- Measurements in this spec: 10 upscaled Shachou ch. 3 panels (2×, Fast model), M1 Mac, 2026-11-19
