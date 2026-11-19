# Handoff for the next Claude chat

The context of a long working session (Nov 18–19, 2026) on Panelyze, so a new chat can continue without re-discovering everything. Measured numbers are in [benchmarks/](benchmarks/README.md), and the to-do list of future ideas is in [ROADMAP.md](ROADMAP.md). How the app works is in [DEVELOPING.md](DEVELOPING.md).

## The project
- **Panelyze** (repo `manga-panel-splitter`): a Python **Flet 0.25.2** desktop app for an M1 Mac.
- **Tabs:**
  - **MangaDex Downloader**
  - **Panel-By-Panel** (Magi v2 cuts pages into panels)
  - **Upscale Images**
  - **Images To Video** (voice-over with edge-tts/Azure)
  - **Pipeline** (runs the steps in a row)
  - Settings (gear icon)
- **venv:** `venv/` (Python 3.12, torch 2.5.1). Install with `uv pip install --python venv/bin/python ...`, since `pip` isn't on PATH.
- **Run:** `npm run dev`, which reloads on save. The user also opens `~/Applications/Panelyze.app`, a hand-made launcher outside the repo that runs `venv/bin/python gui.py`.
- **Tests:**
  - `venv/bin/python -m pytest -q -m "not e2e"`: 184 fast tests, all passing.
  - `-m e2e`: 9 real-tool tests, all passing, about 2 min.
  - Self-test: `venv/bin/python gui.py --self-test`, passing.

## How the user wants to work (important)
- **Follow CLAUDE.md:**
  - Read the code, then propose a plan with todo items.
  - **Check in before working.**
  - Keep changes small and simple.
  - Give high-level explanations along the way, and a summary at the end.
- **Never `git commit` or `git push`.** The user reviews and commits.
- **When the user says "explain" for a file:** summarize `git diff HEAD -- <file>` in **one sentence**: what changed and why.
- **Plain, non-technical language:**
  - The user dictates by voice, so their messages have typos, e.g. "dead spot" means "text box".
  - They like **tables** and short, clear answers ("summarize simply").
- **Be honest** about what was and wasn't tested.
- **Never open Finder windows** (the tests block `open_directory`). Closing them via `osascript` is denied, and `killall Finder` isn't allowed.
- **Kill only processes you started,** never with broad patterns.
- **`.env` has a real Azure key:** never print it. To list variables, mask the values.
- **Test downloads:** use Dragon Ball ch. 93 for MangaDex download tests (pages 1–3). Use **Shachou ch. 3** for benchmarks, because it has history to compare against.
- **Benchmarks:**
  - Run one at a time, so they don't compete for the GPU.
  - Use fresh processes.
  - Watch for the Mac slowing down from heat during long runs.

## State of the repo
- HEAD is `ed0fbb5`. **Everything below is uncommitted** (see `git status`).

