# Spec 07: Page reading with "highlight text boxes"

Roadmap #7. Checked on 2026-11-19. ✅ = checked today against the code, ⚠️ = the note is wrong or out of date, 🟡 = not confirmed.

## 1. Summary
When the Pipeline makes panels and then a video, Panel-By-Panel reads the text on whole **pages** (fast) and saves it in `panel-text.json`, so the video doesn't run Magi again. When "Highlight Text Boxes In Images" is on, that fast path is turned off, because the video needs **where** each line is on its panel, and `panel-text.json` only has the words. The video then runs Magi on every panel (slow).

The fix: when Panel-By-Panel reads the pages, also save each line's box **on its panel**, as fractions of the panel's width and height (0 to 1). Fractions stay right after any upscale or resize, so the Upscale step needs **no change**. The video turns them back into pixels with each image's real size and gives them to the existing highlight code as if Magi had found them.

## 2. Is it doable?
**Yes, medium-small:** about 40 lines in 3 files, plus test updates. No new libraries, no change to the Upscale step.

| Time it saves (Magi, M1 GPU) | Reads the panels (today with highlighting) | Reads the pages (with this change) |
|---|---|---|
| Page 02 of Shachou ch. 3 (8 panels) | 24.9 s | **10.8 s** (measured) |
| Pipeline, 2 pages → 14 panels | 86.2 s in the video step (old code) | **about 25.6 s** in Panel-By-Panel (30.2 s − 4.6 s, measured), 0 s in the video |
| Whole Shachou ch. 3 (27 pages → 97 panels) | about 6–8 min (estimate: 24 panels took 117.7 s to find + read) | **162–179 s** (measured, 27 pages) |

So roughly **3–5 minutes saved per chapter** (estimate), and better text: page reading avoids bubbles cut in half at panel edges (benchmarks/magi.md).

## 3. What's already true (claims checked)
### Where the fast path is turned off (two places)
| Where | Code | Status |
|---|---|---|
| 1. The Pipeline decides not to read the pages | `gui_classes/PipelineView.py`, `video_will_use_text_read_by_panel_by_panel`: `... and not get("highlight_text_boxes_in_images")`. `run_pipeline` stores it in `self.read_text_for_video`; `run_step` passes it to `MagiPanelByPanelView.read_text_for_video` → `magi.get_panels_for_chapter(read_text=...)` → `save_panel_text`. | ✅ |
| 2. The video ignores `panel-text.json` even if it exists | `VideoCreatorFromImages.get_essential_text_and_magi_data`: `panel_text = None if self.highlight_text_boxes_in_images else self.get_panel_text(...)`. | ✅ |

### How highlighting reads the boxes now
| Step | Code | Status |
|---|---|---|
| Get Magi data per panel | `get_essential_text_and_magi_data`: saved `magi-data.json` if it matches the images (`load_saved_magi_data`), else `speech_text_parser.get_essential_text_list_in_images` (Magi on every panel), else (when the text came from a transcript) `magi.get_data_from_images` just for the boxes. | ✅ |
| Which boxes get drawn | `draw_boxes_with_text_and_magi_data`: for image `i`, `magi_output_data[i]["texts"]` filtered by `magi_output_data[i]["is_essential_text"]`, in **pixels of that image**, drawn by `DrawBoxCoords.draw_box_coords_box_list` (one image per box, named `panel_n-1.png`, `panel_n-2.png`, …; one plain copy if no boxes). | ✅ |
| Lines and boxes must line up | The voice-over makes one file per line (`get_images_duration_based_on_tts`), and `get_clips` walks the highlighted images by index. So for every panel, **number of lines = number of boxes**, in the same order. | ✅ (important for the design) |
| The only keys used | `texts`, `is_essential_text` (and `ocr` via `get_essential_text_list_from_magi_data` when data came from `magi-data.json`). | ✅ |

