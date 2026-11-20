# Spec 16: More MangaDex Downloader options in the app

New roadmap item #16. Related: [03 – Whole-series runs](03-whole-series-runs.md) (runs in batches by volume, the cover "chapter") and [08 – Smaller files](08-smaller-files.md).

## 1. Summary
Let the MangaDex Downloader tab use more of the downloader's options. The main one is **chapter ranges** like `1-5, 7-10`. Others: **volume ranges**, and **skipping the manga cover**. Also tidy up two checkboxes that do nothing today.

## 2. Is it doable?
**Yes, with one catch:**
- **The downloader's own `--range` option is turned off** in its latest version ("[DISABLED] … because it's broken and need to rework", `cli/__init__.py`).
- So Panelyze has to do ranges itself: run the downloader once per range with `--start-chapter`/`--end-chapter`. Each extra run only costs about 1 s to fetch the chapter list.

## 3. What's already true (claims checked)
| Claim | Status | Details |
|---|---|---|
| The app uses the **mangadex-downloader** CLI | ✅ | `requirements.txt`: `mangadex-downloader==3.1.4`. Started as `python -m mangadex_downloader` (or `--run-mangadex` in the packaged app), in `download_from_mangadex.py`. |
| 3.1.4 is the newest | ✅ | PyPI and GitHub: v3.1.4 (2025-05-19), no release since. The repo was last pushed Feb 2026, and it's not archived. |
| `--range` works | ⚠️ **disabled** | It's in `--help` but marked [DISABLED], and refused for chapter URLs anyway |
| Chapter/volume options work for a single-chapter URL | ⚠️ **no** | For a chapter URL only `--replace` and `--start/--end-page` are used (`cli/url.py`, `download_chapter`). The chapter/volume options only work with a **manga** URL. |
| "Use Chapter Cover" and "Use Volume Cover" do something | ⚠️ **no** | `--help`: they only work for the single/volume formats ("not enabled if you are using any chapter format (cbz, pdf, raw, etc)"). The app always uses `raw` (no `--save-as`), so both checkboxes do nothing. |
| "Language" only applies to manga URLs | ✅ | Matches the comment in `SettingsMangaDexDownloader.py` |
| A manga URL saves `cover.jpg` in the manga folder | ✅ in the code, not tested in the app | `main.py` saves `path / "cover.jpg"` unless `--cover none`. Panelyze's folder scan would treat that as a 1-image "chapter" (spec 03). |

### All CLI options (mangadex-downloader 3.1.4, from `--help`)
"In the app" = already a setting in the MangaDex Downloader tab.

