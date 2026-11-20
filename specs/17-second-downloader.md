# 17. A second source for pages (better quality than MangaDex)

Written 2026-11-19. Planning only: no code has changed.

## 1. Summary
MangaDex doesn't have every series in good quality. For example, Slam Dunk on MangaDex is only old, low-quality fan scans. The user wants the high-quality Viz Media pages, which they find on a site called "Comix" (comix.to).

**Recommendation:** don't build a downloader for Comix or any site like it. Instead, add an **"Import comic files"** input: the Pipeline (and the Panel-By-Panel, Upscale and Video tabs) can take `.cbz`, `.zip`, `.cbr` and `.epub` files, and later `.pdf`, that the user already has. Inside the app, picking a folder or loose images already works. This adds comic files next to them, using the same "copy into a temporary folder" path the image picker uses.

## 2. Is it doable?
| Option | Doable? | Should the app ship it? |
|---|---|---|
| Scraper for comix.to (or Comick, MangaFire, MangaPark, Weeb Central and the like) | Technically yes | **No.** See below. |
| Import local comic files (.cbz/.zip/.epub) | Yes, with Python's built-in `zipfile` and no new packages | **Yes** |
| Import .cbr (RAR) | Yes on Mac: the built-in `bsdtar` (libarchive 3.7.4) reads RAR4 and RAR5 | Yes. Windows needs a check (see open questions) |
| Import .pdf | Yes, with the new `pypdfium2` package (Apache/BSD license). Avoid PyMuPDF, which is AGPL. | Later, as phase 2 |
| Viz / Shonen Jump / Manga Plus / Kindle / ComiXology | No: these use DRM, and the app must not strip it | No |

**Why not a Comix scraper, said plainly:**
- **It's piracy.** Viz's English Slam Dunk is a licensed, sold product. Its pages rehosted on comix.to or any other aggregator are pirated copies. comix.to is an unofficial reader of the same kind as Comick, which shut down in September 2025 and was described in the press as one of the world's biggest manga piracy sites. A downloader made for it would be a piracy tool built into Panelyze.
- **Legal risk for the app.** Tools built around piracy sources get DMCA takedowns. Tachiyomi shut down after legal threats from Kakao, and Sony's DMCA notice removed about 200 Aniyomi extensions. If Panelyze is ever shared or put on GitHub, a built-in Comix source puts the whole repo at risk.
- **It breaks often.** These sites change domains, layouts and APIs all the time. comix.to is built with Next.js, which made chapter pages hard to scrape even for the keiyoushi extension authors. Many of these sites also sit behind Cloudflare bot checks. Every change would break the feature.
- **Malware and ads.** Aggregators earn money from aggressive ads. Fake copies of these sites spread after shutdowns: after Comick closed, fake ".art" and other copy domains were flagged as possibly malicious.
- **Against their terms.** Scraping usually breaks a site's terms of use anyway, even before the copyright problem.

## 3. What's already true
| Fact | Where |
|---|---|
| With the MangaDex step off, the Pipeline already takes a **picked folder** or **picked images** as its input | `gui_classes/PipelineView.py`: `input_directory_row`, `handle_directory_picked`, `handle_images_picked` |
| Picked images are copied into a temporary folder named after them, then processed exactly like a folder, and the folder is deleted afterwards | `utils.py`: `copy_picked_images_to_folder`; used in `PipelineView.handle_run_pipeline` and `PickInputAndOutputDirectories` (around line 292) |
| Every step handles nested folders (manga/chapter/pages) | `utils.py`: `get_image_folders`, `construct_directory_structure` |
| The app already **writes** .cbz files, so it knows the format | `utils.py`: `save_folder_as_cbz` |
| Natural page order (page_2 before page_10) | `utils.py`: `natural_sort_key` |
| macOS ships `bsdtar` 3.5.3 with libarchive 3.7.4 (checked on this Mac), which can extract RAR | `/usr/bin/bsdtar` |
| No PDF or RAR Python packages are installed now | `requirements.txt` |

So the "Local files" source mostly exists already. What's missing is opening comic **archives**.

