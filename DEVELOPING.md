# Developing Panelyze

Notes for working on the code. If you just want to use the app, see the [README](README.md).

Tested on macOS with Python 3.12.

## Shortcuts in VS Code

`package.json` is only a list of shortcuts (the app doesn't use Node). In VS Code, open the **NPM SCRIPTS** section in the Explorer sidebar, or hover a script in `package.json` and click **Run Script**. Or from a terminal: `npm run <name>`.

| Script | What it does |
|---|---|
| `run` | Start the app |
| `dev` | Start the app and restart it every time a file is saved |
| `test` | The fast tests (a few seconds) |
| `test:all` | The fast tests plus the end-to-end tests with the real tools |
| `self-test` | Check that Magi, waifu2x, video, MangaDex Downloader and text-to-speech work, without opening the window |
| `build-mac-app` | Build the downloadable `Panelyze.app` and its zip |

They use the project's `venv`, so set it up first (below).

## Set up (once)

```bash
git clone https://github.com/curlos/manga-panel-splitter.git
cd manga-panel-splitter
python3.12 -m venv venv        # or: uv venv --python 3.12 venv
source venv/bin/activate
pip install -r requirements.txt        # or, for the exact tested versions of everything: pip install -r requirements-lock.txt
```

`requirements.txt` is the short list of what the app uses directly. `requirements-lock.txt` lists every package (including the ones pip installs automatically) at the exact version the app was tested with.

The first time you use Panel-By-Panel, the small panels-only Magi model is built from the full model (about 2 GB, downloaded from Hugging Face once). See `magi_model/README.md`.

**For the "Upscale Images" tab:** download waifu2x-ncnn-vulkan and add it to your PATH (the downloadable app already includes it):

```bash
cd ~/Downloads
curl -L -o waifu2x.zip https://github.com/nihui/waifu2x-ncnn-vulkan/releases/download/20250915/waifu2x-ncnn-vulkan-20250915-macos.zip
unzip waifu2x.zip && rm -rf waifu2x-ncnn-vulkan && mv waifu2x-ncnn-vulkan-20250915-macos waifu2x-ncnn-vulkan
echo 'export PATH=$PATH:~/Downloads/waifu2x-ncnn-vulkan' >> ~/.zshrc
```

## Run

- `python gui.py` (with the venv activated).
- `flet run -r gui.py` restarts the app every time a file in the repo is saved.
- `python gui.py --self-test` checks that Magi, waifu2x, video, MangaDex Downloader and text-to-speech all work, without opening the window.

## Tests

```bash
python -m pytest          # fast tests (a few seconds), including GUI tests without a window
python -m pytest -m e2e   # end-to-end tests with the real tools (a minute or two, needs the internet and waifu2x)
```

The end-to-end tests that download from MangaDex use Dragon Ball chapter 93 (`https://mangadex.org/chapter/ac33cc50-a1b2-49b0-a388-0d0ee4ebce18/14`) and only fetch pages 2 and 3 (page 1 is a cover with no panels). Set `PANELYZE_TEST_MANGADEX_URL` to use a different chapter.

## Build the downloadable app

```bash
./build_mac_app.sh
```

It bundles everything (including waifu2x and the panels-only Magi model) into `dist/Panelyze.app`, runs the self-test on the built app, and zips it to `dist/Panelyze-macOS-AppleSilicon.zip`. Upload that zip to a [GitHub release](https://github.com/curlos/manga-panel-splitter/releases) for users to download. The app only runs on Apple Silicon Macs (it's built on one).

## How it works

- **Output folders** keep the same structure as the input folder. For example, picking `One Piece` as the input gives `<output>/panel-by-panel/not-grouped-by-page/One Piece/<chapter>/panel_1.png, panel_2.png, ...`. With "Group panels by page" checked, it saves `<output>/panel-by-panel/grouped-by-page/One Piece/<chapter>/page_1/panel_1.png, ...` instead (only one of the two is made).
- **Pipeline:** each step saves to its own numbered folder (`1-mangadex-download`, `2-panel-by-panel`, ...) inside the output folder, and the pipeline stops if a step fails or saves no images.
- **Terminal Output** shows everything the app prints (progress, errors, tool output) and also saves it to `~/Library/Logs/Panelyze/panelyze.log`.

## Magi models

- **Panel-By-Panel uses only the part of Magi that finds panels** (87 MB instead of 2 GB, about 18x faster than running the full model, same panels).
- **Images To Video reads text with the full Magi v2 model** (about 20 seconds per page on CPU). It's downloaded the first time it's needed.
- Magi v1 and v3 were also measured. v1 found slightly different panels, and v3 was much slower (about 15–38 seconds per page) and marks every text as dialogue.
- Magi was trained on manga, so panels on western comics may be found a little less reliably.
- **License:** the Magi AI Model is free for personal, research, non-commercial and not-for-profit use only (see its [model page](https://huggingface.co/ragavsachdeva/magiv2)).

## Text-to-speech

- **edge-tts** is the default. It's free (no API key) but unofficial and needs an internet connection.
- **Azure Speech** is also available: pick "Azure" as the engine in the Text-To-Speech settings and enter your key and region (or put `AZURE_SUBSCRIPTION_KEY` and `AZURE_REGION` in a `.env` file).
- Azure voices can read in a speaking style (cheerful, sad, angry, ...): pick a fixed one, or **Auto**, which reads each line in the style that fits its emotion. Auto downloads a small emotion model (about 330 MB) the first time it's used, and only then. Only some Azure voices have styles; the others just speak normally.

## Video

Shapes are 16:9, 9:16 or 1:1. The resolution setting is the shorter side (1080 gives 1920x1080, 1080x1920 or 1080x1080). Panels are scaled to fit and centered on a black background. mp4 and mov are supported.
