# Spec 13: Upscale every panel to fit the screen

New idea #13 (not in ROADMAP.md yet). **Closely tied to [06 – Upscale only as much as the video needs](06-upscale-to-video-size.md):** both pick each panel's upscale ratio from a target box; 06's box is the video frame, this one's is the reading screen. Build them on the same helper. Also related: [22 – How to read the panels](22-panel-reader.md), [05 – Faster Best](05-faster-best-color.md) (makes 4× affordable), [08 – Smaller files](08-smaller-files.md) (the resize re-saves files).

Checked on 2026-11-19. ✅ = checked today against the code or real files, ⚠️ = an older note that's now out of date, 🟡 = not confirmed.

## 1. Summary
Today every panel gets the **same ratio** (default 2×), so a 235 px tall panel stays 10× smaller than a 2,000 px splash panel. Instead, give each panel **its own ratio**: the smallest of 1×, 2×, 4× (up to the "Upscale Ratio" setting) that makes it **fill a target box** (e.g. an iPad screen, 2048×2732), then resize it to fit that box exactly. Small panels get more AI upscaling, big ones get less or none, and every panel ends up the same size on screen.

It's mostly a generalization of the existing `get_capped_upscale_ratio` (which already finds "the smallest ratio that reaches 3840 px") plus the existing "Use Custom Image Height" resize.

## 2. Is it doable?
**Yes, small.** The cost is the real question: big ratios are expensive, because a 4× is two 2× passes and an 8× is three, each on a 4× bigger image.

Real panel sizes (measured today):

| Chapter | Panels | Panel height: smallest / middle / biggest |
|---|---|---|
| Shachou ch. 3 | 97 | 235 / 458 / 4,092 px |
| One Piece ch. 567 | 97 | 178 / 373 / 1,367 px |

Ratio each panel would need to fill the box (up to 8×):

| Target box | Shachou: panels at 1× / 2× / 4× / 8× | One Piece: 1× / 2× / 4× / 8× |
|---|---|---|
| Today (2× everything, 4K cap) | 1 / 96 / – / – | – / 97 / – / – |
| iPad screen 2048×2732 | 1 / 8 / 53 / 35 | – / 1 / 29 / 67 |
| 1080p video frame 1920×1080 (= spec 06) | 9 / 21 / 67 / – | 1 / 6 / 71 / 19 |
| Height of the tallest panel | 1 / 3 / 6 / **87** | 1 / 4 / 52 / 40 |

Rough work compared with today (counting AI passes by pixels: 2× = 1, 4× = 5, 8× = 21):

| AI ratio allowed, iPad box | Shachou | One Piece | Fast (30 s today) | Best (138 s today) |
|---|---|---|---|---|
| Up to 8× | ~10× more work | ~16× | ~5–8 min | ~25–35 min |
| **Up to 4×** | **~4.6×** | **~5×** | **~2.5 min** | **~10 min** |
| Up to 2× (AI), then plain resize to the box | ~1× (same as today) | ~1× | ~30 s | ~2.3 min |

These are estimates from pixel counts, not timed runs (other jobs were using the GPU today). So **the max AI ratio must stay the user's choice**: the existing "Upscale Ratio" dropdown becomes "up to".

## 3. What's already true (claims checked)
| Claim | Status | What's really true |
|---|---|---|
| `get_capped_upscale_ratio` can be reused | ✅ | `utils.py`: returns the smallest ratio (1, 2, 4, … up to `upscale_ratio`) where the **longest side reaches `max_side`** (3840). That's "fill a square box". Fitting a screen only needs a **width and a height** instead of one side. Tested in `tests/test_utils.py::test_capped_upscale_ratio`. |
| Ratios are powers of 2 | ✅ | waifu2x `-s` and `upscale_image_with_janai` (4× = two 2× passes) only do 1, 2, 4, 8…; the dropdown has 1–32. |
| Per-image ratios already work | ✅ | `UpscaleImagesView.process_image_folder` builds `image_upscale_ratios` per file; `upscale_all_images` runs waifu2x once **per ratio group** and Best per image. Nothing new needed there. |
| An exact-size resize already exists | ✅ | "Use Custom Image Height" resizes each output to that height with Lanczos (`process_image_folder`), and "Use Max Image Width" then shrinks wide ones. Together that **is** "fit inside width × height". But today the AI ratio ignores it, so small panels are AI 2× and then **stretched by Lanczos**, which is soft. |
| An iPad-sized box is already in the code | ✅ | `utils.SMALL_COMIC_FILE_IMAGE_SIZE = (2048, 2732)` for the small .cbz (shrink only). |
| The video already fits each panel to the frame | ✅ | `VideoCreatorFromImages.get_image_clip_fit_to_video_frame` scales every image (up or down) to the frame. So in the **video**, small panels already fill the screen; this idea is about **reading** (the folder / .cbz). |
| Reader apps show small panels smaller | 🟡 | Depends on the reader's mode. In Panels' "fit to screen" mode every image is enlarged to the screen ([22](22-panel-reader.md)), so the problem is **sharpness**, not size. In modes that show real pixel size or fit the width, small panels look small. Ask the user where they saw it. |
| Best picks MangaJaNai's model by page height for each pass | ✅ | `page_height * 2**upscale_pass`, so any ratio works. |

