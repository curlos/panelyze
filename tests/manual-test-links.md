# Things to try by hand

Everything Panelyze can take as input, with what you should see. The automatic versions are `tests/test_every_input.py` (no internet) and `tests/test_e2e_links.py` (`pytest -m e2e tests/test_e2e_links.py`, real links).

## Links (paste in the Download tab)

| Kind | Link | What you should see |
|---|---|---|
| comix.to chapter | `https://comix.to/title/w25zn-slam-dunk/9071380-chapter-1` | Slam Dunk ch. 1 (the VIZ Media upload). "35 of 35 pages", then "Downloaded Slam Dunk chapter 1 · 35 pages". About a minute |
| comix.to series + range | `https://comix.to/title/w25zn-slam-dunk`, "Only some chapters" 1 to 3 | "Chapter 2 of 3 · … pages downloaded", then "Downloaded Slam Dunk: 3 chapters · 77 pages" |
| comix.to webtoon | `https://comix.to/title/emqg8-solo-leveling/6839172-chapter-5` | 169 pages, and the reading direction saved as `webtoon` |
| MangaDex chapter | `https://mangadex.org/chapter/ac33cc50-a1b2-49b0-a388-0d0ee4ebce18` | Dragon Ball ch. 93: "Downloaded Dragon Ball (Official Colored) Vol. 8 Ch. 93 - Goku's Charge · 16 pages" |
| MangaDex webtoon | `https://mangadex.org/chapter/87c3b804-a119-4285-b2f7-74d9d807ac93` | Eleceed ch. 2: 5 pages |
| MangaDex series + range | `https://mangadex.org/title/7991e715-40ae-4c3e-b0e0-aa8bee90ece7` (Shachou), "Only some chapters" 3 to 4 | 2 chapters. Try "Which upload" too (the series has several groups per chapter) |
| Internet Archive | `https://archive.org/details/hillman-pirates-comics-001` | "Downloaded Hillman Pirates Comics 001: 52 pages", with the size shown while it downloads |
| Internet Archive, big `.cbr` | `https://archive.org/details/hollywood-detective-april-1944` | 131 MB: good for watching the progress and trying Cancel. 116 pages |
| Internet Archive, refused | `https://archive.org/details/invincible-compendiums` | Red "Something went wrong": not marked as public domain. Nothing downloaded |
| Web page | `https://comicbookclublive.com/2024/10/04/dc-comics-preview-absolute-batman-1` | By default only the bigger images (600 px): just the 6 comic pages, "12 of 20 images checked · 1 kept so far". Untick "Only keep bigger images" for every image on the page: "12 of 20 images", then "Downloaded 19 images from comicbookclublive.com" (one can't be read) |
| Random web page | `https://example.com` | Red "Download from the web page failed. No images found on this page…" |
| Web page that blocks us | `https://aiptcomics.com/2024/10/03/dc-preview-absolute-batman-1/` | Red: "403 Client Error: Forbidden" (it blocks us only some of the time: if it doesn't, you get its images) |
| Not a link | `slam dunk` | Red "Something went wrong: Not a web link (it should start with https://)". Nothing starts |

When a download finishes, Finder opens the folder that was downloaded (the chapter, or the series for several chapters), for every kind of link. It doesn't open after a failure or a cancel. "Nothing new to download" opens the folder it's already in.

While any job runs (a download, Panel-By-Panel, Upscale, Create Video or a Pipeline), the input, output folder, settings and buttons of that tab are greyed out, the other tabs are faded and can't be opened, and they come back when it's done or fails.

Download any of these twice: the second time says "Already downloaded: …" within a few seconds and opens the same folder, without a "(2)" copy (MangaDex says "Nothing new to download"). Delete the folder, or some of its pages, and it downloads again. "Download again even if already downloaded" forces a new download.

MangaDex pages keep the downloader's names, from `00.jpg`. Downloading the same chapter twice should say "Nothing new to download", also for a chapter without a title (Eleceed ch. 2: its folder keeps the name "Ch. 2 - ", and the result line says "Ch. 2").

While a download runs, check that the link box is greyed out, the Download button is gone and Cancel is there. Cancel on the web page, Internet Archive and MangaDex stops straight away. On comix.to it stops once the chapter being loaded in the browser is done, and keeps the chapters that were finished.

## While a job runs (every tab)

- **Cancel:** in Panel-By-Panel, Upscale and Images To Video, Cancel takes Clear's place. Click it: it turns into a greyed "Cancelling..." at once, and the Status view says when it will stop ("Stopping waifu2x, then resizing the images that finished...", "Cancelling after the image being upscaled (MangaJaNai ...)", "Cancelling after the chapter being split into panels...", "Cancelling after the video being made..."). Then a grey "Cancelled", and the button is "Cancel" again for the next job.
- **Already split:** Split Into Panels twice on the same chapter: the second run is instant and its result line says "Already split into panels (kept): <chapter>" (like the Download tab's "Already downloaded"); for a series with some new chapters, "Panel-By-Panel conversion finished! 1 of 2 chapters was already split (kept)." Changing "Show full characters" (or a page), or ticking "Split into panels again even if already split", splits it again.
- **What will be split:** download one more chapter of a series that's already split: Panel-By-Panel's input (the series) says e.g. "3 chapters · 74 pages · only 1 new chapter to split", or "already split, nothing new to split". Ticking a setting that changes the panels (e.g. "Show full characters") updates it right away.
- **Finder opens the right folder:** after Split Into Panels, Upscale or Images To Video, Finder opens the series' (or chapter's) folder inside the tab's folder, e.g. `Panel-By-Panel/One Piece`, not `Panel-By-Panel` itself (`One Piece (grouped by page)` when grouped). A MangaDex link that's already downloaded ("Nothing new") opens its chapter's folder. The Pipeline still opens two: its own folder and the last step's.
- **Pipeline status:** while it runs, the list under Run Pipeline shows each step (○ waiting, ⏳ running, ✓ done with its time, ✗ failed); the small spinner next to "Activity" shows while it runs. Images To Video shows "12 of 40 images · Making the voice-over" ("text boxes" with highlighted text) and then "120 of 600 frames · Writing the video file". When it ends, Finder opens the Pipeline folder and the video's folder (also when started with `flet run -r`). Folders are named after the series, e.g. `4-images-to-video/Shachou to Sake to Hoshi`, not `…/1-download/…`.
- **Pipeline Cancel:** while it runs, a red Cancel is next to the greyed-out Run Pipeline. Clicking it says "Cancelling..." and stops the current step like that step's own Cancel would (a download or waifu2x right away, Panel-By-Panel after the current chapter); the steps after it don't start, the list shows the step as cancelled (yellow) and the rest as waiting, and the finished steps' folders are kept.
- **Split words:** a bubble with a word split over two lines is read as one word in the video when that makes a real word ("Presi- dential", "Presi- Dent" → "President"), but someone cut off stays apart ("Wait- Stop!", "Wait- what?!").
- **Video stages:** Images To Video shows a line like "✓ Reading the text   ● Making the voice-over   ○ Writing the video" (only the stages it needs), and Panel-By-Panel's text reading counts "text boxes" (one per bubble or caption). The size splits into kinds when there's more than one, e.g. "85 MB (40 MB video + 38 MB audio + 7 MB other)".
- **Cut-off bubbles:** a bubble cut off at a panel's edge and whole in the next panel (Shachou ch. 8, panels 17–18: "Come to think of it...") is only read and highlighted in the panel where it's whole.
- **Said once:** a bubble kept whole in two overlapping panels is only said once by the voice (Images To Video on its own; with highlighting it's also only highlighted once; only lines of 3+ words, since short ones like "No!" are often really said again); and it's in the transcript once too.
- **One job at a time:** while one runs, every other tab (Settings too) is faded and can't be opened, by clicking, ⌘1–5 / ⌘, or the arrow keys; hovering one says "Wait for "Upscale" to finish (only one job runs at a time)". When the job ends, they all open again.
- **Timer and size:** at the top right of the Status view, e.g. "1m5s · 23.4 MB" counting up, then "Took 1m5s · 23.4 MB". With comic files on: "237 MB (80 MB images + 157 MB .cbz files)". A web page or Internet Archive download shows its size only at the end. A Pipeline also shows "· total 3m40s", and ends with a "Time: Download 42s · ... · total" line.
- **One spinner:** the terminal's title bar spins, the Status view shows a still hourglass.
- **A failed job** keeps its error message under "... failed." in the Status view.

## Comic files and Pipeline copies

- Settings → .cbz files → "Small" or "Full quality", then download two chapters of a series: each chapter gets "<chapter>.cbz" next to its folder, not one for the whole series. Download the same link again: no new comic files. Turn it back to "No" afterwards.
- Download a web page or a comix.to chapter in the Download tab, then run a Pipeline with the same link: its Download step says "Already downloaded (copied)" (web page) or "Already downloaded" (comix.to) and doesn't download it again.

## Settings and dropdowns

- Settings is split into boxes (Starting up, Where everything is saved, .cbz files, Log file, Reset). Paths are teal there and in every "Save to:" line.
- Upscale Model shows "Fast / Better / Best", with a grey line under it explaining the picked one (it wraps for "Best"). Hovering a dropdown or picking a choice doesn't change its color.

## Files (Pick Input Image(s) / Pick Input Folder / Pick Comic File(s))

Made by `./venv/bin/python tests/make_test_inputs.py "<folder of real pages>"`, in `~/Documents/Panelyze/<this repo's folder>/test-inputs/`.

| Folder | Pick with | What you should see |
|---|---|---|
| `1 comic files/sample.cbz`, `.zip`, `.epub`, `.pdf` | Pick Comic File(s) | "1 chapter · 5 pages" |
| `1 comic files/sample.cbr` | Pick Comic File(s) | "1 chapter" (a `.cbr`'s pages aren't counted until it's opened). It's a zip file named `.cbr` |
| `1 comic files/real-rar-hollywood-detective-116-pages.cbr` | Pick Comic File(s) | A real RAR file: 116 pages |
| `1 comic files/pepper-carrot-82-pages.pdf` | Pick Comic File(s) | "1 chapter · 82 pages" |
| All of `1 comic files` at once | Pick Comic File(s) | One chapter folder for each file |
| `2 loose images/` (png, jpg, jpeg, webp) | Pick Input Image(s) | "4 images" |
| `3 folders/one chapter` | Pick Input Folder | "4 pages" |
| `3 folders/series with 2 chapters` | Pick Input Folder | "2 chapters · 5 pages" |
| `3 folders/natural order` | Pick Input Folder | "3 pages"; page_10 comes after page_2 in the results |
| `3 folders/no images` | Pick Input Folder | Yellow-ish "No images found in this folder" |
| `4 broken files/broken.cbz` | Pick Comic File(s), then the tab's button | Red "File is not a zip file". The app is usable again |
| `4 broken files/notes.txt` | Pick Comic File(s) | Red "Please pick comic files (.cbz, .zip, .epub, .cbr, .pdf)." Nothing is picked |
