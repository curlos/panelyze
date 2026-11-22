# 17. More sources for pages: comic files, page URLs, comix.to, the Internet Archive

Written 2026-11-19, updated 2026-11-20 (American, Western and French comics; PDF; page URLs; the Internet Archive; **comix.to downloader, user decision**). **Built 2026-11-20** (all three phases; see §10 for what was found while building).

Related: [#31 untested formats](31-format-testing-followups.md) (B: Western comics) · [#27 reading direction](27-reading-direction-from-mangadex.md)

## 1. Summary
MangaDex is the only source today. It doesn't have every series in good quality (Slam Dunk is only old fan scans), and it has almost no **American, Western or French comics**, which the app has never been tested on. The user wants to read those panel by panel too (e.g. Absolute Batman, Invincible), the way Webtoon mode was added for webtoons.

**Recommendation:** four new ways to get pages in:
1. **Import comic files** (`.cbz`, `.zip`, `.epub`, **`.pdf`**, later `.cbr`) the user has. Most legal Western comics are sold as DRM-free PDFs.
2. **Download pages from a URL:** paste a web page, and the app saves its big images in order. Generic, with no site-specific code. Good for official preview pages (e.g. DC's previews of Absolute Batman #1).
3. **comix.to downloader** (user decision 2026-11-20): paste a comix.to series link into the existing MangaDex download box, with the same Start/End Chapter settings. comix.to has better scans of some series than MangaDex (e.g. Slam Dunk) and also hosts Western comics. It's an unofficial aggregator behind Cloudflare, so it needs a real browser (a hidden Chrome/Brave/Edge window through `nodriver`). We **copy in the code** of the open-source [comix-downloader](https://github.com/Yui007/comix-downloader) (MIT, last commit 2026-11-08) so it also works in the packaged Mac app. Other aggregators stay out.
4. **Internet Archive downloader:** the only other free official API with comic pages. It keeps **public-domain items only**.

All four end up as a normal folder of pages, so Panel-By-Panel, Upscale and Video don't change.

## 2. Is it doable?
| Option | Doable? | Should the app ship it? |
|---|---|---|
| Import local comic files (.cbz/.zip/.epub) | Yes, with Python's built-in `zipfile`, no new packages | **Yes** (phase 1) |
| Import .pdf | Yes, with `pypdfium2` (Apache/BSD). Avoid PyMuPDF, which is AGPL. | **Yes** (phase 1) |
| Download pages from a URL | Yes, with `requests` (installed) + the built-in `html.parser` + Pillow (installed) | **Yes** (phase 1) |
| Internet Archive, public domain only | Yes: official `advancedsearch` + `metadata` endpoints, no key | **Yes** (phase 2) |
| comix.to downloader | Yes, with a headless Chromium (`nodriver`); plain `requests` is blocked by Cloudflare and a Turnstile check, and pages are drawn on `<canvas>` | **Yes** (phase 2, user decision) |
| Import .cbr (RAR) | Yes on Mac: the built-in `bsdtar` (libarchive 3.7.4) reads RAR4 and RAR5 | Yes (phase 3). Windows needs a check. |
| Other aggregators (ReadComicOnline, GetComics, MangaFire, MangaPark, Weeb Central…) | Technically yes | No, not in this spec |
| DC Universe Infinite / Hoopla / Libby / Kindle / ComiXology / Viz / Shonen Jump / Manga Plus | No: DRM, and no public API | No. The app must not strip DRM. |

**comix.to: risks the user accepted (2026-11-20):**
- **Copyright.** It rehosts comics that are on sale (Viz's Slam Dunk, DC's titles) without a license, like MangaDex's fan scans but more so. Tools built around such sites have had DMCA takedowns (Tachiyomi, ~200 Aniyomi extensions). Keep it a personal-use input and don't advertise it in the README beyond one line.
- **It breaks often.** Aggregators change layouts and bot checks (comix-downloader had a "Fix Comix discovery and chapter fetching" commit on 2026-10-26), and several have shut down (Comick, Bato, TuMangaOnline). Their code is copied in nearly unchanged, so a fix is "copy their newer files over ours and re-apply our few patches".
- **Malware and ads.** Only ever talk to `comix.to` itself; reject other domains.

MangaDex stays as it is today.

## 3. What's already true (checked 2026-11-20)
| Fact | Where | Status |
|---|---|---|
| With the MangaDex step off, the Pipeline already takes a **picked folder** or **picked images** | `gui_classes/PipelineView.py`: `input_directory_row` (line 221), `handle_images_picked` (line 419) | ✅ |
| Picked images are copied into a temporary folder, processed like a folder, and deleted afterwards | `utils.py`: `copy_picked_images_to_folder` (line 81); used in `PipelineView.handle_run_pipeline` (line 474) and `PickInputAndOutputDirectories.py` | ✅ |
| Every step handles nested folders (manga/chapter/pages) | `utils.py`: `get_image_folders` (line 328) | ✅ |
| The app already **writes** .cbz files | `utils.py`: `save_folder_as_cbz` (line 423) | ✅ |
| Natural page order (page_2 before page_10) | `utils.py`: `natural_sort_key` (line 411) | ✅ |
| `is_image_file` skips `._` files | `utils.py` (line 121) | ✅ |
| `requests` is installed | `requirements-lock.txt` (`requests==2.32.3`) | ✅ |
| No PDF or RAR Python package is installed | `requirements.txt` | ✅ |
| macOS ships `bsdtar` with libarchive 3.7.4, which reads RAR | `/usr/bin/bsdtar` | ✅ |
| **DC and Marvel never sell DRM-free files** | DRM-free store guides (§9) | ⚠️ |
| Image Comics (Invincible, Saga, The Walking Dead, Spawn) sells DRM-free PDFs, also on Google Play Books | DRM-free store guides (§9) | ✅ |
| The Internet Archive has many comics as "Comic Book ZIP" (CBZ) or PDF, **mixed public domain and unauthorized uploads** (e.g. Invincible compendiums) | archive.org search (§9) | ⚠️ so filter on the license |
| Besides MangaDex and the Internet Archive, no free official API gives comic page images | API roundups (§9) | ✅ |
| comix.to has no public API for chapters or images. comix-downloader opens pages in headless Chrome with `nodriver==0.50.3`, reads the series from `<script id="initial-data">` and the pages from the reader's `.rpage-page[data-page="N"]` `canvas`/`img` | comix-downloader `src/api/comix.py` | ✅ (read 2026-11-20, not yet run) |
| comix-downloader has a CLI (`python main.py download <url> -c 1-10 -f images -o <folder> --headless`), but it's not a pip package, so the packaged Mac app (PyInstaller, `build_mac_app.sh`) can't run it. Its non-GUI code can be imported directly: `ComixAPI.extract_manga_code(url)`, `ComixAPI.get_manga_info(code, headless=True)`, `ComixAPI.get_all_chapters(code, headless=True)` (oldest first), `ChapterSelector._parse_selection("1-10", chapters)`, `MangaDownloader(DownloadConfig(download_path=..., headless=True)).download_chapters(manga, chapters, progress)` | comix-downloader `main.py`, `src/cli/app.py`, `src/cli/menus.py`, `src/core/downloader.py` | ✅ (read 2026-11-20, not yet run) |
| It saves `<folder>/<Title>/Chapter_<n>[_<title>]/001.webp`, `002.jpg`… (extension from the real image type) | `src/core/downloader.py`, `src/formats/images.py` | ✅ |
| Its code uses relative imports inside a package named `src`, and checks `ComixAPI.get_chapter_image_report.__module__ == "src.api.comix"` (renaming the package makes it silently open a new browser per chapter) | `src/core/downloader.py` | ✅ |
| It writes Cloudflare cookies to `cf_cookies.dat` two folders above `comix.py` (would be inside the `.app`) | `src/api/comix.py` (`_CANONICAL_COOKIE_FILE`) | ⚠️ patch |
| It never sets `browser_executable_path`, so nodriver only finds Chrome | `src/utils/nodriver_browser.py` (`start_browser`) | ⚠️ patch |
| Each chapter row's group element has an `is-official` class for official uploads (the ✓ next to e.g. "VIZ Media"), and the JS already reads it as `group_official`. But the Python side drops it unless the group name is empty, and hard-codes `"votes": 0`: the 👍 count is never read | `src/api/comix.py` (`_CHAPTER_ROWS_JS`, `_normalize_chapter_dom_row`); `Chapter.votes` exists in `src/core/models.py` | ⚠️ patch |
| Several uploads of one chapter number are all kept (deduped only by `chapter_id`). The CLI's range `-c 1-10` downloads every upload, and two uploads with the same number and title write to the same `Chapter_<n>_<title>` folder and overwrite each other. Only the interactive menu picks one per number (first in list, or a scanlator the user types) | `src/api/comix.py`, `src/cli/menus.py` (`_filter_by_scanlator`), `src/core/downloader.py` | ⚠️ we pick one ourselves |
| `nodriver` and `reportlab` are not installed; `rich` and `requests` are | `requirements-lock.txt` (`rich==15.0.0`) | ✅ |
| The MangaDex settings already have Start/End Chapter (`use_start_and_end_chapters`, `start_chapter`, `end_chapter` in `client_storage`) | `gui_classes/SettingsMangaDexDownloader.py` (line 32) | ✅ |
| **Google Chrome is not installed** on this Mac. Brave, Edge and Playwright's Chromium (`~/Library/Caches/ms-playwright/chromium-*`) are; `nodriver` can be pointed at one with `browser_executable_path`. Tested: Edge passes comix.to's checks, hidden or visible; Brave never does (its shields); Playwright's "Chrome for Testing" doesn't start under nodriver | `/Applications`, `~/Library/Caches/ms-playwright` | ⚠️ Edge used |

## 4. Recommended approach and alternatives
| Approach | Verdict | Why |
|---|---|---|
| **"Pick Comic File(s)"**: extract .cbz/.zip/.epub/.pdf into a temporary folder (one subfolder per file), then run like a picked folder | ✅ **Phase 1** | Reuses the temporary-folder path; legal for files the user has; ~3 files touched |
| **"Download pages from a URL"**: fetch the page, find its big images, save them in order, run like a picked folder | ✅ **Phase 1** | Generic (like a browser's "save all images"), no site-specific code. Works for official previews and any page that shows comic pages openly. Pages that need JavaScript or a login are out of scope. |
| **Internet Archive downloader**, public domain only | ✅ **Phase 2** | The only other official free API with pages. A second real downloader next to MangaDex. |
| **comix.to: copy their non-GUI code** into `comix_downloader/src/` (keeping their `src` package name and their LICENSE), import it from a small `download_from_comix.py` | ✅ **Phase 2** | Works in the packaged app (PyInstaller bundles it like `mangadex_downloader`). Whole series and chapter ranges come free. Updates = copy their newer files over. |
| comix.to: call their CLI (`python main.py download …`) | ❌ Rejected | The packaged Mac app has no `python` to run it with, and their repo isn't a pip package. Would only work when running from source. |
| comix.to: write our own scraper from scratch | ❌ Rejected | More code to write and to fix ourselves when the site changes |
| comix.to with plain `requests` | ❌ Doesn't work | Cloudflare + Turnstile check; pages are drawn on `<canvas>` by JavaScript |
| Other aggregators | ❌ Not now | Same risks as comix.to (§2), and the user only asked for comix.to |
| Wrap **gallery-dl**, HakuNeko / HaruNeko, mangal, Kaizoku, Suwayomi | ❌ Rejected | Heavy, mostly aggregator sources, and break when sites change. A small comix.to file is simpler. |
| A general "downloader interface" (base class + subclasses) | ❌ Not now | Too much for this. Each source stays a small function + an input, like MangaDex today. |
| Comic Vine, Jikan, Kitsu, AniList | ❌ Not a source | Metadata only (titles, covers), no pages |
| Unofficial "manga APIs" (MangaLib wrappers, GitHub REST APIs) | ❌ Rejected | They scrape piracy sites |

### Other APIs, checked 2026-11-20
| Source | Official API? | Page images? |
|---|---|---|
| MangaDex | Yes, free | Yes (in the app) |
| Internet Archive | Yes, free | Yes (CBZ/PDF files); public domain only for Panelyze |
| Jikan, Kitsu, AniList, Comic Vine | Yes | No (metadata only) |
| DC Universe Infinite, Webtoon, Manga Plus, Tapas | No public API | Only inside their apps |
| comix.to | No (only an internal `/api/v1/manga` used by its own search) | Yes, through a headless browser (phase 2) |
| MangaLib, GitHub "manga API" projects | No (wrappers that scrape) | Yes, from aggregator sites |

### American comics (DC Absolute titles)
Absolute Batman, Absolute Wonder Woman and Absolute Superman can be read legally, but none can be downloaded as files:

| Source | Legal? | Into Panelyze? |
|---|---|---|
| Hoopla, Libby (free with a library card) | Yes | No: DRM, read in their apps |
| DC Universe Infinite (incl. a free "All In Access Preview Edition" of Absolute Batman #1) | Yes | No: DRM, no public API |
| Kindle / ComiXology, Kobo, Google Play (DC titles) | Yes | No: DRM |
| CANDY Digital (same-day digital issues) | Yes | No: blockchain collectibles, not files |
| **Official preview pages** (DC releases the first ~5 pages; news sites like AIPT and Comic Book Club post them) | Yes | **Yes, with "Download pages from a URL"** |
| Own scans or photos of print volumes | Yes, for personal use | Yes, with Import or "Pick Images" |

So the Absolute titles are tested with their preview pages. For a full modern American volume, use Invincible (DRM-free PDF from Image / Google Play Books): same kind of comic and page layout.

### Legal sources the new inputs handle
| Source | Notes |
|---|---|
| Image Comics, Google Play Books (Image titles only) | DRM-free PDFs: Invincible, Saga, The Walking Dead, Spawn |
| 2000 AD | DRM-free downloads (Judge Dredd) |
| DriveThruComics, Iron Circus, Panel Syndicate | DRM-free PDFs, mostly indie / creator-owned |
| Humble Bundle, Fanatical | DRM-free CBZ / PDF / EPUB in many (not all) bundles |
| Digital Comic Museum, Comic Book Plus | Public-domain Golden Age comics (1938–1956) as CBZ/CBR. Free account needed, so download by hand and Import. |
| Internet Archive | Public-domain items, automatic (phase 2) |
| Pepper&Carrot | French webcomic, CC-BY, free PDFs in French and English |
| Own scans of volumes the user owns | Personal use |

## 5. Files to change and functions to reuse
| File | Change |
|---|---|
| `utils.py` | Add `COMIC_FILE_EXTENSIONS = (".cbz", ".zip", ".epub", ".pdf")` and `extract_comic_files_to_folder(comic_paths)`: builds a temporary folder (same layout as `copy_picked_images_to_folder`) with one subfolder per file, named after it. Zip-based files: write only image entries (`is_image_file`), in natural order of their paths, as `001.jpg`, `002.png`…: never the path inside the archive (blocks "zip slip", and pages with the same name in two folders can't overwrite each other). PDF: render each page with `pypdfium2` to `001.png`, `002.png`… |
| `download_pages_from_url.py` (new) | `download_pages_from_url(url)`: `requests.get` the page (with a normal browser User-Agent and a timeout) → collect image URLs in page order from `<img src>`, `data-src` and the largest `srcset` entry with `html.parser` → make them absolute (`urljoin`) and drop duplicates → download each, open with Pillow, keep only images at least 600 px on the short side (drops ads, icons, avatars) → save as `001.jpg`, `002.jpg`… in a temporary folder named after the page title. Raises a clear "No comic pages found on this page" error when nothing is kept. |
| `download_from_internet_archive.py` (phase 2) | `download_internet_archive_item(url)` (returns a temporary folder, like the other inputs): take the item id from an `archive.org/details/<id>` URL, `GET /metadata/{id}`, and stop with a clear error unless its `licenseurl` is a public-domain mark / CC0 (`publicdomain`). Then pick the .cbz, else .zip, .cbr (phase 3), else the PDF, download from `/download/{identifier}/{file}` with `requests`, then `extract_comic_files_to_folder`. |
| `comix_downloader/` (new, phase 2) | Copied from comix-downloader `main` (note the commit in `comix_downloader/README.md`): `LICENSE`, and under `src/`: `__init__.py`, `api/` (`__init__.py`, `comix.py`), `core/` (`__init__.py`, `models.py`, `downloader.py`), `formats/` (`__init__.py`, `images.py`, `cbz.py`, `pdf.py`), `utils/` (`__init__.py`, `logger.py`, `session.py`, `comix_session.py`, `nodriver_browser.py`, `nodriver_compat.py`, `config.py`, `retry.py`: `utils/__init__.py` imports the last two; `hash.py` isn't needed). Not copied: `gui/`, `src/cli/`, `main.py`, `config.json`, `cf_cookies.dat`. **Our patches, each marked `# Panelyze patch` and listed in `comix_downloader/README.md`:** (1) `nodriver_browser.py`: pass `browser_executable_path` from our browser finder; (2) `comix.py`: cookie file in `~/Library/Application Support/Panelyze/cf_cookies.dat`, not inside the app; (3) if `pdf.py` needs `reportlab`, make `downloader.py` import it only when PDF is picked (we never do) instead of adding `reportlab`; (4) `comix.py` + `models.py`: keep `group_official` as a new `Chapter.official: bool = False`, and read the 👍 count into `Chapter.votes` (add it to `_CHAPTER_ROWS_JS`; the exact selector is found in the spike from a real row's HTML). |
| `download_from_comix.py` (new, phase 2) | `download_from_comix(url, output_directory, terminal_output_list_view, flet_page_client_storage)`, same shape as `download_from_mangadex`. Accept only `comix.to/title/<code>-<slug>` links (host exactly `comix.to`). A chapter link (`…/<id>-chapter-<n>`) downloads only that upload. Add `comix_downloader/` to `sys.path`, find a browser (Chrome, Chromium, then Edge; not Brave; clear error if none), get the series and chapter list, keep the chapters from the MangaDex Start/End Chapter settings with a small `select_chapters_in_range` (simpler than copying their whole `_parse_selection`; all chapters when off), then **keep one upload per chapter number** with `pick_best_upload(uploads)`: an official one (✓) first, else the most 👍, else the first in the list (ties also go to the first). Print which group was picked for each chapter, then `MangaDownloader(...).download_chapters(manga, chapters, Progress(disable=True), on_chapter_complete=...)` with `output_format=IMAGES`, `headless=True`. Each finished chapter prints a line in the terminal output. Raise a clear error if every chapter failed. |
| `gui_classes/PipelineView.py` | In `input_directory_row`: a "Pick Comic File(s)" button (`FilePicker` limited to `COMIC_FILE_EXTENSIONS`, extension checked again in code) and a "Page URL" text field. `handle_comic_files_picked` (copy of `handle_images_picked`, stores `self.input_comic_paths`). In `handle_run_pipeline`, the `copy_picked_images_to_folder` branch becomes one call to `save_input_to_temporary_folder` (page URL, comic files or images), shared with the tabs (it lives in `PickInputAndOutputDirectories.py`). Picking one input clears the others (as `input_image_paths` does today). Phase 2: no new box. An `archive.org/details/…` link pasted into the same "Page URL" field goes to the Internet Archive downloader instead. comix.to: no new box either. In `run_step`, the "MangaDex Downloader" step calls `download_from_comix` when the link's host is `comix.to`, else `download_from_mangadex` as today. The box's label becomes "Enter a MangaDex or comix.to URL". It saves into the same `1-mangadex-download` step folder (renaming the step is a separate change). **Later (built):** the step is "Download", saves into `1-download`, and takes any link `get_downloader` knows. |
| `gui_classes/PickInputAndOutputDirectories.py` | Phase 3: the same inputs (a "Pick Comic File(s)" button and a "Page URL" field, press Enter), so the Panel-By-Panel, Upscale and Video tabs get them too. `save_input_to_temporary_folder` is here. The pick box scrolls when its buttons don't fit (phone-size windows). |
| `self_test.py` | Two more checks for the built app: `.pdf`/`.cbz` open (loads pypdfium2), and the comix.to code and nodriver load |
| `requirements.txt`, `requirements-lock.txt` | Add `pypdfium2` (phase 1) and `nodriver==0.50.3` (phase 2, the version comix-downloader pins) |
| `build_mac_app.sh` | Add `--paths=$REPO_DIR/comix_downloader`, `--collect-submodules=src`, `--collect-all=nodriver`, `--collect-all=pypdfium2` and `--collect-all=pypdfium2_raw`; check `pypdfium2` and `nodriver` are bundled (rebuild + self-test). The browser itself is not bundled: the user's own Chrome/Brave/Edge is used. |
| `tests/test_utils.py`, `tests/test_download_pages_from_url.py`, `tests/test_download_from_comix.py`, `tests/test_internet_archive.py` | See §7 |

Reuse: `copy_picked_images_to_folder` (layout and cleanup), `is_image_file`, `natural_sort_key`, `get_last_directory`, the existing `shutil.rmtree(os.path.dirname(...))` cleanup in both `finally` blocks, and `default_settings.get_output_directory` for where downloads go. The steps themselves (Panel-By-Panel, Upscale, Video) don't change.

Planned as not changed: `download_from_mangadex.py`, `MangaDexDownloaderView.py`, `SettingsMangaDexDownloader.py`. **In the end all three changed a lot:** the Download tab (one URL box for every source, `get_downloader`), page numbering and the result line for MangaDex, and one settings sidebar for each site (see section 6).

## 6. Steps
Work through all three phases without stopping for review, then report once at the end. Never commit.

Phase 1 (Import incl. PDF + page URLs)
- [x] Add `pypdfium2` to `requirements.txt` / `requirements-lock.txt` and install it into the shared venv on purpose (CLAUDE.md: the venv is shared)
- [x] Add `COMIC_FILE_EXTENSIONS` and `extract_comic_files_to_folder` to `utils.py` (.cbz/.zip/.epub/.pdf) + tests
- [x] Add `download_pages_from_url.py` + tests (fake HTML, no network)
- [x] Add the "Pick Comic File(s)" button and the "Page URL" field to `PipelineView.py`, and the two `elif`s in `handle_run_pipeline`; each input clears the others
- [x] Run the full test suite
- [x] Real runs (§7): Absolute Batman #1 preview article (Comic Book Club; AIPT blocks plain requests), Pepper&Carrot PDF, one Golden Age comic (done in phase 2 through the Internet Archive)

Phase 2 (comix.to + Internet Archive)
- [x] Add `nodriver==0.50.3` to `requirements.txt` / `requirements-lock.txt` and install it into the shared venv on purpose
- [x] Copy their files into `comix_downloader/` (list in §5), with `LICENSE` and a `README.md` naming the commit and our patches
- [x] Spike first: a throwaway script in the scratchpad imports the copied code and downloads the test chapter (§7) headless with Brave. If headless can't pass Cloudflare, try `headless=False` with a minimized window; if that fails too, stop the comix.to part and report it. Also save one Slam Dunk chapter row's HTML to find the 👍 count's selector
- [x] Apply the patches (browser path, cookie file, maybe the PDF import, official + votes)
- [x] Add `download_from_comix.py` + tests (URL check, chapter range, browser and downloader faked, no network)
- [x] In `PipelineView.py`, route `comix.to` links in the MangaDex box to `download_from_comix`, and change the box's label
- [x] Real runs: one chapter, then a 3-chapter range with Start/End Chapter
- [x] Check which test comics (§7) the Internet Archive has with a public-domain license
- [x] Add `download_from_internet_archive.py` + tests (fake JSON, no network)
- [x] In `PipelineView.py`, send `archive.org/details/…` links in the "Page URL" field to the Internet Archive downloader
- [x] Real run on one public-domain comic

Phase 3
- [x] .cbr through `bsdtar`, with a clear error if it's missing
- [x] The same inputs in `PickInputAndOutputDirectories.py`
- [x] Update `README.md` ("Import comic files", "Download pages from a URL")
- [x] Run `./build_mac_app.sh` (pypdfium2, nodriver and the comix.to code in the bundle; self-test passes). Built 2026-11-20: 735 MB app, 368 MB zip, all 7 self-test checks pass. A real comix.to download from the built app still needs a manual GUI run.
- [x] Write the Western / American / French results into `benchmarks/panel-cropping.md` (closes #31 B)

Phase 4 (one Downloader tab for MangaDex and comix.to, user request 2026-11-20)
- [x] Rename the "MangaDex Downloader" tab and Pipeline step to "Downloader" (same icon and Ctrl+1; the Pipeline folder is now `1-download`). The default save folder stays `Documents/Panelyze/MangaDex Downloads`
- [x] One box, "Enter a MangaDex or comix.to URL". `get_downloader(url)` (in `MangaDexDownloaderView.py`, used by the tab and the Pipeline) picks the site; any other link is refused at once ("Only MangaDex and comix.to links can be downloaded"). Cancel only shows for MangaDex
- [x] Settings in two labelled groups: "MangaDex and comix.to" (Start/End Chapters, plus a note on how comix.to picks the upload) and "MangaDex only" (everything else)
- [x] comix.to downloads save the reading direction next to each chapter, like MangaDex ones (spec 27): `rtl` for Japanese, `webtoon` for manhwa/manhua (comix.to has no "Long Strip" tag, so a Korean or Chinese series drawn as pages is read as a webtoon), `ltr` otherwise
- [x] Tests, README; real run from the tab: a Google link is refused; Solo Leveling ch. 5 → 169 pages, `webtoon` saved, Panel-By-Panel filled in

Phase 5 (one box for any link, user request 2026-11-21)
- [x] The tab and the Pipeline step are called "Download" (like the other tabs' names), and the default folder is `Downloads` (was `MangaDex Downloads`; an existing old folder is left as it is)
- [x] One box for any link: MangaDex, comix.to, Internet Archive (`archive.org/details/…`, public domain only) or any other web page (its big images). Page and Internet Archive downloads are saved in the Downloads folder (`<page title>/` or `<item title>/`; a folder with the same name gets " (2)"), not a temporary folder. Only text that isn't a web link is refused ("Not a web link (it should start with https://)")
- [x] The Pipeline keeps its own "Page URL" field, and so do the other tabs (for using a page without keeping the download)
- [x] Settings note for web pages and the Internet Archive; README
- [x] Real runs from the tab: "slam dunk" refused; the Absolute Batman preview → 6 pages; Pirates Comics #1 from the Internet Archive → `Downloads/Hillman Pirates Comics 001`

Phase 6 (all downloading in one place, user request 2026-11-21)
- [x] Removed the "Page URL" field from the Panel-By-Panel, Upscale Images and Images To Video tabs and from the Pipeline's input. Links are downloaded in the Download tab, or by the Pipeline's Download step (this replaces "keep the Pipeline's Page URL field" from phase 5). `save_input_to_temporary_folder` only handles comic files and images now
- [x] Under the input buttons: "Comic files: .cbz, .cbr, .zip, .epub or .pdf. Each file becomes a chapter."
- [x] Tests and README updated

Phase 7 (picking between MangaDex groups, user request 2026-11-21)
- [x] Checked how MangaDex Downloader 3.1.4 picks when a chapter has several uploads in the chosen language: the **newest** one (it asks for the chapters newest first and skips the rest as duplicates, `chapter.py` `_check_duplicate`). Full-quality images (not "data saver")
- [x] New "MangaDex only" settings: **Preferred Group (link)** (`--group <link> --group-nomatch-behaviour fallback`: that group's upload, or the newest one when it skipped a chapter) and **Use the First Upload Instead of the Newest** (`--order oldest`). Not added: `--group all` (every group's copy, so duplicate panels), compressed images, and "prefer official groups" (needs our own API calls, and MangaDex removes most official uploads)
- [x] Real check on Slam Dunk ch. 1 (3 English uploads): default → NFy-scans (newest), first upload → Z Quality Scans, preferred group → Tensai Manga Project

Phase 8 (a simpler Download sidebar, user request 2026-11-21)
- [x] The sidebar shows only the settings for the site of the pasted link (`SettingsMangaDexDownloader.show_settings_for`, called as the link is typed, using `get_downloader`). Before a link is pasted, it lists what can be pasted
- [x] MangaDex: Language, "Only some chapters" (Start/End side by side), "Which upload" (The newest / The first / This group's, with the group link box shown only for that choice; one `upload_choice` setting replaces phase 7's two), and "More options" (folded: pages, folder names, covers, replace, oneshots). comix.to: "Only some chapters" and one line on how it picks. Web page and Internet Archive: one line each
- [x] Tests; checked in the browser (empty, MangaDex, comix.to, chapter range, More options open)

Phase 9 (errors in the Status view, user request 2026-11-21)
- [x] The terminal's "Progress" tab is now called **Status** (Raw Output keeps its name). Every error (all 21 callers use `update_terminal_with_error_message`) goes to the Raw Output as before and also to the Status view: a red icon, "Something went wrong" (or the title of the job that just failed, e.g. "Download from comix.to failed."), the message without "ERROR:", and "Full details are in Raw Output.". It stays until the next job starts
- [x] An error opens a collapsed terminal and switches to the Status view, so it can't be missed. Not covered: a crash nothing catches (a Python traceback) still only goes to Raw Output and the log
- [x] Tests; checked in the browser with "aaa" in the Download box

Phase 10 (a compact layout for the Panel-By-Panel, Upscale Images and Images To Video tabs, user request 2026-11-21)
- [x] The two big empty boxes are gone. The input is a card only as tall as its buttons; after picking it shows the name, a line saying what was found (`get_input_summary` in `utils.py`: "3 chapters · 87 pages", "12 images", "2 chapters · 61 pages" for comic files, "No images found in this folder" as a warning), and a ✕ to clear it. The output is one line, `Save to: <folder> 📁 ↺`, like the Download tab. Clear and Submit are 170 px wide, right under them. `ResponsiveColumns` keeps a short main part at the top
- [x] Tests; checked in the browser (empty, folder picked, phone size)
- [ ] **Drag and drop of folders and files: not possible with Flet 0.25.2.** Its desktop client has no file-drop plugin and `DragTarget` only works between controls inside the app. The newest Flet (1.1.2) lists no file drop either, and upgrading would be a big change (e.g. `InputBorder` changed). Left out; revisit if Flet adds it

Phase 11 (a centered, capped layout, user request 2026-11-21)
- [x] Everything (the tabs at the top, the tab's content and the terminal) is at most **1400 px** wide (`MAX_CONTENT_WIDTH` in `gui.py`; Bootstrap's largest container is 1320 and Tailwind's is 1536) and centered. A narrower window is filled completely, as before, and the phone layout below 760 px is unchanged. A wider window only gets more margin on its sides: about 300 px each side at 2000 px, about 1020 px at 3440 px (ultra-wide). The terminal is capped too, since its Status view is the short version
- [x] Only Bootstrap's largest container is copied, not its smaller steps (540, 720, 960, 1140). Those exist because of its 12-column grid; here they would only shrink the 1100 px default window to 960 px for nothing. Easy to add if wanted (`get_content_width`)
- [x] Tests; checked in the browser at 700, 1100, 2000 and 3440 px
- [x] No maximum window size: full screen stays allowed, because the cap already makes it look right

Phase 12 (borders, download progress, results and Cancel, user request 2026-11-21)
- [x] The Download tab's sidebar has no left border (like the other tabs). The terminal gets blue side borders only when the window is wider than the 1400 px content (`TerminalOutput.set_side_borders`)
- [x] Every download shows progress in the Status view: web page "12 of 20 images checked · 1 kept so far" with a bar (a page has ads and icons too, which are left out, so "20" alone was misleading), Internet Archive "x of 132 MB", comix.to "Reading the chapter list: page 12 (240 uploads so far)", then "Chapter 2 of 3 · 37 pages downloaded" (or "12 of 25 pages" for one chapter), MangaDex "n chapter(s) downloaded · Downloading … page k" (it doesn't say how many there will be). comix.to uses a stand-in for the `rich` progress object (`ChapterProgressReporter`), so the copied code isn't changed for it
- [x] When it's done the Status view says what was downloaded, not every page: "Downloaded Slam Dunk chapter 1 · 35 pages", "Downloaded Slam Dunk: 3 chapters · 77 pages", "Downloaded 6 images from comicbookclublive.com" (a web page could have anything on it, so images), "Downloaded Hillman Pirates Comics 001: 52 pages". A MangaDex link that gave nothing is now an error, and one that's already downloaded says "Nothing new". Counts from the way there are cleared, also when it failed
- [x] While it downloads the link box is greyed out and the Download button is replaced by **Cancel**, for every kind of link. Cancel stops web page, Internet Archive and MangaDex downloads straight away; comix.to stops once the chapter being loaded in the browser is done and keeps the chapters that were finished. A cancelled download shows as "cancelled" (grey), not as an error
- [x] **Bugs found while testing every kind of link:** (1) comix.to cookies saved by an earlier session went stale, and then every page waited 60 seconds and failed, so each download now starts without them (patch 5); (2) comix.to's chapter list stopped silently at the first page that didn't load (Dragon Ball: 200 of 1508 uploads), so it's tried once more and a warning is printed (patch 6), and its progress is shown (patch 7); (3) the Internet Archive picker took a `_jp2.zip` the Archive makes itself instead of the `.cbr`; (4) picked comic files with the same name and different extensions overwrote each other's pages
- [x] A comix.to chapter that was already in the folder got the short result "Downloaded absolute batman": the result was worked out from folders that changed, and writing over the pages in an existing folder doesn't change it. It now uses the chapters that finished and the pages counted during this download (`get_comix_summary`), and the reading direction is written into those chapters' folders. MangaDex still uses the folder check, which is right for "Nothing new to download" but untested with "Replace Existing Manga/Chapter" on
- [x] After a successful download, Finder opens the folder that was downloaded, for every kind of link (the Download tab does it, so the Pipeline doesn't open windows mid-run, and the tests never do). The summary line is a `DownloadSummary` (a string that also knows its `folder`). Panel-By-Panel's input is now the series that was downloaded, not just the newest folder. MangaDex's downloader no longer opens Finder by itself
- [x] The job tabs' button says what it does instead of "Submit": **Split Into Panels**, **Upscale**, **Create Video** (next to "Download" and "Run Pipeline"; `submit_text` on each tab). The Status view's first line is now "Ready. Pick your input, then press the button."
- [x] A web page now saves **every image on it**, in page order (it used to leave out anything under 600 px, which was too much: a gallery or an Imgur post would lose images). The Download tab's web page settings have **Only keep bigger images** (off by default) with "Shorter side at least (px)" (600 to start). Without it the progress is "12 of 20 images"; with it "12 of 20 images checked · 3 kept so far". A page with no images says "No images found on this page". Images that can't be read (e.g. SVG icons) are skipped. Not done: telling the page's main content from its ads and menus (e.g. only images inside `<main>` or `<article>`), which would be a guess
- [x] The Raw Output says "Nothing here yet. The details of what Panelyze and its tools are doing show up here." until there's a line, and again if it's cleared (`RawOutputListView`)
- [x] ~~MangaDex pages are numbered from 1~~ **Dropped (2026-11-21):** renaming the downloader's `00.jpg`, `01.jpg`, … pages also meant editing its record of them (`download.db`), or the next run downloaded the chapter again, and it caused the "Download again" double-pages bug below. MangaDex pages now keep the downloader's names. Every tool sorts the pages the same way and numbers its own output, so nothing else changes.
- [x] While a job runs, the input, the output folder, the settings and the buttons can't be changed, in every tab (`set_locked`): the Download tab keeps Cancel clickable; a Pipeline run locks itself, and the other tabs can't be opened while any job runs (see below). Everything is unlocked again afterwards, also after a failure
- [x] Downloading the same thing again no longer starts over (comix.to, web pages, Internet Archive; MangaDex already skipped through its own `download.db`). Each downloaded folder gets a small `download-info.json` (source, chapter id or minimum size, page count). A download is skipped as "Already downloaded: …" only while the folder **still has at least that many images**, so deleting the folder, deleting pages, or moving it means it's downloaded again (an image the user added doesn't); the proof is never kept anywhere else. comix.to checks each chapter (and the upload, by chapter id) and downloads only the missing ones ("Downloaded Slam Dunk chapter 2 · 36 pages · 2 more chapters already downloaded"); a link to one chapter that's already there needs no chapter list at all. Web pages are matched by link and minimum size, the Internet Archive by item (`/details/<item>/page/n5` is the same item). A folder that lost pages is replaced, not left next to a "(2)" copy. "Replace what's already downloaded" (the same setting as MangaDex's "Replace Existing Manga/Chapter", now also in the comix.to, web page and Internet Archive sidebars) forces a new download. Real checks: comix.to chapter 34 s, then 6 s, then 33 s again after deleting a page; web page 9 s then 4 s; Internet Archive 16 s then 4 s. A Pipeline's Download step always starts fresh, since it clears its folder first
- [x] A Pipeline's Download step copies what's already downloaded in the Download tab's folder instead of downloading it again (comix.to chapters, web pages, Internet Archive; `utils.get_library_directory` and `copy_from_library`). The Pipeline still empties its own `1-download` folder first, so nothing else about it changed. MangaDex is not covered: its tool decides from its own `download.db`, which would have to be copied too. "Download again even if already downloaded" (renamed from "Replace what's already downloaded") turns the copying off too
- [x] The Panel-By-Panel, Upscale Images and Images To Video tabs have a Cancel button that takes Clear's place while a job runs (`PickInputAndOutputDirectories.cancel_button`, `JobView.raise_if_cancelled`). waifu2x is stopped at once; MangaJaNai and the other tabs stop between images or chapters, and finished chapters are kept (the one being worked on may be incomplete). It shows the grey "cancelled" state. A Pipeline has no Cancel button yet
- [x] A timer at the top right of the Status view counts the running job (`ProgressPanel.format_duration`: `42s`, `3m5s`, `1h2m3s`, `1d2h3m4s`) and says "Took 3m5s" when it's over. A Pipeline also shows its total ("3m5s · total 10m2s") and ends with a line giving each step's time ("Time: Download 42s · Panel-By-Panel 3m10s · total 10m17s"). Checked in the browser (Flet web mode) with a fake long job
- [x] Dropdowns with long choices (Upscale Model, the comic file setting, Reading Direction, Video Shape) have short names, and a grey line under the box explains the selected one (`DropdownTextOptions.add_descriptions`). Flet 0.25.2 shows an option's whole content in the closed box too, so a long text can't stay in the list only. Checked in the browser
- [x] The app Settings page is split into boxed sections (Starting up, Where everything is saved, Comic files, Log file, Reset), and its dropdowns use the same `DropdownTextOptions` as the tabs. Dropdowns no longer change color when the mouse is over them or after a choice is picked (`hover_color`, and the theme's `focus_color`, since dropdowns ignore their own). The comic file dropdown's "No" is the key "no" (saved as ""), because a choice with an empty key showed nothing in the box. Checked in the browser
- [x] Folder and file paths are shown in one color everywhere (`Nord.PATH`, Nord's teal): the Save to lines, the Settings folder, the Pipeline's folders (which used green, the color of finished messages)
- [x] Clicking Cancel answers at once, in every tab: the button turns into a disabled "Cancelling...", and the Status view (and the Raw Output) says when the job will really stop (`utils.set_cancel_click`, `ProgressPanel.report_cancelling`): "Stopping waifu2x...", "Cancelling after the image being upscaled (MangaJaNai can't stop in the middle of one)...", "Cancelling after the chapter being split into panels...", "Cancelling after the video being made...", "Stopping the download..." (MangaDex), "Cancelling the download..." (web pages, the Internet Archive) and "Cancelling after the chapter being loaded in the browser..." (comix.to). Checked in the browser with a fake slow MangaJaNai job
- [x] Only one job runs at a time, and now that's visible: while one runs, the other tabs (Settings too) are faded and can't be opened, by click, shortcut or arrow keys, with a hint on hover ("Wait for "Upscale" to finish (only one job runs at a time)") (`gui.set_job_running`, `AppBar.change_view`). At first only the other tabs' main buttons were faded, but then a setting in another tab (e.g. comic files, read after each chapter) could still be changed mid-job, and there's nothing else to do in them anyway. So a Pipeline no longer locks every tab's settings either. A queue or several jobs at once with a terminal each were discussed for later
- [x] The Status view shows how much the job has saved next to its timer ("3m5s · 412 MB", then "Took 3m5s · 412 MB"; `ProgressPanel.format_size`, Finder's 1 KB = 1000 bytes). The job's output folder is measured when it starts, then by the timer's own thread (so the job never waits for it) once a second if the job reported progress since (a page, an image, a panel or a voice line done), and once more at the end. Web pages and the Internet Archive are saved in a temporary folder first, so their size only shows at the end (`report_output_folder`, `measure_output`). It's how much bigger the folder got, so files a job replaced can make it less than what was written. When comic files were made, it says how much of it they are: "237 MB (80 MB images + 157 MB .cbz files)" (`get_folder_size` counts the .cbz files on their own)
- [x] Downloads are also saved as comic files with the "Also save each chapter as a comic file" setting: each downloaded chapter (a folder of images with no folders of images inside it, so not a series folder with a cover) gets "<chapter>.cbz" next to its folder. One whose comic file is newer than its pages is skipped, and a chapter downloaded again gets a new one (`save_downloads_as_comic_files`). Not for a MangaDex list of several series (it would be the whole Downloads folder), and an error while making them is printed but the download still counts as a success. Only .cbz: it's a zip, which every comic reader opens; .cbr is RAR, which can't be made freely. Not in a Pipeline's Download step, whose downloads are only the next step's input. Checked in the browser with a fake job
- [x] Only one spinning ring while a job runs: the terminal's title bar keeps its ring (it's what's seen when the terminal is closed or shows the Raw Output), and the Status view shows a still hourglass instead of a second ring. Shared by every tab
- [x] **MangaDex with "Download again even if already downloaded" (found while testing, 2026-11-21):** the chapter ended up with every page twice (16 pages became 32): the downloader saved it again as `00.jpg`... next to the earlier copy that Panelyze had renamed to `001.jpg`.... Fixed by dropping the renaming (see the "Dropped" item above): the downloader now writes over its own pages. Real check on Dragon Ball ch. 93: 16 pages, "Nothing new", then 16 pages with the setting on.
- [x] **Final reviews (2026-11-21):** a review-only agent read every change, then a second agent reviewed again and fixed: a comix.to chapter downloaded again mixed its old and new pages (old ones are now deleted after the new ones are saved); spaces around a link; a Cancel clicked in the first moment of a download (or just before comix.to starts its chapters) was lost; a web page or comic file that failed left its temporary folder behind (a bad image is now skipped); a comix.to chapter number could name a folder outside the series; an Internet Archive title or license given as a list; letters in Start/End Chapter. Then: comix.to likes like "1.2k" are read as 1,200 (patch 11), and a downloaded folder that gained images (added by the user) still counts as downloaded instead of being replaced, which deleted them (`is_download_intact`: at least the recorded pages). Left as is: a very unlikely double start from two tabs clicked in the same instant, and chapters that finish right after a comix.to Cancel are downloaded again next time
- [x] **Fixed (not caused by this spec, found while testing):** a MangaDex chapter without a title (e.g. Eleceed ch. 2) is downloaded again, into a second folder "Ch. 2 -", when its link is downloaded twice. The downloader names that folder "Ch. 2 -" and `tidy_chapter_folder_names` renames it to "Ch. 2", so on the next run it can't find its pages. Chapters with a title aren't affected. Fixing it means no longer tidying those folder names (they'd keep the dash), or something cleverer **Fix (2026-11-21):** chapter folders are no longer renamed (`tidy_chapter_folder_names` is gone), so they keep the downloader's "Ch. 2 - " name and are found again. Only the result line drops the dash ("Downloaded Eleceed Ch. 2"). A folder an earlier version renamed is downloaded once more under the downloader's name
- [x] Input tests for every kind: `tests/make_test_inputs.py` makes a sample of each (`.cbz`, `.zip`, `.epub`, `.pdf`, `.cbr`, loose png/jpg/jpeg/webp images, a chapter, a series, natural page order, a folder without images, a broken file and a `.txt`); `tests/test_every_input.py` runs them and every kind of link (internet faked); `tests/test_e2e_links.py` does the links for real (`pytest -m e2e`); `tests/manual-test-links.md` is the list to try by hand. Real checks: Dragon Ball ch. 93 from comix.to (14 pages), the cancelled 131 MB Internet Archive download
- [x] **Panel-By-Panel saves like the other tabs (2026-11-21):** panels go to `Panel-By-Panel/<series>/<chapter>/` instead of `Panel-By-Panel/panel-by-panel/not-grouped-by-page/<series>/<chapter>/` (and the Pipeline's `2-panel-by-panel/<name>/` the same way). Grouped by page, they go to `<series> (grouped by page)/<chapter>/page_1/...` so the two never mix, also not in the series' folder the next tab reads. A new run deletes only the chapter's old panels, page folders and `panel-text.json` (`remove_old_panels`), not the whole folder: without the extra folders, a picked output folder (e.g. Downloads) could hold other files there. One function builds the path (`get_panels_folder` in `utils.py`) instead of 4 copies. The app already refuses an output folder that's the input's parent or inside it, so panels can't land in the input's chapter folders. Panels made before keep their old folders.
- [x] **Panel-By-Panel skips a chapter that's already split (2026-11-21):** after a split, `panels-info.json` next to the panels records the pages (names and sizes; not times, since imported comic files and picked images are copied to a new temporary folder every run) and the settings that change the panels (reading direction, plus on "Automatic" the direction a download saved next to the pages, show full characters, split tall panels, grouped by page, text read for a video). The next run skips the chapter when they match and its panels are still there (its result line says "Already split into panels (kept): Ch 1", or "… 1 of 2 chapters was already split (kept)." when only some were, like the Download tab's "Already downloaded"; the Status view shows it while the chapter is skipped). Not in a Pipeline: it clears each step's folder before the step runs, so its Panel-By-Panel step always splits again. "Split into panels again even if already split" (off by default) turns it off. Real check, Shachou ch. 1 (21 pages): 14.6 s, then 0.0 s, 63 panels both times.
- [x] **Finder opens the folder with the results (2026-11-21):** Panel-By-Panel, Upscale (which didn't open anything before) and Images To Video open `<tab folder>/<series>` (or `<chapter>`, like the input; `<series> (grouped by page)` for grouped panels), not the tab's whole folder (`JobView.get_folder_to_open`). A MangaDex link that's already downloaded ("Nothing new") now opens its chapter's folder, or the series' for several chapters, read from the downloader's own lines (`Download directory is set to "…"`, `'…' is verified`). Real check: Dragon Ball ch. 93 again gave its chapter folder. The Pipeline still opens its folder and the last step's.
- [x] **Panel-By-Panel says what will be split (2026-11-21):** after a download, its input is still the whole series (so the panels stay together in `Panel-By-Panel/<series>/`), and the line under it now says e.g. "3 chapters · 74 pages · only 1 new chapter to split", or "already split, nothing new to split", using the same check as the skip (`get_already_split_summary`, through a `get_extra_input_summary` hook on the input card). It updates when a Panel-By-Panel setting or the output folder changes.
- [x] **Pipeline and video fixes from a real 4-step run (2026-11-21):** (1) the green checkmark next to "Terminal Output" is hidden when the next job or step starts, so in a Pipeline it only shows when every step is done; (2) under Run Pipeline, a list of the selected steps shows ○ waiting, ⏳ running, ✓ done (with its time) or ✗ failed (`show_step_statuses`); (3) the voice-over counts "images" (or "lines" with highlighted text), not "pages"; (4) writing the video shows the frames written (`VideoWritingProgress`, MoviePy's own progress); (5) MoviePy's temporary audio file is saved next to the video, not in the current folder: run from source with `flet run -r`, that file in the repo restarted the app right after the video was made, so the folders never opened and the Pipeline was cleared ("Event loop is closed" in the log); (6) words split over two lines of a bubble ("Presi- dential", hyphen then a space) are joined before the voice reads them (`join_words_split_across_lines`), only when that makes a real English word (see the "Clearer video progress and voice" item below), so someone cut off ("Wait- Stop!", "Wait- what?!") stays apart, like real hyphens ("hard-working") and stutters ("Wh- what"); (7) after a Download step, the next steps start from the series' folder, so they're `2-panel-by-panel/<series>`, not `2-panel-by-panel/1-download/<series>` (a list of several series keeps the whole folder). Real check: `pytest -m e2e` Pipeline and voiced-video tests passed, no temporary file in the repo.
- [x] **The Pipeline has a Cancel button (2026-11-21):** next to Run Pipeline while it runs. Each step sets what it stops, the same as in that step's own tab (`run_step`): a download through the downloader's own Cancel (the Pipeline's button is passed to it), Panel-By-Panel, Upscale and Images To Video through their `cancel_event` and `cancel_job` (waifu2x stops at once), with that tab's message ("Cancelling after the chapter being split into panels..."). The steps after it don't start. The list under Run shows the step as cancelled and the rest as waiting, and the terminal says "Pipeline cancelled at …"; the finished steps' folders are kept.
- [x] **Clearer video progress and voice (2026-11-21):** (1) reading the text counts "text boxes" (one per bubble or caption), not "lines", also for the voice-over with highlighting, and "1 of 1 text box" in the singular (`get_singular`); (2) Images To Video shows its stages under the title, only the ones it needs: "✓ Reading the text   ● Making the voice-over   ○ Writing the video" (`stages`/`stage` fields, `get_stages_text`), the bar being the current stage's; (3) the size is split by kind when there's more than one (images, .cbz files, video, audio, other; a kind under 1% of it is left out of the split, e.g. a downloader's small files), e.g. "85 MB (40 MB video + 38 MB audio + 7 MB other)"; (4) the voice skips a line that's the same as one in the image just before (a bubble kept whole in two overlapping panels, read in both when Images To Video reads the panels itself); with highlighting, that line is marked as not dialogue, so its highlighted frame and its audio are both skipped (`mark_repeated_lines_as_not_dialogue`). Also when Images To Video reads the panels itself (with or without highlighting): a line whose text box touches the image's edge (cut off, part of the next panel's bubble) is skipped if a similar whole line is in the panel before or after (Shachou ch. 8: "me to think it..." on panel 17's edge, "come to think of it..." whole in panel 18; on the whole chapter, 1 of 161 lines skipped, 6 other lines at an edge kept since they're not whole next door). The proper fix is spec 7 (saving which panel owns each bubble from the page reading). The video's stages also start with "Finding the text". the transcript skips them too (Shachou ch. 3, page 1: Magi's boxes for the first two panels overlap by 343 px, with three bubbles in the overlap, so both crops have them; trimming overlapping panels is left for spec 35); (5) a word split over two lines with a capital after the dash ("Presi- Dent", "Communica- Tions") is joined only if that makes a real English word, checked with **pyspellchecker** (new package, 7 MB, no other packages, added to both requirements files and to `build_mac_app.sh`), so "Wait- Stop!" and "Wait- what?!" stay apart (also in lowercase: someone cut off looks the same); the voice only skips a repeated line of 3+ words or 15+ characters, since short ones ("No!") are often really said again. Real check: `pytest -m e2e` voiced-video and text-to-speech tests passed.
- [x] **Final review (2026-11-22), fixed:** one "Download again even if already downloaded" checkbox for every site (there were two for the same setting, MangaDex's in More options, that didn't follow each other); a new Panel-By-Panel run also deletes the old `reading-direction.txt` (it could give re-split panels the wrong order); starting a job is checked and claimed under a lock (`GUI.try_to_start_job`), so a double-click can't start two; comix.to only takes its own page names (`001.jpg`...) for old pages, so images the user added are never deleted, and a page served as a GIF is saved as a PNG (it wasn't counted, so the chapter was downloaded again every time); Upscale's .cbz uses the reading direction setting like Panel-By-Panel's; a start tab saved as "MangaDex Downloader" opens Download. **Known limits, left as they are:** while downloading, the size counter measures the whole Downloads folder each second (slow only with a very big library); .epub pages are ordered by file name, not the book's own page order (fine for comic .epubs seen so far); kept ("already split") chapters make their .cbz again each run (quick for "Full", slower for "Small").

## 7. How to test it
| Test | How |
|---|---|
| A .cbz becomes one chapter folder in page order | Make a .cbz in `tmp_path` with `zipfile` (`2.png`, `10.png`, `1.png`), extract, check the folder name and images |
| Two files make two chapter folders | Two .cbz files → two subfolders |
| Zip slip is blocked | An entry named `../../evil.png` ends up only as `001.png` inside the temporary folder |
| Non-image entries are skipped | `ComicInfo.xml`, `__MACOSX/._1.png`, `.DS_Store` aren't copied |
| .epub | A small zip with `OEBPS/images/p1.jpg` → the image is extracted |
| .pdf | A 3-page PDF made in the test (Pillow can save one) → `001.png`–`003.png` |
| Page URL: big images in order, ads dropped | A fake HTML page (no network, `requests` patched) with 3 big images (`src`, `data-src`, `srcset`) and 1 small ad image → 3 pages, in page order |
| Page URL: nothing found | A page with only small images → the clear "No comic pages found" error |
| comix.to (phase 2) | No network, `ComixAPI` and `MangaDownloader` faked: a series URL gives the right manga code; another domain or `comix.to.evil.com` gives a clear error; Start/End Chapter 2–3 picks chapters 2 and 3 (also with 2.5 in between); `pick_best_upload`: official beats more votes, more votes beats fewer, all equal → the first; three uploads of ch. 274 → one folder; settings off → all chapters; every chapter failed → clear error; the browser finder picks Brave when there's no Chrome, and errors clearly when there's nothing. One import test checks the copied package loads (`from src.api.comix import ComixAPI`). |
| Internet Archive (phase 2) | Fake metadata JSON (no network): a public-domain item → the .cbz is picked over the PDF; an item without a public-domain license → a clear error and nothing downloaded; a non-`archive.org` URL goes to the page-URL path instead |
| Full Pipeline | With the existing fake steps in `tests/test_pipeline.py`, a picked .cbz and a page URL flow into Panel-By-Panel |
| Real runs | Output to `~/Documents/Panelyze/17-second-downloader/` (CLAUDE.md). Check the panel order by eye on 3–4 pages each, with "Left to right" |

**Test comics (legal):**
| Comic | Kind | How to get it | Cost |
|---|---|---|---|
| **Absolute Batman #1, Absolute Superman #1** (official preview pages) | American, DC | "Download pages from a URL" on a preview article (AIPT, Comic Book Club: 4–5 pages + cover) | Free |
| **Invincible** (also Saga, The Walking Dead, Spawn) | American, Image | DRM-free PDF from Google Play Books or Image → Import | Paid |
| Judge Dredd / 2000 AD | British | 2000 AD's store, DRM-free → Import | Paid |
| The Private Eye (Panel Syndicate) | American | Pay what you want, DRM-free (check the site) | Free+ |
| **Pepper&Carrot** | French, CC-BY | Free PDF (peppercarrot.com / KDE Store), French and English | Free |
| **Popeye** (Thimble Theatre, 1929) | American strips | Public domain in the US since 2025 | Free |
| **Tintin in the Land of the Soviets** (1930) | Franco-Belgian | Likely public domain in the US since 2026 (not in Europe); check before using | Free |
| **Plastic Man** (Police Comics #1, 1941) and other Golden Age heroes | American, Golden Age | Listed as public domain (name is a DC trademark); Digital Comic Museum (by hand → Import) or the Internet Archive (automatic, phase 2) | Free |
| DC Absolute titles, full volumes | American | Only own scans of print volumes | Paid |

**comix.to test chapters:** Dragon Ball ch. 93 (same as the MangaDex test chapter, so the two can be compared side by side), then Slam Dunk ch. 1–3 as a range (the reason for this source; the VIZ Media ✓ upload should be picked where there is one, checked in the terminal output and by the scan quality). Find the series links by hand on comix.to. Also one run from the built `Panelyze.app`.

Notes: the first Superman (Action Comics #1, 1938) and Batman (Detective Comics #27, 1939) are **not** public domain in the US until Jan 1, 2034 and Jan 1, 2035. The Internet Archive's Invincible uploads aren't public domain either, so the downloader skips them on purpose.

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | **Medium.** Phase 1: ~50 lines in `utils.py`, ~60 in `download_pages_from_url.py`, ~40 in `PipelineView.py`, plus tests. Phase 2: ~60 lines in `download_from_comix.py` + their copied files (~100 KB, mostly `comix.py` and `downloader.py`) + ~70 lines for the Internet Archive, plus tests. |
| Risk: comix.to | Cloudflare may block headless browsers (then a visible window, or give up: see the spike step). The site's layout can change at any time and break the downloader. Chapter loads are slow (seconds per page; up to 90 s per chapter in comix-downloader). Needs a Chromium browser installed (no Google Chrome on this Mac). Their code runs its own event loop in a thread; check it doesn't clash with Flet's. Their `src` package name is generic; Panelyze has no `src` folder today, so no clash. Copyright: see §2. |
| Value | **High.** First real test of American, Western and French comics, and any legal file or page can go into the Pipeline |
| Risk: big files | A large .cbz or PDF is extracted to the temporary folder first (a few hundred MB, deleted afterwards). PDF pages are rendered at a fixed DPI (start at 200; check against the original image size) |
| Risk: page URLs | Lazy-loaded or JavaScript pages give nothing (clear error, by design). Some sites block plain requests. The 600 px filter may keep a big banner image: the user can delete it, and the panel step skips pages with no panels. |
| Risk: Internet Archive licenses | Uploads mix public domain and unauthorized copies. Only items whose `licenseurl` is a public-domain mark or CC0 are downloaded. **But uploaders set that field themselves, and some are wrong**: "Joker Last Laugh Secret Files" (DC, 2001) and Tintin's "Les cigares du Pharaon" are marked CC0. The check stops most unauthorized copies, not all. |
| Risk: EPUB order | Page order may not match file names in some books; leave the EPUB page list out unless it's a real problem |
| Risk: Flet file picker | The Mac filter may let other files through, so the code checks the extension again |

**Decisions (user, 2026-11-20)**
1. **.cbr on Windows:** not now (no Windows testing yet). Later, if needed.
2. **One folder per picked file:** yes. Two .cbz files become two chapter folders.
3. **Page URL:** one page only for now. Following "next page" links can come later.
4. **Which tabs:** the new inputs go into the **Pipeline** tab in phase 1, and into the Panel-By-Panel, Upscale and Video tabs (their own "pick a folder" inputs) in phase 3.
5. **Pacing:** all phases run straight through with one report at the end, no review stops.
6. **comix.to:** yes, add it (2026-11-20), by copying comix-downloader's code in (not calling its CLI), so it works in the packaged Mac app too.
7. **comix.to range:** a whole series with a chapter range, like MangaDex, reusing the MangaDex Start/End Chapter settings.
8. **comix.to duplicate uploads (2026-11-20):** one upload per chapter number: the official one (✓, e.g. VIZ Media) first, otherwise the most 👍, otherwise the first listed. No group setting for now.

## 9. Sources
- Comick shutdown, called a major piracy site: https://animecorner.me/comick-shut-down-manga-piracy-site/
- Fake Comick copy domains flagged: https://tools.malwaretips.com/url-scan/comick.art
- comix.to as an unofficial reader (keiyoushi extension request, Next.js): https://github.com/keiyoushi/extensions-source/issues/11479
- comix-downloader (MIT, nodriver, chapter page parsing in `src/api/comix.py`): https://github.com/Yui007/comix-downloader
- Sony's DMCA notice removes about 200 Aniyomi extensions; Tachiyomi's shutdown: https://torrentfreak.com/sony-dmca-notice-nukes-200-aniyomi-extensions-as-tachiyomi-fork-feels-heat-240617/
- Bato and TuMangaOnline shutdowns: https://en.wikipedia.org/wiki/Bato_(website), https://en.wikipedia.org/wiki/TuMangaOnline
- gallery-dl supported sites: https://github.com/mikf/gallery-dl/blob/master/docs/supportedsites.md
- Suwayomi ships no extensions: https://github.com/Suwayomi/Suwayomi-Server
- Free manga APIs (MangaDex, Jikan, AniList): https://apideposu.com/en/blog/best-free-anime-manga-apis · unofficial MangaLib wrapper: https://parse.bot/marketplace/da5721d4-72ca-417e-b790-88b9d712d559/mangalib-org-api
- DRM-free comic stores (Image incl. Invincible on Google Play Books, DC/Marvel never DRM-free): https://applestan.com/blog/posts/where-to-find-drm-free-comics/, https://www.diversetechgeek.com/where-buy-drm-free-digital-comics-2025-edition/, https://libreture.com/bookshops/
- 2000 AD DRM-free: https://2000ad.com/news/keep-what-you-buy-forever-download-copies-of-your-digital-comics-from-2000-ad-drm-free/
- Kodansha × Humble bundles (DRM-free, CBZ/PDF/EPUB): https://kodansha.us/?p=104702
- Absolute Universe on Hoopla / Libby / DC Universe Infinite: https://theloop.hoopladigital.com/articles/comics/dc-absolute-universe-comics-on-hoopla/, https://www.overdrive.com/media/12163785/absolute-batman-2024-volume-1, https://www.dcuniverseinfinite.com/collections/cc-dc-absoluteuniverse
- Absolute Batman #1 free preview edition (DC Universe Infinite): https://www.dcuniverseinfinite.com/comics/book/absolute-batman-1-all-in-access-preview-edition/6e8e1693-0c87-4763-925d-b335b6c1ca9e
- Absolute Batman #1 preview pages: https://aiptcomics.com/2024/10/03/dc-preview-absolute-batman-1/, https://comicbookclublive.com/2024/10/04/dc-comics-preview-absolute-batman-1
- No DRM-free DC Absolute files; CANDY Digital: https://comicsbulletin.com/dc-absolute-universe-25-bundle-image-hits/
- Internet Archive comics, mixed licenses (public-domain CBZ vs unauthorized Invincible): https://archive.org/details/pa-comics, https://archive.org/details/invincible-compendiums
- Public-domain heroes and 2026 public domain (1930 works): https://pdsh.fandom.com/wiki/Public_Domain_Super_Heroes, https://bwspotlight.com/2026/01/06/public-domain-in-2026-who-joins-the-free/
- Digital Comic Museum (public domain, account needed): https://digitalcomicmuseum.com/
- Pepper&Carrot (CC-BY, free PDFs): https://www.davidrevoy.com/article549/peppercarrot-free-pdf-of-book-one/show, https://store.kde.org/p/1316697
- WEBTOON terms (personal use in their apps only): https://www.webtoons.com/en/terms
- PyMuPDF is AGPL: https://pymupdf.readthedocs.io/en/latest/about.html · pypdfium2 is Apache/BSD: https://pypi.org/project/pypdfium2/
- libarchive RAR5 support: https://gitlab.gnome.org/GNOME/evince/issues/1190
- MangaDex background and takedowns: https://en.wikipedia.org/wiki/MangaDex

## 10. Results (2026-11-20)
| Run | Result |
|---|---|
| Absolute Batman #1 preview (Comic Book Club, page URL) | 6 pages (the article banner is page 1) → 22 panels in 10 s, right order. AIPT gives 403 (Cloudflare), as expected for some sites. |
| Pepper&Carrot book 1 (PDF, 82 pages) | 265 panels in 62 s, right order |
| Pirates Comics #1 (Hillman 1950, Internet Archive .cbz) | 52 pages → 264 panels in 36 s, right order. "Invincible [Compendiums]" is refused (no license). |
| Hollywood Detective (1944, real RAR4 .cbr) | 116 pages extracted in 5.4 s |
| comix.to: Dragon Ball ch. 93 (range 93–93) | VIZ Media ✓ upload picked; 14 pages (1500×2250 WebP) in 74 s, with a hidden Edge window |
| comix.to: Slam Dunk ch. 1–3 (range) + Panel-By-Panel | VIZ Media ✓ picked each time; 77 pages; chapter list 46 s (847 uploads); 354 panels; right order (right to left) |

**Found while building**
- **Browsers:** comix.to's Turnstile check passes in Edge (hidden or visible) and fails in Brave, so Brave isn't used. Without Chrome, Chromium or Edge, the app says so clearly.
- **comix.to's ✓ isn't always a real official scan.** The Slam Dunk ch. 1–3 "VIZ Media ✓" uploads are titled "(Colored Council) (delete)" and are a fan-colored edit (two-tone red, one leftover Chinese translator note). The rule (✓, then likes, then first) follows what the site says; it can't tell.
- **Internet Archive licenses are set by uploaders** and some are wrong (§8).
- Their search (`ComixAPI.search_manga`) fails today (`RemoteObject is not JSON serializable`); Panelyze doesn't use it.
- On a phone-size window the input box shows two of its four options until it's scrolled.

