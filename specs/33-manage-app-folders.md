# Spec 33: See and clean up the app's folders (Settings → Storage)

Researched 2026-11-23 on the Windows PC, while building spec 10. Builds on spec 10 (the downloaded waifu2x folder), which is merged. **Built 2026-11-25 in the `40-housekeeping-and-release-specs` worktree** (with spec 40), as `storage.py` and `gui_classes/StorageSection.py`.

## 1. Summary
A new **Storage** section in Settings that lists everywhere Panelyze keeps files, with each one's size and **Open** / **Delete** buttons:

- **Saved files:** what the tabs saved. When running from source, that's only this repo's or worktree's own folder (`~/Documents/Panelyze/<worktree>`, see `get_dev_output_folder`), never another worktree's. In the packaged app, it's the Panelyze folder (`~/Documents/Panelyze`, or the one picked in Settings), one row per tool folder.
- **Downloaded by the app:** waifu2x, the "Best" models, the Magi model and the log file. Deleting one only frees space: it's downloaded again the next time it's needed.

Today the only way to find these is to know the paths. They add up: 4.3 GB on this PC before any output.

Two more things for the downloads, so the user isn't surprised by the app fetching gigabytes from the internet:
- **A progress bar while something downloads**, in the Status view: "Downloading the Magi model: 812 MB of 2.0 GB". Today it's only a line of text ("Downloading waifu2x (about 40 MB, one time only)..."), and Magi's 2 GB download shows Hugging Face's own progress in the output.
- **"Download now" buttons** in the Storage section for anything not downloaded yet, with its size, so it can be done ahead of time (e.g. before going offline) instead of in the middle of the first job.

## 2. Is it doable?
**Yes, small to medium.** Every path is already known in the code. The work is a size calculation that doesn't freeze the window, a confirm dialog before deleting, and not deleting while a job uses the files.

## 3. What's already true (checked 2026-11-23 on the Windows PC)