## 4. Recommended approach and alternatives
| Approach | Verdict | Why |
|---|---|---|
| **A "Pick Comic File(s)" button that extracts the files into a temporary folder (one subfolder per file), then runs exactly like a picked folder** | ✅ **Recommended** | It reuses the existing temporary-folder path. It's legal for files the user owns, needs no new package for .cbz/.zip/.epub, and touches about 3 files. |
| Scraper for comix.to or other aggregators | ❌ Rejected | Piracy, legal risk to the repo, breaks often, Cloudflare, malware and ads (see §2) |
| Wrap **gallery-dl** (supports MangaDex, Comick, MangaFire, MangaPark, Weeb Central, WEBTOON, Tapas…) | ❌ Rejected | It's a general tool, but most of its manga sources are piracy aggregators. Bundling it still ships a piracy downloader; it just moves the source choice to the user. It also adds a dependency that breaks whenever sites change. |
| Wrap **HakuNeko / HaruNeko**, **mangal** (Lua scrapers), **Kaizoku**, **Suwayomi** (Tachiyomi/Mihon extensions) | ❌ Rejected | Same problem, and heavier: these are whole apps or servers (Electron, Go, a Kotlin/JVM server). Suwayomi ships no sources: the user adds an extension repo, which is mostly aggregators. **The user can still run any of these on their own and point Panelyze at the output folder or .cbz.** Import already covers that, and the app takes no stance on where the files came from. |
| A general "downloader interface" (a base class with MangaDex and Local subclasses) | ❌ Rejected for now | Too much for two sources. MangaDex stays a Pipeline step, and local files stay the input picker, as they are today. |
| Comic Vine API | ❌ Not a source | Metadata only (titles, covers, issue info), no pages |
| Official apps: Viz, Shonen Jump, VIZ Manga, Manga Plus, Kindle, ComiXology | ❌ Can't import | DRM-protected. Removing DRM breaks their terms and, in the US, the DMCA anti-circumvention rule (§1201). |

**Legal ways to get good pages into Panelyze, which Import then handles:**
| Source | Notes |
|---|---|
| DRM-free bundles: Humble Bundle (Kodansha bundles have shipped CBZ, PDF and EPUB), Fanatical (e.g. Vinland Saga in 2026) | Bought, so the user can use them for personal use. Not every bundle is DRM-free: check each one. |
| DriveThruComics and other DRM-free comic stores | Mostly Western and indie comics; few big manga |
| The user's own scans of volumes they own | For personal use |
| Public-domain comics: Digital Comic Museum, Comic Book Plus | Free with an account. Golden Age (1938–1959) Western comics, not manga. Good for testing. |
| MangaDex (already in the app) | Fan scanlations uploaded by groups, not licensed by the publishers. MangaDex removes official releases when asked. This is a gray area too, so the app shouldn't present it as fully licensed. |
| WEBTOON / Tapas | Their terms only allow personal viewing and downloading in their own apps. Don't scrape them. |

**For Slam Dunk specifically:** no legal DRM-free English Viz copy is known. Viz sells it inside its DRM apps and stores. So Import solves "good pages from files I own", but not "Viz Slam Dunk for free". That's honest, and it's the user's call (see open questions).

## 5. Files to change and functions to reuse
| File | Change |
|---|---|
| `utils.py` | Add `COMIC_FILE_EXTENSIONS = (".cbz", ".zip", ".cbr", ".epub")` and `extract_comic_files_to_folder(comic_paths)`: it builds a temporary folder (same layout as `copy_picked_images_to_folder`) with one subfolder per comic file, named after the file, and writes only image entries (`is_image_file`), each by its **base name**, never the path stored in the archive (this blocks "zip slip"). .cbz/.zip/.epub use `zipfile`; .cbr runs `bsdtar -xf` into a scratch folder, and only images are kept. |
| `gui_classes/PipelineView.py` | Add a third button, "Pick Comic File(s)", to `input_directory_row` with a `FilePicker` limited to `COMIC_FILE_EXTENSIONS`. Add `handle_comic_files_picked` (copy of `handle_images_picked`, storing `self.input_comic_paths`). In `handle_run_pipeline`, the `copy_picked_images_to_folder` branch gets an `elif` that calls `extract_comic_files_to_folder`. |
| `gui_classes/PickInputAndOutputDirectories.py` | The same button and `elif` (around line 292), so the Panel-By-Panel, Upscale and Video tabs get it too. Optional, and can be left to a second pass. |
| `tests/test_utils.py` | Tests for `extract_comic_files_to_folder` (see §7) |

Reuse: `copy_picked_images_to_folder` (its layout and cleanup), `is_image_file`, `natural_sort_key`, `get_last_directory`, and the existing `shutil.rmtree(os.path.dirname(...))` cleanup in both `finally` blocks. The steps themselves (Panel-By-Panel, Upscale, Video) don't change.

Not changed: `download_from_mangadex.py`, `MangaDexDownloaderView.py`, `SettingsMangaDexDownloader.py`, and `PIPELINE_STEPS`.

## 6. Steps
Phase 1 (.cbz, .zip, .epub; no new packages)
- [ ] Add `COMIC_FILE_EXTENSIONS` and `extract_comic_files_to_folder` to `utils.py` (zip-based files only)
- [ ] Tests for it in `tests/test_utils.py`
- [ ] Add the "Pick Comic File(s)" button, picker and handler to `PipelineView.py`, and the `elif` in `handle_run_pipeline`
- [ ] Clear `input_comic_paths` when a folder or images are picked, and the other way round (same as `input_image_paths` today)
- [ ] Run the full test suite
- [ ] Stop for the user's review

