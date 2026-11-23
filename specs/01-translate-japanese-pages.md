# 01. Translate raw Japanese pages to English

Roadmap item #1. **Built 2026-11-22** (see §6 for what was found while building, and where the code differs from the first plan). Researched 2026-11-19, **checked again 2026-11-21** (claims, prices, models and code references), and **re-checked against the code after spec 17 was merged (2026-11-22)**.

Related: [#36 better text reading](36-better-text-reading.md) (a stronger reader for English/Spanish sources) · [#38 character sheets](38-character-sheets.md) (could feed the glossary's character names)

## 1. Summary

A new **Translate** tool, as its own tab and a Pipeline step between **Download** and **Panel-By-Panel**. It works on whole **pages**:

1. Magi finds the text boxes (it already does this for the video).
2. A Japanese OCR model reads each box.
3. A vision LLM gets **the page image with each box numbered** plus the OCR text, and returns natural English for each number.
4. The Japanese is erased.
5. The English is lettered into the bubble.

Panel-By-Panel then cuts up the translated pages as usual. The aim is **quality first**: English that reads like a good scanlation, not word-for-word machine translation.

**Why:** to read chapters that only exist in Japanese.

### Who does what

| Step | Who | What comes out |
|---|---|---|
| 1. Find the text | **Magi** (already in the app, local) | A box (pixel position) for each text, dialogue vs sound effect, reading order |
| 2. Read the Japanese | **Hayai OCR v2.7** (local, about 600 MB; manga-ocr in the first plan, see step 3) | The Japanese in each box |
| 3. Translate | **The LLM** (Claude, ChatGPT, Gemini or Ollama) | **Text only:** one English line per box number, as JSON |
| 4. Erase | **Python** (Pillow, plus LaMa for text on artwork) | The page with the bubbles emptied |
| 5. Letter | **Python** (Pillow + Bubble Sans or another bundled font) | The finished page |

No LLM ever edits the image or sees coordinates. The numbers drawn on the copy of the page tell it which line is which, and Python already knows where each numbered box is (from Magi). The numbers are only on the copy that's sent, never on the saved pages.

**What gets sent:**

```
[the page image, with a small number drawn at each text box]

1: なにしてるの？
2: べつに…
```

**What comes back:** `{"1": "What are you doing?", "2": "Nothing..."}`, plus `new_glossary` (see §4).

## 2. Is it doable?

**Yes.**
- Every hard part is already solved by other open-source tools, and two of the pieces are already in the app:
  - Magi's text boxes.
  - `spandrel`, which can already load the LaMa inpainting model.
- The research also shows that a vision LLM translating **one page at a time with the page image** beats line-by-line machine translation.
- **Reading the Japanese:** this is the part that can't reuse Magi. Magi's own reader is an English model (`microsoft/trocr-base-printed` in its config), so a Japanese OCR model is needed. Magi's box **finder** should work on Japanese (it was trained mostly on Japanese manga), which step 2 checks.
- **The weakest part will be lettering**, as in every automatic tool. It will look like a solid fan translation, not a professional release.

## 3. What's already true (claims checked)

| Claim (ROADMAP / HANDOFF / benchmarks) | Check | Status |
|---|---|---|
| "Magi already gives the position of every text box" | `predict_detections_and_associations` returns `texts`, `is_essential_text` (dialogue vs sound effects) and also `text_character_associations` (who says which line). Used today in `find_and_read_dialogue` (`magi.py:917`, the call is at `magi.py:934`). | ✅ |
| Magi can't read Japanese, so a separate reader is needed | The Magi v2 config has `ocr_pretrained_processor_path: microsoft/trocr-base-printed`, an English reader. Step 2 runs it on one Japanese page to show this. | ✅ |
| manga-ocr (`kha-white/manga-ocr-base`, about 450 MB) handles vertical text and furigana | Latest 0.1.16, July 19, 2026, Apache-2.0. | ✅ |
| …and it loads with the app's `transformers` (4.34 then, 4.57.6 after Phase 0) | It's a plain `vision-encoder-decoder` (ViT + BERT), so it very likely does. But its tokenizer needs **fugashi + unidic_lite** (not installed), unless it's loaded with `do_word_tokenize=False`. Not run yet. `transformers` is pinned at 4.34 because Magi needs it. | ⚠️ likely, not tested |
| manga-ocr is the best option | **No, but it's still the right pick here.** JMangaBench v1.3.3 (Oct 27, 2026), character error rate:<br>• Hayai v2.7 Supernova: 1.80% (Apache-2.0, 158M)<br>• manga-ocr-base-CPT-flex: 1.50% (made by the benchmark's own authors)<br>• PaddleOCR-VL-For-Manga: 1.99% (0.9B)<br>• Baberu OCR v1.2: 3.04% (Apache-2.0, 115M)<br>• manga-ocr: 4.81%<br>Hayai needs SigLIP2 and custom model code (`trust_remote_code`), so transformers 4.49+ (done in Phase 0). CPT-flex has no stated weights license and its own package. Baberu has an ONNX build (needs `onnxruntime`, not installed). See the next row for why OCR quality matters less than it looks. | ⚠️ out of date |
| (New) Do LLMs read vertical Japanese badly? | The paper that said so (arXiv 2511.15059) tested GPT-5, GPT-4.1 and Gemma 3. On JMangaBench crops, **Claude Opus 5.5 reads with 0.59% CER**, better than every OCR model. So with a cloud engine, OCR mistakes get fixed by the model looking at the image. OCR quality matters mostly for Ollama. | ✅ (new) |
| Ollama + `qwen3:8b` installed, free and local | Running: Ollama 0.40.16, `qwen3:8b` 5.2 GB. **But qwen3:8b is text-only:** it can't see the page. On JP-TL-Bench JA→EN it wins 64.6%, against 97.4% for Gemini 3 Flash; `shisa-v2.1-qwen3-8b`, same size, wins 73.7%. | ⚠️ works, but lowest quality |
| (New) A free local model that can see the page | **`qwen3-vl:8b`** on Ollama: 6.2 GB, takes images (needs Ollama 0.12.7+). Not in JP-TL-Bench, so step 4 measures it. | ✅ (new) |
| Claude / ChatGPT / Gemini also get the page image | All three take images. Claude Opus 5.5 sees a 1127×1600 page (Shachou) at full size: about **2,400 image tokens**. | ✅ |
| (New) A Claude Pro / ChatGPT Plus / Gemini subscription can be used | **No.** Chat subscriptions don't include API use; each API is billed separately per use. Anthropic banned third-party apps from using Pro/Max logins (Feb 2026); later reports of a separate credit pool conflict. Free routes: a **Gemini free-tier key** (Google trains on it) and **Ollama**. | ✅ (new) |
| Erase with the bubble color; LaMa if too rough | Fine for plain bubbles. LaMa is needed for text on artwork. `spandrel` 0.4.2 (installed) has a `LaMa` architecture (checked: it imports). A manga-tuned big-LaMa exists (dreMaz "AnimeMangaInpainting", MIT on Hugging Face, about 200 MB). | ✅ |
| Comic Neue font (free, OFL license) | It's a Google Font under the OFL, so it's safe to bundle. Scanlations mostly use **CC Wild Words** (paid, $49+) or **Anime Ace** (free for personal use only, not for redistribution), so neither can be bundled. | ✅ |
| Sugoi is Windows-only | **Not anymore:** `Sugoi-14B-Ultra-GGUF` (Apache-2.0, a Qwen2.5-14B fine-tune) runs on Ollama on a Mac. Q4_K_M is 9 GB, tight on the 16 GB M1. It's trained on game text, can't see images, and its own card says to keep the context to about 10 lines. | ⚠️ out of date |
| Example: "Shachou ch. 63, while English stops at 62" | MangaDex has **no Japanese chapters** of Shachou. English has ch. 1–61 and 70, so 62–69 are missing. Raws would have to come from somewhere else. | ⚠️ out of date |
| A test raw on MangaDex | **Dragon Tofu ch. 24**: Japanese (21 pages, `a87c5bcd-2bea-46eb-84d8-a7cc167fa881`) **and** an English version of the same chapter (21 pages, `99dd891b-1ce7-4032-9cd1-5a09f890b579`) to compare with. Checked again on the API. | ✅ |
| HANDOFF: "HEAD is `ed0fbb5`" | HEAD is `1dd0645` (main `e77fbb1`) | ⚠️ out of date |