## 4. Recommended approach + rejected alternatives
**Target-size logic (recommended):**
1. Target box = the user's height × width (default: iPad 2048×2732). If "Don't upscale past 4K" is on, each side is also capped at 3840.
2. Each panel's AI ratio = smallest of 1, 2, 4, … that makes it **touch the box** (width ≥ box width **or** height ≥ box height), but no more than the "Upscale Ratio" setting.
3. After the AI upscale, resize to **fit the box exactly** (scale = min(box width ÷ width, box height ÷ height)), up or down, Lanczos. Usually this is a shrink (AI went a bit past the box); it's an enlargement only when the max ratio stopped the AI short.
4. Panels already bigger than the box: ratio 1 (waifu2x noise clean-up, as today) and shrink to the box.

**With spec 06:** same helper, different box:

| Settings | Box used |
|---|---|
| Fit to screen on | The screen box (it's for reading; the video shrinks images to its frame anyway) |
| Fit to screen off, Pipeline makes a video (spec 06) | The video frame, e.g. 1920×1080 |
| Neither | Today's behavior (fixed ratio, 4K cap) |
| Always | Each side ≤ 3840 when the 4K cap is on |

| Option | Verdict |
|---|---|
| **Fit inside a width × height box, AI ratio up to the dropdown, then exact resize** | ✅ Recommended. Handles tall and wide panels; one rule for #13 and #6. |
| Same **height** for every panel (no width limit) | ❌ A wide 3:1 panel at 2,732 px tall becomes 8,000+ px wide and won't fit a phone. (OK only together with Max Width, which is the box.) |
| Target = **the tallest panel** of the chapter | ❌ One splash or cover page decides everything: on Shachou (4,092 px tallest) 87 of 97 panels would need 8×. |
| Target = this Mac's screen size, read from Flet | ❌ The user reads on iPhone/iPad, not on this Mac; Flet's window size isn't the screen. |
| AI all the way to the box (up to 8×), no plain resize | ❌ 10–16× slower (table above). |
| Plain resize only (no per-panel AI ratio) | ❌ That's today's "Custom Image Height": soft small panels. |

**How it shows up as a setting** (recommended, smallest change): reuse the two existing boxes.
- Rename the "Use Custom Image Height" checkbox to **"Make every image the same size (small panels get upscaled more)"**, with Height and Max Width fields under it (defaults 2732 and 2048, hint: "2732 × 2048 fits an iPad, 2796 × 1290 an iPhone").
- When it's on, the "Upscale Ratio" label reads **"Upscale Ratio (most AI upscaling per image)"**.
- The separate "Use Max Image Width" checkbox stays for people who use it alone.

## 5. Files to change + existing functions to reuse
| File | Change |
|---|---|
| `utils.py` | Add `get_upscale_ratio_to_fit(width, height, max_width, max_height, max_ratio)` (the same 4-line loop, with `width * ratio < max_width and height * ratio < max_height`). Make `get_capped_upscale_ratio` call it with `(max_side, max_side)`, so the 4K cap and spec 06 share it. |
| `gui_classes/UpscaleImagesView.py` | In `process_image_folder`'s ratio loop: when the fit setting is on, use `get_upscale_ratio_to_fit` with the box (each side capped at `MAX_UPSCALED_IMAGE_SIDE` if the 4K cap is on). In the resize loop: replace the "custom height" resize with "fit the box" (one `resize` with `scale = min(...)`). Keep the 4K shrink and max-width code as they are. |
| `gui_classes/SettingsUpscaleImages.py` | Checkbox label, the width field moved under it, Upscale Ratio label hint. |
| `default_settings.py` | Defaults `custom_panel_image_height: "2732"` and a new `fit_image_width: "2048"` (or reuse `max_image_width`; decide in review). |
| `gui_classes/PipelineView.py` | The review line (line 146) says "fit 2048×2732" instead of "height …px". |
| `tests/test_utils.py`, `tests/test_upscale.py` | New ratio cases (tall, wide, already big, capped by max ratio); the old `test_capped_upscale_ratio` cases must still pass. One test that a small and a big image both end up fitting the box. |

Reuse: `get_capped_upscale_ratio`, `MAX_UPSCALED_IMAGE_SIDE`, `SMALL_COMIC_FILE_IMAGE_SIZE` (as the default box), the per-ratio grouping in `upscale_all_images`, `upscale_image_with_janai`.

Note from [08](08-smaller-files.md): the resize step re-saves with Pillow's default quality (WebP/JPG 80). Pass the same quality as elsewhere when saving.

## 6. Steps
- [ ] 1. Ask the user the open questions below (where small panels looked small; iPad or iPhone box; max AI ratio).
- [ ] 2. Add `get_upscale_ratio_to_fit` in `utils.py`; make `get_capped_upscale_ratio` use it; run the existing tests (no change expected).
- [ ] 3. Use it in `process_image_folder` when the setting is on; replace the custom-height resize with the fit-the-box resize.
- [ ] 4. Settings labels, defaults, Pipeline review line.
- [ ] 5. Tests.
- [ ] 6. Timing on a quiet Mac: Shachou ch. 3 and One Piece ch. 567, Fast and Best, with "up to 2×" and "up to 4×". Add to benchmarks/upscaling.md.
- [ ] 7. Look: open the small .cbz in Panels on the iPad/iPhone (or Panels for Mac) and compare small panels before and after.
- [ ] 8. When spec 06 is built, pass the video frame as the box (no new helper).

## 7. How to test it
- `venv/bin/python -m pytest -q -m "not e2e"` and `-m e2e`.
- Unit cases for `get_upscale_ratio_to_fit` (box 2048×2732, max 4): 300 wide × 235 tall → 4 (stopped by the max); 700 × 1,000 → 4 (2× is only 1,400 × 2,000); 1,000 × 3,000 → 1 (already taller than 2,732); 1,500 × 300 → 2 (the width reaches 2,048 first).
- Output check script: every output image has width = 2048 or height = 2732 (± 1 px), none bigger.
- By eye in a reader app.

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | **Small**: ~25 lines + labels + tests. |
| Value | **Medium–High** for reading: every panel the same size and sharp. Low for the video (it already fills the frame). |
| Risks | Much slower with 4× (≈ 5× the work; Best on color is only affordable after [05](05-faster-best-color.md)). Bigger files: every panel becomes ~2048×2732 instead of ~900×700 (see [08](08-smaller-files.md)). Very small panels (a lone sound effect) blown up to a full screen can look odd. Changing what an existing checkbox means could surprise someone who used "Custom Image Height" for another reason. |
| Open questions | 1. **Where** did the small panels look small: Panels in which mode, Finder/Preview, or the video? (If the reader already fits to screen, the gain is sharpness, not size.) 2. iPad box (2048×2732), iPhone box (1290×2796), or a custom one? 3. Max AI ratio: 2× (no extra time, softer small panels) or 4× (≈ 5× the time)? 4. Should panels **bigger** than the box be shrunk too (consistent size, smaller files) — recommended yes. 5. Reuse "Max Image Width" as the box width, or a new field? |

## 9. Sources
- `utils.get_capped_upscale_ratio`, `SMALL_COMIC_FILE_IMAGE_SIZE`; `gui_classes/UpscaleImagesView.py` (`process_image_folder`, `upscale_all_images`); `VideoCreatorFromImages.get_image_clip_fit_to_video_frame`; `janai.upscale_image_with_janai`.
- Panel sizes measured today with `/private/tmp/claude-501/-Users-curlos-Desktop-Github-Repos-manga-panel-splitter/8ee4c6a0-1364-4871-bb81-d6088b80b372/scratchpad/sizes.py` on `~/Documents/Panelyze/Upscale Comparison - Shachou Ch 3/1 - Original panels` and `.../Upscale Comparison - One Piece Ch 567/1 - Original panels`. The old test folders in `~/Documents/Panelyze/` are no longer kept (user decision, 2026-11-21): download what's needed again into the spec's own folder (`~/Documents/Panelyze/<worktree-folder>/`). (Shachou ch. 3 and One Piece ch. 567, then Panel-By-Panel.)
- benchmarks/upscaling.md (Fast 30 s / Best 138 s on Shachou ch. 3; 142 s on One Piece).
- Spec 22 (Panels app, fit-to-screen reading), spec 06, spec 08.
