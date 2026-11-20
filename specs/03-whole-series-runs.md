# Spec 03: Whole-series runs (e.g. all of Slam Dunk)

Roadmap item [#3](../ROADMAP.md#3-whole-series-runs). Related: [08 – Smaller files](08-smaller-files.md) (disk space) and [16 – More MangaDex options](16-mangadex-options.md) (volume ranges, no cover).

## 1. Summary
Download and convert a whole series in one go: e.g. Slam Dunk, 278 chapters. The download part already works if you paste the manga's URL. Three things are missing:
- **Resuming:** a long run that stops halfway has to start over.
- **Disk space:** the series doesn't fit on this Mac's free space with the current PNG output.
- **Batches:** an easy way to run the series in parts.

## 2. Is it doable?
**Yes.** MangaDex's limits don't get in the way (see below). The downloader already skips chapters it has finished. The main work is in Panelyze:
- don't wipe the Pipeline's folders on a re-run;
- skip chapters that are already done;
- keep the files small (spec 08).

## 3. What's already true (roadmap claims checked)

**Slam Dunk on MangaDex** (checked live via the API on 2026-11-19):

| Fact | Value |
|---|---|
| Manga | "Slam Dunk!", `319df2e2-e6a6-4e3a-a31c-68539c140a84` |
| English chapters | **278**: 1–276, plus 10.5 and 276.5. 31 volumes. |
| Uploads | 291. Chapters 1–12 have 2 groups, and the downloader keeps only one per chapter by default. |
| Pages | **5,497**, about 19.8 per chapter (3 to 37) |
| Problem chapters | 0 with no pages, 0 external links, 0 unavailable, 0 without a title |

**Roadmap claims:**

| Claim | Status | What's really true |
|---|---|---|
| "About 278 chapters" | ✅ | 278 |
| "About 20 pages per chapter, about 5,600 pages" | ✅ | 19.8 per chapter, 5,497 pages |
| Download: about 5 s per chapter, about 25 min | ✅ roughly | Measured on Dragon Ball ch. 93: **5.7 s for 16 pages** (0.36 s a page). That's about **33 min** for the series. |
| Panel-By-Panel: 15–20 s per chapter, 1–1.5 h | ⚠️ too high | benchmarks/magi.md: 9.2 s for 27 pages (0.34 s a page). That's about **7 s per chapter, ~31 min** in total, plus saving the files. |
| Upscale Fast: about 25 s per chapter, about 2 h | ✅ | 31 s for 97 panels (0.32 s a panel). At ~3.6 panels a page (Shachou's ratio, an estimate for Slam Dunk), that's about **1.8 h**. |
| Upscale Best: 45–60 s per chapter, about 4 h | ✅ | About 0.7 s per B&W panel on the Neural Engine, so about **~4 h** |
| Small comic files: "a few seconds" per chapter, about 15 min | ⚠️ **far too low** | Measured now: **0.53 s per panel** (10 upscaled panels). That's about 51 s per 97-panel chapter, **~2.9 h for the series**, and twice that, because a comic file is made after Panel-By-Panel *and* after Upscale. |
| Disk: upscaled PNGs about 2.4 MB a panel, "200+ GB" for the series | ⚠️ too high | About 2.0–2.4 MB a panel × ~19,800 panels = **40–48 GB** |
| Small comic files about 6 GB | ✅ | 0.25 MB a panel, so about **5 GB** |
| Check rate limits | ✅ not a problem | API: about **5 requests/s per IP**; `/at-home/server`: **40 a minute**. A run needs 1 feed call plus 1 at-home call per chapter (278), spread over ~33 min, so roughly 8 a minute. The downloader also waits and retries by itself on a 429 (`network.py`: waits `x-ratelimit-retry-after`, or 120 s). |
| Check missing pages | ✅ handled by the downloader | It skips chapters with 0 pages, retries failed requests 5 times, and checks every page's hash (SHA-256). Running it again re-downloads only missing or broken pages. |
| Resuming: skip chapters already done | ⚠️ only half true | **The downloader** resumes: tested with a 2nd run, which took **1.0 s** ("is verified. no need to re-download"). **The Pipeline** deletes every step's folder at the start of each run (`PipelineView.run_pipeline`, `shutil.rmtree(step_output_directory)`), so nothing can be resumed. |

**New problems found:**

| Problem | Details |
|---|---|
| ⚠️ **Free disk space is only 26 GB** | `df` on this Mac. Peak space for the series with the current settings: downloads 3.8 GB + panels 8.3 GB + upscaled PNG 40–48 GB + 2 sets of comic files 10 GB = **~65 GB**. **It doesn't fit.** With WebP from spec 08 and comic files after Upscale only, it's about 3.8 + 8.3 + 6.5 + 5 = **~24 GB**. That's tight, so run it in batches by volume (spec 16). |
| ⚠️ **Renaming folders breaks the downloader's resume** | `tidy_chapter_folder_names` renames `"Vol. 1 Ch. 3 - "` to `"Vol. 1 Ch. 3"`, but the downloader's `download.db` remembers the old name. I tested this by renaming a folder: the next run re-downloaded all 16 pages into a new folder. It only affects chapters without a title (Slam Dunk has none), so it's a known limit, not a blocker. |
| ⚠️ **The manga cover may become a fake "chapter"** | A manga URL saves `cover.jpg` in the manga folder (`mangadex_downloader/main.py`), and `get_image_folders` treats any folder with images as a chapter. Panel-By-Panel would then run on a "chapter" that's just the cover. Not tested yet; spec 16 adds `--cover none`. |

## 4. Recommended approach

| Option | Verdict |
|---|---|
| **A. Pipeline checkbox "Skip chapters that are already done (resume)".** When it's on: (1) the step folders aren't wiped; (2) each tab skips chapters listed in a small `.panelyze-done.txt` in that step's output folder, and adds each chapter to the list when it finishes. The download step needs nothing, since the downloader already resumes. | ✅ **Recommended.** About 20 lines, in 2 files. |
| B. Skip a chapter if its output folder already exists | ❌ A half-finished chapter (stopped mid-way) would count as done |
| C. Run the whole pipeline one chapter at a time (download ch. 1 → panels → upscale → delete → ch. 2 …) | ❌ The best for disk space, but it's a rewrite of how the Pipeline works |
| D. One big run with no batches | ❌ Doesn't fit in 26 GB. Use batches by volume (spec 16) plus WebP (spec 08). |
| E. Keep the done-list in app settings instead of a file | ❌ It would go stale if the user deletes folders. A file next to the output stays correct. |

## 5. Files to change
| File | Change | Reuse |
|---|---|---|
| `gui_classes/JobView.py` | In `start_job`'s chapter loop: if `self.skip_finished_chapters` is on and the chapter's path (relative to the input folder) is in the done file, skip it (and report it as skipped). After `process_image_folder`, add it to the file. | `get_image_folders`, `report_progress` |
| `gui_classes/PipelineView.py` | Add the checkbox (setting `pipeline_resume`). When it's on, skip the `rmtree` in `run_pipeline`, and set `step_view.skip_finished_chapters = True` around `start_job`, like `ignore_group_by_page` is set now. Add a line to `get_settings_review`. | the `ignore_group_by_page` pattern in `run_step` |
| `default_settings.py` | `"pipeline_resume": False` | — |
| *(from spec 16)* | Start/End Volume, and `--cover none` | — |
| *(from spec 08)* | WebP by default, comic files only | — |

## 6. Steps
- [ ] Do spec 08 (WebP by default) first, or the series won't fit on the disk.
- [ ] Do spec 16's Start/End Volume and "no manga cover".
- [ ] Add the done-list to `JobView.start_job` (off by default).
- [ ] Add the resume checkbox to the Pipeline and keep its folders when it's on.
- [ ] Tests (below).
- [ ] Test run: Slam Dunk vol. 1 (chapters 1–8), stop it halfway, run it again.
- [ ] Update ROADMAP #3 with the measured numbers, and the README.

## 7. How to test
| Test | How |
|---|---|
| Unit: skips finished chapters | Fake 3 chapter folders and a done file listing 1 → `process_image_folder` is called 2 times |
| Unit: a stopped chapter isn't marked done | `process_image_folder` raises an error on chapter 2 → the done file has only chapter 1 |
| Unit: the Pipeline keeps its folders when resume is on | Like `test_old_images_from_a_previous_run_are_not_used`, but with the setting on |
| Unit: resume off = same as now | The existing `tests/test_pipeline.py` tests pass |
| Real | Slam Dunk vol. 1 through the Pipeline, cancel during Upscale, re-run → the download takes about 1 s per chapter, and done chapters are skipped. **Don't open Finder** (the tests block `open_directory`). |
| Long run | One batch of 5 volumes. Watch the time (it may slow down from heat, ROADMAP #11) and the free disk space. |

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | **Small–Medium:** about 20–30 lines plus tests, once specs 08 and 16 are done |
| Value | **High:** makes long runs safe to stop and restart |
| Time for the whole series (estimate) | Download 33 min + panels 31 min + upscale (Fast) 1.8 h ≈ **3 h**. A small comic file after Upscale adds ~2.9 h (spec 08 can cut that). With Best instead of Fast: ~5 h + comic files. |
| Risks | Changed settings between runs make a mixed result: done chapters aren't re-done. Heat slowdowns. MangaDex removing a licensed series mid-run. |

**Open questions for you:**
1. Should the resume checkbox be **on by default**? It's safer off, since it keeps the current "start fresh" behaviour.
2. Should resume also apply to the **single tabs** (Panel-By-Panel, Upscale), or only the Pipeline? Pipeline only is simpler.
3. For the series, do you want comic files after **Upscale only**? The Pipeline currently makes them after both steps, which doubles the time and space.
4. Is running in batches of volumes (e.g. 5 volumes at a time) OK, or do you want a single click for all 31 volumes?

## 9. Sources
- MangaDex rate limits: https://api.mangadex.org/docs/2-limitations/
- MangaDex chapter feed (used live): `https://api.mangadex.org/manga/319df2e2-e6a6-4e3a-a31c-68539c140a84/feed?translatedLanguage[]=en`
- mangadex-downloader docs: https://mangadex-dl.mansuf.link/en/stable/cli_ref/index.html
- mangadex-downloader 3.1.4 source (installed in `venv`): `format/raw.py` (resume/verify), `network.py` (429 handling), `main.py` (cover.jpg)
- [benchmarks/magi.md](../benchmarks/magi.md), [benchmarks/upscaling.md](../benchmarks/upscaling.md), [benchmarks/file-sizes.md](../benchmarks/file-sizes.md)
