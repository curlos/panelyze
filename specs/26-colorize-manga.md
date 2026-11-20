# 26. Colorize black-and-white pages (experimental)

New item, not on the roadmap yet. This is a plan only: no app code was changed. Researched 2026-11-19.

## 1. Summary

An optional **Colorize (experimental)** tool, as its own tab and a Pipeline step between **MangaDex Downloader** and **Panel-By-Panel**. It works on whole **pages**:

1. The user puts **one colored picture per main character** in a folder, named after the character (`Goku.png`, `Upa.png`), e.g. cropped from an official color page or cover.
2. **Magi** (already in the app) finds every character on every page and names it from that folder.
3. Each page goes to an **image-editing AI** with the colored pictures of only the characters on that page, plus the previous colored page, so colors stay the same from page to page.
4. **Keep the original lines:** the app keeps the brightness of the original page and takes only the **color** from the AI's picture. Lines, text and screentone stay exactly as drawn, even if the AI redraws something.

Panel-By-Panel then cuts up the colored pages as usual, and "Best" upscaling already switches to the color model by itself.

**Honest quality bar:** one good-looking page is easy today. **The same colors across a whole chapter, without muddy or wrong colors, is the hard part.** This spec starts with a cheap test (Phase 0) to see whether that bar can be met before building anything into the app.

## 2. Is it doable?

**Partly.**

