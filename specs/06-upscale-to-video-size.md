# Spec 06: Upscale only as much as the video needs

Roadmap #6. Checked on 2026-11-19. ✅ = checked today against the code or a real run, ⚠️ = the note is wrong or out of date, 🟡 = not confirmed.

**Closely tied to [13 – Upscale every panel to fit the screen](13-fit-small-panels-to-screen.md):** both pick each panel's upscale ratio from a target box. 06's box is the video frame (e.g. 1920×1080), 13's is the reading screen. Build them on **one shared helper** (`get_upscale_ratio_to_fit`, defined in spec 13).

## 1. Summary
When the Pipeline also makes a video, each panel only needs to be upscaled until it fills the video frame, because the video resizes it to the frame anyway. The idea: give each panel the smallest ratio (1×, 2×, 4×…, up to the "Upscale Ratio" setting) that fills the frame.

**What the real runs showed:** at the **default 2×** this saves **nothing**. It's even a bit slower, because the panels that drop to 1× get a slow clean-up pass (waifu2x cunet) instead of the fast 2× model. It only pays off at **4×**: **28% faster** on Shachou ch. 3 at 1080p (104 s → 74 s), and about **47%** if panels that drop to 1× are just copied.

## 2. Is it doable?
**Yes, small:** about 15 lines plus tests. But it's **only worth doing if the user upscales 4× (or more)**, or as a free extra once spec 13's helper exists.

### Measured today (waifu2x Fast, Shachou ch. 3, 97 panels, M1)
One run at a time, fresh process per run. Each 2× setup was run twice.

| Upscale Ratio | Rule | Panels at 1× / 2× / 4× | Time |
|---|---|---|---|
| 2× | Today (4K cap only) | 1 / 96 / – | **37.3 s, 33.0 s** |
| 2× | Cap at the frame's longest side (1920) | 5 / 92 / – | 35.0 s |
| 2× | **Fit the 1920×1080 frame** | 9 / 88 / – | 42.4 s, 34.8 s ❌ slower |
| 4× | Today (4K cap only) | 1 / 4 / 92 | **103.9 s** |
| 4× | Cap at the frame's longest side (1920) | 5 / 7 / 85 | 94.5 s (−9%) |
| 4× | **Fit the 1920×1080 frame** | 9 / 21 / 67 | **74.3 s (−28%)**, of which 19.3 s is the 1× clean-up of 9 big panels |
| 4× | Fit the frame, but never below 2× | 1 / 29 / 67 | 101.4 s (−2%): the big panels get 2× instead |
| 4× | Fit the frame, panels at 1× just copied | 9 / 21 / 67 | **about 55 s (−47%)**, estimated: the 74.3 s run without its 1× group |

One Piece ch. 567 (color, small panels) at 4×: 73.2 s today vs 75.7 s with "fit the frame, never below 2×" (no gain).

A second round was thrown away: another job was running Magi on the CPU at the same time and every run took 2–3× longer.

### Why 1× isn't free
| Fact | Where |
|---|---|
| The Fast model (`upconv_7`) has no 1× model, so 1× images use **cunet** (the slow one) for a clean-up pass | `waifu2x.get_waifu2x_model` ✅ |
| The panels that drop to 1× are the **biggest** ones (they already fill the frame), so the slow pass is on the most pixels | measured: 9 panels, 19–20 s |
| Each extra ratio group is one more waifu2x start-up (model load) | `UpscaleImagesView.upscale_all_images` ✅ |

### What the cap does at other resolutions (pixel counts, not timed)
Output pixels compared with today. Upscalers work on every pixel, so time follows these roughly.

| Video | Shachou 2× | Shachou 4× | One Piece 4× | Dragon Ball ch. 93, 4× |
|---|---|---|---|---|
| 720p 16:9 | −35% | −75% | −68% | −86% |
| **1080p 16:9 (default)** | −29% | −40% | −27% | −62% |
| 1440p 16:9 | −20% | −26% | −19% | −48% |
| 2160p 16:9 | 0% | −11% | −11% | −13% |
| 1080p 9:16 (1080×1920) | −20% | −61% | −49% | −73% |

At 2×, almost all of the "saved" pixels come from panels moved to 1×, and the measurement above shows those don't actually save time.