Phase 2 (after review)
- [ ] .cbr through `bsdtar`, with a clear error if it's missing
- [ ] The same button in `PickInputAndOutputDirectories.py`
- [ ] .pdf through `pypdfium2`, if the user wants it (a new package, so the build needs a check: `./build_mac_app.sh`)
- [ ] Note in README.md: "Import comic files you own"

## 7. How to test it
| Test | How |
|---|---|
| A .cbz becomes one chapter folder in page order | Make a .cbz in `tmp_path` with `zipfile` (pages `2.png`, `10.png`, `1.png`), extract it, and check the folder name and the images in it |
| Two files make two chapter folders | Two .cbz files make two subfolders, so each gets its own output folder |
| Zip slip is blocked | An entry named `../../evil.png` ends up only as `evil.png` inside the temporary folder |
| Non-image entries are skipped | `ComicInfo.xml`, `__MACOSX/._1.png` and `.DS_Store` aren't copied (the existing `is_image_file` already skips `._` files) |
| .epub | A small zip with `OEBPS/images/p1.jpg` and the image is extracted |
| .cbr (phase 2) | Make a test RAR on the fly if possible. Otherwise, skip the test when `bsdtar` is missing. |
| Full Pipeline | With the existing fake steps in `tests/test_pipeline.py`, a picked .cbz flows into Panel-By-Panel |
| Real run | Run the app in browser mode (see DEVELOPING.md) with a **public-domain** comic from Digital Comic Museum, or a .cbz made from Dragon Ball ch. 93 pages already downloaded from MangaDex. Don't use any pirated files. |

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | **Small.** Phase 1 is about 40 lines in `utils.py`, about 25 in `PipelineView.py`, plus tests |
| Value | **Medium–High.** Any good-quality source the user legally has (bought bundles, their own scans, files from other tools) can go into the Pipeline |
| Risks | A large .cbz is extracted to the temporary folder first (a few hundred MB, deleted afterwards). EPUB page order may not match the file names in some books (proper order needs the EPUB's own page list; leave that out unless it's a real problem). Flet's file picker filter on Mac may still let other files through, so the code should check the extension again. |

**Open questions for the user**
1. Is Phase 1 (.cbz/.zip/.epub in the Pipeline only) the right first step, or should the other tabs get it at the same time?
2. Is .pdf needed? It adds one new package (`pypdfium2`).
3. Is .cbr needed on the Windows PC too? Windows' built-in `tar.exe` may or may not open RAR; this is unchecked.
4. Should a picked .cbz turn into **one** folder per file (recommended), or should several files be merged into one chapter?
5. For Slam Dunk: are you OK with the app only supporting files you own (e.g. a DRM-free purchase or your own scans), and not downloading from Comix?

## 9. Sources
- Comick shutdown, called a major piracy site: https://animecorner.me/comick-shut-down-manga-piracy-site/
- Fake Comick copy domains flagged: https://tools.malwaretips.com/url-scan/comick.art
- comix.to as an unofficial reader (keiyoushi extension request, Next.js): https://github.com/keiyoushi/extensions-source/issues/11479
- Sony's DMCA notice removes about 200 Aniyomi extensions; Tachiyomi's shutdown: https://torrentfreak.com/sony-dmca-notice-nukes-200-aniyomi-extensions-as-tachiyomi-fork-feels-heat-240617/
- gallery-dl supported sites: https://github.com/mikf/gallery-dl/blob/master/docs/supportedsites.md
- Suwayomi ships no extensions: https://github.com/Suwayomi/Suwayomi-Server
- HakuNeko / HaruNeko: https://github.com/manga-download
- Viz Manga and Shonen Jump apps: https://www.viz.com/company-faq, https://animecorner.me/viz-launches-new-official-digital-manga-service-includes-shogakukan-titles/
- Kodansha × Humble bundles (DRM-free, CBZ/PDF/EPUB): https://kodansha.us/?p=104702, https://cbldf.org/tag/kodansha/
- Digital Comic Museum (public domain, account needed): https://en.wikipedia.org/wiki/Digital_Comic_Museum
- WEBTOON terms (personal use in their apps only): https://www.webtoons.com/en/terms
- PyMuPDF is AGPL: https://pymupdf.readthedocs.io/en/latest/about.html · pypdfium2 is Apache/BSD: https://pypi.org/project/pypdfium2/
- libarchive RAR5 support (since 3.4.0): https://gitlab.gnome.org/GNOME/evince/issues/1190
- MangaDex background and takedowns: https://en.wikipedia.org/wiki/MangaDex
