# Spec 24: Test the upscalers on non-manga images (game prestige icons)

New idea #24 (not in ROADMAP.md yet). A **test plan**, not a feature. Related: [05 – Faster Best for color](05-faster-best-color.md) (adds a new color model to compare), [09 – Blurry scans](09-blurry-scan-upscaling.md), [13 – Fit small panels to the screen](13-fit-small-panels-to-screen.md).

Checked on 2026-11-19. ✅ = checked today against the code or a real run, ⚠️ = a problem found, 🟡 = not confirmed.

## 1. Summary
Run every upscaler the app has on a small set of **Call of Duty prestige icons** (Black Ops 7 and Modern Warfare 2019): small images with flat colors, gradients, sharp edges and **transparent backgrounds**. Put the results side by side and pick what works.

The important finding before testing: **"Fast" and "Better" (waifu2x) keep transparency, but "Best" throws it away** (transparent areas turn black and the output has no alpha). So the test must either skip Best for transparent icons or include a tiny fix for it (section 4).

**The icons must come from the user.** They are Activision's artwork: the user drops them in a folder; they're never added to the repo.

## 2. Is it doable?
**Yes.** The Upscale tab already takes any folder of `.png / .jpg / .jpeg / .webp` images (`utils.IMAGE_EXTENSIONS`; the tab's label is "Folder", "any images can be upscaled, not just manga pages"). About 1 hour including the comparison page, once the icons are there.

## 3. What's already true (checked today)
| Claim | Status | What's really true |
|---|---|---|
| waifu2x keeps transparency | ✅ tested | A 128 px RGBA test icon (transparent corners, a half-transparent square) upscaled 2× with `upconv_7` and `cunet`: output is **RGBA**, corners stay `(0,0,0,0)`, the half-transparent square keeps alpha 128. |
| Best (MangaJaNai / IllustrationJaNai) keeps transparency | ⚠️ **No** | `janai.upscale_image_with_janai` does `image.convert("RGB")`: alpha is dropped, transparent pixels become whatever color is hidden under them (black in the test icon), and the saved file has no alpha. |
| Best picks the right model for a color icon | ⚠️ risk | `is_color_image` also works on `convert("RGB")`. Transparent pixels (black underneath) count as "not colorful". An icon that's mostly transparent with under 2% colorful pixels would be called black and white → MangaJaNai → saved as **grayscale**. Most icons are well over 2%, but check each one. |
| Black and white icons in Best | ⚠️ | Saved as grayscale (`result.convert("L")`): fine for gray icons, but alpha is lost too. |
| The resize steps keep transparency | ✅ | The 4K cap, custom height and max width use Pillow `thumbnail`/`resize` + `save`, which keep RGBA in PNG/WebP. |
| JPG output | ⚠️ | JPG can't store transparency. Use **png** (the default, `"image_format": "png"`) or webp for this test. |
| Small comic files | ⚠️ (not needed here) | `get_small_comic_file_image` does `convert("RGB")`: transparency becomes black. Turn the .cbz setting off for this test. |
| Default noise level | ✅ | `"noise_level": 0` in `default_settings.py`. Noise reduction can flatten gradients, so test -1, 0 and 1. |
| `upconv_7` has no 1× | ✅ | HANDOFF.md / `get_waifu2x_model`: images not made bigger use cunet. |
| Which models suit flat-color art | 🟡 (to test) | waifu2x "anime style art" models are trained on flat-color anime art (likely good on flat colors and edges; may band gradients). IllustrationJaNai is trained on color illustrations (likely best on gradients and line edges). MangaJaNai is a black-and-white manga model and shouldn't be used on color. If [05](05-faster-best-color.md) lands, IllustrationJaNai V3 SPAN joins the test. |

## 4. Recommended approach + rejected alternatives
| Option | Verdict |
|---|---|
| **A scratch comparison run (no app change) + one small fix if Best wins** | ✅ Recommended |
| Test only through the app's Upscale tab | ❌ Best would silently lose the transparency, which hides how good the model is on the picture itself |
| Add a "non-manga" mode to the app now | ❌ Wait for the results |
| Fix alpha in Best before testing | ❌ Test first; fix only if Best is the winner |

**The small Best fix, if needed (≈ 6 lines in `janai.py`):** if the image has an alpha channel, keep the alpha aside, upscale the color as today, enlarge the alpha with Lanczos (or with the same model as a gray image) to the new size, and put it back before saving (skip the `convert("L")` in that case). Also run `is_color_image` only on the visible pixels.

**What to compare (one row per icon, one column per upscaler):**

| Column | How |
|---|---|
| Original (shown enlarged with nearest-neighbor, so pixels are visible) | Pillow |
| Plain Lanczos 4× | Pillow |
| Fast (waifu2x upconv_7), noise -1 / 0 / 1 | the waifu2x program, same flags as the app |
| Better (waifu2x cunet), noise 0 / 1 | the waifu2x program |
| Best: IllustrationJaNai V2 (today) | `janai.py` functions, with the alpha kept aside in the scratch script |
| IllustrationJaNai V3 SPAN (if spec 05 is done) | same |

**What to look at:**

| Look for | Where |
|---|---|
| Edges: crisp or wobbly, halos or dark fringes along the transparent border | the outline of the icon |
| Gradients: smooth or banded/blotchy | metallic shading, glows |
| Flat colors: stay flat or get texture/noise | big single-color areas |
| Color shift (purple/blue fringes were seen with waifu2x fast on One Piece) | bright edges |
| Small text and numbers on the icon (prestige level digits) | zoomed crops |
| Transparency: same shape, half-transparent glow kept | check on a checkerboard and on a black background |
| Time per icon | printed by the script |

Show each result on a **checkerboard and a dark background**, since icons are used on dark game menus.

## 5. Files to change + existing functions to reuse
No app files change for the test. A scratch script only (in the session scratchpad), reusing:
- `waifu2x.upscale_with_waifu2x(input, output, upscale_ratio, noise_level, image_format, model=...)` and `utils.get_waifu2x_path()`.
- `janai.download_model_file`, `janai.get_upscaler`, `janai.COLOR_MODEL_FILE`, `janai.COLOR_MODEL_ZIP_URL` (to run IllustrationJaNai while keeping the alpha aside).
- The `Compare upscalers.html` pages in `~/Documents/Panelyze/Upscale Comparison - …` as the layout to copy. Those folders are no longer kept (2026-11-21): make a similar page (one row per image, one column per upscaler, same size side by side).

Only if Best wins: `janai.py` (`upscale_image_with_janai`, `is_color_image`) + a test in `tests/test_janai.py` that an RGBA image comes out RGBA with the same transparent corners.

## 6. Steps
- [ ] 1. **User:** put 6–10 prestige icons (PNG with transparency, as big as you have them; a mix of BO7 and MW19, some with gradients and some with digits) in a folder, e.g. `~/Documents/Panelyze/24-non-manga-upscale-test/originals` (the spec's own folder). Say their source size (e.g. 128, 256 px).
- [ ] 2. Check each icon: size, has alpha, `is_color_image` result.
- [ ] 3. Scratch script: run every column of the table at 4× (icons are small; also 2× for one icon), output to `~/Documents/Panelyze/24-non-manga-upscale-test/<upscaler>`.
- [ ] 4. Build `Compare upscalers.html` with checkerboard and dark backgrounds, plus zoomed crops of an edge, a gradient and the digits.
- [ ] 5. User picks the winner per type of icon. Write the result in a short "Non-manga images" section of benchmarks/upscaling.md.
- [ ] 6. If Best (or V3 SPAN) wins: propose the alpha fix as a separate small change.

## 7. How to test it
- It is the test. Success = the comparison page, times per icon, and a clear "use X for icons" line in benchmarks/upscaling.md.
- Don't open Finder: give the path of the HTML page and let the user open it.
- Run it on a quiet Mac (no other benchmarks), one upscaler at a time.

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | **Small**: ~1 hour after the icons arrive. The alpha fix, if wanted: Small. |
| Value | **Low–Medium**: tells whether Panelyze is useful beyond manga; found a real alpha bug in Best on the way. |
| Risks | Copyrighted images: keep them out of the repo and out of any shared page. Very small icons (64–128 px) at 4×–8× may make every AI model invent texture; plain Lanczos might honestly be the winner. |
| Open questions | 1. What size are the icons, and what size do you want them (for a video, a wallpaper, a website)? 2. Should Best keep transparency in the app (the fix), or is waifu2x enough for icons? 3. Add a general-purpose model (e.g. Real-ESRGAN x4plus) to the comparison, or only the app's own upscalers? (Recommend only the app's own, plus V3 SPAN if spec 05 is done.) |

## 9. Sources
- `janai.py` (`upscale_image_with_janai`, `is_color_image`), `waifu2x.py`, `utils.py` (`IMAGE_EXTENSIONS`, `get_small_comic_file_image`), `default_settings.py`, `gui_classes/UpscaleImagesView.py`.
- Today's transparency test: `/private/tmp/claude-501/-Users-curlos-Desktop-Github-Repos-manga-panel-splitter/8ee4c6a0-1364-4871-bb81-d6088b80b372/scratchpad/alpha/` (input `icon.png` and the waifu2x outputs).
- benchmarks/upscaling.md (color results on One Piece, purple fringes with waifu2x fast).
- MangaJaNai / IllustrationJaNai: https://github.com/the-database/MangaJaNai
