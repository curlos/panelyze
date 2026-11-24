# Spec 10: Run Panelyze on the AMD gaming PC (Radeon RX 6700 XT)

Researched 2026-11-19 on the Mac; built and tested on the PC 2026-11-22.

## 1. Summary
Run Panelyze **from source** on the user's PC (Radeon RX 6700 XT, 12 GB, chip "gfx1031") so Magi and the "Best" upscaler use the AMD card. The good news since the roadmap note was written: AMD's **TheRock** PyTorch builds now build *and sanity-test* gfx1031 on **both Windows and Linux**, so no dual boot and no `HSA_OVERRIDE_GFX_VERSION` trick should be needed. AMD shows up in PyTorch as `"cuda"`, but this PC also has built-in graphics PyTorch can't run on, so `get_device()` needed a small change. This is mostly a **setup guide**, with a few small code fixes.

## 2. Is it doable?
**Yes: done** (2026-11-22). Every tab works on the card from source; times are in `benchmarks/README.md`.

| Part | Works on the 6700 XT? |
|---|---|
| Magi (panels + text reading) | Yes: done, via TheRock PyTorch on Windows (official PyTorch 2.5.1 + ROCm 6.2 on Linux, with the override, is the backup) |
| "Best" upscaler (MangaJaNai via spandrel) | Yes: done, same PyTorch. Core ML is Mac-only, so it uses PyTorch on the card |
| waifu2x ("Fast"/"Better") | Yes. waifu2x-ncnn-vulkan uses **Vulkan**, which every AMD driver supports. The app now downloads the Windows/Linux build itself the first time |
| MangaDex download, video, TTS | Yes. Plain Python; `open_directory` already handles Windows/Linux |
| Ollama, for Translate ([spec 01](01-translate-japanese-pages.md)) | Probably. To check: does Ollama use the 6700 XT (gfx1031) on Windows directly, or only through its Vulkan backend? |

**The PC can run bigger translation models than the Mac** (added 2026-11-22). The PC has **32 GB of RAM**, **12 GB of video memory** on the card and **2 TB of storage**; the Mac has 16 GB shared, about 10.7 GB usable by the GPU, and little free disk.

