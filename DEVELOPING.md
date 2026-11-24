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
| `self-test` | Check that Magi, waifu2x, video, MangaDex Downloader, text-to-speech, opening comic files (.pdf, .cbz) and the comix.to downloader work, without opening the window |
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

The first time you use Panel-By-Panel, the small panels-only Magi model is built from the full model (about 2 GB, downloaded from Hugging Face once). See `magi_model/README.md`.

**For the "Upscale Images" tab:** waifu2x-ncnn-vulkan is downloaded the first time you upscale (about 40 MB, into `~/Library/Application Support/Panelyze/waifu2x`, from its [GitHub releases](https://github.com/nihui/waifu2x-ncnn-vulkan/releases)), like the "Best" models. If waifu2x is already on your PATH, that one is used instead. The downloadable app already includes it.

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

## Run

- `python gui.py` (with the venv activated).
- `flet run -r gui.py` restarts the app every time a file in the repo is saved, which also stops a job that's running. For a long job, use `python gui.py` (restart it to pick up code changes).
- `flet run --web --port 8577 gui.py` opens the app in your web browser instead of a window. Handy for checking how it looks, including at phone sizes (make the browser window narrow). Its settings are separate from the window's.
- `python gui.py --self-test` checks that Magi, waifu2x, video, MangaDex Downloader, text-to-speech, opening comic files (.pdf, .cbz) and the comix.to downloader all work, without opening the window.

## Tests

```bash
python -m pytest          # fast tests (a few seconds), including GUI tests without a window
python -m pytest -m e2e   # end-to-end tests with the real tools (a few minutes, needs the internet and waifu2x)
```

The end-to-end tests that download from MangaDex use Dragon Ball chapter 93 (`https://mangadex.org/chapter/ac33cc50-a1b2-49b0-a388-0d0ee4ebce18/14`) and only fetch its first 3 pages (saved as `00.jpg` for the cover, `01.jpg` and `02.jpg`; the downloader numbers files from 00). The first run saves them in `test-chapter-cache/` (git-ignored), and later runs reuse them. Set `PANELYZE_TEST_MANGADEX_URL` to use a different chapter.

## Build the downloadable app

```bash
./build_mac_app.sh
```

It bundles everything (including waifu2x and the panels-only Magi model) into `dist/Panelyze.app`, runs the self-test on the built app, and zips it to `dist/Panelyze-macOS-AppleSilicon.zip`. Upload that zip to a [GitHub release](https://github.com/curlos/panelyze/releases) for users to download. The app only runs on Apple Silicon Macs (it's built on one).

## How it works

- **Output folders** keep the same structure as the input folder. For example, picking `One Piece` as the input gives `<output>/One Piece/<chapter>/panel_1.png, panel_2.png, ...` (`get_panels_folder` in `utils.py`). With "Group panels by page" checked, it saves `<output>/One Piece (grouped by page)/<chapter>/page_1/panel_1.png, ...` instead, so the two never mix (the next tab reads `<output>/One Piece`). A new run deletes only the chapter's old panels, page folders and `panel-text.json` (`remove_old_panels`), never other files in that folder.
- **Default output folders:** every tool saves to its own folder in the Panelyze folder (`panelyze_folder` setting, `~/Documents/Panelyze` by default, changed in Settings) unless the user picks another one for that tool, which is remembered in the `output_directory_*` settings (empty means the default). `get_output_directory` in `default_settings.py` works out the folder. **Run from source** (the repo has a `.git`), the Panelyze folder is `~/Documents/Panelyze/<repo folder>` instead, e.g. `.../Panelyze/panelyze-main` or `.../Panelyze/17-second-downloader` for a spec's worktree (`get_dev_output_folder`), so development never mixes with the packaged app's folders. The `panelyze_folder` setting and folders picked for one tool are ignored there, and the buttons to pick output folders are hidden (`can_pick_output_folders`): picked folders are saved in settings that every run shares, so a pick made while developing would send other runs' files to the wrong place. When a job finishes, the next tab's input folder is filled in with the result (`JobView.fill_in_next_tab_input`), unless the user picked a folder there themselves.
- **Downloads** go to `<output>/<manga title>/Vol. 1 Ch. 3 - <chapter title>/`. The downloader is given its own placeholders for this (`download_from_mangadex.py`), because passing it a plain folder drops the manga folder, and its "use chapter title" option doesn't change these folder names for the raw format. A chapter without a title keeps the downloader's folder name, `Vol. 1 Ch. 3 - ` (the downloader finds its pages by it); only the result line drops the dash. Pages keep the downloader's names, from `00.jpg`.
- **Pipeline:** each step saves to its own numbered folder (`1-download`, `2-panel-by-panel`, ...) inside the output folder, and the pipeline stops if a step fails or saves no images.
- **Terminal Output** shows everything the app prints (progress, errors, tool output) and also saves it to `~/Library/Logs/Panelyze/panelyze.log`, or `%LOCALAPPDATA%\Panelyze\Logs` on Windows (this run only; the 9 runs before it are `panelyze.1.log` to `panelyze.9.log`).

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
  - The models are downloaded the first time (about 600 MB of zips, 240 MB kept) to `~/Library/Application Support/Panelyze/upscale-models`.
  - **License:** CC BY-NC 4.0 (non-commercial).
- waifu2x upscales a whole folder in one run (about 2x faster than one run per image). Real-CUGAN was also tried: it smears black and white screentone into a gray texture.

## Text-to-speech

- **edge-tts** is the default. It's free (no API key) but unofficial and needs an internet connection.
- **Azure Speech** is also available: pick "Azure" as the engine in the Text-To-Speech settings and enter your key and region (or put `AZURE_SUBSCRIPTION_KEY` and `AZURE_REGION` in a `.env` file).
- Azure voices can read in a speaking style (cheerful, sad, angry, ...): pick a fixed one, or **Auto**, which reads each line in the style that fits its emotion. Auto downloads a small emotion model (about 330 MB) the first time it's used, and only then. Only some Azure voices have styles; the others just speak normally.

## Video

Shapes are 16:9, 9:16 or 1:1. The resolution setting is the shorter side (1080 gives 1920x1080, 1080x1920 or 1080x1080). Panels are scaled to fit and centered on a black background. mp4 and mov are supported.
