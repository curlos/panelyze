# Spec 09: Better upscaling for blurry scans

Roadmap item [#9](../ROADMAP.md#9-better-upscaling-for-blurry-scans). Related: [05 – Faster Best for color](05-faster-best-color.md) (same model code), [13 – Fit small panels to the screen](13-fit-small-panels-to-screen.md).

Checked on 2026-11-19. ✅ = checked today against the code or the web, ⚠️ = an older note that's now out of date, 🟡 = not confirmed.

## 1. Summary
**Measure first, then build only the simple part.** A quick check of the user's own 28 downloaded series showed that real "fake 4K" (big but blurry) images are **rare in manga** and show up mainly in **Korean webtoons**. So:
1. Add a small, automatic check: "would this image lose anything if it were 75% or 50% as big?" If not, shrink it to that size before the AI upscale (the AI then does more real work, and it's faster).
2. Don't add Real-ESRGAN now. Its anime models are from 2021–2022, the authors themselves warn about text, and MangaJaNai/IllustrationJaNai already clean blur and JPEG damage. Test it once on speech bubbles (step 5) and only add it if it clearly wins.

## 2. Is it doable?
**Yes**, the shrink step is a few lines of Pillow and numpy. How much it helps is unknown until it's tried on a real blurry chapter.

**How blurry are the user's chapters?** Measured today: shrink each page with Lanczos, enlarge it back, and compare (PSNR in dB, gray, 3 pages per series). **Above about 40 dB the shrink loses almost nothing** = the image is bigger than its real detail.

| Series (page height) | Shrink to 75% | Shrink to 50% | Fake hi-res? |
|---|---|---|---|
| Shachou (1600) | 27–28 dB | 22–23 dB | No |
| One Piece color (1200) | 23 dB | 19 dB | No |
| Vagabond color (3400) | 26–28 dB | 21–24 dB | No: big **and** detailed |
| Skip Beat (1140) | 18–22 dB | 16–19 dB | No (lots of fine screentone) |
| Kimi ni Todoke (800–1275) | 23–33 dB | 22–29 dB | No |
| Dragon Ball color (2400) | 31–34 dB | 25–28 dB | Slightly soft |
| Webtoons: Iphak Yongbyeong, SSS-geup, Neo man Boindan, Under the Oak Tree (6,000–29,000 tall strips) | 33–39 dB | 28–33 dB | Soft |
| **Oemo Jisangjuui (webtoon)** | **42–45 dB** | **37–39 dB** | **Yes** |
| Jeonjijeok Dokja Sijeom (webtoon) | 31–41 dB | 26–36 dB | Some pages |

So for manga the shrink step would almost never trigger; for some webtoons it would.

## 3. What's already true (roadmap claims checked)
| Claim | Status | What's really true |
|---|---|---|
| waifu2x and MangaJaNai can't fix a big blurry image | ✅ partly | benchmarks/upscaling.md says so for waifu2x. MangaJaNai's own goal is to "clean up JPEG and moiré artifacts" in low-quality digital manga, so it does some repair, but only at the right input size (it's trained per page height, 1200–2048 px). |
| "Shrink, then upscale" idea | 🟡 untested | Nothing in the code does it. The only shrink test was "panels to 75% first" for speed (benchmarks/upscaling.md): **visibly softer** on Shachou, which matches the table above (Shachou isn't fake hi-res). So the shrink must only happen when the check says it's safe. |
| Real-ESRGAN's anime model is trained on blurry, compressed images | ✅ | Real-ESRGAN trains on synthetic blur + noise + JPEG. Anime models: `RealESRGAN_x4plus_anime_6B` (4× only, ESRGAN with 6 blocks) and `realesr-animevideov3` (small "compact" model, 2–4×). Latest release v0.3.0 (Sep 2022). License BSD-3. A ready Mac program exists: `realesrgan-ncnn-vulkan-20220424-macos.zip`, run like waifu2x. |
| "Testers report it can distort text" | ✅ roughly | The project itself says its models "may not perform well on human faces, text, etc." No side-by-side test against MangaJaNai on speech bubbles was found. |
| Newer models | ✅ found, none clearly better for this | OpenModelDB: **2x Manga Ora** (DAT, 2023, CC BY-NC-SA, "restore screentones and remove compression artifacts" for 650–900 px wide images; DAT is slow and won't run on the Neural Engine). **IllustrationJaNai V2 DeJPEG** 1× and 2× (FDAT, color, removes JPEG damage only). **IllustrationJaNai V3denoise** (color, Nov 2025; see [05](05-faster-best-color.md)). No new black-and-white MangaJaNai since V1 (May 2024). |
| spandrel can load Real-ESRGAN models | ✅ | Both are architectures spandrel 0.4.2 supports (ESRGAN/RRDB and SRVGGNetCompact), so they could reuse `janai.py`'s Core ML path, no new program needed. |

## 4. Recommended approach + rejected alternatives
| Option | What it does | Change size | Verdict |
|---|---|---|---|
| **Auto shrink to real detail, then the normal upscaler** | Shrinks only images that lose < ~1% detail (PSNR ≥ 40 dB at 75% or 50%), then upscales by 2× more to get the same final size | ~20 lines in `utils.py` + a call in `UpscaleImagesView.py` | ✅ **Recommended**, as a setting that's **off by default** until tested |
| Real-ESRGAN anime as a 4th "Upscale Model" | New model choice | new download + dropdown entry + tests | 🟡 Only if step 5 shows it beats MangaJaNai on blurry pages **without** hurting text |
| IllustrationJaNai DeJPEG 1× before upscaling | Removes JPEG blocks on color | new model, extra pass | ❌ Not now; color only, and V3denoise covers much of it |
| 2x Manga Ora | Manga restoration | DAT: slow, GPU only | ❌ Too slow on an M1 |
| A sharpening filter after upscaling | Fake crispness | 2 lines | ❌ Makes halos; doesn't add detail |

**How the shrink works (simple version):**
1. For each image, shrink a copy to 50%, enlarge back, measure PSNR. If ≥ 40 dB, use 50%. Else try 75%. Else leave it.
2. Shrink the image to that size (Lanczos) in the temporary folder, and raise its upscale ratio so the final size is the same (75% → still 2× upscale + a final Lanczos to the old size; 50% → 4× instead of 2×).
3. The 4K cap and custom height still apply afterwards, as today.

Keeping only 50% would be simpler (power of 2 = no extra resize). Recommend **50% only** for the first version.

## 5. Files to change + functions to reuse
| File | Change |
|---|---|
| `utils.py` | New `get_real_detail_scale(image)` → 0.5 or 1.0 (PSNR check on a grayscale copy, max 1024 px wide for speed). |
| `gui_classes/UpscaleImagesView.py` | In `process_image_folder`, when the new setting is on: for images where it returns 0.5, save a half-size copy into the input of the waifu2x group / Best call and double that image's ratio in `image_upscale_ratios`. The existing per-image resize loop already brings everything to the right final size. |
| `gui_classes/SettingsUpscaleImages.py` | A `WrappingCheckbox`: "Shrink blurry images before upscaling (for big but soft scans, e.g. some webtoons)". |
| `default_settings.py` | `"shrink_blurry_images": False`. |
| `tests/test_utils.py`, `tests/test_upscale.py` | A blurred test image returns 0.5; a sharp checkerboard returns 1.0; the image gets twice the ratio. |

Reuse: `get_capped_upscale_ratio` (the 4K cap still works on the shrunk size), `link_or_copy_file` / the temporary group folder in `upscale_all_images`, the existing final resize loop.

## 6. Steps
- [ ] 1. Ask the user for a chapter that looks blurry to them (or use Oemo Jisangjuui, already downloaded).
- [ ] 2. Scratch test: on 10 of its panels, compare "upscale 2×" vs "shrink to 50% + upscale 4×" with Fast and Best, same final size. Side-by-side page.
- [ ] 3. Same on 10 Shachou panels with the check on: confirm it **doesn't** trigger (0 shrunk).
- [ ] 4. If step 2 is a clear win, build the check + setting (off by default).
- [ ] 5. (Separate) Real-ESRGAN check: run `realesr-animevideov3` 2× and `RealESRGAN_x4plus_anime_6B` (ncnn program, scratch folder) on the blurry chapter and on 10 Shachou speech bubbles. Zoom on the text. Report; add as a model only if it wins.
- [ ] 6. Tests, docs (README "Upscale" section, benchmarks/upscaling.md).

## 7. How to test it
- Fast tests: `venv/bin/python -m pytest -q -m "not e2e"`.
- By eye: the comparison page from step 2, zoomed on text, lines and screentone.
- Timing: the check costs one shrink + enlarge per image; target < 0.05 s per panel. Measure on Shachou ch. 3 (97 panels).

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | **Small** (shrink check). Real-ESRGAN as a model: Medium. |
| Value | **Low** for the user's manga (none of the 18 Japanese manga series looked fake hi-res), **Medium** for webtoons. |
| Risks | A wrong "blurry" call makes a sharp image softer (that's why it's off by default and uses a strict 40 dB line). Webtoon strips are 6,000–29,000 px tall: shrinking and checking whole strips uses memory; check a resized copy. |
| Open questions | 1. Does the user actually see blurry scans, and in which series? 2. Is webtoon support in scope for Panelyze (Panel-By-Panel is built for pages)? 3. 50% only, or also 75%? |

## 9. Sources
- Real-ESRGAN anime models: https://github.com/xinntao/Real-ESRGAN/blob/master/docs/anime_model.md , releases: https://github.com/xinntao/Real-ESRGAN/releases
- Real-ESRGAN note on text: https://mintlify.com/xinntao/Real-ESRGAN/models/anime-models
- MangaJaNai README and releases: https://github.com/the-database/MangaJaNai , https://github.com/the-database/MangaJaNai/releases
- 2x Manga Ora: https://openmodeldb.info/models/2x-Manga-Ora ; OpenModelDB tags: https://openmodeldb.info/tags
- Today's blur check: `/private/tmp/claude-501/-Users-curlos-Desktop-Github-Repos-manga-panel-splitter/8ee4c6a0-1364-4871-bb81-d6088b80b372/scratchpad/detail.py` on `~/Documents/Panelyze/MangaDex Downloads` (pages 4–6 of each series)
- benchmarks/upscaling.md ("Shrinking panels to 75% first": visibly softer)
