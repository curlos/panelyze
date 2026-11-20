# 17. More sources for pages: comic files, page URLs, the Internet Archive

Written 2026-11-19, updated 2026-11-20 (American, Western and French comics; PDF; page URLs; the Internet Archive). Planning only: no code has changed.

Related: [#31 untested formats](31-format-testing-followups.md) (B: Western comics) · [#27 reading direction](27-reading-direction-from-mangadex.md)

## 1. Summary
MangaDex is the only source today. It doesn't have every series in good quality (Slam Dunk is only old fan scans), and it has almost no **American, Western or French comics**, which the app has never been tested on. The user wants to read those panel by panel too (e.g. Absolute Batman, Invincible), the way Webtoon mode was added for webtoons.

**Recommendation:** three new ways to get pages in, and still **no scraper for piracy sites** (comix.to and the like):
1. **Import comic files** (`.cbz`, `.zip`, `.epub`, **`.pdf`**, later `.cbr`) the user has. Most legal Western comics are sold as DRM-free PDFs.
2. **Download pages from a URL:** paste a web page, and the app saves its big images in order. Generic, with no site-specific code. Good for official preview pages (e.g. DC's previews of Absolute Batman #1).
3. **Internet Archive downloader:** the only other free official API with comic pages. It keeps **public-domain items only**.

All three end up as a normal folder of pages, so Panel-By-Panel, Upscale and Video don't change.

## 2. Is it doable?
| Option | Doable? | Should the app ship it? |
|---|---|---|
| Import local comic files (.cbz/.zip/.epub) | Yes, with Python's built-in `zipfile`, no new packages | **Yes** (phase 1) |
| Import .pdf | Yes, with `pypdfium2` (Apache/BSD). Avoid PyMuPDF, which is AGPL. | **Yes** (phase 1) |
| Download pages from a URL | Yes, with `requests` (installed) + the built-in `html.parser` + Pillow (installed) | **Yes** (phase 1) |
| Internet Archive, public domain only | Yes: official `advancedsearch` + `metadata` endpoints, no key | **Yes** (phase 2) |
| Import .cbr (RAR) | Yes on Mac: the built-in `bsdtar` (libarchive 3.7.4) reads RAR4 and RAR5 | Yes (phase 3). Windows needs a check. |
| Scraper for comix.to (or ReadComicOnline, GetComics, Comick, MangaFire, MangaPark, Weeb Central…) | Technically yes | **No.** See below. |
| DC Universe Infinite / Hoopla / Libby / Kindle / ComiXology / Viz / Shonen Jump / Manga Plus | No: DRM, and no public API | No. The app must not strip DRM. |

**Why not a piracy-site scraper, said plainly:**
- **It's piracy of comics on sale now.** Viz's Slam Dunk or DC's Absolute Batman rehosted on an aggregator are pirated copies. A downloader made for those sites would be a piracy tool built into Panelyze.
- **Legal risk for the repo.** Tools built around piracy sources get DMCA takedowns: Tachiyomi shut down after legal threats from Kakao, and Sony's DMCA notice removed about 200 Aniyomi extensions.
- **It breaks often.** These sites change domains, layouts and APIs all the time, use JavaScript readers (comix.to is Next.js) and Cloudflare bot checks. Several big ones (Comick, Bato, TuMangaOnline) have shut down.
- **Malware and ads.** Fake copies of these sites spread after shutdowns (e.g. fake Comick ".art" domains flagged as possibly malicious).

MangaDex is a gray area too (fan scanlations, not licensed), but it's a general platform with an official API that removes official releases when asked. The app keeps using it as it does today.

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

## 4. Recommended approach and alternatives
| Approach | Verdict | Why |
|---|---|---|
| **"Pick Comic File(s)"**: extract .cbz/.zip/.epub/.pdf into a temporary folder (one subfolder per file), then run like a picked folder | ✅ **Phase 1** | Reuses the temporary-folder path; legal for files the user has; ~3 files touched |
| **"Download pages from a URL"**: fetch the page, find its big images, save them in order, run like a picked folder | ✅ **Phase 1** | Generic (like a browser's "save all images"), no site-specific code. Works for official previews and any page that shows comic pages openly. Pages that need JavaScript or a login are out of scope. |
| **Internet Archive downloader**, public domain only | ✅ **Phase 2** | The only other official free API with pages. A second real downloader next to MangaDex. |
| Scraper for comix.to or other aggregators | ❌ Rejected | Piracy, legal risk, breaks often, Cloudflare, malware (§2) |
| Wrap **gallery-dl**, HakuNeko / HaruNeko, mangal, Kaizoku, Suwayomi | ❌ Rejected | Most of their manga/comic sources are piracy aggregators; bundling them ships a piracy downloader. Heavy and breaks when sites change. |
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
| MangaLib, GitHub "manga API" projects | No (wrappers that scrape) | Yes, from piracy sites |

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
| `utils.py` | Add `COMIC_FILE_EXTENSIONS = (".cbz", ".zip", ".epub", ".pdf")` and `extract_comic_files_to_folder(comic_paths)`: builds a temporary folder (same layout as `copy_picked_images_to_folder`) with one subfolder per file, named after it. Zip-based files: write only image entries (`is_image_file`), each by its **base name**, never the archive path (blocks "zip slip"). PDF: render each page with `pypdfium2` to `001.png`, `002.png`… |
| `download_pages_from_url.py` (new) | `download_pages_from_url(url)`: `requests.get` the page (with a normal browser User-Agent and a timeout) → collect image URLs in page order from `<img src>`, `data-src` and the largest `srcset` entry with `html.parser` → make them absolute (`urljoin`) and drop duplicates → download each, open with Pillow, keep only images at least 600 px on the short side (drops ads, icons, avatars) → save as `001.jpg`, `002.jpg`… in a temporary folder named after the page title. Raises a clear "No comic pages found on this page" error when nothing is kept. |
| `download_from_internet_archive.py` (phase 2) | `search_internet_archive(title)`: `advancedsearch.php` with `mediatype:texts` and the title, fields `identifier, title, licenseurl, rights`. Keep **only** items whose `licenseurl` is a public-domain mark / CC0 (`publicdomain`), skip everything else. `download_internet_archive_item(identifier, folder)`: `GET /metadata/{identifier}`, pick the "Comic Book ZIP" (.cbz) file, else the PDF, download from `/download/{identifier}/{file}` with `requests`, then `extract_comic_files_to_folder`. |
| `gui_classes/PipelineView.py` | In `input_directory_row`: a "Pick Comic File(s)" button (`FilePicker` limited to `COMIC_FILE_EXTENSIONS`, extension checked again in code) and a "Page URL" text field. `handle_comic_files_picked` (copy of `handle_images_picked`, stores `self.input_comic_paths`). In `handle_run_pipeline`, the `copy_picked_images_to_folder` branch gets two `elif`s: comic files and page URL. Picking one input clears the others (as `input_image_paths` does today). Phase 2: an "Internet Archive" source next to MangaDex, with a title box and a list of public-domain results. |
| `gui_classes/PickInputAndOutputDirectories.py` | Phase 3: the same inputs, so the Panel-By-Panel, Upscale and Video tabs get them too |
| `requirements.txt`, `requirements-lock.txt` | Add `pypdfium2` |
| `build_mac_app.sh` | Check `pypdfium2`'s native library is bundled (rebuild + self-test) |
| `tests/test_utils.py`, `tests/test_download_pages_from_url.py`, `tests/test_internet_archive.py` | See §7 |

Reuse: `copy_picked_images_to_folder` (layout and cleanup), `is_image_file`, `natural_sort_key`, `get_last_directory`, the existing `shutil.rmtree(os.path.dirname(...))` cleanup in both `finally` blocks, and `default_settings.get_output_directory` for where downloads go. The steps themselves (Panel-By-Panel, Upscale, Video) don't change.

Not changed: `download_from_mangadex.py`, `MangaDexDownloaderView.py`, `SettingsMangaDexDownloader.py`.

## 6. Steps
Phase 1 (Import incl. PDF + page URLs)
- [ ] Add `pypdfium2` to `requirements.txt` / `requirements-lock.txt` and install it into the shared venv on purpose (CLAUDE.md: the venv is shared)
- [ ] Add `COMIC_FILE_EXTENSIONS` and `extract_comic_files_to_folder` to `utils.py` (.cbz/.zip/.epub/.pdf) + tests
- [ ] Add `download_pages_from_url.py` + tests (fake HTML, no network)
- [ ] Add the "Pick Comic File(s)" button and the "Page URL" field to `PipelineView.py`, and the two `elif`s in `handle_run_pipeline`; each input clears the others
- [ ] Run the full test suite
- [ ] Real runs (§7): Absolute Batman #1 preview article, one Golden Age comic, Pepper&Carrot PDF
- [ ] Stop for the user's review

Phase 2 (Internet Archive)
- [ ] Check which test comics (§7) the Internet Archive has with a public-domain license
- [ ] Add `download_from_internet_archive.py` + tests (fake JSON, no network)
- [ ] Add the Internet Archive source to the Pipeline
- [ ] Real run on one public-domain comic

Phase 3
- [ ] .cbr through `bsdtar`, with a clear error if it's missing
- [ ] The same inputs in `PickInputAndOutputDirectories.py`
- [ ] Update `README.md` ("Import comic files", "Download pages from a URL") and run `./build_mac_app.sh` (pypdfium2 in the bundle)
- [ ] Write the Western / American / French results into `benchmarks/panel-cropping.md` (closes #31 B)

## 7. How to test it
| Test | How |
|---|---|
| A .cbz becomes one chapter folder in page order | Make a .cbz in `tmp_path` with `zipfile` (`2.png`, `10.png`, `1.png`), extract, check the folder name and images |
| Two files make two chapter folders | Two .cbz files → two subfolders |
| Zip slip is blocked | An entry named `../../evil.png` ends up only as `evil.png` inside the temporary folder |
| Non-image entries are skipped | `ComicInfo.xml`, `__MACOSX/._1.png`, `.DS_Store` aren't copied |
| .epub | A small zip with `OEBPS/images/p1.jpg` → the image is extracted |
| .pdf | A 3-page PDF made in the test (Pillow can save one) → `001.png`–`003.png` |
| Page URL: big images in order, ads dropped | A fake HTML page (no network, `requests` patched) with 3 big images (`src`, `data-src`, `srcset`) and 1 small ad image → 3 pages, in page order |
| Page URL: nothing found | A page with only small images → the clear "No comic pages found" error |
| Internet Archive (phase 2) | Fake search JSON with one public-domain item and one item without a public-domain license → only the first is offered; fake metadata JSON → the .cbz is picked over the PDF |
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

Notes: the first Superman (Action Comics #1, 1938) and Batman (Detective Comics #27, 1939) are **not** public domain in the US until Jan 1, 2034 and Jan 1, 2035. The Internet Archive's Invincible uploads aren't public domain either, so the downloader skips them on purpose.

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | **Small–Medium.** Phase 1: ~50 lines in `utils.py`, ~60 in `download_pages_from_url.py`, ~40 in `PipelineView.py`, plus tests. Phase 2: ~70 lines + tests. |
| Value | **High.** First real test of American, Western and French comics, and any legal file or page can go into the Pipeline |
| Risk: big files | A large .cbz or PDF is extracted to the temporary folder first (a few hundred MB, deleted afterwards). PDF pages are rendered at a fixed DPI (start at 200; check against the original image size) |
| Risk: page URLs | Lazy-loaded or JavaScript pages give nothing (clear error, by design). Some sites block plain requests. The 600 px filter may keep a big banner image: the user can delete it, and the panel step skips pages with no panels. |
| Risk: Internet Archive licenses | Uploads mix public domain and unauthorized copies. Only trust the `licenseurl` field; skip anything unclear or missing. |
| Risk: EPUB order | Page order may not match file names in some books; leave the EPUB page list out unless it's a real problem |
| Risk: Flet file picker | The Mac filter may let other files through, so the code checks the extension again |

**Decisions (user, 2026-11-20)**
1. **.cbr on Windows:** not now (no Windows testing yet). Later, if needed.
2. **One folder per picked file:** yes. Two .cbz files become two chapter folders.
3. **Page URL:** one page only for now. Following "next page" links can come later.

**Open question for the user**
1. The new inputs go into the **Pipeline** tab first (one place, where MangaDex already is). Should the Panel-By-Panel, Upscale and Video tabs, which each have their own "pick a folder" input, get them in phase 1 too, or in phase 3 as planned (recommended)?

## 9. Sources
- Comick shutdown, called a major piracy site: https://animecorner.me/comick-shut-down-manga-piracy-site/
- Fake Comick copy domains flagged: https://tools.malwaretips.com/url-scan/comick.art
- comix.to as an unofficial reader (keiyoushi extension request, Next.js): https://github.com/keiyoushi/extensions-source/issues/11479
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
