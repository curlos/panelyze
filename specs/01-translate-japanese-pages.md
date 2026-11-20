# 01. Translate raw Japanese pages to English

Roadmap item #1. This is a plan only: nothing in the app has changed yet. Researched 2026-11-19.

## 1. Summary

A new **Translate** tool, as its own tab and a Pipeline step between **MangaDex Downloader** and **Panel-By-Panel**. It works on whole **pages**:

1. Magi finds the text boxes (it already does this for the video).
2. A Japanese OCR model reads each box.
3. A vision LLM gets **the page image with each box numbered** plus the OCR text, and returns natural English for each number.
4. The Japanese is erased.
5. The English is lettered into the bubble.

Panel-By-Panel then cuts up the translated pages as usual. The aim is **quality first**: English that reads like a good scanlation, not word-for-word machine translation.

**Why:** to read chapters that only exist in Japanese.

## 2. Is it doable?

**Yes.**
- Every hard part is already solved by other open-source tools, and two of the pieces are already in the app:
  - Magi's text boxes.
  - `spandrel`, which can already load the LaMa inpainting model.
- The research also shows that a vision LLM translating **one page at a time with the page image** beats line-by-line machine translation.
- **Reading the Japanese:** this is the part that can't reuse Magi. Magi's own reader is an English model (`microsoft/trocr-base-printed` in its config), so a Japanese OCR model is needed.
- **The weakest part will be lettering**, as in every automatic tool. It will look like a solid fan translation, not a professional release.

## 3. What's already true (claims checked)

| Claim (ROADMAP / HANDOFF / benchmarks) | Check | Status |
|---|---|---|
| "Magi already gives the position of every text box" | `predict_detections_and_associations` returns `texts`, `is_essential_text` (dialogue vs sound effects) and also `text_character_associations` (who says which line). Used today in `magi.py:510`. | ✅ |
| Magi can't read Japanese, so a separate reader is needed | The Magi v2 config has `ocr_pretrained_processor_path: microsoft/trocr-base-printed`, an English reader | ✅ |
| manga-ocr (`kha-white/manga-ocr-base`, about 450 MB) handles vertical text and furigana | It's still the standard. Latest 0.1.16, July 2026, Apache-2.0. | ✅ |
| …and it loads with the app's `transformers` 4.34 | It's a plain `vision-encoder-decoder` (ViT + BERT), so it very likely does. But its tokenizer needs **fugashi + unidic_lite** (not installed), unless it's loaded with `do_word_tokenize=False`. Not run, since this task can't install anything. | ⚠️ likely, not tested |
| manga-ocr is the best option | **Not anymore.** On JMangaBench, character error rates are:<br>• Baberu OCR v1.2: 3.04% (Oct 2026, Apache-2.0, 115M, same size)<br>• PaddleOCR-VL-For-Manga: 1.99% (0.9B)<br>• manga-ocr: 4.81%<br>On handwritten text, Baberu is much better (67% vs 48% exact). Baberu has its own model code, so it may not work with transformers 4.34; it also has an ONNX version. | ⚠️ out of date |
| Ollama + `qwen3:8b` installed, free and local | Running: Ollama 0.40.16, `qwen3:8b` 5.2 GB. **But qwen3:8b is text-only:** it can't see the page. On JP-TL-Bench JA→EN it wins 64.6%, against 97.4% for Gemini 3 Flash; `shisa-v2.1-qwen3-8b`, same size, wins 73.7%. | ⚠️ works, but lowest quality |
| Claude / ChatGPT / Gemini also get the page image | All three take images. Claude Opus 5.5 sees a 1127×1600 page (Shachou) at full size: about **2,400 image tokens**. | ✅ |
| Erase with the bubble color; LaMa if too rough | Fine for plain bubbles. LaMa is needed for text on artwork. **New finding:** `spandrel` 0.4.2 (already installed) has a `LaMa` architecture. A manga-tuned big-LaMa exists (dreMaz "AnimeMangaInpainting", MIT on Hugging Face, about 200 MB). | ✅ |
| Comic Neue font (free, OFL license) | It's a Google Font under the OFL, so it's safe to bundle. Scanlations mostly use **CC Wild Words** (paid, $49+) or **Anime Ace** (free for personal use only, not for redistribution), so neither can be bundled. | ✅ |
| Sugoi is Windows-only | **Not anymore:** `Sugoi-14B-Ultra-GGUF` (Apache-2.0, a Qwen2.5-14B fine-tune) runs on Ollama on a Mac. Q4_K_M is 9 GB, tight on the 16 GB M1. It's trained on game text, can't see images, and its own card says to keep the context to about 10 lines. | ⚠️ out of date |
| Example: "Shachou ch. 63, while English stops at 62" | MangaDex has **no Japanese chapters** of Shachou. English has ch. 1–61 and 70, so 62–69 are missing. Raws would have to come from somewhere else. | ⚠️ out of date |
| A test raw on MangaDex | **Dragon Tofu ch. 24**: Japanese (21 pages, `a87c5bcd-2bea-46eb-84d8-a7cc167fa881`) **and** an English version of the same chapter (`99dd891b-1ce7-4032-9cd1-5a09f890b579`) to compare with. A chapter link downloads in that chapter's own language. | ✅ (new) |
| HANDOFF: "HEAD is `ed0fbb5`" | HEAD is `b44fbac` | ⚠️ out of date |