## 3. What's already true (claims checked)
| Claim (ROADMAP #6) | Status | What's really true |
|---|---|---|
| "In a 1080p video, panels are shrunk to fit the frame anyway" | ✅ | `VideoCreatorFromImages.get_image_clip_fit_to_video_frame` scales every image **up or down** to fit the frame (`min(frame_w / w, frame_h / h)`), on a black background. |
| "The video's resolution is a dropdown: 360p–4K" | ✅ | `SettingsImagesToVideo.py`: 360/480/720/1080/1440/2160. It's saved as `video_height` but it's the **shorter side**: 1080 gives 1920×1080 for 16:9, **1080×1920 for 9:16**, 1080×1080 for 1:1 (`get_video_frame_size`). |
| "The existing 4K-cap function `get_capped_upscale_ratio` can take a different limit" | ⚠️ partly | It has a `max_side` argument (default 3840), but it only looks at the **longest side** (a square box). Used with `max_side=1920` it saves much less than fitting the real frame (4×: −9% vs −28%). Fitting a width × height needs the small helper from spec 13. |
| "Test first how much time it saves: Shachou's panels are small, so most still need 2×" | ✅ | At 1080p 16:9, 88 of 97 Shachou panels still need 2×. Measured: no saving at 2× (table above). |
| The cap already works per image | ✅ | `UpscaleImagesView.process_image_folder` builds `image_upscale_ratios` per file, and `upscale_all_images` runs waifu2x once per ratio group (and "Best" per image). Nothing new needed there. |
| Default settings | ✅ | `default_settings.py`: `upscale_ratio` 2, `upscale_model` "fast", `limit_upscale_to_4k` True, `video_height` 1080, `video_aspect_ratio` "16:9", `noise_level` 0. |
| The Pipeline can pass a per-run flag to a step | ✅ | It already does for Panel-By-Panel: `run_step` sets `step_view.read_text_for_video` and resets it in `finally` (`gui_classes/PipelineView.py`). |

## 4. Recommended approach + rejected alternatives
**Recommended:** only when the Pipeline runs both **Upscale Images** and **Images To Video**, use the video frame as the box: each panel gets the smallest ratio that makes it fill the frame (width ≥ frame width **or** height ≥ frame height), up to the "Upscale Ratio" setting, and never more than the 4K cap. Nothing else changes (no extra resize; the video does that).

| Option | Verdict |
|---|---|
| **Fit the real frame (width × height), via spec 13's `get_upscale_ratio_to_fit`** | ✅ Recommended. −28% at 4×, one shared helper for #6 and #13. |
| `get_capped_upscale_ratio(..., max_side=max(frame))` with no new helper | ❌ Simplest, but only −9% at 4× (tall panels in a 16:9 frame still go to 4×). |
| Never drop below 2× | ❌ Measured −2%: the big panels are exactly the ones that should drop to 1×. |
| Copy panels that drop to 1× instead of the cunet clean-up | 🟡 Optional extra (about −47% at 4×). But it also changes how "already 4K" images are handled everywhere, so it's a separate decision (open question 3). |
| Shrink the outputs to the frame size too | ❌ Saves no upscale time, and the video resizes anyway. |
| Apply the cap in the Upscale tab too | ❌ The tab doesn't know a video will be made. |

## 5. Files to change + existing functions to reuse
| File | Change |
|---|---|
| `utils.py` | Nothing new if spec 13 lands first (it adds `get_upscale_ratio_to_fit(width, height, max_width, max_height, max_ratio)`). If 06 goes first, add that helper here (the same 4-line loop as `get_capped_upscale_ratio`, with `width * ratio < max_width and height * ratio < max_height`). |
| `gui_classes/UpscaleImagesView.py` | New attribute `self.video_frame_size = None` (set by the Pipeline). In the ratio loop in `process_image_folder`: if it's set, `image_upscale_ratio = min(image_upscale_ratio, get_upscale_ratio_to_fit(w, h, *self.video_frame_size, upscale_ratio))`. One `print` like the 4K one. |
| `gui_classes/PipelineView.py` | In `run_step`, for "Upscale Images" when "Images To Video" is also picked: set `step_view.video_frame_size` and reset it to `None` in the same `finally` that resets `read_text_for_video`. In `get_settings_review`: add ", only as big as the video needs" to the Upscale line. |
| `tests/test_utils.py`, `tests/test_upscale.py`, `tests/test_pipeline.py` | Helper cases; a 4× run where a big image gets 1× and a small one 4×; the Pipeline sets and resets the attribute only when a video is made. |

| Reuse | Where |
|---|---|
| `get_capped_upscale_ratio`, `MAX_UPSCALED_IMAGE_SIDE` | `utils.py` |
| Per-image ratios and per-ratio waifu2x groups | `UpscaleImagesView.process_image_folder`, `upscale_all_images` |
| The frame size: `get_video_frame_size()` | `VideoCreatorFromImages.py`, through `self.parent_gui.ImagesToVideoView.video_creator_from_images` after `initialize_flet_client_storage_values(storage)` (so it follows the current aspect ratio and resolution) |
| The "per-run flag, reset in finally" pattern | `PipelineView.run_step` (`read_text_for_video`) |

## 6. Steps
- [ ] 1. Ask the user the open questions (mainly: do they ever use 4×? Is a lower-resolution .cbz from the Pipeline OK?).
- [ ] 2. If spec 13 isn't built yet, add `get_upscale_ratio_to_fit` to `utils.py` with tests.
- [ ] 3. `UpscaleImagesView`: `video_frame_size` attribute + the `min(...)` in the ratio loop.
- [ ] 4. `PipelineView`: set and reset it in `run_step`; review line.
- [ ] 5. Tests (`-m "not e2e"`, then `-m e2e`).
- [ ] 6. Re-time Shachou ch. 3 at 4× (Fast and Best) on a quiet Mac; add to `benchmarks/upscaling.md`.

## 7. How to test it
- Unit, `get_upscale_ratio_to_fit` with the 1920×1080 frame and max 4: 600×400 → 4; 1,000×1,000 → 2 (2,000 tall fills 1,080); 1,920×500 → 1 (already as wide as the frame); 300×1,200 → 1 (already taller than 1,080).
- `test_upscale.py`: fake waifu2x (as the existing tests do), 4× setting, `video_frame_size=(1920, 1080)`: a 2,000 px image runs at 1×, a 400 px one at 4×.
- `test_pipeline.py`: the attribute is set only when both Upscale and Images To Video are picked, and is `None` again after the run (also after a failure).
- Real run: the timing table in section 2 with the scratch script `/private/tmp/claude-501/-Users-curlos-Desktop-Github-Repos-manga-panel-splitter/8ee4c6a0-1364-4871-bb81-d6088b80b372/scratchpad/bench.py` (arguments: scratch folder, panels folder, ratio, frame width, frame height, mode `base` / `longest` / `exact` / `exact2`). Then a full Pipeline at 4× and watch the video: it should look the same.

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | **Small**: ~15 lines + tests (less if spec 13's helper exists). |
| Value | **None at the default 2×** (measured). **Medium at 4×**: −28% upscale time at 1080p, more at 720p or vertical video. Bigger for "Best" (slower per pixel), not measured. |
| Risks | The Pipeline's upscaled folder and its .cbz get **lower resolution** than the "Upscale Ratio" says, so they're worse for reading on an iPad. Highlighted text boxes use a fixed 15 px padding in image pixels (`DrawBoxCoords`), so on smaller images they look a little bigger in the video. |
| Open questions | 1. Does the user ever use 4×? If not, park this until spec 13 is built (then it's ~5 lines). 2. When "save as .cbz" is on, should the cap be skipped, so the comic file stays full size? (Recommended: yes, skip the cap when a .cbz is saved.) 3. Panels that drop to 1×: keep the cunet clean-up (today's behavior for 4K images) or just copy them (about −47% at 4× instead of −28%)? 4. If spec 13's "fit to screen" is on, its box wins (it's for reading); confirm. |

## 9. Sources
- Code: `utils.get_capped_upscale_ratio`, `MAX_UPSCALED_IMAGE_SIDE`; `gui_classes/UpscaleImagesView.py` (`process_image_folder`, `upscale_all_images`); `waifu2x.get_waifu2x_model`; `VideoCreatorFromImages.get_video_frame_size`, `get_image_clip_fit_to_video_frame`; `gui_classes/PipelineView.run_step`; `gui_classes/SettingsImagesToVideo.py`; `default_settings.py`.
- Panels: Shachou ch. 3 (97 panels), One Piece ch. 567 (97) and Dragon Ball ch. 93 (83). The old test folders in `~/Documents/Panelyze/` are no longer kept (user decision, 2026-11-21): download what's needed again into the spec's own folder (`~/Documents/Panelyze/<worktree-folder>/`). Download the three chapters from MangaDex (Shachou ch. 3: `https://mangadex.org/chapter/f54fb875-d732-42d2-9926-b25767ee4cda`; Dragon Ball ch. 93: `https://mangadex.org/chapter/ac33cc50-a1b2-49b0-a388-0d0ee4ebce18`) and run Panel-By-Panel on them. Panel counts can differ a little from the ones above, because the panel rules changed since.
- Scripts: `/private/tmp/claude-501/-Users-curlos-Desktop-Github-Repos-manga-panel-splitter/8ee4c6a0-1364-4871-bb81-d6088b80b372/scratchpad/cap.py` (pixel counts), `/private/tmp/claude-501/-Users-curlos-Desktop-Github-Repos-manga-panel-splitter/8ee4c6a0-1364-4871-bb81-d6088b80b372/scratchpad/bench.py` (waifu2x timings, real `waifu2x-ncnn-vulkan`, noise 0, PNG).
- `benchmarks/upscaling.md` (Fast 30 s, cunet 70 s on Shachou ch. 3); spec 13.
