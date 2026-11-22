<p align="center">
  <img src="/assets/no-face.png" alt="Panelyze logo" width="96" height="96">

  <h1 align="center">Panelyze</h1>
  <p align="center">Turn manga pages into easy-to-read panels, upscale them, and make videos from them. All on your Mac, no terminal needed.</p>

  <p align="center">
    <a href="https://github.com/curlos/panelyze/releases/latest"><b>⬇ Download for Mac (Apple Silicon)</b></a>
  </p>
</p>

Manga is made for bigger formats, so reading a full page on a phone means a lot of zooming. Panelyze splits each page into one image per panel, in reading order, so you can read panel by panel instead.

<div>
  <img src="https://github.com/user-attachments/assets/03c2f979-4305-4050-8739-c6e14ab0f9c4" height="400" />
</div>

<div>
  <img src="https://github.com/user-attachments/assets/02b85b61-b373-4b4a-890f-e56d68ccca8e" height="300" />
  <img src="https://github.com/user-attachments/assets/72885e7d-bffe-496e-96eb-d3ed7fe0607c" height="300" />
  <img src="https://github.com/user-attachments/assets/76c9cda4-7c86-47b9-b617-84714c562526" height="300" />
  <img src="https://github.com/user-attachments/assets/e0bb6609-3353-4754-b93d-34741bd3717d" height="300" />
  <img src="https://github.com/user-attachments/assets/dc3a868c-1134-4e02-9c41-1f44e8fc0dd6" height="300" />
  <img src="https://github.com/user-attachments/assets/dd88d0b1-151c-44a3-9a8e-21fc25635081" height="300" />
</div>

## What it does

- **Split pages into panels:** an AI model finds every panel and saves each as its own image, in reading order (right to left for manga, left to right for comics, or strip by strip for 4-koma). With the Reading Direction on **Automatic**, chapters downloaded from MangaDex get the right order from the series' original language and format tags, and other chapters are checked for 4-koma and webtoon pages. Speech bubbles and characters drawn over a panel's border are kept whole. About 1–2 seconds per page. Webtoons (vertical scroll) work too: the chapter is joined into one strip and Magi looks at it one screen at a time.
  - <img src="https://github.com/user-attachments/assets/d0eb6fbd-c1d6-435a-b775-4bd488512d70" height="400" />
- **Download** (one box for any link): MangaDex or comix.to chapters (pick the chapters; MangaDex also lets you pick a language and pages; no account needed), a public-domain comic from the Internet Archive, or the images on any web page (e.g. an official preview of a new comic), all of them or only the bigger ones. comix.to needs Google Chrome or Microsoft Edge installed, and picks the official upload of each chapter when there is one. The reading direction is saved with each manga or webtoon chapter.
  - <img src="https://github.com/user-attachments/assets/9b5ab7fd-666e-4ad0-882c-e2fdf13cce81" height="400" />
- **Import comic files:** `.cbz`, `.zip`, `.epub`, `.cbr` and `.pdf` (e.g. the DRM-free PDFs Image Comics sells). Each file becomes a chapter.
- **Upscale images** (2x, 4x, ...) with waifu2x (fast), or with MangaJaNai for the best-looking manga (clean halftone dots), which uses IllustrationJaNai for color pages. There's a limit so a huge image doesn't take forever.
- **Make videos** from your panels, timed by reading speed or read aloud with text-to-speech (free voices, or Azure with your own key). Choose YouTube (16:9), TikTok / Shorts / Reels (9:16) or square (1:1).
- **Run it all at once:** tick the steps you want (download → split → upscale → video) and run them in a row.
- **.cbz files for reader apps:** turn it on in Settings to also save each downloaded chapter, its panels or its upscaled images as a `.cbz` (Panels on iPhone and iPad, Mihon on Android, ...). Off by default, since it about doubles the space used.

Works on a whole folder, a few images, or comic files (anything from the Download tab too). Nothing to set up: results are saved in **Documents → Panelyze** (a folder for each tool), and each step starts from the result of the one before it. You can change that folder in the Settings (gear icon), or pick a different output folder in any tab.

While a job runs, the bottom of the window shows how far it is, how long it has taken and how much it has saved, and **Cancel** stops it (right away for downloads and waifu2x, after the current image or chapter otherwise; what's finished is kept). One job runs at a time, so the other tabs wait until it's done. A link that's already downloaded isn't downloaded again, and a chapter that's already split into panels isn't split again, unless you ask for it.

## Install

1. Download `Panelyze-macOS-AppleSilicon.zip` from the [latest release](https://github.com/curlos/panelyze/releases/latest).
2. Double-click the zip to unzip it, then drag **Panelyze** into your **Applications** folder.
3. Double-click Panelyze. The first time, macOS says it can't check the app for malicious software (it isn't signed with a paid Apple Developer account). Click **Done**, then open **System Settings → Privacy & Security**, scroll down and click **Open Anyway** next to "Panelyze was blocked". You only do this once.

Everything is built in, including the panel-finding AI model and the upscaler. The only download: the first time a video reads the text of your pages, an AI model (about 2 GB) is downloaded automatically.

## Good to know

- **Mac with Apple Silicon only** (M1 or newer) for now. Windows is planned.
- **For personal, non-commercial use.** The Magi AI model that finds the panels is free only for personal, research and non-commercial use (see its [model page](https://huggingface.co/ragavsachdeva/magiv2)). The MangaJaNai and IllustrationJaNai upscale models are licensed [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) (non-commercial).
- Everything the app does is saved to `~/Library/Logs/Panelyze/panelyze.log` (Settings → Open Log File). Send it along if something goes wrong.

## License

Distributed under the MIT License.

## Acknowledgements

- [Magi](https://github.com/ragavsachdeva/magi) by Ragav Sachdeva (panel and text detection)
- [MangaJaNai and IllustrationJaNai](https://github.com/the-database/MangaJaNai) by the-database (the "Best" upscale model), run with [spandrel](https://github.com/chaiNNer-org/spandrel) and [Core ML Tools](https://github.com/apple/coremltools)
- [comix-downloader](https://github.com/Yui007/comix-downloader) by Yui007 (the comix.to downloader, copied into `comix_downloader/`) and [pypdfium2](https://github.com/pypdfium2-team/pypdfium2) (PDF pages)
- [MangaDex Downloader](https://github.com/mansuf/mangadex-downloader), [waifu2x-ncnn-vulkan](https://github.com/nihui/waifu2x-ncnn-vulkan), [Flet](https://flet.dev/), [MoviePy](https://github.com/Zulko/moviepy) and [edge-tts](https://github.com/rany2/edge-tts)
- Icons made by <a href="https://www.freepik.com" title="Freepik">Freepik</a> from <a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a>
