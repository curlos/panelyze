# comix_downloader

The comix.to downloader that Panelyze uses (through `download_from_comix.py`), copied from [comix-downloader](https://github.com/Yui007/comix-downloader) by Yui007 (MIT license, see `LICENSE`).

Copied from commit `b7096c1bb28009edb39c62da6580d62d13e384c4` (2026-11-09, "solved both issues close #33 and #34").

It's copied rather than installed because it isn't a pip package, and the packaged Mac app can't run its command-line tool. Its package is still named `src`, as in the original: its code checks that name, and renaming it would make it open a new browser for every chapter.

## What was copied
Everything in `src/` except `cli/` (the menus and command-line tool) and `utils/hash.py` (not used). Not copied: the PyQt6 window (`gui/`), `main.py`, `config.json`, `cf_cookies.dat`, the tests.

## Panelyze patches
Each one is marked with a `# Panelyze patch` comment.

1. `utils/nodriver_browser.py`: `BROWSER_EXECUTABLE_PATH`, set by Panelyze, so Microsoft Edge can be used too. nodriver only looks for Chrome and Chromium.
2. `api/comix.py`: the Cloudflare cookie file is saved in `~/Library/Application Support/Panelyze/cf_cookies.dat`, not next to this code (which is inside the app when it's packaged).
3. `formats/__init__.py`, `core/downloader.py`: `create_pdf` is only imported when a PDF is made. It needs reportlab, which Panelyze doesn't install (it only saves images).
4. `api/comix.py`, `core/models.py`: each chapter upload keeps its likes (`Chapter.votes`, from `.mchap-row__likes`) and whether it's official (`Chapter.official`, from `.mchap-row__group.is-official`, the checkmark next to e.g. VIZ Media). Panelyze uses them to pick the best upload of each chapter. The original always set the likes to 0.

5. `api/comix.py`: `_cookie_file_candidates` only returns Panelyze's own cookie file, not a "cf_cookies.dat" in the current folder. And `download_from_comix.py` deletes the saved file when a download starts: cookies from an earlier session go stale, and then pages never finish loading (seen on 2026-11-21).

6. `api/comix.py`: the chapter list is read page by page, and it used to stop silently at the first page that didn't load, leaving out every chapter after it. After a full page, an empty one is tried once more, and a warning is printed if the list still stops there (seen on 2026-11-21: Dragon Ball's list stopped after 200 uploads).

7. `api/comix.py`: `CHAPTER_LIST_PROGRESS_CALLBACK`, called after each page of the chapter list, so Panelyze can show how far it is.
8. `core/models.py`: `_safe_path_component` only removes the characters a folder name can't have (`\ / : * ? " < > |` and control characters) and keeps everything else as the site wrote it. It used to turn every character that wasn't a letter, digit, space, `-` or `_` into `_`, so "Absolute Batman #1" became "Absolute Batman _1".
9. `core/models.py`: `get_safe_folder_name` cleans the chapter number the same way. It comes from the chapter's link, and a number like "1/../.." could have named a folder outside the series' folder.
10. `core/downloader.py`: `download_chapters` no longer clears the cancel signal when it starts (`download_from_comix.py` clears it when its download starts). A Cancel clicked just before the chapters started downloading was forgotten.
11. `api/comix.py`: `parse_count` reads the likes, which can be shortened on the site ("1.2k" is 1,200, "1M" is 1,000,000). Reading only the digits made "1.2k" 12, so the wrong upload could be picked.

## Updating
Copy the same files from a newer commit over these ones, apply the patches again (search for `Panelyze patch` in the old copy), update the commit above, and run `python -m pytest tests/test_download_from_comix.py` and one real download.
