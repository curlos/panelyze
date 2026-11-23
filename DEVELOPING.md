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

**For the "Upscale Images" tab:** download waifu2x-ncnn-vulkan and add it to your PATH (the downloadable app already includes it):

```bash
cd ~/Downloads
curl -L -o waifu2x.zip https://github.com/nihui/waifu2x-ncnn-vulkan/releases/download/20250915/waifu2x-ncnn-vulkan-20250915-macos.zip
unzip waifu2x.zip && rm -rf waifu2x-ncnn-vulkan && mv waifu2x-ncnn-vulkan-20250915-macos waifu2x-ncnn-vulkan
echo 'export PATH=$PATH:~/Downloads/waifu2x-ncnn-vulkan' >> ~/.zshrc
```

**For the "Translate" tab:** install [Ollama](https://ollama.com) and download the default model (TranslateGemma 12B, 8.1 GB) under **Manage Ollama models** in the Translate settings, or with `ollama pull translategemma:12b`. Or use Gemini, ChatGPT or Claude with an API key, typed in the Translate settings or saved in a `.env` file as `GEMINI_API_KEY`, `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`. Hayai OCR and the manga LaMa (about 800 MB) download from Hugging Face the first time.

## Run

- `python gui.py` (with the venv activated).
- `flet run -r gui.py` restarts the app every time a file in the repo is saved.
- `flet run --web --port 8577 gui.py` opens the app in your web browser instead of a window. Handy for checking how it looks, including at phone sizes (make the browser window narrow). Its settings are separate from the window's.
- `python gui.py --self-test` checks that Magi, waifu2x, video, MangaDex Downloader, text-to-speech, opening comic files (.pdf, .cbz), the comix.to downloader and Translate's fonts and libraries all work, without opening the window.

## Tests

```bash
python -m pytest          # fast tests (a few seconds), including GUI tests without a window
python -m pytest -m e2e   # end-to-end tests with the real tools (a few minutes, needs the internet and waifu2x)
```

The Translate end-to-end test downloads pages 2–4 of Dragon Tofu chapter 24 in Japanese, and is skipped unless Ollama is running with one of the suggested models downloaded.

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
- **Pipeline:** each step saves to its own numbered folder (`1-download`, `2-translate`, `3-panel-by-panel`, ...) inside the output folder, and the pipeline stops if a step fails or saves no images.
- **Terminal Output** shows everything the app prints (progress, errors, tool output) and also saves it to `~/Library/Logs/Panelyze/panelyze.log`.

## Magi models

- **Panel-By-Panel uses only the part of Magi that finds panels** (87 MB instead of 2 GB, about 18x faster than running the full model, same panels).
- **Images To Video reads text with the full Magi v2 model.** It's downloaded the first time it's needed. Both Magi models run on the GPU when there is one (the Mac GPU or an NVIDIA GPU), and on the CPU otherwise. Only the dialogue is read (sound effects are skipped), one image at a time and 8 lines at a time, which measured fastest.
- **When the Pipeline also makes a video, Panel-By-Panel reads the text on the whole pages** (much faster than reading every panel) and saves it as `panel-text.json` next to the panels. Upscale carries it along, and Images To Video uses it instead of running Magi again (not when highlighting text boxes, which needs the boxes on each panel).
- Magi v1 and v3 were also measured. v1 found slightly different panels, and v3 was much slower (about 15–38 seconds per page) and marks every text as dialogue.
- Magi was trained on manga, so panels on western comics may be found a little less reliably.
- **License:** the Magi AI Model is free for personal, research, non-commercial and not-for-profit use only (see its [model page](https://huggingface.co/ragavsachdeva/magiv2)).

## Translate

`translate.py` (spec 01) works on whole pages, before Panel-By-Panel:

1. **Magi** finds the text boxes (`Magi.find_text_boxes`; for Japanese at 0.1, well below Magi's own 0.3, so fewer bubbles and captions are missed; for English and Spanish at 0.3, since its English reader makes up whole sentences for extra boxes with no text). Magi's "is this dialogue" flag is ignored: on Japanese pages it marks most dialogue as not dialogue. Boxes found twice become one, and boxes right next to each other in one speech bubble become one line.
2. **Reading:** Japanese with [Hayai OCR v2.7](https://huggingface.co/JustANormalTinkerer/hayai-ocr-v2.7-supernova) (pinned revision; it runs its own model code, and its tokenizer is built from `tokenizer.json` because its config is in the transformers 5 format). It read better than manga-ocr and was 3x faster on the test chapter. English and Spanish with Magi's own reader.
3. **Translating:** one request per page with the page image (each box outlined and numbered in red), the numbered lines, the previous page's lines and the series glossary (`translation-glossary.json` next to the chapters). The answer is JSON with every line number required, so none can be skipped. Ollama goes through its own HTTP API (with thinking off), Gemini and ChatGPT through the `openai` library, Claude through `anthropic` (with server-side fallback if it declines a page). The translator returns `""` for sound effects and signs, which are left as they are. **Line by line** (`translate_line_by_line`): PLaMo 3 Translate and TranslateGemma 4B are pure translators that can't follow rules or write JSON, so each line is sent alone in the model's own prompt format (PLaMo's PFML3 with up to 10 lines before it as context; TranslateGemma's documented prompt), without the page image. Lines with no letters aren't sent. PLaMo only knows Japanese to English (`only` in `OLLAMA_MODELS`, checked by `is_pair_supported`).
4. **Erasing:** a speech bubble is found as the light area around the box. The text in it is the letter-sized dark shapes chained to Magi's box (so furigana and text Magi's box cut off are included, but a drawing on a plain white panel, one big shape, isn't); it's filled with the bubble's color, and the outline is kept. The same text area is what's read in step 2. Two touching bubbles share one light area, so each line gets the part closest to its own box. A bubble at least half inside a box on the art (a sound effect drawn around it) stays its own line; a big white background the text is written on isn't a bubble. Big text on the art (letters over 4% of the page's height) is a sound effect or logo and is left alone, and so is text on the art with fewer than 2 letters (ド, "…": Magi and the OCR find these on a drawn TV screen too) and a "bubble" line with letters over 8% (a sound effect on a white wall or sky, which counts as a light area; erasing it would wipe the drawings in it), all in `is_left_alone`. The same text found twice (in its bubble and on the art) is lettered once (`remove_repeated_lines`), and a translation still in Japanese counts as empty; text on the art is lettered first, kept in its panel, and any bubble inside its box is put back. Each line in the request says about how many letters fit. Text not in a bubble is filled if the color around it is flat (letters just past Magi's box along the text, like a caption's last "…", go too), otherwise painted over by the manga LaMa (with spandrel).
5. **Lettering:** in capitals, word-wrapped (long words split at syllables with `pyphen`), with some padding, and shrunk until it fits: it never runs past its area (down to 6 px, where a word may be split anywhere as a last resort). On the art, the white outline counts toward the width. In a bubble, rectangles of six shapes (tall to wide) are tried around the point deepest inside it, and the text goes in the one it fits biggest in. Text on flat color outside a bubble gets an area grown only over that color, so it stops at a caption's border. On artwork it's black with a white outline.

Until one is picked, the model is `get_default_model`: the best suggested model that knows the languages and can run here: it fits the computer's memory (`get_ram_gb`, also on Windows) and is downloaded or has room to be (PLaMo 8B for Japanese to English, else TranslateGemma 12B, or their 8 GB picks). The Model dropdown in the settings lists, for Ollama, the suggested models in `OLLAMA_MODELS` (best first; ones that can't do the languages at the bottom, greyed out) grouped by the computer memory they're made for (8, 16 and 32 GB, three each, with a line saying what each is good and bad at), then any others installed (`list_installed_ollama_models`; a model the user downloaded with Ollama themselves can be picked, and gets the page request; the line under the list says it hasn't been tested in Panelyze); for the others the models the API key can use (`list_models`; tests stub both out in `conftest.py`). **Manage Ollama models** (folded under the Model list) downloads (`download_ollama_model`, through Ollama's `/api/pull`, progress in the Status view, Cancel at the top of the list) and uninstalls (`delete_ollama_model`, `/api/delete`, after a confirmation dialog that says how much space it frees) models. Pressing Translate with a model that isn't downloaded downloads it first, as part of the job (`TranslateView.download_model_if_needed`; Cancel stops it at once). A download needs its size plus 2 GB free (`get_room_for_model_error`): Ollama writes straight into `~/.ollama/models` with no unpacking or second copy. Sizes are in GB of 1,000,000,000 bytes, like ollama.com. A "too many requests" answer is waited out (20, 40, 60 s) before the job stops at the daily limit. A bubble line left empty is asked for once more, and dialogue ending in a letter gets a period.

Each chapter gets a `translation.json` (every box, its text and its translation), saved after every page so a cancelled run keeps what's done. Translating the chapter again with the same languages and model reuses it without asking the translator, so a line fixed by hand there is kept. `reading-direction.txt` is copied along. The glossary is kept in the series folder, or next to the chapter when only one chapter was picked; the Pipeline starts each run with an empty `2-translate` folder, so there the glossary only lasts for that run. The Ollama model list greys out models that clearly won't fit in the computer's memory (`is_too_big`), and after the first page the status line warns if Ollama could put less than 90% of the model on the graphics card (`get_ollama_gpu_share`), since the rest runs several times slower on the processor. With Ollama, Magi and Hayai are unloaded before translating (they hold about 3 GB), so they load again for each chapter (a few seconds).

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