| Size | What runs | Example models (Ollama) |
|---|---|---|
| Up to about 11 GB | Fully on the card, fast | `ministral-3:14b` (9.1 GB, 90.7% on JP-TL-Bench, the Mac's tight limit), `gemma4:12b` (7.7 GB) |
| About 12–28 GB | Split between the card and system RAM: slower, but works. Mixture-of-experts models use only part of the model per word, so they stay fairly fast | **`qwen3-vl:30b-a3b-instruct`** (20 GB, sees the page; the text-only Qwen3-30B-A3B scores 9.77/10 on JP-TL-Bench, close to Gemini 3 Flash's 9.98), `gemma4:26b` (16–19 GB) |
| Storage | All candidates can stay downloaded at once (no download-test-delete as on the Mac) | — |

The model is a setting in spec 01's Translate tab, so nothing extra is needed in the app. Measure speed and quality on the same 5 test pages as spec 01's step 7.

## 3. What's already true (roadmap claims checked)

| Claim (ROADMAP #10 / benchmarks README) | Status | What's true now |
|---|---|---|
| "Linux with ROCm is the most proven route; needs `HSA_OVERRIDE_GFX_VERSION=10.3.0`" | ⚠️ partly out of date | Still true for **official** PyTorch wheels (AMD's official Linux list is RX 7000/9000 only, ROCm 7.2.1 + PyTorch 2.9.1). But TheRock now builds gfx1031 natively, marked Build ✅ / Sanity tested ✅ / Release ready ✅ on Linux. Override not needed there |
| "Windows TheRock builds list gfx1031 but are previews; nobody tested this card" | ⚠️ out of date | TheRock's SUPPORTED_GPUS table now marks **Windows gfx1031 sanity tested ✅**. Install is `pip install --index-url https://nightly.repo.amd.com/rocm/whl-next/ "torch[device-gfx1031]" "torchvision[device-gfx1031]"`. Still a nightly channel ("may be unstable"). AMD's *official* Windows PyTorch list (ROCm 7.2.1, PyTorch 2.9, Python 3.12) still has no RX 6000 cards |
| "VM or WSL2 can't use the card" | ✅ verified (WSL2) | AMD's WSL2 matrix (ROCm 7.2.1, librocdxg) lists only RX 7000/9000 + Pro cards. No RDNA2 |
| "DirectML is unmaintained, stuck on PyTorch 2.0" | ⚠️ number wrong, conclusion right | Latest `torch-directml` is 0.2.5.dev240914 (Sept 2024), needs **torch 2.4.1**. No release in over 2 years. Still not worth it |
| "AMD shows up as `cuda`, so the GPU picker needs no code change" | ⚠️ partly (found on the PC) | There's no GPU picker in Settings; `get_device()` in `magi.py` picks mps → cuda → cpu automatically, and ROCm PyTorch answers `torch.cuda.is_available() == True`. But the PC has two GPUs and the built-in one fails, so `get_device()` now tests each GPU and picks the most powerful that works. `DEVICE_NAMES["cuda"]` also said "the NVIDIA GPU" |
| "Runs from source there, not the Mac app; waifu2x needs its Windows/Linux download" | ✅ verified | `get_waifu2x_path()` (utils.py) uses `shutil.which("waifu2x-ncnn-vulkan")`, which finds `.exe` on Windows too. `coremltools` is already marked Mac-only in requirements.txt |
| "3–5× faster than the M1" | ✅ measured (2026-11-22) | 1.7× (Panel-By-Panel), 3× (Fast), 2.5–5× (Best), 5× (video), once a series' image sizes have been seen; the first run of a new size is 2–4× slower (`benchmarks/README.md`) |

**Pinned versions vs. the PyTorch builds (tested today on this Mac, CPU):**

| PyTorch | transformers 4.34.0 + Magi panels | Full Magi (text reading) | MangaJaNai via spandrel 0.4.2 |
|---|---|---|---|
| 2.5.1 (current pin) | ✅ 3 of 3 panels, 10.6 s | ✅ 12.0 s | ✅ (in use today) |
| 2.11.0 (oldest TheRock offers; it offers 2.11–2.14) | ✅ 3 of 3 panels, 7.2 s | ✅ 8.7 s | ✅ 0.72 s on a 64 px test tile |

So the pinned `transformers==4.34.0` works with the newer PyTorch TheRock needs. (Times include first-run loading; they show "it works", not speed.) Torch 2.12–2.14 were not tried.

Also: official `torch==2.5.1+rocm6.2` exists for Linux, Python 3.12 (checked on download.pytorch.org), so the Linux route can keep the exact pin.

**Checked on the PC itself (2026-11-22):** Windows 11 Pro, AMD Radeon RX 6700 XT (driver 32.0.21045), Python 3.10.11 only (3.11 was installed: TheRock's Windows builds start at 3.11, and tokenizers 0.14.1 has no Windows build for 3.12), git 2.44, no venv, no waifu2x. `magi_model/panels_fp16.safetensors` isn't there (not in git); `build_panels_model_file` in `magi.py` builds it from the full Magi download the first time.

**Missed in the first review:**
- `.cbr` import doesn't work on Windows: `save_rar_pages` (`utils.py`) looks only for `bsdtar` or `/usr/bin/bsdtar`. Windows 11's built-in `C:\Windows\System32\tar.exe` *is* bsdtar (3.8.9, opens RAR), so using that exact path on Windows fixes it (not `shutil.which("tar")`, which can find Git's GNU tar, which can't open RAR).
- Logs go to `~/Library/Logs/Panelyze` on a Mac and, since the user asked on 2026-11-24, to `%LOCALAPPDATA%\Panelyze\Logs` on Windows (`LOG_FOLDER` in `default_settings.py`, used by `gui_classes/AppOutput.py` and `self_test.py`). The "Best" models and the comix.to cookie file still use Mac-style folders (spec 32).
- The worktree setup in CLAUDE.md uses `ln -s`, which in Git Bash on Windows copies instead of linking (unless Developer Mode is on). On Windows, link the venv with a directory junction (`mklink /J`) instead.

## 4. Recommended approach + rejected alternatives

| Option | Verdict | Why |
|---|---|---|
| **Windows + TheRock nightly PyTorch (`torch[device-gfx1031]`)** | ✅ **Recommended** | No dual boot. gfx1031 is built and sanity-tested for Windows. Pinned transformers works with torch 2.11. Only the torch install line differs |
| Linux dual boot + `torch==2.5.1+rocm6.2` + `HSA_OVERRIDE_GFX_VERSION=10.3.0` | Backup | Keeps exact pins and is the long-proven community route, but needs a Linux install |
| Linux + TheRock | Backup | Same as Windows route, if the user ever has Linux |
| WSL2 | ❌ | RDNA2 not supported in AMD's WSL matrix |
| DirectML | ❌ | Dead since Sept 2024, torch 2.4.1 only |
| CPU only on the PC | Fallback | Always works; useful to separate "app works on Windows" from "GPU works" |

## 5. Files to change + existing functions to reuse

| File | Change | Size |
|---|---|---|
| `DEVELOPING.md` | New section "On a Windows PC with an AMD GPU": the install steps that worked | ~20 lines |
| `README.md` | "Tested on" table: tested, should work, won't work | ~8 lines |
| `magi.py` | `get_device()` + new `gpu_works()` pick the most powerful GPU that works, once per run (`get_device_choice`); `get_device_name()` names it for Settings and the Status view (replaces `DEVICE_NAMES`) | ~60 lines |
| `utils.py` | `save_rar_pages`: Windows' built-in `tar` (it's bsdtar), given a plain-named copy (it can't read Japanese letters in its arguments); folder names for picked images and comic files don't end in a space or dot; `PYTHONIOENCODING=utf-8` for the downloader's process | ~15 lines |
| `VideoCreatorFromImages.py` | Close the voice-over audio files after writing the video (Windows can't delete open files); `transcript.txt` in UTF-8 | ~15 lines |
| `waifu2x.py`, `utils.py`, `gui_classes/UpscaleImagesView.py`, `self_test.py` | waifu2x is downloaded the first time it's needed (`download_waifu2x`, into `~/Library/Application Support/Panelyze/waifu2x`, the right zip for Windows/Mac/Linux) instead of an error asking to install it; `get_waifu2x_path` also looks there (after the app's own copy and the PATH). A shared `download_file` uses certifi's certificates (one download on the PC failed with "CERTIFICATE_VERIFY_FAILED"); the "Best" models use it too | ~50 lines |
| `janai.py`, `utils.py`, `gui_classes/UpscaleImagesView.py` | "Best" with AMD's PyTorch: same-size tiles; "Best" to 4K: one pass less when it would go far past 4K, leaving the image a bit under 4K (`get_best_upscale_ratio`) | ~30 lines |
| `magi.py` | Panel-By-Panel's stages in the Status view | ~15 lines |
| `gui_classes/AppOutput.py`, `README.md`, `DEVELOPING.md` | Log rotation: each start moves `panelyze.log` to `panelyze.1.log` (up to `panelyze.9.log`), so the log is only this run; instead of deleting it all past 10 MB (the user's call, 2026-11-24) | ~20 lines |
| `download_pages_from_url.py` | A size cap for web page downloads: 10 MB for the page itself (its HTML), 50 MB for each image; bigger ones aren't read (`read_at_most`) | ~25 lines |
| `VideoCreatorFromImages.py`, `tests/test_images_to_video_settings.py`, `tests/test_video_durations.py` | A reading speed of 0 or less uses 150 and an image duration of 0 or less uses 3 s (both crashed the video); negative pauses and minimum time count as 0; tests for every Images To Video setting, making real small videos offline | ~5 lines + tests |
| `EmotionAnalyzer.py` | The emotion model (Azure "Auto" voice style) runs on the GPU Magi picked (`get_emotion_model_device`), not transformers' own pick, which was the built-in graphics | ~10 lines |
| `TextToSpeech.py`, `VideoCreatorFromImages.py` | Azure returns the audio in memory and the app saves it, so Azure never holds the file open (Windows couldn't delete it), and a partial file that still can't be deleted stops the video with the real error instead of "file in use" | ~10 lines |
| `default_settings.py` | Upscale saves WebP by default instead of PNG; a video's "audio-files" and "images-with-highlighted-text-boxes" folders are cleaned up by default (the user's calls, 2026-11-24). Spec 08 still adds the smaller lossy WebP | 3 lines |
| `gui_classes/UpscaleImagesView.py` | A cancelled upscale still shrinks the images that finished to 4K (and the custom height / max width); a cut-off image is removed | ~15 lines |
| `gui_classes/ProgressPanel.py` | Sizes in the Status view are written by Windows itself on Windows (`StrFormatByteSizeW`, what File Explorer uses: 1 KB = 1024 bytes, 3 digits, not rounded up); the Mac keeps Finder's way | ~15 lines |
| `gui_classes/PipelineView.py` | The Pipeline's settings summary only lists the Download settings the link's site uses (`get_download_review`), and updates as the link is typed; its Upscale Images line says "at most 4K (3840px)" when the 4K limit is on (the user, 2026-11-24) | ~27 lines |
| `download_pages_from_url.py` | `get_safe_folder_name`: no space or dot at the end after cutting to 100 letters | 1 line |
| `download_from_comix.py` | Windows Chrome and Edge paths | 6 lines |
| `package.json` | `:windows` npm scripts (npm uses cmd.exe there) | 5 lines |
| `tests/` | `test_magi.py` covers the GPU picking; 6 other tests fixed for Windows assumptions; 7 new tests for the Windows bugs above | small |
| `ROADMAP.md` | Update #10 table with the findings above | ~6 lines |

Reuse, no changes: `run_with_cpu_fallback()` in `magi.py`; `get_pytorch_upscale_function()` / `can_use_coreml()` in `janai.py` (already uses PyTorch off-Mac); `get_waifu2x_path()` and `open_directory` in `utils.py`; `python gui.py --self-test` (`self_test.py`) as the first check.

## 6. Steps (todo)
- [x] On the PC: install Python ~~3.12~~ **3.11** (tokenizers 0.14.1 has no Windows build for 3.12) and git; clone the repo; make a venv
- [x] `pip install -r requirements.txt` **without** the `torch`/`torchvision` lines (installed those two first from TheRock, then the rest with them filtered out)
- [x] `pip install --index-url https://nightly.repo.amd.com/rocm/whl-next/ "torch[device-gfx1031]" "torchvision[device-gfx1031]"` → torch 2.15.0+rocm10.3.0a20261122 (not 2.11; the pinned transformers 4.34.0 works with it)
- [x] Check: `python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"` → `True`, RX 6700 XT, as GPU 1: GPU 0 is the CPU's built-in graphics (gfx1036), which fails with "invalid kernel file". `get_device()` now tries a tiny calculation on each GPU and picks the one with the most compute units of those that work (not the most memory: the built-in one reports 12.2 GB, the 6700 XT 12.0 GB), so no `HIP_VISIBLE_DEVICES` is needed
- [x] ~~Download waifu2x-ncnn-vulkan for Windows, put its folder on the PATH~~ Not needed any more: the app downloads it the first time (see below)
- [x] `python gui.py --self-test` → SELF-TEST PASSED
- [x] Benchmark ~~Dragon Ball ch. 93~~ **Shachou ch. 3** (the chapter the M1 numbers are for): Panel-By-Panel, Best upscale, Fast upscale, video, vs the M1 numbers in `benchmarks/README.md`
- [x] ~~If Windows fails: try Linux~~ Not needed: Windows works
- [x] Fix `.cbr` import on Windows (`save_rar_pages` uses Windows' own `System32\tar.exe`) and the `DEVICE_NAMES["cuda"]` wording
- [x] Also found: the comix.to downloader only looked for Mac browsers (added Chrome and Edge's Windows paths), and 6 tests assumed Mac paths, `\n` line endings or a fine-grained clock
- [x] Write the DEVELOPING.md section with what actually worked; update ROADMAP #10
- [x] A review of the whole app for Windows bugs found 5 to fix here, each with a test: voice-over audio files stayed locked, so cleaning them up or re-making a video failed; `transcript.txt` couldn't hold "♥" or Japanese; folder names ending in a space (long web page titles, "Issue 1 .cbz"); `.cbr` files with Japanese names; garbled Japanese in the MangaDex downloader's output. The rest (Documents inside OneDrive, the 260-letter path limit, console windows in a packaged app, the comix cookie file in `~/Library`) went to spec 32
- [x] "Best" to 4K on Absolute Batman ch. 1 (a comic: 318 panels of every size) was very slow: about 19.5 s a panel. Two fixes, 4× faster (391 s → 98 s for 20 panels): same-size 512×512 tiles with AMD's PyTorch (`janai.py`; AMD works out each new tile size the first time), and stopping one 2× pass short of 4K when that pass would go far past it and the image is then at most 1.5× under 4K (`get_best_upscale_ratio` in `utils.py`, `UpscaleImagesView.py`). The image stays at that size: at first it was stretched up to 4K, but that adds no detail, so the user chose to drop it (2026-11-23). Also: Panel-By-Panel shows its stages in the Status view ("Finding the panels", "Saving the panels", and the two text stages in a Pipeline with a video), like Images To Video
- [x] Found by hand on Windows: Images To Video with Azure's "Auto (emotion of each line)" voice style failed with "CUDA error: invalid kernel file". The emotion model (`EmotionAnalyzer.py`) let transformers pick the GPU, and it took GPU 0, the built-in graphics. It now uses the GPU Magi picked (`get_emotion_model_device`); on a Mac it runs on the CPU (as with the pinned transformers 4.34, whose default was the CPU). Then a second error, "Cannot copy out of meta tensor": a video makes 4 voice-over lines at once, and all 4 started loading the model at the same time. Now the first one loads it and the others wait (a lock in `EmotionAnalyzer.emotion_pipeline`; the shared analyzer is made up front). Every model was checked: Magi (both models) and "Best" already used `get_device()`, waifu2x picks the card by itself (1.9 s vs 10 s on the built-in graphics), and the voices (Edge, Azure) run online
- [x] Found by hand on Windows: Images To Video with Azure said "[WinError 32] The process cannot access the file ... panel_1.mp3". The real error was Azure's "Authentication error (401). Please check subscription information and region name" (a key/region problem, not the app). Azure's SDK keeps the audio file open until its synthesizer is gone, so the app couldn't delete the half-made mp3, and that error hid the real one. Then, with a valid key and the "Auto" style, a 2-line panel was skipped with "file in use" on `panel_3.mp3.part-1.mp3`: Azure kept the file open for a while even after it succeeded, and the parts are deleted right after being joined. Now Azure gives the audio back in memory (`audio_config=None`, `result.audio_data`) and the app saves it, so Azure never holds a file (`generate_azure_audio_for_text`); and if a partial file still can't be deleted, the real error is shown (`generate_voice_over`)
- [x] The user asked about viruses from a web page download. What protects: no JavaScript runs, only files that open as an image are kept, the app picks the names (`001.jpg`) and the extension (jpg/png/webp), only http(s), Pillow's decompression-bomb guard, comic files only give their images. The gap was size: the page and each image were read whole into memory, so a huge one could fill it. Now at most 10 MB for the page (its HTML) and 50 MB for each image are read (read in 1 MB pieces, stopping once over the limit); a bigger image is skipped, a bigger page gives a clear error. Also worth doing elsewhere: keep Pillow up to date (11.1.0 here; image-reader bugs are the real risk with images). "Reset All Settings": a new test changes every setting, resets, and checks each is back to its default and the tabs show it
- [x] The user asked for tests of every Images To Video setting. New, offline (Magi and the voice faked, real moviepy/ffmpeg): format (mp4, mov), shape and resolution, fixed time per image, reading speed (a higher speed makes the video shorter, down to the minimum time per image), the minimum time, the voice-over's length with pauses before and after, highlighting (one image per line), the box look (border color, width, padding, background), the pause between lines, both clean-up checkboxes, and reading the saved settings. Found on the way: **a reading speed of 0 crashed the video** (divided by zero) and a negative one gave negative times; now anything not above 0 uses 150. There's no maximum speed: a very high one just makes each image's time tiny (the minimum time then applies). The review found the same for the other times: **an image displayed duration of 0 or less crashed the video** (now 3 s), and a negative pause before/after the voice cut the voice off (now 0; a negative minimum time is 0 too). Also tested: every border style (solid, dotted, dashed, dashdot), and a panel without text shows for the minimum time
- [x] The user asked for tests of everything else not tested yet (the other tabs and Settings). Fast: Upscale's custom panel height, max image width and noise level (and the waifu2x command it becomes); MangaDex's chapter and page ranges, language and every checkbox (no group name, no oneshots, chapter and volume covers, replace) as downloader options; "split tall panels" reaching Magi; the Clear button on the three job tabs; Open Log File. End-to-end (`-m e2e`): a 2-chapter MangaDex range (Dragon Ball ch. 1–2, 2 pages each; a whole-series download also saves the series' `cover.jpg`), a real "Fast" upscale with noise reduction and a custom height, a real "Best" upscale of a color panel (on the GPU), and the Pipeline from a comix.to link (Slam Dunk ch. 1: Download and Panel-By-Panel). All 4 passed on the PC (2026-11-24). Then the combinations where two settings change the same thing: "Best" + 4K limit + custom height + max width, the WebP-to-PNG fallback + custom height, a cancel + custom height, highlighting with the reading speed or a fixed time (no voice), group by page + `.cbz`, and a webtoon + split tall panels
- [x] The user's call: Upscale's default image format is WebP, not PNG (`default_settings.py`). waifu2x writes it lossless, about 43% smaller than PNG (but a resize afterwards, like the 4K shrink, re-saves it at Pillow's default quality 80, and "Best" saves quality 95). A WebP image can't be more than 16383 px on a side, so a folder with an image that would be bigger (a long webtoon strip, or a big upscale without the 4K limit) is saved as PNG, with a message (`WEBP_MAX_SIDE` in `UpscaleImagesView.py`). Spec 08's lossy WebP (about 6× smaller) is still to do, and its line "Default `image_format: png`" is now out of date. Only new installs and "Reset All Settings" get the new default: a saved "png" stays. "Limit to 4K" was already on by default
- [x] Found by hand on Windows: after a cancelled "Fast" upscale of Slam Dunk ch. 1, the 19 finished panels were 4200–6866 px (up to 51 MB). The 4K limit works ("4x instead of 16x"), but the last shrink to exactly 4K ran only when every image was done, and a cancel skipped it. Now a cancel still shrinks the finished images (and applies the custom height / max width); images that never started are skipped without "failed" messages, and one cut off by the cancel is removed
- [x] Found by hand on Windows: the Status view said 70.4 MB for Slam Dunk ch. 1, File Explorer 67.1 MB. Both were right (70,413,414 bytes): Explorer counts 1 MB as 1,048,576 bytes, the app as 1,000,000 (like Finder). On Windows the app now has Windows write the size, with the function Explorer uses (`format_size_like_file_explorer` in `ProgressPanel.py`), so it shows exactly what Explorer shows (67.1 MB). Counting by 1024 alone gave 67.2 MB: Explorer also keeps only 3 digits and doesn't round up
- [x] Found by hand on Windows: with a comix.to link, the Pipeline's settings summary still said "language English (MangaDex only)". It now shows only the Download settings the link's site uses ("from comix.to, chapters 1 to 3"; MangaDex: all of them; a web page: "Only keep bigger images"; the Internet Archive: none), and updates as the link is typed. Before a link is entered it shows the MangaDex ones, as before
- [x] Upscaling failed with "waifu2x-ncnn-vulkan was not found" whenever it wasn't on the PATH (a fresh Mac from source too, and even for "Best", which only uses waifu2x for images that are already 4K). Now it's downloaded the first time, like the "Best" models. Tests never download it (`tests/conftest.py`), so they also no longer depend on whether waifu2x is installed
- [x] Found by hand on Windows: "Reset All Settings" jumped back to the top of the Settings page and said nothing. Reset rebuilt every tab, Settings included. Now Settings is kept (so it stays scrolled where it was) and shows its defaults in place (start tab, .cbz, folder). A green "All settings in every tab are back to their defaults." shows next to the button for 3 seconds, or above it when the window is narrow (under 760 px, the same width the other tabs use; there it doesn't fit next to the button, and under it is out of view since Reset is the last part of the page; the user's call; scrolling to the end of the page was tried first and didn't show it) (`AppSettingsView.show_reset_settings`). No spinner: rebuilding the other tabs takes about 10 ms.
- [x] The user asked for an "Open Logs Folder" button next to "Open Log File", to see past runs (e.g. why the app crashed last time). Windows logs moved from `C:\Users\<you>\Library\Logs\Panelyze` to `%LOCALAPPDATA%\Panelyze\Logs`; old logs there are left where they are. "Open Log File" is renamed "Open Current Log", and the help text says the current log is everything since Panelyze was opened and the folder keeps the last 9 times.
- [x] The user asked to point people to GitHub issues when something goes wrong: a "Something went wrong?" section in `README.md`, a "Report a Problem" button in Settings → Log file (opens https://github.com/curlos/panelyze/issues/new/choose, the template picker), and an issue template (`.github/ISSUE_TEMPLATE/bug_report.md`: steps, what happened, computer, which log). All three warn that issues are public and the log has folder paths (with the user name) and chapter links.
- [x] The user asked for a link to the GitHub repo in the app: Settings has an "About" section (before Reset) with "Panelyze 1.0.0" (`APP_VERSION` in `default_settings.py`, the user's call for the first release; spec 40 should use it), what the app does in three short paragraphs, and a "View on GitHub" button.
- [x] The user asked for a review of the default settings (what a new user starts with, and what Reset All Settings goes back to). Changed (the user's calls): the app opens on **Download** (a new user has nothing to split yet; also the fallback for an unknown saved tab), a web page keeps **only images at least 600 px** (pages are full of logos and icons), videos have the **free Edge voice on** (people expect sound; reading speed is off, since the two are one choice in the tab and both on showed "Reading Speed" picked while the voice was used), with a **0.5 s pause** after each panel's voice. Kept: 16:9 videos (a chapter makes a 5–15 minute video, too long for Shorts), the rest. Tests that relied on the old defaults now set what they test.
- [x] The user's idea: in the Download tab's "Paste a link from" list (shown before a link is pasted), the site names are links (blue, underlined) that open MangaDex, comix.to and the Internet Archive's comics collection (`archive.org/details/comics`), so a new user can find something to paste right away (`SOURCES` in `gui_classes/SettingsMangaDexDownloader.py`). Not in About, where it would be tucked away. The links are Nord's light blue (`ACCENT`), since its darker blue was hard to read on the background.
- [x] Found by hand on Windows: tooltips (the tabs, "Wait for ... to finish", the folder buttons, the site links) showed as plain text floating over the page: the theme's tooltip box had no border or shadow and was almost the page's color. Every tooltip now uses `Nord.tooltip(message)`: a box with a light blue border, rounded corners and a shadow, just under what it's about. Flutter tooltips can't have an arrow pointing at the control.
- [x] The user's call: a tab that shows its name has no tooltip ("Upscale Images (Ctrl+3)" under "Upscale Images" said it twice). A tab has one only while a job runs ("Wait for ... to finish") or when the window is narrow and only its icon shows (the name and shortcut). The shortcuts are listed in the README's "Good to know" instead.
- [x] The user's idea: show which GPU the AI models use. `get_device()` is now worked out once per run (`get_device_choice`, trying each GPU took video memory each time) and prints a sentence like "The AI models run on the AMD Radeon RX 6700 XT. Not used: the AMD Radeon(TM) Graphics (PyTorch can't run on it)." The Settings page has a "GPU" section with it (found the first time Settings is opened, in the background). The Status view shows "Running on the AMD Radeon RX 6700 XT" during jobs that use Magi or "Best" (`get_device_name`: the name from the driver, "Apple M1" from macOS on a Mac, or "CPU"). Every device name (used or not) is in a light Nord purple (`Nord.DEVICE`). The Status view also scrolls when the terminal is dragged too small for it

## 7. How to test it
- Existing test suite on the PC: `pytest` (`tests/test_magi.py` covers mps/cuda/cpu picking and the GPU probe).
- `python gui.py --self-test`.
- Real run: each tab on its own for Shachou ch. 3, One Piece ch. 567 and Dragon Ball ch. 93; compare panel counts with the Mac run; record times in a table.
- Check the GPU is used: the check command in DEVELOPING.md prints `cuda:1` and the card's name. A wrong PyTorch build gives `cpu` without any message, and "Magi failed on the GPU (...). Running it on the CPU instead." in the log means the card failed while running.

## 8. Size, value, risks, open questions

| | |
|---|---|
| Size | Small for code (about 120 lines plus tests). Medium for setup and testing on the PC (1–2 hours) |
| Value | Low–Medium: only helps when working on the PC. Becomes Medium if whole-series runs (#3) happen |
| Risk: nightly builds | TheRock nightlies can break between days. Pin the exact wheel that works |
| Risk: newer torch | 2.11 (Mac, CPU) works with transformers 4.34; retest if a newer nightly breaks |
| The PC's venv has newer packages than `requirements.txt` | Spec 01 (Translate Japanese pages) upgraded the shared venv on 2026-11-23: transformers 4.57.6 (pinned here 4.34.0), tokenizers 0.22.2, huggingface-hub 0.36.2, safetensors 0.8.0, timm 1.0.31 (spec 01 checked Magi gives the same results). Everything spec 10 tested on the PC after that ran with them. **Decided (the user, 2026-11-24): the newer versions are the ones to use; spec 01 makes them official** (its `requirements.txt` / `requirements-lock.txt` already pin them, torch 2.14.1 on the Mac too). Spec 10 doesn't copy them, so the two don't conflict: merge 10, then 01. Spec 10's code works with both (the emotion model gets its device explicitly) |
| Risk: app on Windows at all | README says "Mac only, Windows planned". Flet desktop works on Windows, but Panelyze itself has never been run there; path or subprocess bugs may show up (separate from the GPU) |
| Risk: 12 GB VRAM | Full Magi is ~2 GB; fine. CPU fallback already handles out-of-memory |

**Open questions for the user**
1. ~~Is the PC on Windows 10 or 11?~~ Windows 11 Pro (checked 2026-11-22).
2. ~~Is a Linux dual boot acceptable as a backup, or Windows only?~~ Not needed: Windows works.
3. ~~Want the 1-line "the GPU" wording fix in `magi.py`, or leave code untouched?~~ Done, then replaced by the GPU's real name (`get_device_name`).
4. ~~Is this still wanted now that spec 20 (free NVIDIA options) exists?~~ Yes: built.

## 9. Sources

- JP-TL-Bench (Japanese↔English translation scores): https://arxiv.org/html/2601.00223v1
- Ollama models: https://ollama.com/library/qwen3-vl · https://ollama.com/library/gemma4 · https://ollama.com/library/ministral-3
- TheRock releases / install + device extras: https://github.com/ROCm/TheRock/blob/main/RELEASES.md
- TheRock supported GPUs (gfx1031 Linux + Windows ✅): https://github.com/ROCm/TheRock/blob/main/SUPPORTED_GPUS.md
- AMD Windows PyTorch support matrix (RX 7000/9000 only): https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/windows/windows_compatibility.html
- AMD native Linux matrix (ROCm 7.2.1 + PyTorch 2.9.1, no RDNA2): https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/native_linux/native_linux_compatibility.html
- AMD WSL matrix: https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/wsl/wsl_compatibility.html
- HSA override for gfx1031 (10.3.0): https://localaimaster.com/blog/rocm-unsupported-gpu-hsa-override , https://github.com/ROCm/ROCm/issues/2527
- Community Windows ROCm on RX 6750 XT (gfx1031): https://forum.level1techs.com/t/native-vllm-rocm-7-15-runtime-for-rx-6000-rdna2-on-windows-11-26-tflops-fp16-62-tok-s-one-click-install-no-wsl2-rx-6750-xt-gfx1031-verified/254042
- torch-directml on PyPI: https://pypi.org/project/torch-directml/
- PyTorch ROCm 6.2 wheels: https://download.pytorch.org/whl/rocm6.2/torch/
- Local check: scratch venv with torch 2.11.0 + transformers 4.34.0 running `magi.Magi().predict_panels`, `get_per_page_results` and `janai.get_pytorch_upscale_function` (2026-11-19)