| Part | Doable? | Why |
|---|---|---|
| Knowing which character is which | ✅ **Yes, measured** | Magi v2's "character bank" naming is already in the repo's Magi code. On 14 pages of Dragon Ball ch. 93 on this M1 it took **33 s** (plus 10 s to load), and named Goku and Upa correctly. It works about **3 times out of 4** in the paper. |
| Coloring a page on the M1 | ⚠️ **Too slow or too big** | The good reference-based models need an NVIDIA GPU: SD 1.5 at 512×512 (MangaNinja) or FLUX.2 klein 9B (about 20–29 GB, which won't fit in 16 GB). None of them has Mac support, and no Mac speeds are published. |
| Coloring a page with a paid API | ✅ **Yes** | Gemini's Nano Banana 2.1 takes a page plus several reference pictures. It costs about **$0.05 a page** (about **$0.80 for a 16-page chapter**), or half that in batch mode. |
| Same colors across a chapter | ⚠️ **Unknown until tested** | Nobody publishes a chapter-length consistency test. That's why Phase 0 comes first. |

## 3. What's already true (claims checked)

| Claim | Check | Status |
|---|---|---|
| "The repo has Magi v1" | The repo uses **Magi v2**: `magi_model/` is the Magi v2 code, copied unchanged from Hugging Face (`magi_model/README.md`). | ⚠️ wrong |
| Magi can name characters across pages | `Magiv2Model.do_chapter_wide_prediction(pages, character_bank, do_ocr=False)` and `assign_names_to_characters` are at `magi_model/modelling_magiv2.py:71` and `:105`. The bank is `{"images": [...], "names": [...]}`. A character that doesn't match anyone in the bank is named `"Other"`. | ✅ |
| It runs with the app's setup | The full Magi weights (1.9 GB) are already downloaded, since Images To Video uses them. `pulp` 2.9.0 and `scipy` 1.14.1 are installed. Tested in a scratch script (below). | ✅ measured |
| How accurate the naming is | Paper (ACCV 2024), one reference picture per character: **73–75% of characters named right**, or **87–88%** with ideal reference pictures. All minor characters are put together as "Other". | ✅ |
| Magi v3 adds better naming | `ragavsachdeva/magiv3` (0.8B) finds panels, characters and text, reads the text, and links captions to characters. It has **no character bank** and does no naming. | ⚠️ no help here |
| Upscaling handles color pages | `janai.is_color_image` (`janai.py:71`) already sends color images to IllustrationJaNai instead of MangaJaNai. | ✅ |
| The default test chapter is B&W | **No.** `ac33cc50…` is **Dragon Ball (Official Colored)**, ch. 93, 16 pages. Ch. 93 was also a color chapter in the magazine, so none of the other MangaDex versions (pt-br, vi, fa) are black and white either. That's useful: **turn the official color pages gray, colorize them, and compare with the real colors.** | ✅ (new) |

**Our own test (scratch script, not app code):**
- Bank: Goku and Upa, cropped from page 2 of the official color ch. 93.
- Input: pages 1–14 turned gray.
- **Result:** Goku and Upa were named right on every page checked by eye (pages 1, 4 and 7).
- **The main failure:** on page 13, Yamcha, who isn't in the bank, was named **"Goku" 5 times** (both have black spiky hair). Bulma, Roshi, Oolong and Puar were correctly "Other".
- **Lesson:** every main character on a page must be in the bank. Otherwise a look-alike gets the wrong character's colors.

| Step on the M1 (Mac GPU) | Time |
|---|---|
| Load the full Magi | 10.2 s |
| Find and name the characters, 14 pages | 33.1 s (about 2.4 s a page) |

## 4. Recommended approach and rejected alternatives

**Recommended:**
- **Phase 0:** a bake-off on 5 pages, with no app code.
- **Then:** if an API wins, a small `colorize.py` that uses **Magi character naming**, **Gemini Nano Banana 2.1** (page + that page's character pictures + the previous colored page + a short color note per character) and **"keep the original lines"**.

| Choice | Picked | Rejected (why) |
|---|---|---|
| Who is who | **Magi v2's character bank** (already in the repo, 2.4 s a page, measured) | Magi v3: no naming<br>Asking the image AI to work out who's who: it can't keep it the same across 20 separate requests |
| Coloring engine (default) | **Gemini Nano Banana 2.1** (`gemini-nano-banana-2.1`): several reference pictures per request, $0.034 (1K) / $0.050 (2K) a page, half in batch mode. **There is no free tier for image models.** | **GPT image 2.x:** $30 per 1M output tokens, about the same; could be a second option later<br>**Nano Banana Pro:** $0.134 a page |
| Local engine | **None in version 1.** Optional later: run MangaNinja on a free Kaggle GPU (spec 20's notebook) | **MangaNinja** (CVPR 2025): SD 1.5 + ControlNet, 512×512, one reference, about 6 GB, CC BY-NC, NVIDIA only<br>**ColorFlow** (TencentARC, MIT): SD 1.5 at 1024×1600 and needs a pool of colored pages from the same series; tested only on A100s<br>**Cobra** (SIGGRAPH 2025): 200+ references, NVIDIA (license not confirmed)<br>**FLUX.2 klein 9B** + a manga "colorize by reference" LoRA: closest to what we want, but non-commercial and 20–29 GB (doesn't fit 16 GB); 3–5 min an image even on an M1 Max with 64 GB |
| Automatic, no references | **Rejected** | **manga-colorization-v2** (and the GUIs built on it): fast and small, but it picks its own colors, so Goku's clothes change from page to page; no license stated<br>**Style2Paints V5:** never released<br>**Petalica Paint:** a website only, no API |
| Lines, text and screentone | **Keep the original brightness, take only the color** (LAB: the original L channel + the AI's a/b channels), after resizing the AI's picture to the page size | Using the AI's picture as is: image models redraw details and lettering. *Risk:* if the AI moves or reframes things, the colors land in the wrong places (Phase 0 checks this). |
| Keeping colors the same | (1) only the characters on **this** page, from Magi<br>(2) the **previous colored page** as an extra reference<br>(3) a `colorize-notes.txt` in the series folder ("Goku: orange gi, blue undershirt and wristbands, black hair") added to the prompt | Sending all pages in one request: too many images, and the output is still one picture per request |
| Character input | A **folder of pictures named after each character** (`Goku.png`), the same for every chapter of a series | A drawing or cropping UI in the app: much more code |

## 5. Files to change and functions to reuse

| File | Change |
|---|---|
| `colorize.py` (new, about 150–200 lines) | `load_character_bank(folder)` (file name = character name)<br>`colorize_chapter(chapter_dir, output_dir, settings)`<br>`colorize_page(page, references, previous_page, notes)`: Gemini call<br>`keep_original_lines(original, colored)`: LAB merge<br>Writes the colored pages (same file names) and `colorize.json` (characters named on each page) |
| `magi.py` | Add `find_named_characters(chapter_pages, character_bank)`, about 10 lines: `self.run_with_cpu_fallback("_full_model", lambda: self.full_model.do_chapter_wide_prediction(chapter_pages, character_bank, batch_size=1, do_ocr=False))` |
| `gui_classes/ColorizeView.py` (new, about 80 lines) | A `JobView` subclass like `MagiPanelByPanelView`:<br>• `process_image_folder` calls `colorize_chapter`<br>• Settings on the right: character pictures folder, model name, a "Keep original lines" checkbox (on), and an "Experimental: costs about $0.05 a page" note |
| `gui_classes/PipelineView.py` | Add `"Colorize (experimental)"` after the downloader in `PIPELINE_STEPS`, `PIPELINE_STEP_FOLDER_NAMES`, `FINAL_RESULT_DESCRIPTIONS`, `get_settings_review` and `step_views` in `run_step`. `get_next_step_input_directory` needs **no change** (its last case fits). Same slot and same folder-numbering question as spec 01. |
| `gui_classes/AppBar.py`, `gui.py` | Add the tab (`ft.Icons.PALETTE`) like spec 01 does |
| `default_settings.py` | `OUTPUT_SUBFOLDERS["output_directory_colorize"] = "Colorized"`, `colorize_model: "gemini-nano-banana-2.1"`, `colorize_keep_lines: True` |
| `requirements*.txt` | `google-genai` (or reuse the `openai` SDK if spec 01 adds it, if Gemini's OpenAI-compatible endpoint supports image output; check first) |
| `tests/test_colorize.py` (new), `tests/test_pipeline.py` | Fake engine; checks for bank loading, the LAB merge and the Pipeline step |

**Reused as they are:**
- `get_magi()`, `Magi.full_model`, `run_with_cpu_fallback` and `get_chapter_pages_image_numpy_array` (`magi.py`)
- `JobView.start_job` (`gui_classes/JobView.py:75`)
- `report_progress`
- `utils_load_dotenv` (`GEMINI_API_KEY`)
- `list_images` (`utils.py`)
- `janai.is_color_image` (already routes the colored pages to the color upscaler)

## 6. Steps (todo list)

**Phase 0: is it worth it? (scratch scripts only, about 1–2 hours, under $2)**
- [ ] 1. Make the test input: pages 1–5 of the official colored ch. 93 turned gray. The real colors are the answer key. Also pick 3 **real** black-and-white pages with screentone (e.g. the Frieren ch. 55 already in `testing-output/`).
- [ ] 2. Bank: Goku, Upa and **Yamcha, Bulma, Roshi** (from other color pages), since the test showed that missing characters get a look-alike's name.
- [ ] 3. Gemini Nano Banana 2.1: each page + its characters' pictures + the previous colored page. Save the raw output **and** the "keep original lines" version.
- [ ] 4. Optional: the same pages with MangaNinja on a free Kaggle GPU (spec 20), and with manga-colorization-v2, for comparison.
- [ ] 5. Side-by-side HTML page: gray input, each engine, the official colors. Note the time and cost per page. **Stop for the user's review: go or no-go.**

**Phase 1: in the app (only if Phase 0 is a "go")**
- [ ] 6. `magi.find_named_characters` + `colorize.py` (Gemini only).
- [ ] 7. Re-runs skip pages already in `colorize.json` (no paying twice).
- [ ] 8. `ColorizeView` tab + settings + defaults.
- [ ] 9. Pipeline step + review row + folder name.
- [ ] 10. Tests and docs (Magi and Gemini credits, "experimental" and cost notes). **Stop for the user's review.**

## 7. How to test it

| Test | How |
|---|---|
| Fast tests (no internet) | A fake engine returns a fixed colored image. Check: bank names come from the file names, only the characters on a page are sent, "keep original lines" leaves gray pixels the same brightness, a missing API key gives a clear error, and the Pipeline order and folders are right. |
| Naming check | Re-run the scratch test with the full bank and count the right names by eye on pages 1–14 (Yamcha should no longer be "Goku"). |
| Quality (by eye) | Phase 0 side by side with the official colors. Score each page: (a) are main characters the right colors? (b) are they the **same** as on the last page? (c) muddy or gray areas? (d) text and lines untouched? |
| Real B&W | The 3 Frieren pages: does screentone turn into flat color or into dirty dots? |
| Speed and cost | Time per page from the API, and cost from the response's token counts. One run at a time. |

## 8. Size, value, risks, open questions

| | |
|---|---|
| **Size** | Phase 0: **Small** (scratch scripts). Phase 1: **Medium**, about 300–350 new lines + about 25 changed lines. |
| **Value** | **Unknown, possibly Low–Medium.** It's fun for videos and color reading, but only if a whole chapter looks consistent. |
| **Speed** | Magi naming: about 2.4 s a page (measured). Gemini: about 10–30 s a page (estimate, not measured), so about 3–8 min for a 16-page chapter. |
| **Cost** | About $0.05 a page at 2K: **about $0.80 a chapter** (16 pages), or about $0.40 in batch mode. Plus a little for the input pictures. |

**Risks:**
- **Colors drift or go muddy over a chapter.** This is the main risk, and the reason for Phase 0.
- **Wrong names mean wrong colors:** about 1 in 4 characters in the paper, and look-alikes when a character isn't in the bank (measured: Yamcha → Goku). Minor characters are all "Other" and get whatever color the AI picks.
- **Screentone under color** can look dirty, and "keep original lines" keeps the dots on purpose. An option to soften the tone first may be needed (ColorComic does that for its automatic mode).
- **The AI moves things,** so the LAB merge puts colors in the wrong places. Phase 0 checks this. Fallback: use the AI's picture as is.
- **The API may refuse some pages** (violence, fan service). Keep the gray page and say so.
- **Licenses:** Magi is non-commercial only (already true for the app). MangaNinja is CC BY-NC. Gemini output is fine for personal use.
- **Gemini changes model names and prices fast** (2.5 Flash Image shuts down on 2027-03-15). The model name is a text setting.
- **No free tier** for Gemini image models.

**Open questions for the user:**
1. Is about **$0.80 a chapter** (paid Gemini key) OK for an experiment, or should it be free and local only? Local only means a Kaggle notebook (spec 20) and much more setup.
2. Is cropping one colored picture per main character, once per series, OK as the manual step?
3. Should "keep original lines" (exact lines, flatter look) be the default, or the AI's full repaint (prettier, may change details and lettering)?
4. Which real black-and-white series should be the second test (for screentone)? Frieren ch. 55 is already on disk.
5. Should Colorize come before or after Translate (spec 01) when both are picked? Suggested: Translate first, then Colorize, so the new lettering is kept as lines.

## 9. Sources

- Magi v2 model card (character bank): https://huggingface.co/ragavsachdeva/magiv2
- Magi v2 paper, *Tails Tell Tales* (ACCV 2024), naming accuracy tables: https://arxiv.org/html/2408.00298
- Magi repo (v1/v2/v3): https://github.com/ragavsachdeva/magi · Magi v3: https://huggingface.co/ragavsachdeva/magiv3
- MangaNinja (CVPR 2025): https://github.com/ali-vilab/MangaNinjia
- ColorFlow: https://arxiv.org/html/2412.11815v2 · https://huggingface.co/TencentARC/ColorFlow
- Cobra (SIGGRAPH 2025): https://arxiv.org/abs/2504.12240
- MangaDiT: https://arxiv.org/html/2508.09709
- FLUX.2 klein manga colorization LoRA: https://huggingface.co/milo01/FLUX.2-klein-9B-manga-colorization-by-reference-LORA · FLUX.2 klein licenses and sizes: https://bfl.ai/blog/flux2-klein-towards-interactive-visual-intelligence , https://blog.comfy.org/p/flux2-klein-4b-fast-local-image-editing · Mac speed: https://lilting.ch/en/articles/flux2-klein-apple-silicon
- ColorComic (wraps manga-colorization-v2, MangaNinja, Gemini): https://github.com/vikast908/ColorComic
- manga-colorization-v2: https://github.com/qweasdd/manga-colorization-v2
- Style2Paints status: https://github.com/lllyasviel/style2paints/blob/master/README.md
- Gemini prices: https://aistudio.google.com/docs/pricing · OpenAI prices: https://developers.openai.com/api/docs/pricing
- MangaDex API (ch. 93 versions): https://api.mangadex.org
- Scratch test script: `/private/tmp/claude-501/-Users-curlos-Desktop-Github-Repos-manga-panel-splitter/8ee4c6a0-1364-4871-bb81-d6088b80b372/scratchpad/scripts/bank_test.py`
