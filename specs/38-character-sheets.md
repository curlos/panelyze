# 38. Character sheets (experimental)

Related: [#26 colorize manga](26-colorize-manga.md), [#37 better voices](37-better-voices.md), [#39 highlighter style](39-highlighter-text-highlighting.md)

New item, not on the roadmap yet. **Draft from the user's ideas (2026-11-22), not researched yet**: written from what's already known, to be checked and researched before building. **Experimental.**

## 1. Summary

Let the user add a **character sheet** for a series: a picture (or a few) of each main character, with their name and, optionally, a voice and their colors. Magi then knows **which character is which** in every panel.

That unlocks:
- **Coloring** (spec 26): "This is Luffy: red vest, blue shorts, straw hat, peach skin", so he's colored the same way every time.
- **Voices** (spec 37): each named character keeps their own voice across every chapter.
- **Name tags** in videos: "Luffy" shown next to him, or in the transcript ("Luffy: …").

## 2. Is it doable?

Probably. Magi v2 was made for this: given pictures of the characters, it names them across a chapter (spec 26 found this works on the M1).

## 3. What's already true

| Claim | Status |
|---|---|
| Magi v2 can name characters from reference pictures | ✅ Noted in spec 26 (works on the M1) |
| Magi links each bubble to a character | ✅ Full model |
| Coloring plan | ✅ Spec 26: Magi names the characters, coloring through the Gemini image API |

## 4. Recommended approach

1. A **Characters** list per series: name, 1–5 pictures (crops from a page are fine), and optional notes (colors, voice).
2. Where it lives: a `characters/` folder next to the series, so it can be shared and reused.
3. Panel-By-Panel (full model) names the characters in each panel and saves them with the panels (like `panel-text.json`).
4. The video, the voices, and coloring read those names.
5. Later: suggest pictures automatically (e.g. from AniList or MyAnimeList), if that's allowed.

## 5. Files to change

| File | Change |
|---|---|
| `magi.py` | Name characters from the sheet; save them per panel |
| New GUI part | Add and edit characters (pictures, names, notes) |
| `VideoCreatorFromImages.py`, `TextToSpeech.py` | Use the names (tags, transcript, voices) |
| Spec 26's coloring | Use the notes (colors) |

## 6. Steps

- [ ] Scratch test: 3 characters of one series, one chapter: how often Magi names them right.
- [ ] If it's good enough: the Characters list, then names in the transcript, then voices (37), then coloring (26).

## 7. How to test

| Check | Pass |
|---|---|
| Naming | Most appearances of the main characters named right in a test chapter (target after the scratch test) |
| Unknown characters | Not given a wrong name |

## 8. Size, value, risks, open questions

| | |
|---|---|
| Size | Medium–Large |
| Value | Low–Medium on its own; High together with spec 26 and 37 |
| Risk | Wrong names (similar-looking characters, different outfits); slower (full model) |
| Open questions | How many pictures per character are needed? Where do sheets come from? |

## 9. Sources

- [Spec 26](26-colorize-manga.md); the user's ideas, 2026-11-22