| Option | What it does | In the app? | Recommendation |
|---|---|---|---|
| `URL` | Manga/chapter/list URL, or a **text file of URLs** | ✅ (one URL) | Later: several URLs, one per line |
| `--type/-t` | Override the URL type | ❌ | No (auto-detect works) |
| `--replace/-r` | Re-download even if done | ✅ "Replace Existing Manga/Chapter" | Keep |
| `--filter/-ft` | Filters for search/random | ❌ | No |
| `--download-mode` default/unread | Only unread chapters (needs a login) | ❌ | No (needs a login) |
| `--path/-d` | Folder, with placeholders | ✅ (always set by the app) | Keep |
| `--filename-single/-volume` | Names for the single/volume formats | ❌ | No (the app uses raw) |
| `--filename-chapter/-fc` | Chapter folder name | ✅ "Include Chapter Title in Folder Names" | Keep |
| `--search/-s` | Search by title | ❌ | No (the app has no prompt) |
| `--use-alt-details/-uad` | Alternative title | ❌ | No |
| `--create-manga-info`, `--manga-info-format/-filepath/-only` | Write manga_info.csv/json | ❌ | No |
| `--group/-g` ID or `all` | Pick the scanlation group | ❌ | **Maybe later** (needs a group ID; "all" makes duplicates) |
| `--group-nomatch-behaviour` | Fallback if the group is missing | ❌ | Only with `--group` |
| `--language/-lang` | Language | ✅ dropdown | Keep |
| `--list-languages` | Print the languages | ❌ (the app has its own list) | No |
| `--volume-cover-language/-vcl` | Volume cover language | ❌ | No (raw doesn't use it) |
| `--start-volume/-sv`, `--end-volume/-ev` | Volume range | ❌ | ✅ **Add** (batches for spec 03) |
| `--start-chapter/-sc`, `--end-chapter/-ec` | Chapter range | ✅ "Use Start and End Chapters" | Replace with **Chapters** ranges (below) |
| `--no-oneshot-chapter/-noc` | Skip oneshots | ✅ | Keep |
| `--no-group-name/-ngn` | No group name in the folder name | ✅ | Keep |
| `--use-chapter-title/-uct` | Title in the name | (the app uses `--filename-chapter` instead) | Keep as is |
| `--range/-rg` | Range pattern | ❌ **disabled in the tool** | Done by the app instead |
| `--sort-by` chapter/volume | Download order | ❌ | No |
| `--use-chapter-cover/-ucc` | Chapter info page (single/volume formats only) | ✅ but **does nothing** | **Remove the checkbox** (or hide it) |
| `--use-volume-cover/-uvc` | Volume cover (volume formats only) | ✅ but **does nothing** | **Remove the checkbox** (or hide it) |
| `--ignore-missing-chapters/-imc` | Don't re-download deleted chapters | ❌ | Maybe (handy if you delete the raw pages after a run; spec 08 Q3) |
| `--create-no-volume/-cnv` | Volume format only | ❌ | No |
| `--order` newest/oldest | Which upload wins for duplicates | ❌ | No |
| `--start-page/-sp`, `--end-page/-ep` | Page range | ✅ | Keep |
| `--use-compressed-image/-uci` | MangaDex "data saver" (smaller, lower-quality pages) | ❌ | **Maybe**: the downloads are smaller, but worse pages before upscaling |
| `--cover/-c` original/512px/256px/none | Manga cover quality | ❌ | ✅ **Add as a checkbox, default "no cover"** (`--cover none`) |
| `--login`, `--login-method/-username/-password/-api-id/-api-secret/-cache` | MangaDex account | ❌ | No (passwords in the app, and not needed for public chapters) |
| `--save-as/-f` raw/pdf/cbz/cb7/epub (+volume/single) | Output format | ❌ (always raw) | No: Panel-By-Panel needs raw images, and Panelyze makes its own .cbz |
| `--proxy/-p`, `--proxy-env`, `--dns-over-https/-doh` | Network routing | ❌ | No |
| `--force-https/-fh` | Port 443 only | ❌ | No (only for blocked networks) |
| `--delay-requests/-dr` | Wait between requests | ❌ | No (rate limits aren't a problem, spec 03) |
| `--timeout`, `--http-retries` | Network retries (default 5) | ❌ | No for now |
| `--input-pos`, `-pipe`, `--page-size`, `--run-forever` | Prompts/pipes/loops | ❌ | No |
| `--no-track` | No download tracking | ❌ | **Never**: it turns off resume and page checks (spec 03) |
| `--no-metadata` | ComicInfo.xml for cbz | ❌ | No |
| `--log-level`, `--progress-bar-layout`, `--stacked-progress-bar-order` | Console output | ❌ | No: the progress panel reads the "Downloading … page N" lines (`parse_mangadex_progress_line`) |
| `--update`, `-v` | Update / version | ❌ | No (pinned version) |

## 4. Recommended approach
| Option | Verdict |
|---|---|
| **A. A "Chapters" text box (e.g. `1-5, 7-10, 12`) in place of the Start/End Chapter boxes.** Empty = all. The app splits it into ranges and runs the downloader once per range with `--start-chapter X --end-chapter Y`. `12` = 12–12. Ranges are inclusive, so `10-11` includes 10.5. Show a clear error for text it can't read. | ✅ **Recommended** |
| B. Use the downloader's `--range` | ❌ Disabled in 3.1.4 |
| C. Call the downloader's Python code directly with its range parser | ❌ The app runs it as a separate process so it can be cancelled and its output shown. Too big a change. |
| D. Keep Start/End Chapter and add the ranges box too | ❌ Two ways to do one thing. *Your call (question 1).* |
| **E. Also add a "Volumes" box** (`1-5`, one range only) → `--start-volume/--end-volume` | ✅ Recommended. One range only (a list of volume ranges could reuse A's loop, but isn't needed now). |
| **F. "Download the manga cover" checkbox, off by default** → `--cover none` when off | ✅ Recommended (no fake cover "chapter") |
| **G. Remove "Use Chapter Cover" / "Use Volume Cover"** | ✅ Recommended. They do nothing with the raw format. |
| H. Group picker, data saver, several URLs, login | ❌ Not now (listed above for later) |

## 5. Files to change
| File | Change | Reuse |
|---|---|---|
| `download_from_mangadex.py` | New `parse_chapter_ranges(text)` → `[(start, end), ...]` or an error. In `download_from_mangadex`, loop over the ranges and run the existing command once per range (one `ProcessManager`, so Cancel stops the loop). Add `start_volume`/`end_volume` and `--cover none` to `get_additional_terminal_options`. Drop the 2 cover options. | `get_additional_terminal_options`, `ProcessManager.monitor_terminal_output`, `get_mangadex_progress_reporter` (create it once so the chapter count carries across ranges), `tidy_chapter_folder_names` (once at the end) |
| `gui_classes/SettingsMangaDexDownloader.py` | The Chapters box (a normal `TextField`, not a number box) instead of the Start/End Chapter boxes and checkbox. The Volumes box. The cover checkbox. Remove the 2 cover checkboxes. A hint: "Chapters and volumes only work with a manga link, not a chapter link." | `SettingsBase.change_setting`, `WrappingCheckbox` |
| `default_settings.py` | `"chapter_ranges": ""`, `"volume_range": ""`, `"download_manga_cover": False`. Remove the old chapter/cover keys. | — |
| `gui_classes/PipelineView.py` | `get_settings_review`: show "chapters 1-5, 7-10" / "volumes 1-5" | — |

## 6. Steps
- [ ] `parse_chapter_ranges` and its tests (`"1-5, 7-10"`, `"12"`, `"10.5"`, `"5-1"` → error, `"abc"` → error, `""` → all).
- [ ] The loop in `download_from_mangadex`, with one progress reporter and Cancel stopping it.
- [ ] Volumes box and cover checkbox → the right command-line options.
- [ ] Remove the 2 cover checkboxes that do nothing.
- [ ] Update the Settings form, the defaults and the Pipeline review.
- [ ] Update README/DEVELOPING.md ("Downloads" section).

## 7. How to test
| Test | How |
|---|---|
| Unit: commands | Like `tests/test_mangadex_folders.py`: fake storage with `chapter_ranges="1-5, 7-10"` → 2 commands with the right `--start-chapter/--end-chapter`; `volume_range="2-3"` → `-sv 2 -ev 3`; the cover box off → `--cover none` |
| Unit: Cancel | A fake process cancelled during range 1 → range 2 never starts |
| Real (short) | Dragon Ball ch. 93 chapter URL, pages 1–3 (the default test chapter). It still works; chapter ranges are ignored for a chapter URL, as expected. |
| Real (ranges) | The Slam Dunk manga URL with `Chapters = 1-2, 4` → exactly 3 chapter folders, no `cover.jpg`. About 1 minute and ~10 MB. |
| GUI | Web mode + headless Playwright screenshot of the settings panel (see the "Flet web mode testing" memory). Don't open Finder. |

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | **Small:** ~40 lines plus tests |
| Value | **Medium–High:** chapter picking you can't do now, and it's needed for spec 03's batches |
| Risks | Your saved Start/End Chapter values are dropped. A chapter numbered "0" or a oneshot can slip through a range (the downloader treats it specially). Ranges with a chapter URL quietly do nothing, so the hint is needed. |

**Open questions for you:**
1. **Replace** the Start/End Chapter boxes with the "Chapters" box, or keep both?
2. Should the "Volumes" box also take a list (`1-3, 7-9`), or is one range enough?
3. OK to **remove** "Use Chapter Cover" and "Use Volume Cover", since they do nothing today?
4. Any interest in **"data saver" images** (smaller downloads, lower quality) or **picking a scanlation group**?
5. Want a box for **several manga links at once** (one per line)? The downloader supports a file of URLs.

## 9. Sources
- mangadex-downloader CLI reference: https://mangadex-dl.mansuf.link/en/stable/cli_ref/index.html
- PyPI (3.1.4 newest): https://pypi.org/project/mangadex-downloader/
- GitHub releases: https://github.com/mansuf/mangadex-downloader/releases
- Installed source (`venv/.../mangadex_downloader`): `cli/args_parser.py`, `cli/__init__.py` ("--range is disabled"), `cli/url.py` (options by URL type), `main.py` (cover.jpg), `chapter.py` (duplicate and oneshot handling)
- `venv/bin/python -m mangadex_downloader --help` (run on 2026-11-19)
