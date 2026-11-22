# 36. Better text reading: a second OCR and a word check

Related: [#35 bubbles shown once](35-panels-without-repeats-and-closer-shots.md), [#37 better voices](37-better-voices.md), [#1 translate Japanese pages](01-translate-japanese-pages.md)

New item, not on the roadmap yet. **Draft from the user's ideas (2026-11-22), not researched yet**: written from what's already known, to be checked and researched before building.

## 1. Summary

Magi finds the text boxes very well, but its reading of the words (OCR) makes mistakes, especially with unusual comic fonts. The text it reads goes into the transcript, the voice, and (with spec 1) translation, so mistakes are heard and seen.

Two ideas, which can be combined:
1. **A second OCR:** keep Magi for **finding** the text boxes, but read each box's picture with a stronger OCR made for reading text.
2. **A word check:** run Magi's text through a dictionary and context check. A word that isn't a real word (e.g. "yedj" for "yes") is probably a misreading, and the words around it suggest the right one.

## 2. Is it doable?

Yes. The text boxes are already found, so each one can be cropped and read again. The word check can start small: `pyspellchecker` is already installed (spec 17).

## 3. What's already true

| Claim | Status |
|---|---|
| Magi misreads some words | ✅ Shachou ch. 3 and ch. 8 (spec 17): "Presi- dental" (presidential), "JOMEONE" (someone), "work- Ries" (wor- ries), "Proba- sly", "conversa- lion", "emban- rassing", "hallucti- nation", "IsHizumi" |
| Words split over two lines are joined for the voice when that makes a real word | ✅ Spec 17 (`join_words_split_across_lines`, using pyspellchecker) |
| The text boxes' positions are saved | ✅ `magi-data.json` (video) and `panel-text.json` (Pipeline) |
| The transcript can be edited by hand and is then reused | ✅ `transcript.txt` next to the video |

## 4. Recommended approach + alternatives

1. **Build a small test set first:** about 100 bubbles from the test chapters, with the right text typed by hand. Count how many words each option gets wrong.
2. **Compare second OCRs** on each text box's crop (candidates from what's known; to be checked):

   | Option | Notes |
   |---|---|
   | Apple Vision (macOS text recognition, through pyobjc) | Free, on the Mac, fast, good with English. Mac only (the app is Mac only anyway). |
   | PaddleOCR / EasyOCR | Free and local; quality on hand-lettered comic fonts to be tested |
   | Tesseract | Free, but usually weak on comic fonts |
   | A vision LLM (Claude, Gemini) reading the bubble crops | Probably the best, but costs money per chapter and needs a key and internet |
   | manga-ocr | Japanese only: for spec 1, not English |

3. **Word check:** for each word that isn't in the dictionary:
   - when the two OCRs disagree, prefer the reading that's real words;
   - otherwise, suggest the closest real word that fits the sentence (a small local language model, or an LLM), and only change it when it's clearly better;
   - never change names, made-up words or sound effects ("IsHizumi", "Skedaddle"): only fix a word when the fix is clearly more likely, and keep a list of names per series.
4. Keep Magi's original text in `magi-data.json`, so a bad fix can be undone.

| Alternative | Why not (alone) |
|---|---|
| Only a dictionary check | Can't tell "IsHizumi" (a name) from a misreading, and can't pick between several close words without context |
| Replace Magi completely | Magi's text box finding and speaker links are still the best part |

## 5. Files to change

| File | Change |
|---|---|
| `magi.py` | After Magi reads the text: optionally read each text box again with the second OCR |
| New `text_check.py` | The word check (dictionary, context, names list) |
| `gui_classes/AppSettingsView.py` or the Panel-By-Panel / Images To Video settings | "Check the text" option, and the second OCR if more than one |
| `requirements.txt` + lock | The chosen OCR package (shared venv: install on purpose) |
| Tests | The test set as a fixed comparison |

## 6. Steps

- [ ] Make the test set (bubbles + correct text) from 2–3 test chapters.
- [ ] Measure Magi alone, each second OCR, and the word check on it.
- [ ] Build the best combination as an option; check it on a whole chapter.

## 7. How to test

| Check | Pass |
|---|---|
| Test set | Clearly fewer wrong words than Magi alone (target to be set after measuring) |
| Names and sound effects | Not changed |
| Speed | Not much slower per chapter (to be measured) |

## 8. Size, value, risks, open questions

| | |
|---|---|
| Size | Medium |
| Value | Medium–High: better voice, transcripts, and translation (spec 1) |
| Risk | "Fixing" correct words (names); slower runs; a paid OCR costs money |
| Open questions | Which OCR wins on comic fonts? Local only, or allow a paid LLM option? |

## 9. Sources

- Misread words seen in Shachou to Sake to Hoshi ch. 3 and ch. 8 (spec 17 session, 2026-11-21)
