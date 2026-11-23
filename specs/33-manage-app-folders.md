# Spec 33: See and clean up the app's folders (Settings → Storage)

Researched 2026-11-23 on the Windows PC, while building spec 10. Planning only: no app code was changed. Builds on spec 10 (the downloaded waifu2x folder), which has to be merged first.

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
| What's downloaded when | waifu2x (both "Fast" and "Better": one program with both models) on the first upscale (`download_waifu2x`, `waifu2x.py`). "Best": only the model that's needed, the first time it's needed (`download_model_file`, `janai.py`): IllustrationJaNai for color images; for black and white, one zip with all 7 MangaJaNai page-height models (all kept). Full Magi on the first video that reads the text (or the first Panel-By-Panel run from source, to build the panels model). Each is checked first and never downloaded twice | — | — |
| Download progress today | `download_file` (`utils.py`) and `download_model_file` only print one line; Magi's download goes through Hugging Face's `from_pretrained` (`magi.py`), which prints its own tqdm bars. `report_progress` (`gui_classes/ProgressPanel.py`) already shows a bar with `pages_done`/`pages_total`/`unit`/`detail` | — | Can show MB done of the total |
| One job at a time | `try_to_start_job` / `is_job_running` (`gui.py`) | — | Delete is turned off while a job runs, so nothing in use is deleted |
| Existing Settings layout | `get_section(title, controls)` and `get_help_text` (`gui_classes/AppSettingsView.py`); sections: start tab, folder, .cbz, log file, reset | — | The new section goes after the folder section |

The Windows paths are the same `~/Library/...` ones for now. Spec 32 moves them to `%LOCALAPPDATA%\Panelyze`; this section reads the same constants, so it follows along.

## 4. Recommended approach + rejected alternatives

| Option | Verdict | Why |
|---|---|---|
| **One "Storage" section in Settings, one row per folder: name, what it is, path, size, Open, Delete** | ✅ **Recommended** | Everything in one place; reuses `get_section`, `open_directory` and the existing constants |
| Sizes worked out when Settings opens, in a background thread ("Calculating..." until done), plus a Refresh button | ✅ | 2–4 GB folders take a second or more to add up; the window mustn't freeze |
| A confirm dialog for every Delete, saying what's lost and whether it comes back ("downloaded again next time" vs "can't be undone") | ✅ | Saved files can't be brought back |
| Saved files: one row per tool folder (Download, Panel-By-Panel, Upscale, Video, Pipeline) plus a total | ✅ | Usually only one tool's output is worth clearing |
| Show other worktrees' folders | ❌ | The user's call: from source, only this worktree's own folder. The packaged app shows no worktree folders at all |
| Delete the whole Hugging Face cache | ❌ | Other apps share it; only Magi's 3 model folders |
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
| `tests/test_storage.py` (new) | Rows from source vs packaged app (no other worktree's folder ever); waifu2x row only for the downloaded copy; sizes; Delete removes only that folder (only Magi's 3 cache folders); Delete is off during a job; the confirm dialog | ~100 lines |
| `README.md`, `DEVELOPING.md` | One line each: where the files are, and that Settings → Storage shows them | ~4 lines |

Reuse: `get_dev_output_folder`/`DEV_OUTPUT_FOLDER`, `OUTPUT_SUBFOLDERS`, `get_output_directory`, `PANELYZE_FOLDER` (`default_settings.py`); `DOWNLOADED_WAIFU2X_FOLDER`, `get_waifu2x_path`, `open_directory`, `is_running_as_packaged_app` (`utils.py`); `MODELS_FOLDER` (`janai.py`); `LOG_FILE_PATH` (`AppOutput.py`); `get_section`, `get_help_text` (`AppSettingsView.py`); `try_to_start_job` / `is_job_running` (`gui.py`).

## 6. Steps (todo)
- [ ] Merge spec 10 into `main` first, then `git merge main` here
- [ ] `get_app_folders` + `get_folder_size`, with tests (source vs packaged, waifu2x only when downloaded, Magi's 3 cache folders only)
- [ ] `StorageSection`: rows, background sizes, Open, Refresh
- [ ] Delete with a confirm dialog; off while a job runs; tests
- [ ] Download progress bar (MB done of the total) for waifu2x, the "Best" models and Magi; tests with a fake download
- [ ] "Download now" buttons for what isn't downloaded yet
- [ ] Add it to Settings; check it at phone width in the browser view (`flet run --web`)
- [ ] Try it on the Mac and the Windows PC: delete the "Best" models and waifu2x, then upscale (they come back); delete a tool's saved files
- [ ] README and DEVELOPING.md lines

## 7. How to test it
- Fast tests (`python -m pytest`), with fake folders in `tmp_path` and the constants pointed at them.
- By hand: open Settings, check the sizes against Explorer/Finder; delete the "Best" models and run "Best" (they're downloaded again); try Delete during a job (it's off).
- Never point a test at the real Hugging Face cache or the real Documents folder.

## 8. Size, value, risks, open questions

| | |
|---|---|
| Size | Medium (~300 lines with tests) |
| Value | Medium: the app quietly uses 4+ GB of downloads, and saved output grows fast (spec 23 found 17 GB of old test output) |
| Risk: deleting the wrong thing | Paths come only from the app's own constants, never from user input; the Hugging Face row deletes only Magi's 3 folders; a confirm dialog every time |
| Risk: deleting while in use | Delete is off while a job runs. A Magi model already loaded in memory stays usable until the app restarts |
| Risk: slow sizes | Calculated in the background |
| Open | Name: "Storage", "Files and storage" or "Disk space"? |
| Open | Should Delete on saved files go to the Recycle Bin/Trash (adds `send2trash`)? |
| Open | Also say it in the README's install steps: "the first upscale and the first video download about 2.5 GB more (shown in Settings → Storage)"? |

## 9. Sources
- Code: `default_settings.py`, `utils.py`, `janai.py`, `magi.py`, `magi_model/full_config.json` (resnet50, trocr), `gui_classes/AppOutput.py`, `gui_classes/AppSettingsView.py`, `gui.py`, `comix_downloader/src/api/comix.py`
- Sizes measured with `du -sh` on the Windows PC, 2026-11-23
- Spec 10 (`specs/10-amd-gaming-pc.md`), spec 23 (`specs/23-cleanup.md`), spec 32 (`specs/32-windows-app.md`)