**What the research says about translation quality:**

| Finding | Source |
|---|---|
| **A whole page plus the page image** is the best unit. Line by line is worst. More previous pages, or the whole volume, did **not** help. Numbering the bubbles works as well as passing the OCR text. | Lippmann et al., COLING 2025 |
| A 46-page manga test (Oct 2026), counting clear mistakes:<br>• **Claude Opus 5.5: 0**<br>• **Gemini 3.8 Flash: 0**<br>• GPT-6 Sol: 1<br>• GPT-6 Luna: 3<br>• Claude Sonnet 5.5: 5<br>• Claude Haiku 5.5: 9<br>Some mistakes (a patient's gender) could only be fixed by **looking at the picture**. Every model got the page, the 2 previous pages and the same instructions. | Serifu blog (a vendor; one run) |
| Small local models fall well behind frontier models on JA→EN, especially on hard lines | JP-TL-Bench (Jan 2026) |
| DeepL and Sugoi translate one line at a time, with no picture and no memory of names or voice | Several tool comparisons |

## 4. Recommended approach and rejected alternatives

**Recommended:**
- Magi boxes, then **manga-ocr**, then a **numbered page image + OCR text** sent to **Claude Opus 5.5** (default), **Gemini 3.8 Flash** (cheap) or **Ollama** (free).
- Erase with a **color fill**, or **LaMa** on artwork.
- Letter in **Comic Neue Bold**, auto-fitted.

| Choice | Picked | Rejected (why) |
|---|---|---|
| Build our own vs call an existing tool | **Build a small `translate.py`** that reuses Magi, spandrel and Pillow | **manga-image-translator:** GPL-3, a separate 15 GB Docker or Python setup, no Claude, and its author calls its lettering "barely functional"<br>**BallonsTranslator:** has a headless mode and macOS support, but it's GPL-3 (Panelyze is MIT), a whole second app to install, and it only works with OpenAI-compatible translators<br>**Koharu:** good, MIT/Apache, Apple silicon, Claude. But it has no CLI or headless mode (only a GUI and an MCP server). Worth recommending to the user for hand-fixing pages. |
| Reading the Japanese | **manga-ocr**, with the LLM told to fix OCR mistakes by looking at the image | **Baberu OCR:** better scores, but custom model code; try it in step 1 and switch if it loads<br>**PaddleOCR-VL:** 0.9B and a different library stack<br>**LLM reads the image alone:** frontier models still do worse on vertical Japanese (arXiv 2511.15059), and Ollama's qwen3:8b can't see images |
| Translator (default) | **Claude Opus 5.5:** 0 mistakes, best-sounding English, about **$1.10 a chapter** | **Claude Sonnet 5.5 / Haiku 5.5:** 5 and 9 mistakes<br>**DeepL / Google / Sugoi:** line by line, no image, no character voice |
| Translator (cheap) | **Gemini 3.8 Flash:** 0 mistakes, about **$0.20 a chapter**. Has a free tier, but **Google trains on free-tier data**. | — |
| Translator (free, local) | **Ollama**, with the model name typed in Settings. Default `qwen3:8b` (installed); suggest `shisa-v2.1-qwen3-8b`. | Sugoi-14B as the default: 9 GB on a 16 GB Mac, and no image |
| ChatGPT | **Optional** (GPT-6 Sol: 1 mistake, about $0.55 a chapter) | — |
| How many SDKs | `anthropic` for Claude, plus `openai` for **ChatGPT, Gemini and Ollama**: all three have OpenAI-compatible endpoints that take images | One SDK per provider (3–4 new libraries) |
| Translation unit | **One page per request**, with that page's image, the **previous page's Japanese and English** as plain text (cheap), and a **glossary** | Several page images per request: costs more, and didn't help in the paper<br>One request per bubble: worst quality |
| Erasing | **Mask = dark strokes inside the box, slightly widened.** If the ring around it is one flat color (a bubble), fill it with that color (instant, perfect). Otherwise, **manga LaMa** through spandrel on a crop around the box. | Filling the whole rectangle: erases bubble outlines and art<br>LaMa on everything: slower, and can smudge a white bubble<br>Stable Diffusion / FLUX inpainting: heavy, and research-only licenses |
| Lettering | **Comic Neue Bold** (bundled), with an optional "custom font file" setting so the user can pick Wild Words or Anime Ace if they own it. The area is the **inside of the bubble**, found by spreading out from the box over the bubble color, since Japanese boxes are tall and narrow. Word-wrapped, shrunk until it fits, centered. On artwork: black text with a white outline. | Lettering only inside Magi's narrow box: unreadable 1-word lines |
| Sound effects | **Left in Japanese** (`is_essential_text` = false is skipped) | Translating them: hard even for the best tools |

**Prompt design (the part that makes it read like a scanlation):**

| Rule | How |
|---|---|
| Natural English, not literal | System prompt: "Translate like an official English manga release. Short, natural lines that fit a speech bubble. Keep each character's voice (rough, polite, childish, dialect → light English equivalent). Never add or drop meaning." |
| Mapping lines to bubbles | Draw small numbers on a copy of the page at each box (in Magi's reading order). Send that image, plus `1: <OCR text>`, `2: …`. The model must return exactly one English line per number, as JSON. Use structured output: Claude's `output_config.format`, or `response_format` for the OpenAI-compatible APIs. |
| OCR mistakes | "The Japanese came from OCR and may have mistakes; trust the image when they disagree." |
| Who is speaking | Optional hint from Magi's `text_character_associations` ("2 and 5 are the same character"). The model mostly works this out from the image. |
| Honorifics | A setting: **Keep** (-san, -chan, senpai, the scanlation style, the default) or **Localize** (Mr., first names) |
| Names and terms stay the same | The model also returns `new_glossary` (name → English spelling, plus a one-line voice note per character). It's saved as `translation-glossary.json` in the **series** folder and sent with every page, so it carries on to the next chapter. |
| Effort | Claude Opus 5.5 at effort `medium` (its default; quality was already 0 mistakes in the test). `high` is a setting to try. |

## 5. Files to change and functions to reuse

| File | Change |
|---|---|
| `translate.py` (new, about 300–400 lines) | `translate_chapter(chapter_dir, output_dir, settings)`:<br>• `read_japanese(page, boxes)`<br>• `get_numbered_page_image(page, boxes)`<br>• `translate_page(…)`, with one small function per engine<br>• `get_text_mask` / `erase_text(page, box)`<br>• `fit_and_draw_text(page, bubble_area, text, font)`<br>Writes the translated pages (same file names) and `translation.json` (boxes, Japanese, English). |
| `magi.py` | Add `find_text_boxes(chapter_pages)` (about 15 lines): the "Finding the text" half of `find_and_read_dialogue` (`magi.py:494`), wrapped in `run_with_cpu_fallback`. Optionally make `find_and_read_dialogue` call it. |
| `gui_classes/TranslateView.py` (new, about 80 lines) | A `JobView` subclass like `MagiPanelByPanelView`:<br>• `process_image_folder` calls `translate_chapter`<br>• `next_view_name = "MagiPanelByPanelView"`<br>• Settings on the right: engine dropdown, model name, honorifics, API key field (hidden text), custom font |
| `gui_classes/PipelineView.py` | Add `"Translate"` to `PIPELINE_STEPS` (after the downloader), `PIPELINE_STEP_FOLDER_NAMES`, `FINAL_RESULT_DESCRIPTIONS`, `get_settings_review` (one row: engine + model) and `step_views` in `run_step`. `get_next_step_input_directory` needs **no change**: its last case (`<output>/<input folder name>`) already fits. |
| `gui_classes/AppBar.py`, `gui.py` | Add the tab to `TAB_NAMES` / `TAB_ICONS` (`ft.Icons.TRANSLATE`), create `TranslateView` in `create_views`, and add it to `set_views_narrow`. The shortcuts renumber themselves. |
| `default_settings.py` | `OUTPUT_SUBFOLDERS["output_directory_translate"] = "Translated"`, plus defaults: `translate_engine: "claude"`, `translate_model`, `translate_honorifics: "keep"`, `translate_font: ""` |
| `requirements.txt`, `requirements-lock.txt`, `build_mac_app.sh` | `anthropic`, `openai`, plus `fugashi` + `unidic-lite` (or none, with `do_word_tokenize=False`). Bundle `assets/fonts/ComicNeue-Bold.ttf` and its `OFL.txt`. |
| `tests/test_translate.py` (new) and `tests/test_pipeline.py` | Fake engines, masks, text fitting and the Pipeline step. In test_pipeline (and one line in test_e2e), about 8 lines that use the folder names change if the folders are renumbered (see open questions). |
| README, DEVELOPING, ROADMAP, HANDOFF | Docs, plus credits: manga-ocr (Apache-2.0), LaMa (Apache-2.0) / the manga LaMa (MIT), Comic Neue (OFL) |

**Reused as they are:**
- `JobView.start_job` (finding the chapter folders, progress, errors)
- `get_magi()`, plus `get_chapter_pages_image_numpy_array` and `run_with_cpu_fallback` in magi.py
- `report_progress` (ProgressPanel)
- `utils_load_dotenv` (keys `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, like the Azure key)
- `save_folder_as_cbz`
- `spandrel.ModelLoader`, the way `janai.py` loads models
- The model-download pattern from janai.py (to `~/Library/Application Support/Panelyze/`)

## 6. Steps (todo list)

**Phase 1: prove the quality on one chapter (no GUI)**
- [ ] 1. Download Dragon Tofu ch. 24 (Japanese) and ch. 24 (English, for comparison) with the existing downloader.
- [ ] 2. Add `magi.find_text_boxes`. Check that the boxes and `is_essential_text` look right on Japanese pages (dialogue vs sound effects).
- [ ] 3. Load manga-ocr with the existing transformers 4.34. Also try Baberu OCR on the same boxes; keep whichever reads better and loads cleanly.
- [ ] 4. `translate_page` for **Ollama** (real) and **Claude** (fake, until the key is added). Numbered image, JSON out, glossary.
- [ ] 5. Erasing: color fill first, then manga LaMa through spandrel for boxes over artwork.
- [ ] 6. Lettering: bubble area, wrap, fit, outline.
- [ ] 7. Save the pages + `translation.json`. **Stop for the user's review:** a side-by-side of the official English and our English for pages 1–5.

**Phase 2: in the app**
- [ ] 8. `TranslateView` tab + settings + defaults.
- [ ] 9. Pipeline step + review row + folder name.
- [ ] 10. Gemini and ChatGPT through the `openai` SDK (same function, different base URL).
- [ ] 11. Re-runs: if `translation.json` already has a page's English, skip the LLM. That makes re-lettering free and lets the user hand-fix a line in the JSON.
- [ ] 12. Tests, docs, credits, and `build_mac_app.sh` (font + new libraries). **Stop for the user's review.**

## 7. How to test it

| Test | How |
|---|---|
| Fast tests (no internet) | Fake engines return fixed JSON. Check: one English line per box, the honorifics setting reaches the prompt, the glossary is saved and sent again, a white bubble is filled with pure white, text over art goes to LaMa (faked), text always fits inside its area, and the Pipeline order and folders are right. |
| Real end to end (`-m e2e`) | Ollama on 3 pages of Dragon Tofu ch. 24: pages are saved, no Japanese is left in the bubbles, and Panel-By-Panel runs on the result. |
| Quality check (by eye) | Side by side with the official English ch. 24, using the existing `Compare upscalers.html` idea: Japanese, our English and the official English for each page. Count clear mistakes as the Serifu test did (wrong meaning, wrong person, broken name, missing line). |
| Speed (measure, don't guess) | Time per step on 21 pages: Magi boxes, OCR, LLM, erasing, lettering. One run at a time, fresh process. |
| Claude for real | Once the user adds `ANTHROPIC_API_KEY`: the same chapter, with the cost read from `response.usage` |

## 8. Size, value, risks, open questions

| | |
|---|---|
| **Size** | **Large.** About 500–600 new lines (translate.py + tab + tests) and about 30 changed lines in existing files. Phase 1 alone is about half of that. |
| **Value** | **High.** It opens up every untranslated chapter, and its output also feeds Panel-By-Panel and the video. Magi's English reader can read the English we letter. |
| **Speed (estimate, not measured)** | 21 pages:<br>• Magi boxes about 10–20 s<br>• OCR about 30 s<br>• Claude about 10–20 s a page, one page after another (each page uses the previous one), so **about 4–7 min**. Gemini Flash is about 15 s a page; Ollama qwen3:8b about 10–30 s a page on the M1.<br>• Erasing + lettering: a few seconds, plus about 1 s per LaMa crop. |

**Cost per chapter** (20 pages; about 4,000 input tokens a page = 2,400 image + about 1,500 text, and about 2,000 output tokens a page including thinking; estimate):

| Engine | Price per 1M tokens (in / out) | About per chapter |
|---|---|---|
| Claude Opus 5.5 | $4 / $20 | **$1.10** |
| Claude Sonnet 5.5 | $2 / $10 | $0.55 |
| GPT-6 Sol | $2 / $10 | $0.55 |
| Gemini 3.8 Flash (until Dec 31, 2026; doubles on Jan 1, 2027) | $0.75 / $3.75 | **$0.20** ($0.40 from Jan) |
| Claude Haiku 5.5 / GPT-6 Luna | $0.10 / $0.50 | $0.03 |
| Ollama (local) | free | $0 |

**Risks:**
- **Lettering looks automatic:** odd bubble shapes, long English lines. Mitigation: shrink to fit, plus the custom font option.
- **Magi may mark some Japanese dialogue as non-dialogue,** so it would stay untranslated. Step 2 checks this.
- **manga-ocr's tokenizer** may need fugashi. Step 3 checks this.
- **Model names and prices change fast** (Gemini's price doubles on Jan 1, 2027). The model name is a text setting, not hard-coded.
- **Claude Opus 5.5 can refuse a page** (`stop_reason: "refusal"`). Fall back to `fallbacks: "default"`, or skip the page with a message.
- **Disk:** 26 GB free (94% full). New models add about 650 MB (manga-ocr 450 MB + LaMa 200 MB).

**Open questions for the user:**
1. **Honorifics:** keep -san/-chan/senpai (scanlation style, recommended) or localize?
2. **Engines in the first version:** Claude + Gemini + Ollama (recommended), or ChatGPT too?
3. **Default engine before you have a Claude key:** Ollama (free, rougher), or a free Gemini key (much better, but Google trains on free-tier data)?
4. **Pipeline folder numbers:** renumber to `2-translate`, `3-panel-by-panel`, … (cleaner; about 8 test lines change), or keep the old numbers and call it `1b-translate`?
5. **Where do your Japanese raws come from?** MangaDex has almost none (e.g. no Shachou raws). The Translate tab works on any folder of images, so local files work.
6. **Font:** is Comic Neue OK, or do you own Wild Words / Anime Ace to point the setting at?

## 9. Sources

- Lippmann et al., *Context-Informed Machine Translation of Manga using Multimodal LLMs* (COLING 2025): https://arxiv.org/html/2411.02589v2
- Serifu, *Best AI Model for Manga Translation in 2026: Six Models Tested on 46 Pages* (Oct 2026): https://serifu.net/blog/best-ai-model-for-manga-translation
- JP-TL-Bench (Jan 2026): https://arxiv.org/html/2601.00223v1
- Manga translation tools compared (2026): https://www.kitsutl.com/blog/manga-translation-tools-comparison-2026
- Vertical Japanese text and multimodal LLMs: https://arxiv.org/html/2511.15059v1
- manga-image-translator: https://github.com/zyddnys/manga-image-translator
- BallonsTranslator: https://github.com/dmMaze/BallonsTranslator
- Koharu: https://raw.githubusercontent.com/koharu-rs/koharu/main/README.md
- manga-ocr: https://pypi.org/project/manga-ocr/ · tokenizer config: https://huggingface.co/kha-white/manga-ocr-base/blob/main/tokenizer_config.json
- Baberu OCR (benchmark table): https://huggingface.co/genshiai-daichi/baberu-ocr
- Manga LaMa: https://huggingface.co/dreMaz/AnimeMangaInpainting · IOPaint: https://github.com/Sanster/IOPaint
- Sugoi 14B Ultra GGUF: https://huggingface.co/sugoitoolkit/Sugoi-14B-Ultra-GGUF
- Claude vision token cost: https://platform.claude.com/docs/en/build-with-claude/vision · Claude prices: claude-api skill model table (cached 2026-10-06)
- OpenAI prices: https://developers.openai.com/api/docs/pricing
- Gemini prices: https://aistudio.google.com/docs/pricing
- MangaDex API (chapter checks for Shachou and Dragon Tofu): https://api.mangadex.org