**What the research says about translation quality:**

| Finding | Source |
|---|---|
| **A whole page plus the page image** is the best unit. Line by line is worst. More previous pages, or the whole volume, did **not** help. Numbering the bubbles works as well as passing the OCR text. | Lippmann et al., COLING 2025 |
| A 46-page test (Oct 10, 2026), counting clear mistakes:<br>• **Claude Opus 5.5: 0**<br>• **Gemini 3.8 Flash: 0**<br>• GPT-6 Sol: 1<br>• GPT-6 Luna: 3<br>• Claude Sonnet 5.5: 5<br>• Claude Haiku 5.5: 9<br>Every model got the page, the 2 previous pages and the same instructions, at **low or no thinking**. Some mistakes (a patient's gender) could only be fixed by **looking at the picture**: both GPT-6 models wrote "him" for a woman. Opus, Gemini and Sonnet also kept a country dialect in English. Only 35 of the 46 pages were Japanese (*Give My Regards to Black Jack* vol. 1); the rest were Korean and Chinese. | Serifu blog (a vendor; one run, one judge) |
| A blind A/B with and without the page image (same model, 29 pages): the image won **63%** of decisive votes, at about **3× the input tokens**. | MangaDock issue #1141 (Oct 2026) |
| Small local models fall well behind frontier models on JA→EN, especially on hard lines. Best local-size scores: Ministral-3-14B 90.7%, shisa-v2.1-unphi4-14b 78.5%, shisa-v2.1-qwen3-8b 73.7%, Qwen3-8B 64.6% (Ministral-3-8B, Qwen3-VL and Gemma 4 weren't tested) | JP-TL-Bench (Jan 2026) |
| DeepL and Sugoi translate one line at a time, with no picture and no memory of names or voice | Several tool comparisons |

### What makes it read naturally

| Do | Why |
|---|---|
| One page per request, with the page image and numbered bubbles | COLING 2025 and the MangaDock A/B |
| A frontier model: Claude Opus 5.5 or Gemini 3.8 Flash | 0 mistakes, and they kept each character's voice |
| Send the previous page's Japanese and English as text, plus a glossary with a **voice note per character** (pronouns, speech style) | Keeps names and voices the same from page to page and chapter to chapter |
| Ask for "an official English release": free to reword, short lines that fit a bubble | Serifu's instructions |
| Tell it a sentence can run across two bubbles: split it naturally, don't translate each half alone | A real mistake in the Serifu test |
| Tell it to check the picture for who's speaking and their gender | 2 of the Serifu mistakes needed the picture |
| **No** second "polish" pass | No evidence it helps, and it doubles the cost |

## 4. Recommended approach and rejected alternatives

**Recommended:**
- Magi boxes, then **Hayai OCR** (manga-ocr in the first plan), then a **numbered page image + OCR text** sent to **Claude Opus 5.5** (default), **ChatGPT** (GPT-6 Sol), **Gemini 3.8 Flash** (cheap, free tier) or **Ollama** (free, local).
- Erase with a **color fill**, or **LaMa** on artwork.
- Letter in **Bubble Sans** (one of six bundled free fonts), auto-fitted.

| Choice | Picked | Rejected (why) |
|---|---|---|
| Build our own vs call an existing tool | **Build a small `translate.py`** that reuses Magi, spandrel and Pillow | **manga-image-translator:** GPL-3, a separate 15 GB Docker or Python setup, no Claude, and its author calls its lettering "barely functional"<br>**BallonsTranslator:** has a headless mode and macOS support, but it's GPL-3 (Panelyze is MIT), a whole second app to install, and it only works with OpenAI-compatible translators<br>**MangaTranslator** (meangrinch): Apache-2.0, a real CLI with folder/CBZ batches, supports Claude. But it's a second Python app with its own torch (2.14.1 vs our 2.5.1), so it needs its own environment.<br>**Koharu:** good, MIT/Apache, Apple silicon, Claude, and now Baberu/Hayai OCR and local Gemma 4 / Qwen 3.8. Its README shows a GUI and an MCP server but no batch CLI. Worth recommending to the user for hand-fixing pages. |
| Reading the Japanese | **Hayai OCR v2.7** (built; manga-ocr was the first plan, see step 3), with the LLM told to fix OCR mistakes by looking at the image | **Baberu OCR:** better scores; try its ONNX build in step 3 (needs `onnxruntime`) and switch if it reads better<br>**Hayai v2.7 / manga-ocr-CPT-flex:** best scores, but Hayai needs a newer `transformers` than Magi allows, and CPT-flex has no stated license<br>**PaddleOCR-VL:** 0.9B and a different library stack<br>**LLM reads the image alone:** Claude Opus 5.5 now reads better than any OCR, but Ollama models still need OCR, and OCR text helps match lines to numbers |
| Translator (default) | **Claude Opus 5.5:** 0 mistakes, best-sounding English, about **$1.10 a chapter** | **Claude Sonnet 5.5 / Haiku 5.5:** 5 and 9 mistakes<br>**DeepL / Google / Sugoi:** line by line, no image, no character voice |
| Translator (cheap) | **Gemini 3.8 Flash:** 0 mistakes, about **$0.20 a chapter**. Has a free tier, but **Google trains on free-tier data**. | — |
| ChatGPT | **Included** (GPT-6 Sol: 1 mistake, about $0.55 a chapter). It's the most popular, and it costs almost nothing to add (same `openai` library). | — |
| Translator (free, local) | **Ollama**, with a Model dropdown (no box to type a name in, step 15). Default **`translategemma:12b`** (steps 16–17). Nine suggested models, three for each size of computer memory (8, 16 and 32 GB+, see §8 "Local models"), downloaded and removed from the app (step 18). Thinking is turned off (it's slow and the 0-mistake test didn't use it). | Sugoi-14B: 9 GB, and no image<br>shisa-v2.1-qwen3-8b: not on Ollama<br>gemma4 and qwen3.5: Ollama can't force their answer format ("structured output is unavailable")<br>Hy-MT2 (Tencent): more mistakes than PLaMo; the 1.8B repeats until Ollama aborts |
| DeepSeek | Left out for now | No manga quality data. Can be added later through the same `openai` code. |
| Paying | The user's own **API key** for each service (`.env` or Settings) | **The user's Claude Pro / ChatGPT Plus login:** not allowed for third-party apps (Anthropic banned it in Feb 2026)<br>**Driving a chat window:** breaks easily, and against the terms<br>**Later idea:** call the user's own installed `claude -p` / Codex CLI, once the current terms are checked |
| How many SDKs | `anthropic` for Claude, plus `openai` for **ChatGPT, Gemini and Ollama**: all three have OpenAI-compatible endpoints that take images | One SDK per provider (3–4 new libraries) |
| Translation unit | **One page per request**, with that page's image (a setting can turn the image off for speed), the **previous page's Japanese and English** as plain text (cheap), and a **glossary** | Several page images per request: costs more, and didn't help in the paper<br>One request per bubble: worst quality<br>Sending box coordinates: not needed, the numbers on the image do the matching |
| Erasing | **Mask = dark strokes inside the box, slightly widened.** If the ring around it is one flat color (a bubble), fill it with that color (instant, perfect). Otherwise, **manga LaMa** through spandrel on a crop around the box. | Filling the whole rectangle: erases bubble outlines and art<br>LaMa on everything: slower, and can smudge a white bubble<br>Stable Diffusion / FLUX inpainting: heavy, redraws the art, and research-only licenses |
| Lettering | A **Font** dropdown of six bundled **OFL** fonts (default **Bubble Sans**; also Comic Neue Bold, McLaren, Patrick Hand, DynaPuff, Bangers; under 1 MB together). **Only the bundled fonts can be used** (no custom font file). | **CC Wild Words** (the standard for official English manga, Comicraft, $49 a style): needs a separate app license to ship inside an app<br>**Anime Ace:** no redistribution<br>The free "wildwords.ttf" copies in scanlation packs: unlicensed<br>A custom font file setting: dropped by the user (2026-11-22) |
| Lettering area | The area is the **inside of the bubble**, found by spreading out from the box over the bubble color, since Japanese boxes are tall and narrow. Word-wrapped, shrunk until it fits, centered. On artwork: black text with a white outline. | Lettering only inside Magi's narrow box: unreadable 1-word lines |
| Languages | **From:** Japanese (Hayai OCR), English and Spanish (Magi's own reader already reads Latin letters; it may drop accents like ñ or á, which the LLM fixes from the picture). **To:** English and Spanish. The LLM handles any pair; only the reader and the lettering depend on the language. | Chinese / Korean sources: need another reader (Baberu reads Chinese; nothing picked for Korean). Japanese / Chinese / Korean as the target: needs a CJK font and vertical lettering. Both later. |
| Sound effects | **Left in Japanese** (`is_essential_text` = false is skipped) | Translating them: hard even for the best tools |
| Model downloads | Hayai OCR + LaMa (about 800 MB) download **automatically** on first use, after checking there's enough free disk (only when they're not downloaded yet). **Ollama models are downloaded and removed from the app** (changed 2026-11-23, step 18): "Manage Ollama models" in the Translate settings, only after a click, when there's the model's size plus 2 GB free. Ollama itself has to be installed by the user. | Only the `ollama pull` command (the first plan): users don't know where models are kept or how to remove them |

**Prompt design (the part that makes it read like a scanlation):**

| Rule | How |
|---|---|
| Natural English, not literal | System prompt: "Translate like an official English manga release. Short, natural lines that fit a speech bubble. Keep each character's voice (rough, polite, childish, dialect → light English equivalent). Never add or drop meaning." |
| Mapping lines to bubbles | Draw small numbers on a copy of the page at each box (in Magi's reading order). Send that image, plus `1: <OCR text>`, `2: …`. The model must return exactly one English line per number, as JSON. Use structured output: Claude's `output_config.format`, or `response_format` for the OpenAI-compatible APIs. |
| Sentences across bubbles | "A sentence may continue into the next bubble. Translate it as one sentence and split the English naturally between those numbers." |
| OCR mistakes | "The Japanese came from OCR and may have mistakes; trust the image when they disagree." |
| Who is speaking | "Check the picture for who is speaking and their gender." Optional hint from Magi's `text_character_associations` ("2 and 5 are the same character"). |
| Honorifics | From Japanese: **Keep** (-san, -chan, senpai, the scanlation style). From other languages: localized, no setting needed |
| Names and terms stay the same | The model also returns `new_glossary` (name → English spelling, plus a one-line voice note per character: pronouns, how they talk). It's saved as `translation-glossary.json` in the **series** folder and sent with every page, so it carries on to the next chapter. |
| Effort | Claude Opus 5.5 at its default effort (`medium`). No setting for it (kept simple); the 0-mistake test ran at low or no thinking, so `low` could be tried once there's a key. |

## 5. Files to change and functions to reuse

| File | Change |
|---|---|
| `translate.py` (new, about 750 lines as built) | `translate_chapter(image_folder, image_names, output_folder, settings, glossary_folder)`:<br>• `get_lines(page, magi_boxes)`: boxes per speech bubble (`get_bubble`, `group_by_bubble`, `get_text_box_in_bubble`)<br>• `read_japanese` (Hayai) / `read_latin` (Magi)<br>• `get_numbered_page_image(page, boxes)`<br>• `translate_page(…)`, with `ask_ollama`, `ask_openai_compatible`, `ask_claude`<br>• `erase_in_bubble` / `erase_box` (LaMa: `paint_over_with_lama`)<br>• `fit_and_draw_text(page, area, text, font_path, color)`<br>Writes the translated pages (same file names) and `translation.json` (boxes, original text, translation) after every page. **Copies `reading-direction.txt`** next to the pages, like `UpscaleImagesView.py:196`, so Automatic reading direction (spec 27) still works. (`panel-text.json` isn't copied: Panel-By-Panel hasn't run yet at this point.) |
| `magi.py` | Add `find_text_boxes(chapter_pages)` (about 15 lines): the "Finding the text" half of `find_and_read_dialogue` (`magi.py:917`), wrapped in `run_with_cpu_fallback`. Optionally make `find_and_read_dialogue` call it. |
| `gui_classes/TranslateView.py` (new, about 80 lines) and `gui_classes/SettingsTranslate.py` (new, about 150 lines) | A `JobView` subclass like `UpscaleImagesView`:<br>• `process_image_folder` calls `translate_chapter`<br>• `next_view_name = "MagiPanelByPanelView"` and `get_next_tab_input_directory` (same as `UpscaleImagesView.py:43`), so Panel-By-Panel's input is filled in<br>• `before_job`: checks the key, or that Ollama is running and has the model<br>• Calls `self.raise_if_cancelled()` before each page, so the Cancel button (spec 17) stops it between pages<br>• Settings on the right: From and To dropdowns, engine dropdown, Model dropdown (step 15), honorifics (Japanese only), API key field (hidden text), Font dropdown, **"Send the page image"** checkbox (on by default; turning it off is faster but the model can't check who's speaking or fix OCR mistakes; hidden for text-only models) |
| `gui_classes/PipelineView.py` | Add `"Translate"` to `PIPELINE_STEPS` (right after `"Download"`), `PIPELINE_STEP_FOLDER_NAMES` (renumbered: `2-translate`, `3-panel-by-panel`, `4-upscale-images`, `5-images-to-video`), `FINAL_RESULT_DESCRIPTIONS`, `get_settings_review` (one row: engine + model) and `step_views` in `run_step`. `get_next_step_input_directory` needs **no logic change**: its last case (`<output>/<input folder name>`) already fits. Only its last comment ("Panel-By-Panel … and Upscale Images") gets Translate added. |
| `gui_classes/AppBar.py`, `gui.py` | Add the tab to `TAB_NAMES` / `TAB_ICONS` (`ft.Icons.TRANSLATE`), create `TranslateView` in `create_views`, and add it to `set_views_narrow`. The shortcuts renumber themselves. The downloader keeps filling Panel-By-Panel's input (`MangaDexDownloaderView.py:304`), since most downloads are already English. |
| `default_settings.py` | `OUTPUT_SUBFOLDERS["output_directory_translate"] = "Translated"`, plus defaults: `translate_from: "japanese"`, `translate_to: "english"`, `translate_keep_honorifics: True`, `translate_engine: "ollama"`, `translate_models: {}` and `translate_api_keys: {}` (one per translator; a missing model uses `DEFAULT_MODELS`, a missing key the `.env`), `translate_font: "Bubble Sans"`, `translate_send_page_image: True` |
| `requirements.txt`, `requirements-lock.txt`, `build_mac_app.sh` | `anthropic`, `openai` (no `fugashi` or `onnxruntime`: Hayai needs neither). Bundle the six fonts in `assets/fonts/`, each with its `OFL.txt`. Plus the Phase 0 upgrade. |
| `tests/test_translate.py` (new) and `tests/test_pipeline.py` | Fake engines, masks, text fitting and the Pipeline step. In test_pipeline (and one line in test_e2e), the lines that use the folder names change for the renumbered folders (after spec 17: 12 in test_pipeline, 4 in test_every_input, 3 in test_e2e). |
| README, DEVELOPING, ROADMAP, HANDOFF | Docs, plus credits: Hayai OCR (Apache-2.0), LaMa (Apache-2.0) / the manga LaMa (MIT), the bundled fonts (OFL). Note that a chat subscription doesn't cover the API, and where to get a free Gemini key. |

**Reused as they are:**
- `JobView.start_job` (finding the chapter folders, progress, errors)
- `get_magi()`, plus `get_chapter_pages_image_numpy_array` and `run_with_cpu_fallback` in magi.py
- `report_progress` (ProgressPanel)
- `utils_load_dotenv` (keys `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, like the Azure key)
- `save_folder_as_cbz`
- `spandrel.ModelLoader`, the way `janai.py` loads models
- The model-download pattern from janai.py (to `~/Library/Application Support/Panelyze/`)

## 6. Steps (todo list)

**Phase 0: modern Magi stack** (user request, 2026-11-22: "make Magi and its packages modern while staying on Magi v2")
- [x] 0. Upgrade torch 2.5.1 → **2.14.1**, torchvision 0.20.1 → 0.29.2, transformers 4.34.0 → **4.57.6** (newest 4.x; 5.x drops things Magi's code uses), huggingface-hub 0.17.3 → 0.36.2, tokenizers 0.14.1 → 0.22.2, safetensors 0.4.5 → 0.8.0, timm 1.0.12 → 1.0.31, coremltools 8.1 → 9.0. Why both: transformers ≥ 4.50-ish refuses to load Magi's `.bin` weights with torch older than 2.6. Checked first in a scratch venv, then installed in the shared venv on purpose:
  - Magi v2 on 2 Dragon Ball pages: **identical** panel boxes, same text boxes, same text read (4.34, 4.49 and 4.57).
  - Fast tests: 513 passed. End-to-end (`-m e2e`): 14 passed, 1 skipped (Azure, no key); the one failure (comix.to download) fails the same way on the old stack, so it's the site, not the upgrade.
  - "Best" upscaler: Core ML conversion works with torch 2.14.1 + coremltools 9.0 (coremltools warns torch 2.14 is untested), and its output matches PyTorch's (max difference 0.007).
  - Emotion model (voice styles): identical scores.
  - Why it matters here: newer transformers makes **Hayai OCR v2.7** (needs SigLIP2, transformers 4.49+ and < 5) usable, so step 3 compares it too.


**Phase 1: prove the quality on one chapter (no GUI)**
- [x] 1. Download Dragon Tofu ch. 24 (Japanese) and ch. 24 (English, for comparison) with the existing downloader, into the spec's folder. Added both to `benchmarks/test-chapters.md`. *(21 pages each, into `~/Documents/Panelyze/01-translate-japanese-pages/test-raws/`.)*
- [x] 2. Add `magi.find_text_boxes`. On the Japanese pages, check for missed or merged bubbles and that `is_essential_text` separates dialogue from sound effects. Also run Magi's own reader on one Japanese page to confirm it can't read it. **Found:**
  - Magi's boxes are good (the big sound effects get no box at all), but **`is_essential_text` is useless on Japanese**: it marked almost all dialogue as "not dialogue" (0 or 1 of 4–5 boxes a page). So Translate ignores it and sends every box; the LLM returns `""` for sound effects and signs.
  - At Magi's own threshold (0.3) it **missed some bubbles** (2 of 6 on page 5). At **0.2** it finds more (123 boxes instead of 83 on the chapter), with some duplicates and some boxes on artwork; duplicates are joined, and boxes on artwork come back empty from the LLM. One bubble (だって…あいつが始めたんだ) is still missed at 0.2: a known limit. **Lowered to 0.1** while testing Shachou ch. 3 page 1, which needed it for two captions (問題は人間関係, まだまだ社員との間に距離がある); it also finds the title logo and the author's name, which the prompt tells the LLM to skip.
  - Magi's own reader on Japanese: `'#01-1st?!'`. It can't read it, as expected.
- [x] 3. Pick the Japanese reader. **Hayai OCR v2.7** (newly possible after Phase 0) instead of manga-ocr: on the 83 boxes, they differed on 17, and Hayai was right where manga-ocr wasn't (`3位の差`, `DRAGON TOFU`, `CH.24/END`); manga-ocr also **made up text** on two crops of plain artwork (`そうなのですから`, `そうですね`). Hayai read all 83 in 7 s, manga-ocr in 21 s. Its tokenizer config is in the transformers 5 format, so the tokenizer is built from `tokenizer.json` (5 lines); the revision is pinned since it runs its own model code. Baberu wasn't tried (lower score than Hayai on the same benchmark, and it would need `onnxruntime`). **Enlarging crops 2× didn't help**: 7 of 83 differed, 6 of them boxes of artwork with no text; Hayai already enlarges small crops itself (up to 4×). So no enlarging, and no `fugashi`.
- [x] 4. `translate_page` for **Ollama** and **Gemini** (both real) and **Claude / ChatGPT** (fake). Numbered image, JSON out, glossary. Ollama goes through its own HTTP API (`/api/chat`) so it can send `think: false` and a JSON schema. **Found:** with a list of `{number, text}`, qwen3-vl once answered with an empty list; the schema now has every line number (`"1"`, `"2"`, …) as a **required** field, so none can be skipped.
- [x] 5. Erasing. **Changed from the plan:** per **speech bubble**, not per box. The bubble is the light area around the box; all the text inside it (the holes in that area, so also furigana and text Magi's box cut off) is filled with the bubble's color, and the outline is kept. Boxes right next to each other in one bubble become one line (Magi split 何を from 配ってるのかな?). Two touching bubbles share one light area, so each line gets the part closest to its own box. Text not in a bubble (e.g. a caption joined to the page's white margin): flat color fill, including letters just past Magi's box along the text (a caption's last "…"), with the lettering area grown only over that flat color so it stops at the caption's border; or the manga LaMa (it loads in spandrel once its weights get a `model.` prefix; about 1 s a box on the CPU).
- [x] 6. Lettering: in capitals, word-wrapped, with padding, shrunk until it fits a **rectangle inside the bubble's shape** (the bubble's box crossed the outline on round bubbles), centered. Rectangles of six shapes (tall to wide) are tried around the point deepest inside the bubble, and the text goes in the one it fits biggest in (a tall Japanese-shaped area made English small); white text on a dark bubble; black with a white outline on artwork.
- [x] 7. Save the pages + `translation.json`. **Quality and speed test on pages 1–5:** see "Quality test results" below.

**Phase 2: in the app**
- [x] 8. `TranslateView` tab + `SettingsTranslate` + defaults, plus the key / Ollama / disk checks (the RAM warning is a line under the Translator dropdown).
- [x] 9. Pipeline step + review row + folder names (`2-translate`, then 3–5).
- [x] 10. Claude (`anthropic`, with `fallbacks: "default"` if it declines a page) and ChatGPT / Gemini through the `openai` library. Not run for real: no Claude or OpenAI key; Gemini ran for real.
- [x] 11. Re-runs: a page whose original text matches the saved `translation.json` reuses its translation without asking the LLM (tested: a line fixed by hand is kept).
- [x] 12. Tests (`tests/test_translate.py`, 40 tests, plus an end-to-end test that also checks no Japanese is left in the translated bubbles), docs (README, DEVELOPING, HANDOFF, ROADMAP), credits, `build_mac_app.sh` (fonts, `anthropic`, `openai`) and a self-test check. Also: the reading models are unloaded before Ollama runs (they hold about 3 GB, and the 16 GB Mac went deep into swap with both loaded).
- [x] 13. **Models too big for the computer** (added 2026-11-22): the Ollama model list greys out models whose download + 2 GB is more than 70% of the computer's memory (`is_too_big`). After the first page, Ollama says how much of the model is on the graphics card (`/api/ps`); under 90%, the status line says it's slow and suggests a smaller model. That second check is what works on Windows, where the graphics card's own memory counts (e.g. 12 GB on an RX 6700 XT) and `get_ram_gb` can't read the memory (it returns None there instead of crashing).
- [x] 14. **Lettering and text finding, from Shachou ch. 3 pages 1–3** (added 2026-11-22): (a) Magi found the two speech bubbles inside page 2's big ゴゴゴ sound effect, but joining repeated boxes merged them into it, so they were never translated and LaMa painted over them and a face. Now a bubble at least half inside a box on the art stays its own line, and a big white panel background the text is written on joins the text on the art (page 3's thought captions). (b) Only dark pixels count as letters, a ring around a bigger space (another bubble's outline) doesn't, a bubble inside the light area is never erased or lettered over, and the letter size is capped by the shapes in Magi's box (a block of columns made it 3× too big, so the text search spread over a whole panel). (c) Text on the art that isn't in a bubble or flat caption, with letters over 4% of the page's height, is a sound effect or logo and is left alone; a line in a bubble never is (changed in step 16d: not when its letters are over 8%). Text on the art is lettered first and any bubble inside its box is put back, so bubbles always win. Its area is the Japanese box, 10% wider, kept in its panel (Magi's panels). (d) Long words split at syllables with `pyphen` (INTER-PERSONAL, new package), text that always fits (the font shrinks as far as 6 px rather than run past its bubble; a word moved to a new line can still be split; the white outline on the art counts toward the width), a thicker white outline on the art, and each line in the request says about how many letters fit (`~40 letters`).
- [x] 15. **Model list and usage limits** (added 2026-11-22): the Translate settings have one **Model** dropdown and no box to type in. Ollama: the suggested models (greyed out when too big) plus any others installed; Gemini, ChatGPT and Claude: the models the API key can use, fetched with the key (`list_models`; Gemini's own model list, OpenAI's and Anthropic's `models.list`), or the default model and a hint until a key is entered. An API key can't show its daily quota or usage (only the provider's website does). A "too many requests" answer is waited out (20, 40, 60 s) since Gemini's free tier allows about 5 requests a minute; still refused after that, it's the daily limit (about 20 requests a day for gemini-3.6-flash on the free tier, so roughly a chapter a day), and the job stops with a plain message. Also: a line in a speech bubble left empty by the translator is asked for once more, and dialogue that ends in a letter gets a period.

- [x] 16. **Lettering checks on two chapters** (2026-11-23). Shachou pages 1–3 for all 11 models, zoomed in on every tight spot: no letters past a bubble, caption box or panel border. Dragon Tofu ch. 24 pages 1–5 found four problems, all fixed: (a) one bubble found twice, once "in the bubble" and once "on the art", was lettered twice on top of itself (the chapter title, "…GUILD WON"): two lines whose boxes overlap by half and whose text is almost the same become one (`remove_repeated_lines`, keeping the one in a bubble); (b) a translation still in Japanese (a lone ド) drew "▯": it now counts as empty; (c) lone marks on the art (ド, ッ, 死, あ, "…" read off a drawn TV screen, "〜") got lettered as "Doh", "Tsu", "A" or erased the TV picture: text on the art with fewer than 2 letters is left alone; (d) the big ウオオオオオ and ド sound effects sit on a white wall and sky, which count as "light areas", so they were treated as speech bubbles, never skipped, and erasing them wiped the drawings on the wall and the crowd's stands: a "bubble" line with letters over 8% of the page's height is left alone (the biggest real dialogue in the tests was 6%; the sound effects were 12–31%). All in `is_left_alone`. Before/after sheets: `~/Documents/Panelyze/01-translate-japanese-pages/open-issues.jpg` and `open-issues-after-fix.jpg`.
- [x] 17. **Second-chapter model test** (2026-11-23, Dragon Tofu ch. 24 pages 1–5, 21 real lines, official English in `test-raws/dragon-tofu-ch24-en/`; comparisons in `dragon-tofu-test/compare/`). See "Local model results" below. TranslateGemma 4B, "broken" in the page request (it copied the Japanese back), works when asked in its own prompt format.
- [x] 18. **Models by computer memory, line by line, and downloads from the app** (user decisions, 2026-11-23): the default is `translategemma:12b`; the suggested list is three models for each of 8, 16 and 32 GB+ computers, shown under headings in the Model list ("FOR 16 GB RAM OR MORE", and each size says "on disk" so it isn't taken for RAM; "free and runs on this computer" is said once, in the Translator choice and at the top of Manage Ollama models), each with a line saying what it's good and bad at; PLaMo is greyed out (and refused before a job starts) for anything but Japanese to English. **Line-by-line mode** (`translate_line_by_line`) for the pure translators PLaMo and TranslateGemma 4B: each line alone in the model's own prompt format (PLaMo's PFML3 with up to 10 earlier lines as context; TranslateGemma's documented prompt), no page image, lines with no letters not sent, no second ask for empty lines. Any Japanese copied into a translation is dropped (the whole line only when no letters are left). The left-alone rules only apply to new translations, so a line fixed by hand in `translation.json` is kept. The "next line as context" idea was dropped: neither prompt format has a place for text after the line, and putting it in the input gets it translated too. **Manage Ollama models** (folded under the Model list): every suggested model by tier with its size and whether it's downloaded, Download (needs the size + 2 GB free; progress in the Status view, Cancel at the top of the list, other buttons off meanwhile; a cancelled download is kept by Ollama and carries on next time) and Uninstall (a dialog asks to be sure and says how much space it frees; "Removed PLaMo 3 Translate 8B. 5.3 GB of disk space freed." after), plus any other downloaded models, the free disk space and where the models are kept (`~/.ollama/models`). Checked for real: a download, a cancel at 0.3 GB (Ollama stops; its leftover file used 309 MB), and removing Hy-MT2-1.8B. Also: dropdown choices fill the box, so long model names no longer push the ▼ out of it.

- [x] 19. **Language pairs** (2026-11-23, Soul Anomaly ch. 1 pages 2–5, full color, ~31 lines; English is the original, the Spanish and Japanese are the publisher group's own versions; comparisons in `language-test/compare/`). See "Language-pair results" below. Found and fixed: (a) for English and Spanish pages, Magi's English reader makes up a whole sentence for an extra box with no text ("I have a few more of the" lettered on a roof, "The first time I was in the middle of the day" squeezed next to a bubble), so those pages use Magi's own threshold (0.3) instead of 0.1: every made-up line went and every real line stayed (only a lone "!" and one copy of a door sign were lost); (b) English words on a Japanese page lost their spaces ("Yuichi'sroom"): only spaces next to Japanese characters are removed now.

- [x] 20. **Default model and settings layout** (user decisions, 2026-11-23): the Ollama default is no longer one fixed model but the best suggested model for the picked languages that can run on the computer (`get_default_model`): it fits the memory, and it's downloaded already or there's room to download it (size + 2 GB). TranslateGemma 4B isn't greyed out for English and Spanish pages (it scored ~11 on Spanish to English); Qwen3-VL 4B simply ranks above it, so it's only the default when Qwen3-VL can't run: Japanese to English → PLaMo 8B (8 GB computers: PLaMo 2B), any other pair → TranslateGemma 12B (8 GB: Qwen3-VL 4B); 32 GB+ computers get the 16 GB pick until the 32 GB models are tested. It follows the languages until the user picks a model, and a picked model that can't do new languages (PLaMo after switching to Spanish) is dropped for the default. Memory is now read on Windows too (`GlobalMemoryStatusEx`). Ollama stays the default translator (free, private, no limits); the line under Translator points to Gemini, ChatGPT or Claude for the best quality. The Model list is best first in each section (8 GB: PLaMo 2B, Qwen3-VL 4B, TranslateGemma 4B), models that can't do the languages go to the bottom of their section, and disabled choices are drawn grey by hand (Flet draws them like any other). The sidebar is From, To, honorifics, Translator, API key, Model, Send the page image, Manage Ollama models, Font. In Manage Ollama models the sections have space between them and the selected model is in teal ("· selected"). The Pipeline review shows the model's name instead of its Ollama ID. **Pressing Translate with an Ollama model that isn't downloaded downloads it first** (decided 2026-11-23, for accessibility: even the smallest is 1.8 GB, but people shouldn't have to find "Manage Ollama models" first): a line in the Raw Output says so, the Status view shows "Downloading … before translating" with the GB done, Cancel stops it at once ("Cancelling the download...") and Ollama keeps what's downloaded for next time; it's never downloaded just by picking or switching models (`TranslateView.download_model_if_needed`).

**Still to do** (2026-11-23; the handoff prompt for the next chat is [01-translate-japanese-pages-handoff.md](01-translate-japanese-pages-handoff.md), and the results are in [benchmarks/translate.md](../benchmarks/translate.md)):
- [ ] 21. **Full-chapter run:** Shachou ch. 3 (22 Japanese pages) with the Japanese-to-English default (PLaMo 8B) and with TranslateGemma 12B: total time, comparison images for a few pages, and the height of every sound effect's letters against the 8% rule (and any big real shout near it).
- [ ] 22. **32 GB models on the Windows PC** (32 GB RAM, RX 6700 XT 12 GB): PLaMo 31B, TranslateGemma 27B and Ministral 3 14B on Shachou ch. 3 pages 1–3 and Dragon Tofu ch. 24 pages 1–5. Also check there that memory is read (`get_ram_gb`), the graphics-card warning (`get_ollama_gpu_share`), and the model downloads. Then decide whether 32 GB+ computers get the 32 GB picks as the default.
- [ ] 23. **By hand in the real app:** Translate with a model that isn't downloaded (it should download first, with progress and Cancel), Uninstall from Manage Ollama models (the dialog), and the user's own Spanish check of the Soul Anomaly comparisons.
- [ ] 24. **Review subagent** (CLAUDE.md rule 10) on everything since the last review (steps 19–20 and the settings changes), then the end-to-end tests (`-m e2e`).
- [ ] 25. The user decides whether the spec is finished; then the "Finish" steps in CLAUDE.md.

**Quality test results** (2026-11-22, Dragon Tofu ch. 24 pages 1–5, 19 real lines; side by side with the official English in `~/Documents/Panelyze/01-translate-japanese-pages/quality-test/compare.html`). A **mistake** is a wrong meaning, wrong person, broken name, or a line number left in the text. **Junk** is lettering put on something that isn't dialogue (a sign, a stray mark) or Japanese left in the lettering.

| Translator | Mistakes | Junk | Time a page (translator only) | Notes |
|---|---|---|---|---|
| Claude (Opus 5.5 in Claude Code, by hand, the user's Pro plan) | 0 | 0 | – | Reference only; not how the app works |
| Gemini 3.6 Flash (free tier) | **0** | 0 | ~20 s | Stand-in: 3.8 and 3.7 Flash answered "high demand, try later" (503) all afternoon, then 3.8 hit the free tier's usage limit (429), now explained in plain words in the app. Only model with every name right ("Chanbo and Daito's guild") and the crowd ("look at all these people") |
| **`ministral-3:8b`** (6.0 GB) | **3** | 1 | ~28 s | **Best local model → new Ollama default.** Mistakes: "an amazing person" (the crowd), "Sit down, loser!" and "Guild of Losers" for Chanbo |
| `ministral-3:14b` (9.1 GB) | 3 | 1 | ~42 s | Same count, 1.5× slower, tight in 16 GB |
| `qwen3-vl:8b-instruct` without the image | 4 | 2 | ~13 s | |
| `qwen3-vl:8b-instruct` with the image | 5 | 2 | ~28 s | The image cost 2× the time and didn't help this model here |
| `qwen3:8b` (text only) | 6 | 2 | ~12 s | |
| `HY-MT1.5-7B` (text only) | 9 | 2 | ~10 s | Put "2:", "5:" in front of a page's lines |
| `gemma4:12b` | – | – | – | Ollama 0.40.16 says "structured output is unavailable" for it, so it can't be used; removed from the list |

- Every local model got わーすごい人だね wrong ("an amazing person" instead of "a lot of people") and most broke a name (Chanbo, Daito, Jundonia). Gemini and Claude didn't. So for the best English, a cloud translator is still clearly better; Ollama is "free and understandable".
- Times were measured while the Mac was deep in swap (other apps open), so they're rough; the whole job adds about 40 s a chapter for Magi and Hayai.
- One bubble (だって…あいつが始めたんだ) is missed by Magi for every translator, so it stays in Japanese.

**Shachou ch. 3 page 1** (2026-11-22, 13 real lines; comparisons in `~/Documents/Panelyze/01-translate-japanese-pages/shachou-test/comparison-page-1-run3.jpg`). With `ministral-3:8b` after the fixes above and "always translate narration and caption boxes and the chapter title" in the prompt: every caption and the chapter title translated, 1 clear mistake ("Reports are always late!" for 遅いのよ報告が!, "Your report is late!"), and the author's name translated ("Slip Knight") even though the prompt says to skip it (the same model skipped it on another run). `qwen3-vl:8b-instruct` translated the title logo and the author's name, and had 2 mistakes. Magi has no "title" or "author" label, so leaving those alone is up to the LLM.

**Local model results** (2026-11-23, one run each; a mistake as above, counted against the official English; translator time only, on the 16 GB M1):

| Model | Size | Sees page | Shachou ch. 3 p. 1–3 (~34 lines) | Dragon Tofu ch. 24 p. 1–5 (21 lines) | s/page (Dragon Tofu) |
|---|---|---|---|---|---|
| Claude (blind subagent, reference) | cloud | yes | 0 | 1 ("Great Sword Guild" for Daito's guild) | – |
| Gemini 3.6 Flash (free tier) | cloud | yes | 0 | 0 (step 7) | ~10–20 |
| **PLaMo 3 Translate 8B** (line by line) | 5.3 GB | no | 4 | **2** (only local model to get "so many people"; "Sit cross-legged!" for "Chanbo, sit down!") | **9** |
| **translategemma:12b** | 8.1 GB | yes | 4 | 3 ("what amazing people", "Jun'dunia", dropped "Gorilla!") | 39 |
| ministral-3:8b | 6.0 GB | yes | 8 | 3 ("Sit down, loser!", "that guy's amazing") | 36 |
| qwen3.5:9b | 7.6 GB | yes | 4 (the only one with the boss as "she") | – | – |
| gemma4:12b | 7.7 GB | yes | 5 | – | – |
| PLaMo 3 Translate 2B (line by line) | 1.8 GB | no | 5 | – | 10 (Shachou) |
| translategemma:4b (line by line) | 3.3 GB | no | – | 5 ("Junonia", "Katanas Guild", "That's also why we came in third") | 6 |
| Hy-MT2-7B (line by line) | 4.6 GB | no | 6 | – | – |
| qwen3-vl:4b | 3.3 GB | yes | 7 | – | – |
| ministral-3:3b | 3.0 GB | yes | 11 | – | – |

- Every local model breaks some names (石墨 = Ishizumi → "Ishiboku", "Stone", "graphite") and most call Shachou's female boss "he".
- PLaMo only knows Japanese and English. TranslateGemma knows 55 languages, so it's the pick for Spanish (from or to).
- **To check in the full-chapter runs:** how tall the sound effects' letters are on more pages (the 8% rule for "bubble" lines), and whether a real shouted line in a big speech bubble (like One Piece's "PEOPLE'S DREAMS… DON'T EVER END!!", or a short big shout like え!? whose size is guessed from few characters) ever gets near 8%; if one does, the rule needs a second test (e.g. only when the white area isn't enclosed like a bubble).

**Language-pair results** (2026-11-23, Soul Anomaly ch. 1 pages 2–5, one run each; mistakes counted by Claude against the official versions, so the Spanish ones are for the user to check by eye; translator seconds a page):

| Pair | TranslateGemma 4B (8 GB, line by line) | Qwen3-VL 4B (8 GB, sees page) | TranslateGemma 12B (16 GB, sees page) | PLaMo 8B (16 GB, line by line) |
|---|---|---|---|---|
| Spanish → English | **~11**, 6 s ("Are you Miranda?" for "¿Me estás mirando?", "Okay, everyone, please be quiet."): it can't see the page to fix the reader's mistakes | ~3, 26 s | **~1**, 35 s | – (Japanese only) |
| English → Spanish | ~3, 5 s ("¿Quién está sufriendo de gripe…?" from the reader's "Who the flu") | ~3, 27 s | ~1, 34 s | – |
| Japanese → Spanish | ~6, 6 s (names: "Hayato Shiryu") | ~5, 28 s | ~4, 41 s ("¿Quieres venir conmigo?" for "go wake Yuichi") | – |
| Japanese → English | ~6, 6 s | ~6, 26 s | ~3, 40 s ("can you come with me?") | **~2**, 16 s (the only one to get "go wake Yuichi up") |

- **Reading English and Spanish is the weak step**: Magi's reader is trained on English, so Spanish comes out as "Yuna, episodes for favor desperate a yuichi" (¿Puedes por favor despertar…) and "jme estas Mirando" (¿Me estás mirando?). Models that see the page fix most of it; line-by-line models can't. A better Latin reader is spec 36.
- PLaMo 8B is again the best for Japanese to English; TranslateGemma 12B is the best for every other pair. Full-color pages were found, erased and lettered as well as black-and-white ones.

## 7. How to test it

| Test | How |
|---|---|
| Fast tests (no internet) | Fake engines return fixed JSON. Check: one English line per box, the honorifics setting reaches the prompt, the glossary is saved and sent again, a white bubble is filled with pure white, text over art goes to LaMa (faked), text always fits inside its area, `reading-direction.txt` is copied next to the translated pages, the Ollama check gives a clear message when the model is missing, and the Pipeline order and folders are right. |
| Real end to end (`-m e2e`) | Ollama on 3 pages of Dragon Tofu ch. 24: pages are saved, no Japanese is left in the bubbles, and Panel-By-Panel runs on the result. |
| Quality check (by eye) | Pages 1–5, side by side with the official English ch. 24, using the existing `Compare upscalers.html` idea: Japanese, each engine's English and the official English. Engines: every local candidate (text-only and vision), `qwen3-vl:8b-instruct` with and without the image, Gemini 3.8 Flash (free tier), and Claude Code by hand as a reference. Time each page too. Count clear mistakes as the Serifu test did (wrong meaning, wrong person, broken name, missing line). |
| Spanish (by the user) | A few pages of a Spanish chapter from MangaDex to English, and an English chapter to Spanish, with Ollama. The user checks these by eye, since they read both. |
| Speed (measure, don't guess) | Time per step on 21 pages: Magi boxes, OCR, LLM, erasing, lettering. One run at a time, fresh process. |
| Claude / ChatGPT for real | Once the user adds `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`: the same chapter, with the cost read from `response.usage` |

## 8. Size, value, risks, open questions

| | |
|---|---|
| **Size** | **Large.** As built: about 750 lines in `translate.py`, 230 in the tab and its settings, 450 of tests, and about 60 changed lines in existing files (plus the Phase 0 upgrade). |
| **Value** | **High.** It opens up every untranslated chapter, and its output also feeds Panel-By-Panel and the video. Magi's English reader can read the English we letter. |
| **Speed (estimate, not measured)** | 21 pages:<br>• Magi boxes about 10–20 s<br>• OCR about 30 s<br>• Claude Opus about 10–20 s a page (sometimes over a minute), one page after another (each page uses the previous one), so **about 4–7 min**. Gemini Flash is about 15 s a page, GPT-6 Sol about 7 s; Ollama about 20–90 s a page on the M1 depending on the model (see "Local models").<br>• Erasing + lettering: a few seconds, plus about 1 s per LaMa crop. |

**Local models** (the suggested list, `OLLAMA_MODELS`; sizes from ollama.com and Hugging Face, 2026-11-23). A model is greyed out when its size + 2 GB is more than 70% of the computer's memory (`is_too_big`), so each tier fits computers with at least that much memory:

| For computers with | Japanese to English (line by line, no page image) | Any language, line by line | Any language, sees the page |
|---|---|---|---|
| **8 GB+** | PLaMo 3 Translate 2B (1.8 GB) | TranslateGemma 4B (3.3 GB) | Qwen3-VL 4B (3.3 GB) |
| **16 GB+** | PLaMo 3 Translate 8B (5.3 GB, fastest and fewest mistakes) | – | **TranslateGemma 12B (8.1 GB, default)**, Ministral 3 8B (6.0 GB) |
| **32 GB+** (not tested yet; the 32 GB Windows PC can) | PLaMo 3 Translate 31B (19.5 GB) | – | TranslateGemma 27B (17 GB), Ministral 3 14B (9.1 GB) |

All are free to download and use. Licenses: TranslateGemma under Google's Gemma terms, Ministral and Qwen under Apache 2.0, PLaMo under PFN's own PLaMo Community License (https://plamo.preferredai.jp/info/plamo-community-license-en; its text couldn't be read automatically, so check its commercial-use terms before relying on it).

A chapter of 21 pages is then about 3 minutes with PLaMo 8B and 14 minutes with TranslateGemma 12B (translator time), against about 5 minutes with Gemini or Claude.

**Cost per chapter** (20 pages; about 4,000 input tokens a page = 2,400 image + about 1,500 text, and about 2,000 output tokens a page including thinking; estimate, rechecked 2026-11-21):

| Engine | Price per 1M tokens (in / out) | About per chapter |
|---|---|---|
| Claude Opus 5.5 | $4 / $20 | **$1.10** |
| Claude Sonnet 5.5 | $2 / $10 | $0.55 |
| GPT-6 Sol | $2 / $10 | $0.55 |
| Gemini 3.8 Flash (until Dec 31, 2026; doubles on Jan 1, 2027) | $0.75 / $3.75 | **$0.20** ($0.40 from Jan) |
| Gemini free tier | free, with daily limits; Google trains on it | $0 |
| Claude Haiku 5.5 / GPT-6 Luna | $0.10 / $0.50 | $0.03 |
| Ollama (local) | free | $0 |

**Risks:**
- **Lettering looks automatic:** odd bubble shapes, long English lines. Mitigation: shrink to fit, plus six fonts to pick from.
- **Magi may mark some Japanese dialogue as non-dialogue, or miss bubbles,** so they would stay untranslated. Step 2 checks this.
- **The modern stack (Phase 0)** may break something not covered by the tests (e.g. the PyInstaller build). `build_mac_app.sh` is rebuilt in step 12.
- **Model names and prices change fast** (Gemini's price doubles on Jan 1, 2027). The Model dropdown lists the models the API key can use (fetched from the service), so new models show up without a code change.
- **Claude Opus 5.5 can refuse a page** (`stop_reason: "refusal"`). Fall back with `fallbacks: "default"` (beta `server-side-fallback-2026-07-01`), or skip the page with a message.
- **Small computers:** the 8 GB models (PLaMo 2B, TranslateGemma 4B, Qwen3-VL 4B) make more mistakes than the 16 GB ones. The list greys out what won't fit, and the cloud engines work on any computer.
- **Disk:** 18 GB free (96% full). New models add about 800 MB (Hayai OCR about 600 MB + LaMa 200 MB), plus 5–9 GB for each Ollama model tested (29 GB free on 2026-11-22, so they're pulled and removed one at a time).

**Later (not in this spec):** character names and genders are the local models' weakest point (Shachou ch. 3: 石墨 came out "Ishibu", "Stone"; the boss became "he"). Reading furigana (the reading いしずみ printed by a name's first appearance) was considered and dropped: manga print it only sometimes, usually once, so it fails for a single chapter from the middle of a series. A per-series name and character sheet (names, readings, genders) built once and sent with every page fits better as part of spec 38 (character sheets). A blind Claude reference got both right from the page image alone.

**Decisions (from the user, 2026-11-21 and 2026-11-22):**

| Question | Decision |
|---|---|
| Engines in v1 | Claude, ChatGPT, Gemini and Ollama |
| Default engine | **Ollama** (free, local, no limits; kept over the cloud models on 2026-11-23: they need an account and a key, cost money or allow about a chapter a day). Model: **the best one for the computer and the languages** (step 20; `translategemma:12b` for a day, `ministral-3:8b` before, `qwen3-vl:8b-instruct` the first guess). Gemini free tier only for light testing (pages 1–5), to stay inside its daily limits |
| Honorifics | **Keep** them when translating from Japanese; **localize** for other source languages (the setting only shows for Japanese) |
| Languages | **From:** Japanese, English, Spanish. **To:** English, Spanish (see §4, "Languages") |
| Pipeline place and folders | Translate goes **right after the downloader**, and the folders are renumbered: `1-download`, `2-translate`, `3-panel-by-panel`, `4-upscale-images`, `5-images-to-video`. Every step stays optional, so Download → Translate alone gives normal pages to read like a regular manga. **Translate stays before Upscale** (decided 2026-11-22): Magi and the cloud models shrink big pages anyway, manga-ocr reads each crop at 224×224, and upscaling whole pages first costs time and tokens. Only small text crops may be enlarged inside Translate (step 3) |
| Font | Ship **all six free OFL fonts** in a Font dropdown: **Bubble Sans (default**, closest to the Wild Words look), Comic Neue Bold, McLaren, Patrick Hand, DynaPuff and Bangers (for shouts). **Only these bundled fonts**, no custom font file (decided 2026-11-22). No separate title font in v1. All six have the Spanish characters (¿ ¡ á é ñ); previewed 2026-11-22 |
| Japanese raws | The user finds them. Since spec 17 the Download tab also imports `.cbz` / `.zip` / `.pdf` files and downloads from page URLs, comix.to and the Internet Archive, so raws from any of those work. Dragon Tofu ch. 24 is still used for Phase 1 |
| Quality test | `qwen3:8b`, `qwen3-vl:8b`, Gemini free tier and Claude Code by hand |

## 9. Sources

- Lippmann et al., *Context-Informed Machine Translation of Manga using Multimodal LLMs* (COLING 2025): https://arxiv.org/html/2411.02589v2
- Serifu, *Best AI Model for Manga Translation in 2026: Six Models Tested on 46 Pages* (Oct 10, 2026): https://serifu.net/blog/best-ai-model-for-manga-translation · same test on DEV: https://dev.to/hx23840/best-llm-for-translation-i-tested-six-models-on-46-manga-pages-a5h
- MangaDock, page image A/B test (Oct 2026): https://github.com/Slow-Inc/MangaDock/issues/1141
- Text-only vs image-aware judges for manga translation (Oct 2026): https://arxiv.org/html/2610.17908
- JP-TL-Bench (Jan 2026): https://arxiv.org/html/2601.00223v1
- Manga translation tools compared (2026): https://www.kitsutl.com/blog/manga-translation-tools-comparison-2026
- Vertical Japanese text and multimodal LLMs: https://arxiv.org/html/2511.15059v1
- JMangaBench_Read (OCR leaderboard, v1.3.3): https://github.com/muscgab/JMangaBench_Read
- manga-image-translator: https://github.com/zyddnys/manga-image-translator
- BallonsTranslator: https://github.com/dmMaze/BallonsTranslator
- MangaTranslator: https://github.com/meangrinch/MangaTranslator
- Koharu: https://raw.githubusercontent.com/koharu-rs/koharu/main/README.md
- manga-ocr: https://pypi.org/project/manga-ocr/ · tokenizer config: https://huggingface.co/kha-white/manga-ocr-base/blob/main/tokenizer_config.json
- Baberu OCR: https://huggingface.co/genshiai-daichi/baberu-ocr
- Hayai OCR v2.7 Supernova: https://huggingface.co/JustANormalTinkerer/hayai-ocr-v2.7-supernova
- Fonts (all OFL): Bubble Sans https://github.com/abayemes/bubblesans · Comic Neue, McLaren, Patrick Hand, DynaPuff, Bangers: https://github.com/google/fonts/tree/main/ofl · Wild Words pricing: https://fontspring.com/fonts/comicraft/wildwords
- Manga LaMa: https://huggingface.co/dreMaz/AnimeMangaInpainting · IOPaint: https://github.com/Sanster/IOPaint
- Sugoi 14B Ultra GGUF: https://huggingface.co/sugoitoolkit/Sugoi-14B-Ultra-GGUF
- Ollama models: https://ollama.com/library/qwen3-vl · https://ollama.com/library/ministral-3 · https://ollama.com/library/gemma4 · https://ollama.com/demonbyron/HY-MT1.5-7B
- Claude vision token cost: https://platform.claude.com/docs/en/build-with-claude/vision · Claude prices: claude-api skill model table (cached 2026-10-06)
- Claude subscription use in other apps: https://code.claude.com/docs/en/legal-and-compliance · https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access
- OpenAI prices: https://developers.openai.com/api/docs/pricing
- Gemini prices: https://aistudio.google.com/docs/pricing · free-tier data use: https://ai.google.dev/gemini-api/docs/logs-policy
- MangaDex API (chapter checks for Shachou and Dragon Tofu): https://api.mangadex.org
