# Handoff: spec 01 (Translate raw Japanese pages)

How to start on another computer: open a Claude chat there and send it this one line:

> Read `specs/01-translate-japanese-pages-handoff.md` on the `01-translate-japanese-pages` branch of https://github.com/curlos/panelyze (if the repo isn't on this computer yet, read it with `gh api` or by cloning) and do what it says.

Everything below is for that Claude.

---

We're continuing spec 01 (Translate raw Japanese pages) in Panelyze, on another computer. The previous chats got too long, so this is where things stand (2026-11-23).

**First, set this computer up** (section "Set up this computer" below), telling me briefly what you do at each step. Then read `CLAUDE.md`, `specs/01-translate-japanese-pages.md` (§6 steps 0–20 say what was built and found, "Still to do" lists steps 21–25, §8 has my decisions), `benchmarks/translate.md` (every measured result, with comparison images) and the "Translate" section of `DEVELOPING.md`. Then tell me briefly that you're caught up, and wait for my questions. Don't change any code yet.

## The situation
- The work is on the branch `01-translate-japanese-pages` on GitHub, in **3 commits on top of `main`** (66 files: 28 edited, 38 new), with a **draft pull request** (#2) that I use to review it on GitHub. It is **not merged** into `main`.
- I only committed and pushed to move to this computer. I review in VS Code's Source Control, so the 3 commits must become **uncommitted, unstaged changes again** in this spec's worktree (`git reset origin/main`, which keeps every file as it is).
- After that reset, `git status` says the branch is behind `origin/01-translate-japanese-pages` by 3 commits. That's expected. **Never `git pull` here** (it brings the commits back) and never force-push. When I say the spec is finished, follow CLAUDE.md's "Finish" steps as usual (commit, merge into `main` in `panelyze-main`, push `main`), then close draft PR #2 (`gh pr close 2`) and delete the remote branch (`git push origin --delete 01-translate-japanese-pages`).

## Set up this computer
Work out first what's already here (the OS, whether `Github-Repos/panelyze/panelyze-main/` exists, Python, Ollama), and skip what's done. Ask me before anything big (installing Python packages into a new venv, downloading Magi's weights or Ollama models).

1. **`panelyze-main`** (the `main` branch, CLAUDE.md's layout): if it isn't there, `git clone https://github.com/curlos/panelyze.git panelyze-main` inside `Github-Repos/panelyze/`, and set it up as in `DEVELOPING.md` ("Set up"): the venv from `requirements-lock.txt` (Python 3.12, torch 2.14.1, transformers 4.57.6, `pyphen`, `anthropic`, `openai`), Magi's weights in `magi_model/`, a `.env` (I'll give you the keys; never print them), [Ollama](https://ollama.com), and an empty `test-chapter-cache/` folder.
2. **The spec's worktree**, from `panelyze-main`:
   ```
   git fetch origin
   git worktree add ../01-translate-japanese-pages 01-translate-japanese-pages
   cd ../01-translate-japanese-pages
   git reset origin/main
   ```
   `git status` should then list the 66 files as unstaged changes (the new ones untracked).
3. **Links to the big shared files**, as in CLAUDE.md. Mac: `ln -s ../panelyze-main/venv venv`, `ln -s ../../panelyze-main/magi_model/panels_fp16.safetensors magi_model/panels_fp16.safetensors`, `ln -s ../panelyze-main/test-chapter-cache test-chapter-cache`, `cp ../panelyze-main/.env .`. Windows (PowerShell, Developer Mode on): `cmd /c mklink /D venv ..\panelyze-main\venv`, `cmd /c mklink magi_model\panels_fp16.safetensors ..\..\panelyze-main\magi_model\panels_fp16.safetensors`, `cmd /c mklink /D test-chapter-cache ..\panelyze-main\test-chapter-cache`, `Copy-Item ..\panelyze-main\.env .`.
4. **Check:** the fast tests in the worktree (`venv/bin/python -m pytest -q` on a Mac, `.\venv\Scripts\python -m pytest -q` on Windows) should give **583 passed**. Tell me if anything differs; the code has only been run on the Mac so far, so Windows problems are worth writing down.
5. **Test chapters** go outside the repo, in `~/Documents/Panelyze/01-translate-japanese-pages/test-raws/` (the app's output folder for this worktree):
   - Dragon Tofu ch. 24 (Japanese and English) and Soul Anomaly ch. 1 (English, Spanish, Japanese): `benchmarks/scripts/translate/md_download.py <chapter id> <folder>`, with the ids and folder names in `benchmarks/test-chapters.md`.
   - Shachou ch. 3, official English: MangaDex (id in `benchmarks/test-chapters.md`).
   - **Shachou ch. 3, Japanese:** Niconico's reader (https://sp.manga.nicovideo.jp/watch/mg939870) draws its pages on canvases, so it's saved in the browser: open the chapter in Chrome, paste `benchmarks/scripts/translate/save-canvas-pages.js` into the console, and it scrolls through and downloads `shachou-ch3-ja.zip` (page-001.webp …); unzip it into `test-raws/shachou-ch3-ja/`. If Claude in Chrome is connected you can run it yourself; otherwise ask me to.
6. **Ollama models** (only when a test needs them, after asking me): check this computer's RAM first; the Windows PC has 32 GB RAM and an RX 6700 XT with 12 GB, so it's the one for step 22's 32 GB models.

## Where things stand
- Fast tests: 583 passed on the Mac. End-to-end (`-m e2e`): 16 passed, 1 skipped (a site that only sometimes blocks), on Nov 23 before the last settings changes.

## What the pipeline does
Magi finds text boxes (threshold 0.1 for Japanese, 0.3 for English and Spanish) and panels → boxes joined per speech bubble, repeats of the same text joined → Hayai OCR v2.7 reads Japanese (Magi's English reader reads English and Spanish) → the translator → erase → letter in capitals (Bubble Sans by default), always inside its bubble or box (deterministic code, shrinks to 6 px rather than overflow).

Two ways of asking a translator:
- **Whole page** (chat models, Gemini, ChatGPT, Claude): one request per page with the numbered page image and numbered lines, the answer as JSON.
- **Line by line** (pure translators: PLaMo, TranslateGemma 4B): one request per line in the model's own prompt format (PLaMo's PFML3 with up to 10 earlier lines as context; TranslateGemma's documented prompt), no image, lines with no letters not sent.

Left alone, whatever the translator says (`is_left_alone`): big text on the art (letters over 4% of the page height, not a flat caption), text on the art with fewer than 2 letters (ド, ッ, "…"), and a "bubble" line with letters over 8% (a sound effect on a white wall or sky). Speech bubbles otherwise always win and always end with punctuation; a bubble line left empty is asked for once more (page mode only).

## Models and settings (my decisions)
- **Ollama stays the default translator** (free, private, no limits). The line under Translator points to Gemini, ChatGPT or Claude for the best quality.
- **Nine suggested models, three per RAM size, best first** (`OLLAMA_MODELS` in `translate.py`):

| RAM | Models (on disk) |
|---|---|
| 8 GB or more | PLaMo 3 Translate 2B (1.8 GB, Japanese to English only), Qwen3-VL 4B (3.3 GB), TranslateGemma 4B (3.3 GB) |
| 16 GB or more | PLaMo 3 Translate 8B (5.3 GB, Japanese to English only), TranslateGemma 12B (8.1 GB), Ministral 3 8B (6.0 GB) |
| 32 GB or more | PLaMo 3 Translate 31B (19.5 GB), TranslateGemma 27B (17 GB), Ministral 3 14B (9.1 GB): **not tested** |

- **The default model** (until the user picks one) is the best model for the picked languages that fits the RAM and is downloaded or has room to be (`get_default_model`): Japanese to English → PLaMo 8B (8 GB: PLaMo 2B); anything else → TranslateGemma 12B (8 GB: Qwen3-VL 4B). 32 GB computers get the 16 GB picks until step 22. A picked PLaMo is dropped when the languages change to a pair it can't do.
- **Model list:** headings "FOR 8 GB RAM OR MORE", sizes say "on disk", models that can't do the languages are grey and at the bottom of their section, and a line under the list says what the picked model is good and bad at (or "Downloaded with Ollama outside Panelyze, so it hasn't been tested here." for the user's own models).
- **Manage Ollama models** (folded under the Model list): download (needs the size + 2 GB free; progress in the Status view; Cancel), uninstall (a confirmation dialog that says how much space it frees), the selected model in teal, and "Models you download yourself with Ollama (ollama pull) show up here too."
- **Pressing Translate with a model that isn't downloaded downloads it first**, as part of the job (Raw Output says so, Status shows the GB, Cancel stops it at once, Ollama keeps what's downloaded). Never just from picking or switching.
- Sidebar order: From, To, honorifics, Translator, API key, Model, Send the page image, Manage Ollama models, Font.
- Gemini free tier only when I say so; it allows about 20 requests a day (about one chapter).
- No character list or name sheet in this spec, no furigana reading: names stay the model's guess; a per-series name sheet goes in spec 38. A better reader for English and Spanish is spec 36.
- UI text: full sentences end with a period, short fragments don't (decided per line).

## Results so far (details and images in `benchmarks/translate.md`)
- Japanese to English mistakes, three chapters: PLaMo 8B 4 / 2 / 2, TranslateGemma 12B 4 / 3 / 3, Ministral 8B 8 / 3 / –. PLaMo 8B is 3–4 times faster (9–29 s a page against 38–62 s). Gemini and blind Claude: 0–1.
- Other pairs (Soul Anomaly): TranslateGemma 12B ~1 (Spanish↔English) and ~4 (Japanese to Spanish); TranslateGemma 4B ~11 on Spanish to English, because Magi's reader garbles Spanish ("jme estas Mirando") and a model that can't see the page can't fix it.
- Lettering checked zoomed in on every Shachou page: nothing past a bubble, caption box or panel border.

## Known weak spots (not fixed)
- A real shout in a big speech bubble could pass the 8% rule and stay in Japanese (check on more pages in step 21).
- Text erased from grey screentone leaves a flat white rectangle.
- Local models break names and genders (spec 38); English and Spanish reading is weak (spec 36).
- Models the user downloads themselves get the page request: models Ollama can't force JSON from (gemma4, qwen3.5) stop with a clear message; pure translators not in the list (e.g. Hy-MT2) translate poorly.
- Memory is counted in 1024³ bytes (as the computer does) while model sizes are in 1,000,000,000 (like ollama.com): about 7% stricter, changes no tier.

## Next steps
Steps 21–25 in the spec's "Still to do": the full Shachou ch. 3 run (and the sound-effect sizes), the 32 GB models on the Windows PC (also check `get_ram_gb`, the graphics-card warning and downloads there), the by-hand checks in the real app, the review subagent and `-m e2e`, then I decide whether the spec is finished.

## How to work with me
- Follow CLAUDE.md: plan first, small and simple changes, a short summary at the end; after changes, the review subagent (rule 10). **Don't commit or push** unless I say so (the branch was pushed only so I could switch computers; see "The situation").
- Short, plain answers, tables, and real measured numbers; say plainly what wasn't tested.
- **Reference translations come only from a blind subagent** that gets the numbered page images (`benchmarks/scripts/translate/make_blind.py`) and the line list, never the official English (the main chat has seen it).
- Run Ollama tests one model at a time, `ollama stop <model>` after each, and check memory first (old processes once made a model 6 times slower).
- Never open Finder (or Explorer) windows from tests. Never print API keys from `.env`. Never add "Co-Authored-By: Claude" to commits.
- Test scripts: `benchmarks/scripts/translate/` (`run_translate.py`, `run_pair.py`, `reletter.py`, `run_by_hand.py`, `compare.py`, `make_blind.py`, `md_download.py`, and `save-canvas-pages.js` for the browser; each says how to use it at the top).