### The roadmap's claims
| Claim (ROADMAP #7) | Status | What's really true |
|---|---|---|
| "The fast path is turned off when the video highlights text boxes" | ✅ | Two places, table above. |
| "Highlighting needs each box's position on each panel" | ✅ | Boxes in each panel image's own pixels. |
| "The video step then reads every panel again, which is much slower" | ✅ | 86.2 s vs about 25.6 s on 14 panels; 24.9 s vs 10.8 s on one page (benchmarks/video.md, magi.md). |
| "Convert each box from the page to its panel" | ✅ doable | `save_panel_text` already has each page's crop boxes (`get_panel_crop_box`, the exact rectangle `save_cropped_panels` cuts) and gives each line to a panel with `get_panel_index_of_text`. The panel box = line box − crop's top-left corner. |
| "Scale it if the panel gets upscaled" | ⚠️ not needed | Saving fractions of the panel size makes it independent of every resize (upscale ratio, 4K shrink, custom height, max width all keep the shape). Upscale already copies `panel-text.json` as is (`UpscaleImagesView.process_image_folder`). |
| (not in the roadmap) Highlighting with a **fixed time per image** | ⚠️ also slow | `video_will_use_text_read_by_panel_by_panel` also needs TTS or WPM, but highlighting alone still runs Magi on every panel (`text_is_needed` in the video includes highlighting). The fix should cover it too. |
| `panel-text.json` is used when the counts match | ✅ | `get_panel_text` falls back to Magi when the number of panels differs (e.g. an image failed to upscale). |

## 4. Recommended approach + rejected alternatives
**Recommended:**
1. **`panel-text.json` gets one more list.** It becomes `{"lines": [[...], ...], "boxes": [[[x1, y1, x2, y2], ...], ...]}`: one entry per panel in both, boxes as fractions of the panel (0–1), clamped to the panel. `get_panel_text` reads `"lines"` (and still accepts the old plain list, so nothing breaks).
2. **Panel-By-Panel** (`save_panel_text`) fills `"boxes"` with the same loop that gives each line its panel.
3. **The video:** when highlighting and no Magi data is loaded yet, build Magi-shaped data from `"boxes"` (`{"texts": pixel boxes, "is_essential_text": [True, …], "ocr": lines}`) using each image's size. Only if the counts don't match does it run Magi as today.
4. **The Pipeline** reads the pages whenever the video needs the text: TTS, WPM **or highlighting**.

| Option | Verdict |
|---|---|
| **Fractions of the panel, in `panel-text.json`** | ✅ Recommended. One file (lines and boxes can't get out of step), Upscale untouched. |
| Panel pixels + the Upscale step rescales the boxes | ❌ Upscale would need to know every resize (4K shrink, custom height, max width) for every image. More code, more ways to be wrong. |
| A separate `panel-text-boxes.json` | ❌ Upscale's copy/remove code would need a second file, and the two files could disagree. |
| Run Magi's box finder only (no reading) on the panels for highlighting | ❌ Still runs Magi on every panel ("finding" is half the cost: 51.9 s of 117.7 s on 24 panels). |
| Highlight on the page, then cut the page | ❌ Highlighted images are per line; would need a new cutting step. |

**Edge cases and how they're handled**

| Case | Handling |
|---|---|
| A bubble in the gutter (overlaps no panel, so it goes to the closest one) | Clamped to the panel's edge, so the highlight is a thin strip at the edge (with the 15 px padding). Line and voice are still right. 🟡 How often it happens is not measured (see section 7). |
| A bubble partly outside its panel (growth stopped by the 30% limit) | Clamped: only the part inside the panel is highlighted, which is all the viewer sees anyway. |
| An image failed to upscale (fewer images than entries) | The existing count check in `get_panel_text` → Magi on the panels, as today. |
| Lines and boxes counts differ for a panel | Don't use the boxes → Magi on the panels (safe fallback). |
| Images To Video run on its own on a Pipeline folder | Works too, since the file is next to the panels. |
| Order of lines in a panel | The page's reading order (already true for TTS); can differ slightly from Magi-on-the-panel order, which is fine. |

## 5. Files to change + existing functions to reuse
| File | Change |
|---|---|
| `magi.py` | New small `get_dialogue_boxes_for_each_panel(page_result, panel_boxes)` next to `get_dialogue_for_each_panel`: same loop, uses `get_panel_index_of_text`, appends `[(x1 − px1) / w, (y1 − py1) / h, …]` clamped to 0–1. `save_panel_text` writes `{"lines": ..., "boxes": ...}`. ~20 lines. |
| `VideoCreatorFromImages.py` | `get_panel_text`: accept the dict (`data["lines"]`) or the old list. Remove `None if self.highlight_text_boxes_in_images else` so the lines are used when highlighting. New `get_magi_data_from_panel_boxes(image_folder, lines)` (reads `"boxes"`, checks counts, multiplies by each image's size from `list_images` + `PIL.Image.open(...).size`). Call it in the "highlight and `magi_output_data is None`" block, before the existing Magi fallback. ~25 lines. |
| `gui_classes/PipelineView.py` | `video_will_use_text_read_by_panel_by_panel`: replace `... and bool(tts or wpm) and not highlight` with `bool(tts or wpm or highlight)`; update its docstring. ~3 lines. |
| `tests/test_magi.py` | Line 190: expect the new shape; new test for box conversion (a box at the panel corner, one in the gutter). |
| `tests/test_video.py` | `test_highlighting_still_reads_the_panels_because_it_needs_where_the_text_is` flips: with boxes, no Magi run and pixel boxes match; a new test for mismatched counts → Magi runs. The old plain-list format still works. |
| `tests/test_pipeline.py` | `test_panel_by_panel_reads_the_text_only_when_the_video_will_use_it`: expected `[True, False, False]` → `[True, True, False]`. |

| Reuse | Where |
|---|---|
| `get_panel_crop_box`, `get_panel_index_of_text`, `get_dialogue_for_each_panel`, `apply_reading_direction`, `save_panel_text` | `magi.py` |
| `PANEL_TEXT_FILE_NAME`, `list_images` | `utils.py` |
| `get_panel_text`, `draw_boxes_with_text_and_magi_data`, `load_saved_magi_data` | `VideoCreatorFromImages.py` |
| Copying `panel-text.json` along (no change) | `UpscaleImagesView.process_image_folder` |

## 6. Steps
- [ ] 1. Ask the user the open questions (mainly the gutter-bubble look).
- [ ] 2. `magi.py`: `get_dialogue_boxes_for_each_panel` + the new file shape in `save_panel_text`; update `test_magi.py`.
- [ ] 3. `VideoCreatorFromImages.py`: read both shapes; build highlight data from the boxes; update/add `test_video.py` tests.
- [ ] 4. `PipelineView.py`: read the pages when highlighting too; update `test_pipeline.py`.
- [ ] 5. `venv/bin/python -m pytest -q -m "not e2e"`, then `-m e2e`.
- [ ] 6. Real check (section 7), then add the timing to `benchmarks/video.md`.

## 7. How to test it
- **Unit:** page 100×100, panel crop `[50, 0, 100, 50]`, line box `[60, 10, 90, 30]` → `[0.2, 0.2, 0.8, 0.6]`; a gutter box gets clamped into 0–1; after a 2× "upscale" of a 50×50 panel to 100×100 the video's pixel box is `[20, 20, 80, 60]`.
- **Real, side by side (Dragon Ball ch. 93 from `test-chapter-cache/`, pages 1–3):** run the Pipeline Panel-By-Panel → Upscale (2×) → Images To Video with highlighting + WPM twice: once today's code (Magi on the panels) and once with the change. Compare (a) time of each step, (b) the `images-with-highlighted-text-boxes` images side by side: same number per panel, boxes on the same bubbles. Then the same on Shachou ch. 3 for the chapter-size number.
- **Gutter bubbles:** a scratch script that counts, over the 25-chapter crop test set, dialogue boxes with zero overlap with every crop box (how often the thin-strip case happens).
- Don't open Finder: run with `open_directory` patched out (as the tests do).

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | **Medium-small**: ~45 lines in 3 files + ~4 test updates. |
| Value | **Medium**: only for people who use highlighting, but for them about 3–5 min saved per chapter (estimate) and fewer junk lines from cut bubbles. |
| Risks | Boxes from the page can differ a little from what Magi would find on the panel (usually better: whole bubbles). Gutter bubbles get a thin edge highlight. `panel-text.json` changes shape: anything else reading it must use `get_panel_text` (today nothing else does ✅, grep). `magi.py` is being changed by other work right now (panel growth); rebase on it. |
| Open questions | 1. Gutter bubbles: thin highlight at the panel edge OK, or skip the highlight for that line (show the plain panel while it's read)? 2. Should a stand-alone Panel-By-Panel run (its own tab) also save the text and boxes, so a later video is fast? (Today it only does in the Pipeline; it costs ~3 min per chapter there.) 3. Keep reading the old plain-list `panel-text.json`, or drop it (the file is remade on every Pipeline run)? Recommended: keep, it's one line. |

## 9. Sources
- Code: `gui_classes/PipelineView.py` (`video_will_use_text_read_by_panel_by_panel`, `run_pipeline`, `run_step`, `get_settings_review`); `gui_classes/MagiPanelByPanelView.py` (`read_text_for_video`); `magi.py` (`get_panels_for_chapter`, `get_panels_using_local_cpu`, `save_panel_text`, `get_dialogue_for_each_panel`, `get_panel_index_of_text`, `get_panel_crop_box`, `save_cropped_panels`); `VideoCreatorFromImages.py` (`get_essential_text_and_magi_data`, `get_panel_text`, `draw_boxes_with_text_and_magi_data`, `get_images_duration_based_on_tts`, `get_clips`); `DrawBoxCoords.py`; `gui_classes/UpscaleImagesView.py` (copies `panel-text.json`); `SpeechTextParser.py`.
- Tests: `tests/test_magi.py:190`, `tests/test_video.py:299–330`, `tests/test_pipeline.py:253–278`.
- Numbers: `benchmarks/magi.md` (pages vs panels; 27 pages 162–179 s; 24 panels 51.9 + 65.8 s), `benchmarks/video.md` (2 pages → 14 panels: 86.2 s vs 30.2 − 4.6 s).
- Related: [06](06-upscale-to-video-size.md) (smaller upscales; boxes as fractions work with any size), [01](01-translate-japanese-pages.md) (also maps page text boxes to panels).