| What | Where (from the code) | Size here | Deleting it means |
|---|---|---|---|
| Saved files, from source | `DEV_OUTPUT_FOLDER` = `~/Documents/Panelyze/<repo folder>` (`default_settings.py`) | 2.4 GB (`10-amd-gaming-pc`) | Gone for good (needs a confirm) |
| Saved files, packaged app | `panelyze_folder` setting or `~/Documents/Panelyze`, tool folders from `OUTPUT_SUBFOLDERS` (`default_settings.py`), plus any folder picked for one tool | — | Gone for good (needs a confirm) |
| waifu2x (downloaded) | `DOWNLOADED_WAIFU2X_FOLDER` = `~/Library/Application Support/Panelyze/waifu2x` (`utils.py`, spec 10) | 40 MB | Downloaded again on the next upscale. Only shown when the app downloaded it (not the packaged app's own copy, not one on the PATH) |
| "Best" models (+ their Core ML copies on a Mac) | `MODELS_FOLDER` = `~/Library/Application Support/Panelyze/upscale-models` (`janai.py`) | 241 MB (up to ~600 MB with every model) | Downloaded again on the next "Best" upscale |
| Magi (reads the text, and builds the panels model) | Hugging Face cache, `~/.cache/huggingface/hub`: `models--ragavsachdeva--magiv2` (3.9 GB), and two parts Magi loads with it, `models--timm--resnet50.a1_in1k` (98 MB) and `models--microsoft--trocr-base-printed` (1.4 MB) | 4.0 GB | Downloaded again (about 2 GB download) the next time a video reads the text. Only these 3 folders: other apps share the cache |
| Panels-only Magi model | `magi_model/panels_fp16.safetensors` (84 MB), inside the packaged app or the repo | 84 MB | Not shown: it's part of the app (in a worktree it's a link to `panelyze-main`'s copy) |
| Log file | `LOG_FILE_PATH` = `~/Library/Logs/Panelyze/panelyze.log` (`gui_classes/AppOutput.py`); already has an "Open Log File" button in Settings | 13 KB (capped at 10 MB) | Not worth a Delete button; just show its size next to the existing button |
| comix.to cookies | `~/Library/Application Support/Panelyze/cf_cookies.dat` (`comix_downloader/src/api/comix.py`) | — | Not shown: tiny, and deleting it only means comix.to's check runs again |
| What's downloaded when | waifu2x (both "Fast" and "Better": one program with both models) on the first upscale with them (`download_waifu2x`, `waifu2x.py`); "Best" only downloads it for an image that's already 4K (it's only cleaned up by waifu2x). "Best": only the model that's needed, the first time it's needed (`download_model_file`, `janai.py`): IllustrationJaNai for color images; for black and white, one zip with all 7 MangaJaNai page-height models (all kept). Full Magi on the first video that reads the text (or the first Panel-By-Panel run from source, to build the panels model). Each is checked first and never downloaded twice | — | — |
| Download progress today | `download_file` (`utils.py`) and `download_model_file` only print one line; Magi's download goes through Hugging Face's `from_pretrained` (`magi.py`), which prints its own tqdm bars. `report_progress` (`gui_classes/ProgressPanel.py`) already shows a bar with `pages_done`/`pages_total`/`unit`/`detail` | — | Can show MB done of the total |
| One job at a time | `try_to_start_job` / `is_job_running` (`gui.py`) | — | Delete is turned off while a job runs, so nothing in use is deleted |
| Existing Settings layout | `get_section(title, controls)` and `get_help_text` (`gui_classes/AppSettingsView.py`); sections: start tab, folder, .cbz, log file, reset | — | The new section goes after the folder section |

The Windows paths are the same `~/Library/...` ones for now. Spec 32 moves them to `%LOCALAPPDATA%\Panelyze`; this section reads the same constants, so it follows along.

### Download sizes (checked 2026-11-25; kept as constants in `storage.py`, so Settings shows them without internet)

| Row | Comes from | Download | Where it's saved |
|---|---|---|---|
| waifu2x ("Fast", "Better") | [GitHub releases](https://github.com/nihui/waifu2x-ncnn-vulkan/releases), v20250915 | 54.1 MB on a Mac, 35.9 MB on Windows (unzipped, without the photo model) | `DOWNLOADED_WAIFU2X_FOLDER`. Packaged app: "Built in". On the PATH: "Installed on this computer", no Delete |
| MangaJaNai, 7 models ("Best", black and white) | [MangaJaNai releases](https://github.com/the-database/MangaJaNai/releases), 1.0.0 | 236 MB unzipped (217 MB of a 433 MB zip) | `MODELS_FOLDER` (`2x_MangaJaNai_*` and their `.mlpackage` Core ML copies) |
| IllustrationJaNai ("Best", color) | the same, 2.0.0 | 16.2 MB unzipped (15 MB of a 159 MB zip) | `MODELS_FOLDER` (`2x_IllustrationJaNai_*` and its `.mlpackage`) |
| Magi (full) + TrOCR | [huggingface.co/ragavsachdeva/magiv2](https://huggingface.co/ragavsachdeva/magiv2) | 2.06 GB + 1 MB (about 2.1 GB) | Only its 2 `models--…` folders in the Hugging Face cache (Magi and TrOCR; see the ResNet-50 note below) |
| Magi (panels only) | made from the full model | — | `magi_model/panels_fp16.safetensors`, "Built in", no buttons |

The JaNai zips also hold 4x (and bigger) models that aren't used. Only the 2x models are downloaded, straight out of the zips on GitHub (HTTP "Range" requests, `open_remote_zip` in `utils.py`): MangaJaNai 217 MB of its 433 MB zip (6 s here; 236 MB once unzipped), IllustrationJaNai 15 MB of its 159 MB (under 1 s; 16 MB unzipped). If a server ever sends whole files only, the whole zip is downloaded instead. On a Mac, a Core ML copy of each model used is added.

ResNet-50 (`models--timm--resnet50.a1_in1k`, 98 MB) is **not** Magi v2's: `full_config.json` has `"use_pretrained_backbone": false`, so its weights come inside Magi's own file. The copy in this Mac's cache is from the older Magi v1 (Dec 2024), so the Storage section leaves it alone (found by the review).

## 4. Recommended approach + rejected alternatives

| Option | Verdict | Why |
|---|---|---|
| **One "Storage" section in Settings, one row per folder: name, what it is, path, size, Open, Delete** | ✅ **Recommended** | Everything in one place; reuses `get_section`, `open_directory` and the existing constants |
| Sizes worked out when Settings opens, in a background thread ("Calculating..." until done), plus a Refresh button | ✅ | 2–4 GB folders take a second or more to add up; the window mustn't freeze |
| A confirm dialog for every Delete, saying what's lost and whether it comes back ("downloaded again next time" vs "can't be undone") | ✅ | Saved files can't be brought back |
| Saved files: one row per tool folder (Download, Panel-By-Panel, Upscale, Video, Pipeline) plus a total | ✅ | Usually only one tool's output is worth clearing |
| Show other worktrees' folders | ❌ | The user's call: from source, only this worktree's own folder. The packaged app shows no worktree folders at all |
| Delete the whole Hugging Face cache | ❌ | Other apps share it; only Magi's (and the emotion model's) own folders |
| Move to the Recycle Bin / Trash instead of deleting | Later | Safer, but needs `send2trash` (a new package). A confirm dialog is enough for now |

## 5. Files to change + existing functions to reuse

| File | Change | Size |
|---|---|---|
| `default_settings.py` (or `utils.py`) | `get_app_folders(storage)`: the list of rows (name, description, paths, "comes back when needed" or not), built from the existing constants; `get_folder_size(path)` | ~40 lines |
| `gui_classes/StorageSection.py` (new) | The section: rows with size, Open, Delete; background size calculation; confirm dialog; Delete disabled while a job runs; Refresh | ~120 lines |
| `gui_classes/AppSettingsView.py` | Add the section after the folder section | ~3 lines |
| `utils.py` `download_file` | Report progress while downloading (MB done of the response's Content-Length) through `report_progress`, with what's being downloaded | ~10 lines |
| `magi.py` | The same for Magi's download: Hugging Face's tqdm progress passed on to `report_progress` (or a message with the size before it starts, if that's simpler) | ~10 lines |
| `gui_classes/StorageSection.py` | "Download now" button on each row that isn't downloaded yet, with its size; runs like a job (one at a time, Cancel) | ~30 lines |
| `tests/test_storage.py` (new) | Rows from source vs packaged app (no other worktree's folder ever); waifu2x row only for the downloaded copy; sizes; Delete removes only that folder (only Magi's own cache folders); Delete is off during a job; the confirm dialog | ~100 lines |
| `README.md`, `DEVELOPING.md` | One line each: where the files are, and that Settings → Storage shows them | ~4 lines |

Reuse: `get_dev_output_folder`/`DEV_OUTPUT_FOLDER`, `OUTPUT_SUBFOLDERS`, `get_output_directory`, `PANELYZE_FOLDER` (`default_settings.py`); `DOWNLOADED_WAIFU2X_FOLDER`, `get_waifu2x_path`, `open_directory`, `is_running_as_packaged_app` (`utils.py`); `MODELS_FOLDER` (`janai.py`); `LOG_FILE_PATH` (`AppOutput.py`); `get_section`, `get_help_text` (`AppSettingsView.py`); `try_to_start_job` / `is_job_running` (`gui.py`).

## 6. Steps (todo)
- [x] Merge spec 10 into `main` first, then `git merge main` here
- [x] `get_saved_files_rows` / `get_model_rows` + `get_size` (in `storage.py`), with tests (source vs packaged, waifu2x only deletable when the app downloaded it, Magi's own cache folders only)
- [x] `StorageSection`: rows, background sizes, Open, Refresh
- [x] Delete with a confirm dialog; off while a job runs; tests
- [x] Download progress (MB done of the total) for waifu2x and the "Best" models, in the Status view's status line; Magi shows its size before it starts (Hugging Face shows its own progress in Raw Output); tests with a fake download
- [x] "Download" buttons for what isn't downloaded yet
- [x] Add it to Settings; checked at normal and phone width in the browser view, sizes match `du`; deleted and downloaded IllustrationJaNai again with the buttons
- [ ] Try it on the Windows PC: delete the "Best" models and waifu2x, then upscale (they come back); delete a tool's saved files
- [x] README and DEVELOPING.md lines

- [x] After the user's review: rows use the real folder names (Downloads, Upscaled Images, Videos...); Open / Download / Delete are small icons with tooltips (Delete in red), with Refresh as an icon next to the "Storage" title; teal subheadings; the total lines up with the sizes; dialogs are a shade lighter than the page, and their Cancel has an outline.
- [x] A download a job needs is a step of its own in the Status view ("✓ Downloading Magi (full model) ● Finding the text"; for Upscale, "Downloading MangaJaNai" then the upscale), with its progress (MB of the total). Magi's progress comes from watching its Hugging Face folder grow (`report_folder_download` in `utils.py`), since Hugging Face downloads it with its own code. Loading a model is a step too, the first time in each run of the app (the names were changed later, see the note on listing every step from the start). On a Mac the one-time Core ML conversion is its own step before it ("Converting IllustrationJaNai for Core ML (one time only)", `convert_to_coreml` in `janai.py`), and the JaNai steps each have a line under them saying what Core ML or PyTorch is. The load step also runs Core ML's first tile (its warm-up: 3.9 s the first time, 0.4 s after), so the upscale's own bar starts right away. Measured again on the M1 for IllustrationJaNai after this change: 16 s the first time (converting, loading and the warm-up tile), 3 s in each later run of the app (the freeze fix's numbers below were measured differently, through a whole upscale). (The 4x case where a second MangaJaNai model went back to "Converting MangaJaNai", and failed Core ML steps staying ticked, were fixed later: see the note on listing every step from the start.) `show_extra_stage` is in `ProgressPanel.py`.
- [x] Deleting a JaNai model in Storage also forgets it if it's loaded (`delete_paths` in `storage.py` empties its `_loaded_upscalers` entry), so the next upscale downloads, converts and loads it again instead of using the copy in memory until the app is closed. The Magi models aren't forgotten this way (`_shared_magi` in `magi.py` stays loaded until the app is closed).
- [x] Fixed a lock-up found while testing (older than this spec, also on `main`): after the window went from wide to narrow (or back), the next job's button crashed with "Control must be added to the page first" and the app stayed locked as if a job were running, until it was restarted. Flet 0.25 loses track of controls moved into a new row or column in one update, so `handle_resized` in `gui.py` now takes the tab off the page first, then puts it back in its new layout (only the four tabs with settings on the side: Pipeline and Settings move nothing, so they stay, scrolled where they were). The Download tab's button updates during and after a download check that the button is on the page, since it's off it for a moment if the window is resized right then. Guardrail: in the Upscale, Panel-By-Panel, Images To Video, Download and Pipeline tabs, everything after a job is started is inside the `try` whose `finally` ends it (the Pipeline ends it first in its `finally`), so a job that fails as it starts shows the error and never leaves the app locked. Tests: a real Flet page over a fake connection (`test_layout.py`) and a failing first update in each tab (`test_gui.py`).
- [x] Upscale with "Best" no longer downloads waifu2x at the start of every job (found while testing: after deleting waifu2x in Storage, a Best upscale downloaded it again first). It's only downloaded when an image is already 4K, since waifu2x only cleans those up (`before_job` and `upscale_all_images` in `UpscaleImagesView.py`), and before the MangaJaNai images, so a failed download doesn't come after minutes of upscaling. Fast and Better still download it at the start.
- [x] On a phone-size window (under 560 px, `PHONE_WINDOW_WIDTH` in `gui.py`), the Status view puts the timer and size ("Took 53s · 3.4 MB ...") on a line of their own under the title, and each step on a line of its own (`set_phone_size` in `ProgressPanel.py`). Before, the timer squeezed the title into one letter a line, and the steps wrapped in the middle of their names. Wider windows look as before.
- [x] Every step a model still needs is listed from the start, not only as it comes: Upscale on Best works out each image's models before the first step (color or not, and for MangaJaNai the page height of each 2x pass), then lists what each still needs from what's on the disk and in memory (`get_steps_to_get_ready` in `janai.py`: downloading, converting for Core ML, loading). Those steps show as "○" until they run (`show_upcoming_stages` in `ProgressPanel.py`), and one that turns out not to be needed (e.g. Core ML failed) is dropped when the job ends. MangaJaNai's steps name the model ("Loading MangaJaNai 1600p into Core ML"), since a 4x upscale can use two of the 7. Magi and the emotion model say where they load too ("Loading Magi (full model) into PyTorch", "Loading the emotion model into PyTorch"; the download step is "Downloading Magi (full model)", like Storage's name; later "Downloading Magi (full model, one time only)", see below), with a line under the step saying what PyTorch is (`PYTORCH_LOAD_DETAIL`). `show_extra_stage` takes that line (none for a step without one, e.g. a download inside a loading step, which shows its own progress) and puts the job's own line back afterwards. A step that fails isn't ticked as done: it's taken off the list (e.g. Core ML failed and PyTorch was used). The step names come from one place (`get_download_step`, `get_convert_step`, `get_load_step` in `janai.py`), so a step listed ahead is always the one ticked off. Left as is: Magi's and the emotion model's downloads also load the weights (one Hugging Face call), so part of the loading time shows under "Downloading".
- [x] The steps are in color, so progress is seen at a glance: a green ✓ and normal text for each one done, a blue ● (the app's accent, like the running hourglass; the bar's darker blue was too faint for a small dot) and normal text for the one it's on, and gray for the ones still to come (`get_stages_spans` in `ProgressPanel.py`). Only the marks are colored, not the whole names: easier to read, and green text stays for "finished".
- [x] The panel at the bottom is now called **Activity** (it was "Terminal Output"), with **Status** and **Log** (it was "Raw Output"; "Log" is the word Settings already uses for the log file). Its header no longer repeats the running job's name and a ✓ (the Status view shows them, and on a narrow window they pushed the Status and Log buttons off the edge): only a small spinner while a job runs, which still shows something is running when Activity is collapsed or on the Log. The Log is one selection area, so a selection can go across lines (each line used to be selectable on its own, so only one line could be copied), and a **Copy all** button (on the Log only) copies every line with its line breaks (a drag-selection only reaches the lines on screen, and Flutter joins the lines it copies without line breaks). `TerminalOutput.py`, `AppOutput.py`.
- [x] The Status view has space under its progress bar (12 px), so the bar isn't right at the bottom edge, which was most noticeable on a phone-size window (`ProgressPanel.py`).
- [x] Downloads say they only happen once, so a slow first run isn't taken for a slow app: every download step's name ends in "(one time only)" (like the Core ML conversion's; Magi's is "Downloading Magi (full model, one time only)"), and a line under the download's progress says "This is only downloaded once. It's kept on this computer, so later jobs don't download it again." (`DOWNLOAD_ONCE_DETAIL` and `get_download_detail` in `ProgressPanel.py`, used by `download_file`, `save_zip_files` and `report_folder_download` in `utils.py`, and by each download step). Magi's progress line no longer says "(one time only)" itself, since its step does.
- [x] Counts get commas in the thousands, in the Status view ("1,139 of 4,637 frames", "Chapter 2 of 1,200") and in the summaries (`pluralize` in `utils.py`: "Downloaded Slam Dunk: 278 chapters · 5,497 pages", the picked input's "3 chapters · 1,200 pages").
- [x] The count and the bar come right under the title (found while testing: a blue-ish line blinked under "Activity" during jobs). The Status view didn't fit in the Activity panel's default 200 px, so it scrolled, and its "Running on the Apple M1" line (last, with the chip's name in color) was cut in half under the title, jumping as lines came and went. Now the order is: the title, how far it is with where the AI model runs ("1 of 1 image · Ran on the Apple M1", `count_text` and `show_count_and_device` in `ProgressPanel.py`), the bar, the steps, then anything else (a download's progress, what a step does, or an error: `status_text`). It all scrolls when it doesn't fit, so what's cut off is at the bottom, never the count or the bar. (Pinning the count and the bar to the bottom was tried first; it looked odd on a big window, far from the title.) The steps "Finding the text", "Reading the text" and "Making the voice-over" no longer repeat their name as the line under the steps (`magi.py`, `VideoCreatorFromImages.py`). Activity is 260 px by default (`DEFAULT_TERMINAL_HEIGHT` in `TerminalOutput.py`), so a job's Status fits on a normal window without scrolling.
- [x] waifu2x on the PATH isn't used anymore: the packaged app uses its built-in copy, and running from source uses the app's own download, so everyone runs the same version and Storage manages it.

- [x] Fixed a freeze found while testing: converting IllustrationJaNai for Core ML also loaded it for every chip, so macOS compiled it for the Neural Engine (many minutes, app frozen). Now it's only saved, then loaded for the GPU (`skip_model_load=True` in `janai.py`). Measured: 19 s the first time for IllustrationJaNai, 41 s for MangaJaNai, then 6 s per run of the app.

- [x] Magi took 4.1 GB: newer `transformers` (4.57, in the shared venv) also downloads a converted copy (`model.safetensors`, from a Hugging Face conversion pull request) in the background, which Panelyze never uses. Turned off with the library's own `DISABLE_SAFETENSORS_CONVERSION=true` (`utils.py`, for every model); checked on an empty cache: only the pinned files are downloaded.
- [x] The emotion model (j-hartmann, about 330 MB, for Azure's "Auto" voice style) was missing from Storage: added, with its version pinned (`EMOTION_MODEL_REVISION`) and "Downloading" / "Loading" steps. Nothing else is downloaded as a model (Edge and Azure voices are online services, comix.to uses the installed browser, ffmpeg and the spell checker come inside pip packages).

- [x] Downloads fill the Status bar (a `fraction_done` field, which leaves the job's own count alone): from the zip's file sizes (JaNai), the server's Content-Length (waifu2x), or the exact size of the pinned file (Magi 2,063,693,064 bytes, the emotion model 331,156,595; a pinned commit can't change). A Download from Storage is the job itself, so it isn't shown again as a step of its own.

- [x] Storage shows each download's exact size (in bytes in `storage.py`, written like Finder or File Explorer with `format_size`), and so do the messages and hints.

- [x] The sizes Storage shows before downloading are what each one takes on disk once there (unzipped), so the number doesn't change after: waifu2x 54.1 MB on a Mac (35.9 MB on Windows), MangaJaNai 236 MB, IllustrationJaNai 16.2 MB. waifu2x is also taken straight out of its zip now (`save_zip_files` in `utils.py`, shared with the JaNai models), without the photo model Panelyze doesn't use (`models-upconv_7_photo`). Checked: 54,085,110 bytes on disk, the same as shown, and it upscales.

- [x] Running out of space: each model download first checks the disk has room for it (`check_free_space` in `utils.py`), and an upscale checks before it starts that each image fits in memory (at most 16,384 x 16,384 px, `MAX_UPSCALED_PIXELS`) and that the results fit on the disk (at most 3 bytes a pixel). A disk that fills up anyway ("[Errno 28] No space left on device", also inside a failed download) shows one clear message in every tab (`get_error_text`). Storage's first line says how much is free on each disk the files are on ("This computer: 50.4 GB free of 494 GB"; a Panelyze folder on an external drive gets its own line).

- [x] Second review's fixes: Magi's and the emotion model's download progress counted each file twice (a Hugging Face link and its blob); a Pipeline step started with the stages of the step before; a missing Windows drive could make the free space checks loop forever; Magi and the emotion model showed "Downloaded" after a download that stopped half-way (now: their pinned model file must be there); partial downloads retry a dropped connection and skip a server that ignores ranges without downloading the whole file first; waifu2x zip paths are kept inside their folder; the upscale size check counts 4 bytes a pixel (transparency); the sizes everywhere are what's taken on disk.

- [x] Layout after the user's review: each disk as a usage bar (red under 10% free, like File Explorer) with "47.4 GB free of 494 GB"; the "Saved files" and "Downloaded models" headings close to their lists; compact rows; the models grouped by what they're for (Panels and text, Upscaling, Voices) under small gray labels, with bold names and dimmer descriptions; gigabytes with 3 digits ("2.07 GB").

## 7. How to test it
- Fast tests (`python -m pytest`), with fake folders in `tmp_path` and the constants pointed at them.
- By hand: open Settings, check the sizes against Explorer/Finder; delete the "Best" models and run "Best" (they're downloaded again); try Delete during a job (it's off).
- Never point a test at the real Hugging Face cache or the real Documents folder.

## 8. Size, value, risks, open questions

| | |
|---|---|
| Size | Medium (~300 lines with tests) |
| Value | Medium: the app quietly uses 4+ GB of downloads, and saved output grows fast (spec 23 found 17 GB of old test output) |
| Risk: deleting the wrong thing | Paths come only from the app's own constants, never from user input; the Hugging Face rows delete only their own folders; a confirm dialog every time |
| Risk: deleting while in use | Delete is off while a job runs. A Magi model already loaded in memory stays usable until the app restarts |
| Risk: slow sizes | Calculated in the background |
| Answered | Name: "Storage" |
| Answered | Delete is permanent, after a confirm dialog (no `send2trash`, no new package) |
| Answered | Yes, a README line: the first "Best" upscale and the first video that reads the text download up to 2.3 GB more (Settings → Storage) |

## 9. Sources
- Code: `default_settings.py`, `utils.py`, `janai.py`, `magi.py`, `magi_model/full_config.json` (resnet50, trocr), `gui_classes/AppOutput.py`, `gui_classes/AppSettingsView.py`, `gui.py`, `comix_downloader/src/api/comix.py`
- Sizes measured with `du -sh` on the Windows PC, 2026-11-23
- Spec 10 (`specs/10-amd-gaming-pc.md`), spec 23 (`specs/23-cleanup.md`), spec 32 (`specs/32-windows-app.md`)
