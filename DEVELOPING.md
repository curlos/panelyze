# Developing Panelyze

Notes for working on the code. If you just want to use the app, see the [README](README.md).

Tested on macOS with Python 3.12, and from source on Windows 11 with an AMD GPU and Python 3.11 (see below).

## Shortcuts in VS Code

`package.json` is only a list of shortcuts (the app doesn't use Node). In VS Code, open the **NPM SCRIPTS** section in the Explorer sidebar, or hover a script in `package.json` and click **Run Script**. Or from a terminal: `npm run <name>`.

| Script | What it does |
|---|---|
| `run` | Start the app |
| `dev` | Start the app and restart it every time a file is saved |
| `test` | The fast tests (a few seconds) |
| `test:all` | The fast tests plus the end-to-end tests with the real tools |
| `self-test` | Check that Magi, waifu2x, video, MangaDex Downloader, text-to-speech, opening comic files (.pdf, .cbz), the comix.to downloader and the Best upscaler (spandrel, Core ML) work, without opening the window |
| `build-mac-app` | Build the downloadable `Panelyze.app` and its zip |

They use the project's `venv`, so set it up first (below).

## Set up (once)

```bash
git clone https://github.com/curlos/panelyze.git
cd panelyze
python3.12 -m venv venv        # or: uv venv --python 3.12 venv
source venv/bin/activate
pip install -r requirements.txt        # or, for the exact tested versions of everything: pip install -r requirements-lock.txt
```

`requirements.txt` is the short list of what the app uses directly. `requirements-lock.txt` lists every package (including the ones pip installs automatically) at the exact version the app was tested with.

The first time you use Panel-By-Panel, the small panels-only Magi model is built from the full model (2.06 GB, downloaded from Hugging Face once). See `magi_model/README.md`.

**For the "Upscale Images" tab:** waifu2x-ncnn-vulkan is downloaded the first time you upscale with "Fast" or "Better" ("Best" only needs it for an image that's already 4K) (54 MB on a Mac, 36 MB on Windows once unzipped, without the photo model it doesn't use, into `~/Library/Application Support/Panelyze/waifu2x`, from its [GitHub releases](https://github.com/nihui/waifu2x-ncnn-vulkan/releases)), like the "Best" models. A copy already installed on your computer (e.g. on your PATH) isn't used, so everyone runs the same version and Settings → Storage can manage it. The downloadable app already includes it.

### On a Windows PC with an AMD GPU

Tested on Windows 11 with a Radeon RX 6700 XT (gfx1031), 2026-11-22. Only running from source; there's no Windows app to download. In PowerShell:

```powershell
winget install Python.Python.3.11   # 3.11, not 3.12: tokenizers 0.14.1 has no Windows build for 3.12
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install --index-url https://nightly.repo.amd.com/rocm/whl-next/ "torch[device-gfx1031]" "torchvision[device-gfx1031]"
Get-Content requirements.txt | Where-Object { $_ -notmatch '^(torch|torchvision)==' } | Set-Content requirements-no-torch.txt
.\venv\Scripts\python.exe -m pip install -r requirements-no-torch.txt; Remove-Item requirements-no-torch.txt
```

- **PyTorch comes from AMD's "TheRock" nightly builds**, not the pinned `torch==2.5.1` (on Windows that's the CPU-only build). The line above is for the RX 6700 XT (`gfx1031`). For another AMD card, change both `gfx1031`s to its chip (see your card's name with `Get-CimInstance Win32_VideoController | Select-Object Name`, then its chip in [TheRock's list](https://github.com/ROCm/TheRock/blob/main/SUPPORTED_GPUS.md); RX 5000 to RX 9000 are all there). For NVIDIA, use `--index-url https://download.pytorch.org/whl/cu124 torch==2.5.1 torchvision==0.20.1` instead (RTX 50 cards: `--index-url https://download.pytorch.org/whl/cu128 torch torchvision`). Neither has been tested. With the wrong chip, nothing crashes, but Magi and "Best" quietly run on the CPU (about 12× slower). Tested with `torch 2.15.0+rocm10.3.0a20261122`; nightlies can break, so if a newer one fails, install that exact version (`"torch[device-gfx1031]==<version>"`).
- **A CPU with built-in graphics (most Ryzen 7000/9000) also shows up as a GPU**, often GPU 0, and PyTorch installed for the graphics card's chip can't run on it ("invalid kernel file"). The app skips it on its own: `get_device()` in `magi.py` tries a tiny calculation on each GPU and uses the one with the most compute units of those that work. Check which one it picks in Settings → GPU, or with `.\venv\Scripts\python.exe -c "import magi; magi.get_device()"`: it should print your card's name. "The AI models run on the CPU" means the installed PyTorch doesn't match your card.
- **waifu2x** is downloaded the first time you upscale, as on the Mac (into `C:\Users\<you>\Library\Application Support\Panelyze\waifu2x`). It uses Vulkan, so it works on any AMD, NVIDIA or Intel GPU.
- `.cbr` files are opened with Windows' own `tar.exe`. Logs go to `%LOCALAPPDATA%\Panelyze\Logs` (Settings → Open Logs Folder).
- Run with `.\venv\Scripts\python.exe gui.py`, and the tests the same way. The `npm` shortcuts have Windows versions ending in `:windows` (`npm run dev:windows`, `npm run test:windows`, ...); the plain ones use Mac paths. The worktree steps in `CLAUDE.md` use `ln -s`. On Windows, link a worktree's folders with `cmd /c mklink /J venv ..\panelyze-main\venv` (the same for `test-chapter-cache`), and copy `magi_model\panels_fp16.safetensors` (or let the first Panel-By-Panel run build it).
- **Harmless warnings:** MIOpen's "CK grouped conv library not found" and "File is unreadable ... .fdb.txt" on the first GPU run, huggingface_hub's "symlinks aren't supported", and "Event loop is closed" tracebacks when the app closes after a comix.to download.
- **PowerShell 5.1's `>` writes UTF-16**, which git and Python don't read as text. Use `Out-File -Encoding utf8` (or Git Bash) for files the app, the tests or git read.

### On a Windows PC with an NVIDIA GPU

**Not tested** (no NVIDIA PC here). The same as for AMD, but with PyTorch's own CUDA build of the pinned `torch==2.5.1`, which runs on NVIDIA cards that PyTorch 2.5.1 supports (GTX 900 or newer, per [spec 32](specs/32-windows-app.md)):

```powershell
winget install Python.Python.3.11
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install --index-url https://download.pytorch.org/whl/cu124 torch==2.5.1 torchvision==0.20.1
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

The last line keeps the CUDA build: the versions already match `requirements.txt`. An RTX 50 card needs a newer PyTorch (`.../whl/cu128 torch torchvision`), which isn't the pinned version, so things may behave differently there.

## Run

- `python gui.py` (with the venv activated).
- On a Mac, `npm run run` and `npm run dev` show the window as **Panelyze** in the Dock and menu bar (plain `python gui.py` shows Flet's name and icon). `make_dev_window_app.sh` makes that renamed copy of Flet's window app once, in `~/Library/Application Support/Panelyze/dev-window`, and the scripts point Flet to it (`FLET_VIEW_PATH`). Delete that folder to make it again (e.g. after the icon changes).
- `flet run -r gui.py` restarts the app every time a file in the repo is saved, which also stops a job that's running. For a long job, use `python gui.py` (restart it to pick up code changes).
- `flet run --web --port 8577 gui.py` opens the app in your web browser instead of a window. Handy for checking how it looks, including at phone sizes (make the browser window narrow). Its settings are separate from the window's.
- `python gui.py --self-test` checks that Magi, waifu2x, video, MangaDex Downloader, text-to-speech, opening comic files (.pdf, .cbz), the comix.to downloader and the Best upscaler (spandrel, Core ML) all work, without opening the window.

## Tests

```bash
python -m pytest          # fast tests (about 45 seconds), including GUI tests without a window
python -m pytest -m e2e   # end-to-end tests with the real tools (a few minutes, needs the internet and waifu2x)
```

The fast tests include a type check (`tests/test_types.py`): it runs [Pyright](https://github.com/microsoft/pyright) (`npx --yes pyright@1.1.414`, settings in `pyproject.toml`) and fails if it finds any type error, listing them. It needs [Node.js](https://nodejs.org) for `npx`, and is skipped without it. VS Code's Python extension (Pylance) shows the same errors in the Problems panel for the files you have open.

They also include a lint check (`tests/test_lint.py`): [Ruff](https://docs.astral.sh/ruff/) (`ruff check .`, installed with requirements.txt, rules in `pyproject.toml`) looks for mistakes like unused imports and variables, undefined names or likely bugs. `ruff check --fix .` fixes most of them. The code is also formatted with `ruff format .` (the same style as Black, 88 characters a line, which VS Code's Black extension uses when saving a file), and the check fails if a file isn't.

GitHub runs the fast tests on every push to `main` (`.github/workflows/tests.yml`, the Actions tab). The slower "Clean Mac check" (`.github/workflows/clean-mac-check.yml`) installs everything on a fresh Mac and builds the app; it's started by hand before a release.

The end-to-end tests that download from MangaDex use Dragon Ball chapter 93 (`https://mangadex.org/chapter/ac33cc50-a1b2-49b0-a388-0d0ee4ebce18/14`) and only fetch its first 3 pages (saved as `00.jpg` for the cover, `01.jpg` and `02.jpg`; the downloader numbers files from 00). The first run saves them in `test-chapter-cache/` (git-ignored), and later runs reuse them. Set `PANELYZE_TEST_MANGADEX_URL` to use a different chapter.

## Build the downloadable app

```bash
./build_mac_app.sh
```

It bundles everything (including waifu2x and the panels-only Magi model) into `dist/Panelyze.app`, runs the self-test on the built app, and zips it to `dist/Panelyze-macOS-AppleSilicon.zip`. Upload that zip to a [GitHub release](https://github.com/curlos/panelyze/releases) for users to download. The app only runs on Apple Silicon Macs (it's built on one).

Before a release, run the **Clean Mac check** on GitHub (`gh workflow run clean-mac-check.yml`, or Actions → Clean Mac check → Run workflow). On a brand-new Mac it installs from `requirements.txt`, runs the fast tests and the self-test (downloading the Magi model for real), and builds and self-tests the app. It takes a while, since the Mac has no GPU.

## How it works

- **Output folders** keep the same structure as the input folder. For example, picking `One Piece` as the input gives `<output>/One Piece/<chapter>/panel_1.png, panel_2.png, ...` (`get_panels_folder` in `utils.py`). With "Group panels by page" checked, it saves `<output>/One Piece (grouped by page)/<chapter>/page_1/panel_1.png, ...` instead, so the two never mix (the next tab reads `<output>/One Piece`). A new run deletes only the chapter's old panels, page folders and `panel-text.json` (`remove_old_panels`), never other files in that folder.
- **Default output folders:** every tool saves to its own folder in the Panelyze folder (`panelyze_folder` setting, `~/Documents/Panelyze` by default, changed in Settings) unless the user picks another one for that tool, which is remembered in the `output_directory_*` settings (empty means the default). `get_output_directory` in `default_settings.py` works out the folder. **Run from source** (the repo has a `.git`), the Panelyze folder is `~/Documents/Panelyze/<repo folder>` instead, e.g. `.../Panelyze/panelyze-main` or `.../Panelyze/17-second-downloader` for a spec's worktree (`get_dev_output_folder`), so development never mixes with the packaged app's folders. The `panelyze_folder` setting and folders picked for one tool are ignored there, and the buttons to pick output folders are hidden (`can_pick_output_folders`): picked folders are saved in settings that every run shares, so a pick made while developing would send other runs' files to the wrong place. When a job finishes, the next tab's input folder is filled in with the result (`JobView.fill_in_next_tab_input`), unless the user picked a folder there themselves.
- **Settings → Storage** (`storage.py`, `gui_classes/StorageSection.py`) lists every folder the app uses, from its own constants only: each tool's saved files (from source, only this repo's or worktree's own folder), waifu2x, the "Best" models (with their Core ML copies), and in the Hugging Face cache only Magi's 2 folders (Magi and TrOCR) and the emotion model's (never the rest of the cache). Its first line says how much is free on each disk. Sizes are the space taken once downloaded (unzipped). Sizes are added up in the background each time Settings opens. Delete asks first, is off while a job runs, and never deletes a folder picked in a tab; Download runs like a job.
- **Downloads** go to `<output>/<manga title>/Vol. 1 Ch. 3 - <chapter title>/`. The downloader is given its own placeholders for this (`download_from_mangadex.py`), because passing it a plain folder drops the manga folder, and its "use chapter title" option doesn't change these folder names for the raw format. A chapter without a title keeps the downloader's folder name, `Vol. 1 Ch. 3 - ` (the downloader finds its pages by it); only the result line drops the dash. Pages keep the downloader's names, from `00.jpg`.
- **Pipeline:** each step saves to its own numbered folder (`1-download`, `2-panel-by-panel`, ...) inside the output folder, and the pipeline stops if a step fails or saves no images.
- **Activity** (the panel at the bottom, `TerminalOutput.py`) has the **Status** view (what the job is doing, its steps and progress) and the **Log** (everything the app prints: progress, errors, tool output; select across lines, or copy every line shown with the copy button; the app keeps the last 2,000, the log file has all). The Log is also saved to `~/Library/Logs/Panelyze/panelyze.log`, or `%LOCALAPPDATA%\Panelyze\Logs` on Windows (this run only; the 9 runs before it are `panelyze.1.log` to `panelyze.9.log`).

## Magi models

- **Panel-By-Panel uses only the part of Magi that finds panels** (87 MB instead of 2 GB, about 18x faster than running the full model, same panels).
- **Images To Video reads text with the full Magi v2 model.** It's downloaded the first time it's needed. Both Magi models run on the GPU when there is one (the Mac GPU, or an NVIDIA or AMD GPU), and on the CPU otherwise. Only the dialogue is read (sound effects are skipped), one image at a time and 8 lines at a time, which measured fastest.
- **When the Pipeline also makes a video, Panel-By-Panel reads the text on the whole pages** (much faster than reading every panel) and saves it as `panel-text.json` next to the panels. Upscale carries it along, and Images To Video uses it instead of running Magi again (not when highlighting text boxes, which needs the boxes on each panel).
- Magi v1 and v3 were also measured. v1 found slightly different panels, and v3 was much slower (about 15–38 seconds per page) and marks every text as dialogue.
- Magi was trained on manga, so panels on western comics may be found a little less reliably.
- **License:** the Magi AI Model is free for personal, research, non-commercial and not-for-profit use only (see its [model page](https://huggingface.co/ragavsachdeva/magiv2)).

## Upscale models

The "Upscale Model" setting picks one of three:

- **Fast** (default): waifu2x `upconv_7_anime_style_art_rgb`. About 2x faster than cunet and nearly the same on manga.
- **Better**: waifu2x `cunet`. Slightly cleaner screentone (gray shading).
- **Best**: [MangaJaNai](https://github.com/the-database/MangaJaNai) for black and white images, IllustrationJaNai for color ones (`janai.py`). By far the best on manga: it restores clean halftone dots. MangaJaNai turns color into black and white dots, so color images are detected and sent to IllustrationJaNai.
  - MangaJaNai has a model for each common page height (1200p to 2048p), and the closest one restores the dots at the right size. Panel-By-Panel saves each panel's page height in its PNG file for this.
  - On Apple Silicon Macs they run with Core ML: MangaJaNai on the Neural Engine (about 0.44 s a panel, 3.6x faster than the GPU with PyTorch) and IllustrationJaNai on the GPU (Apple's Neural Engine compiler gets stuck on it). Each model is converted to Core ML the first time it's used. Elsewhere they run with PyTorch.
  - The models are downloaded the first time (only their 2x models, 252 MB once unzipped, taken straight out of the zips on GitHub: the whole zips are 592 MB) to `~/Library/Application Support/Panelyze/upscale-models`.
  - **License:** CC BY-NC 4.0 (non-commercial).
- waifu2x upscales a whole folder in one run (about 2x faster than one run per image). Real-CUGAN was also tried: it smears black and white screentone into a gray texture.

## Text-to-speech

- **edge-tts** is the default. It's free (no API key) but unofficial and needs an internet connection.
- **Azure Speech** is also available: pick "Azure" as the engine in the Text-To-Speech settings and enter your key and region. The Azure end-to-end test reads them from the `AZURE_SUBSCRIPTION_KEY` and `AZURE_REGION` environment variables and skips without them.
- Azure voices can read in a speaking style (cheerful, sad, angry, ...): pick a fixed one, or **Auto**, which reads each line in the style that fits its emotion. Auto downloads a small emotion model (331 MB) the first time it's used, and only then. Only some Azure voices have styles; the others just speak normally.

## Video

Shapes are 16:9, 9:16 or 1:1. The resolution setting is the shorter side (1080 gives 1920x1080, 1080x1920 or 1080x1080). Panels are scaled to fit and centered on a black background. mp4 and mov are supported.