### Speed: Magi ([magi.py](magi.py))
- **GPU:** `get_device()` picks the Mac GPU (mps), then CUDA, then the CPU. `PYTORCH_ENABLE_MPS_FALLBACK=1` is set before torch is imported. On a GPU `RuntimeError`, `run_with_cpu_fallback` moves the model to the CPU and runs again. This applies to both the full and the panels-only model.
- **Dialogue only:** `find_and_read_dialogue` reads only the `is_essential_text` boxes and puts `""` for the others, so `ocr` stays the same length as `texts`.
- **Batch sizes:** `FIND_TEXT_BATCH_SIZE = 1`; `READ_TEXT_BATCH_SIZE = 8`. `read_text_in_parts` reads exactly 8 lines per call (a page's lines can be split between calls), so the progress counts lines without slowing down.
- **Progress:** the Progress tab shows "Finding the text · x of y images" and "Reading the text · x of y lines".
- **Page height:** Panel-By-Panel saves each panel's **page height** in the panel PNG (text key `panelyze_page_height`, via `janai.get_page_height_info`).

### Speed: reading text from pages for the video
- When the Pipeline also makes a video that needs the text (and highlighting is off), Panel-By-Panel runs `save_panel_text`:
  - Magi reads whole pages.
  - `get_dialogue_for_each_panel` gives each line to the panel it overlaps most, or the nearest one.
  - The result is written to `panel-text.json` next to the panels.
- **Upscale** copies `panel-text.json` along, or removes a stale one.
- **Images To Video** (`get_panel_text`) uses it when the number of lines matches the number of images, so Magi doesn't run again.
- `PipelineView.video_will_use_text_read_by_panel_by_panel` decides when; the review line says so. **There's no checkbox:** the user found one confusing and it was removed.

### Speed: video ([VideoCreatorFromImages.py](VideoCreatorFromImages.py))
- **Voice-over 4 lines at a time:** `ThreadPoolExecutor`. The failure counter is locked, and a stop `Event` keeps waiting lines from being tried after "3 failures in a row".
- `concatenate_videoclips(method="chain")`.
- Lines with nothing speakable ("!", "...") are skipped (in TextToSpeech.py, from earlier work).
- `MAGI_DATA_FILE_NAME` caching from earlier.
- **Default changes:** `minimum_image_duration` is now 3. The **Video Resolution** is now a dropdown (360/480/720/1080/1440/2160) in `SettingsImagesToVideo.py`.

### Upscale ([waifu2x.py](waifu2x.py), [gui_classes/UpscaleImagesView.py](gui_classes/UpscaleImagesView.py), [janai.py](janai.py))
- **Folder mode:**
  - waifu2x runs once per folder: one run per upscale ratio, from a temporary folder of **hard links**, because waifu2x skips symlinks. `-v` "done" lines drive the progress.
  - The 4K cap still works per image.
  - **Not here:** a custom height or max width; those are applied per image afterwards.
- **"Upscale Model" dropdown** (setting `upscale_model`):
  - `fast` (waifu2x `upconv_7_anime_style_art_rgb`, the default)
  - `better` (waifu2x `cunet`)
  - `best` (`janai.py`)
- **What `best` does:**
  - **MangaJaNai** for B&W, **IllustrationJaNai** for color (`is_color_image`: more than 2% of pixels with saturation above 0.25).
  - MangaJaNai's model is picked by **page height** (7 models, 1200p–2048p).
  - **Core ML:** MangaJaNai on the **Neural Engine** (`ComputeUnit.ALL`, fixed 256 px tiles). IllustrationJaNai on the **GPU only** (`CPU_AND_GPU`), because the Neural Engine compiler hangs on it.
  - **Fallback:** PyTorch, in full precision (half precision made NaN with IllustrationJaNai).
  - **Models:** downloaded from the MangaJaNai GitHub releases (1.0.0 and 2.0.0 zips) to `~/Library/Application Support/Panelyze/upscale-models`. Only the `2x_*` models are kept (240 MB). Each is converted to `*-256.mlpackage` once.
  - **Upscale ratio:** 4× = two 2× passes.
  - Images not made bigger (already 4K) use waifu2x cunet.
  - **Output:** B&W results are saved as grayscale.
- **Errors:** an `OSError` (network or disk) during Best stops the job; other errors skip the image.
- **Licenses:** MangaJaNai and IllustrationJaNai are **CC BY-NC 4.0** (non-commercial). They're credited in the README and DEVELOPING.md.
- **Dependencies:** `spandrel==0.4.2` and `coremltools==8.1` (Mac only) were added to requirements.txt, and the lock file gained cattrs, coremltools, protobuf, pyaml and spandrel. `build_mac_app.sh` now bundles the upconv_7 model and does `--collect-all` for spandrel and coremltools.

### Comic files
- Settings (gear icon) has "Also save each chapter as a comic file (.cbz)" (setting `save_as_cbz`):
  - `""`: no file.
  - `small`: WebP 85%, up to 2048×2732, B&W saved without color.
  - `full`: the images as they are.
- `utils.save_folder_as_cbz(folder, size)` makes `<folder>.cbz` next to the folder, with files numbered 0001…, after Panel-By-Panel and after Upscale.
- The app recommends **Panels** (iPhone and iPad).

### Other
- A **"Panelyze" Dock icon** for the launcher, outside the repo:
  - `~/Applications/Panelyze.app/Contents/Resources/window/Panelyze.app` is a copy of Flet's window app, renamed and re-iconed with flet_cli's `update_flet_view_icon` / `update_flet_view_version_info`, and re-signed ad hoc.
  - The launcher script exports `FLET_VIEW_PATH` to it.
  - The launcher's Info.plist has `LSUIElement=true`.
  - A backup was in the old session's scratchpad, which may be gone.
- **New tests:** `tests/test_magi.py`, `tests/test_janai.py`, `tests/test_upscale.py`, and more in test_video, test_pipeline, test_utils, test_gui and test_panel_output.
- **Docs:** README and DEVELOPING.md were updated; the [benchmarks/](benchmarks/README.md) folder was added (one file per topic: Magi, video, upscaling, file sizes).

## Things installed or created outside the repo
- **Ollama** (Homebrew, 0.40.16) with **`qwen3:8b`** (5.2 GB) pulled, for the planned free translator. It was started with `nohup ollama serve`. After a restart, run `ollama serve` (or `brew services start ollama`).
- **Upscale models and Core ML conversions** in `~/Library/Application Support/Panelyze/upscale-models`.
- **Test output folders in `~/Documents/Panelyze/`,** all safe to delete:
  - `Speed Test - Shachou Ch 3`
  - `Speed Test 2 - Shachou Ch 3 Full Pipeline` (also the only copy of the Shachou ch. 3 pages; MangaDex link `https://mangadex.org/chapter/f54fb875-d732-42d2-9926-b25767ee4cda`, downloaded with the cover)
  - `Upscale Comparison - Shachou Ch 3` and `Upscale Comparison - One Piece Ch 567` (each has a `Compare upscalers.html` side-by-side page)
  - `Best Upscale Test`
- **macOS `ANECompilerService`** may still hold about 1.8 GB from the IllustrationJaNai Neural Engine hang. It's a system process, so don't kill it; a restart clears it.

## Lessons and gotchas
- **Flet:** controls not on screen have `control.page == None`, so use `parent_gui.page`.
- **MPS (Apple GPU):**
  - Every new image size costs setup time.
  - Batching differently sized images pads them to the biggest, so it's slower.
  - It can run out of memory at about 18–20 GB.
- **Batch sizes:** padding makes big batches slow for panels. For reading text, lines wait for the longest one.
- **waifu2x:**
  - Skips symlinks in folder mode.
  - Exits 0 even when it fails (check that the output file exists).
  - `upconv_7` has no 1× (noise-only) model.
- **coremltools:**
  - Can only save to names ending in `.mlpackage`.
  - Warns that torch 2.5.1 is untested; it works anyway.
  - Flexible input sizes failed for MangaJaNai on the Neural Engine and for IllustrationJaNai's conversion.
  - The Neural Engine needs fixed sizes and convolution-style models.
- **Upscalers work on every pixel:** pages aren't cheaper than panels to upscale, the opposite of Magi.
- **zsh:** `set -- $var` doesn't split words. macOS has no `timeout` command.
- **Benchmarks in one long process** slow down over time (GPU memory, heat), so compare within a round.

## What's next
The full list of future ideas (with sizes, status and what's already known) is in [ROADMAP.md](ROADMAP.md). The most important ones:

1. **Translating raw Japanese pages (the plan was proposed, waiting for the user's OK).** It would be a new **Translate** tool, as a tab and a Pipeline step after Download and before Panel-By-Panel, working on **pages**:
   1. Magi finds the text boxes.
   2. **manga-ocr** (`kha-white/manga-ocr-base`, loaded with the existing `transformers` 4.34) reads the Japanese.
   3. The page's lines are translated in one request, with a dropdown for Claude / ChatGPT / Gemini (keys from `.env` or Settings; vision models also get the page image) or **Ollama + qwen3:8b** (free, local).
   4. The Japanese is erased: fill the bubble's text area with the bubble color (flood fill from the box). If too rough, use LaMa inpainting.
   5. The English is lettered in **Comic Neue** (OFL), word-wrapped and auto-fitted, with a white outline on artwork.
   6. The translated pages are saved, and a .cbz if turned on.
   - **Sound effects stay untranslated** in the first version.
   - **Testing:** fakes for Claude, ChatGPT and Gemini. **The user will add a Claude key later.** Ollama for real, on a raw Japanese chapter such as Shachou ch. 63.
   - **Sugoi** (Windows-only) may be an option later, for their Windows PC.
2. **Optional:** Magi's box finder on the Neural Engine. It works, 3.8× faster on that step, but that step is only about 10–20 s per chapter. It needs one conversion per page shape.
3. **Untested:**
   - Building the packaged Mac app with the new libraries.
   - A real first-time download of the upscale models. The URLs were checked, and the zip handling was tested with a fake zip.
   - Macs without Core ML.
4. **Ideas from earlier:**
   - In the Pipeline, upscale only as much as the video needs.
   - Make page reading work with "highlight text boxes", by converting text box positions from the page to each panel.
   - A user with an AMD RX 6700 XT gaming PC may try Linux or ROCm later (see benchmarks/README.md).
