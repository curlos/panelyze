# 39. Highlighter-style text highlighting in videos

Related: [#7 highlight boxes on the fast path](07-page-reading-highlight-boxes.md), [#35 closer shots](35-panels-without-repeats-and-closer-shots.md)

New item, not on the roadmap yet. **Draft from the user's ideas (2026-11-22), not researched yet**: written from what's already known, to be checked and researched before building.

## 1. Summary

A panel on screen can have 4 or more speech bubbles, and it's hard to follow which one is being read. Today "Highlight Text Boxes In Images" draws a **box outline** around each text box as it's read. Videos on TikTok or YouTube often use a **highlighter** look instead: a see-through yellow marker over the text being said.

The highlight should also cover **only the text itself**: today the box reaches out to almost the whole speech bubble (e.g. "MORNING." and the tall "SHE MEN- TIONED IT THE OTHER DAY..." caption, user's screenshots, 2026-11-22).

Add highlight styles to choose from:
- **Box** (today): an outline.
- **Highlighter**: a see-through yellow fill over the bubble or text being read.
- **Spotlight**: the rest of the panel slightly darker, the bubble being read normal.

## 2. Is it doable?

Yes. The video already knows each text box's position and when each line is said (one voice file per line when highlighting).

## 3. What's already true

| Claim | Status |
|---|---|
| Box highlighting exists | ✅ Images To Video setting "Highlight Text Boxes In Images" (`HighlightTextBoxesInImages.py`, `DrawBoxCoords.py`), with color and opacity settings |
| One voice file per line when highlighting | ✅ `VideoCreatorFromImages.py` |
| Magi's text box is around the text, not the bubble | ✅ But it's a little loose, and there's one box per text box, not per line or word |
| Panelyze adds padding around it | ✅ `DrawBoxCoords.py` adds `images_to_video_text_box_padding` (15 px by default) on every side, which is most of why the box reaches the bubble's edge |
| Highlighting is slow today | ✅ It reads every panel with Magi; spec 7 would use the page reading instead |

## 4. Recommended approach

- A **Style** dropdown next to "Highlight Text Boxes In Images": Box / Highlighter / Spotlight.
- **Highlighter**: fill the text box (with a little margin) in see-through yellow (the existing color and opacity settings), drawn under the text so the words stay black.
- **Spotlight**: darken everything but the current text box a little.
- Later: a "marker sweep" that fills the box left to right while the line is said.

### Only the text itself (tight boxes)

From simplest to best:
1. **Less padding:** 0–4 px by default instead of 15 (it's already a setting).
2. **Shrink the box to the ink:** inside Magi's box, find the dark pixels of the letters (on the bubble's light background) and shrink the box to them. Careful with screentone, the bubble's outline, and white text on dark backgrounds.
3. **A box per line** (like a real highlighter, and needed for the marker sweep): group the dark pixels into rows of letters; or use a second OCR that gives line and word boxes (spec 36, e.g. Apple Vision). With word boxes, words could even light up one by one as they're said (karaoke style), using the voice's word timings if the engine gives them.

## 5. Files to change

| File | Change |
|---|---|
| `DrawBoxCoords.py` | Draw the highlighter fill and the spotlight; shrink each box to its text (and split it into lines) |
| `gui_classes/HighlightTextBoxesInImages.py`, `default_settings.py` | The Style dropdown |
| Tests | Each style draws where the text box is, and only there |

## 6. Steps

- [ ] Draw each style on one panel as a picture, for the user to pick.
- [ ] Add the dropdown and use it in the video.

## 7. How to test

| Check | Pass |
|---|---|
| A panel with 4 bubbles | Only the bubble being said is highlighted, in the picked style |
| Text | Still readable under the highlighter |
| Tight boxes | On "MORNING." and the tall caption, the highlight covers the letters with a small margin, not the bubble |

## 8. Size, value, risks, open questions

| | |
|---|---|
| Size | Small |
| Value | Medium for TikTok and YouTube videos |
| Risk | Little: it's a drawing style |
| Open questions | Box per text box, per line or per word? Do spec 7 first (faster highlighting)? |

## 9. Sources

- The user's idea, 2026-11-22; `DrawBoxCoords.py`, `HighlightTextBoxesInImages.py`
