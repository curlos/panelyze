# 30. Optional: skip the first and last images of each chapter

Related: [#11 smaller ideas](11-smaller-ideas.md)

New item, not on the roadmap yet. This is a plan only: no app code was changed. Researched 2026-11-20. **Low priority and optional.**

## 1. Summary

Scanlations often add credit pages, group ads, "support us" banners or colored fan art at the start or end of a chapter. Panel-By-Panel turns them into panels like any other page.

These pages **can't be detected reliably**:
- There can be 0 to 6 of them, at the start, the end or both (e.g. One Piece scanlations with several colored fan-art pages).
- Official chapters have none.
- Some official first pages look like credits (a title page).

So there's no automatic removal, only an explicit setting: **"Skip the first N and last M images of each chapter"**, off by default (0 and 0). The label must make clear it skips a fixed number of images and doesn't detect credits.

## 2. Is it doable?

Yes, and it's easy. It's just dropping some files from the chapter's list before Magi runs.

## 3. What's already true (checked 2026-11-20)

| Claim | Check | Status |
|---|---|---|
| Credit pages become panels | Seen in Eleceed ch. 2 (credits page), Neo man Boindan Mariya ch. 3 ("other works" grid), Teenage Mercenary ch. 233 (a ko-fi banner, 3 times) | ✅ |
| They could be detected automatically | The user's experience across many series: 0–6 credit pages, at the start and/or end, varying per group and chapter; official chapters have none. No reliable signal. Repeated banners can't be told apart from repeated story panels either (`benchmarks/webtoons.md`). | ❌ not reliably |
| The chapter's images are listed in one place | `get_chapter_pages_image_numpy_array` / `list_images` in `magi.py` / `utils.py` | ✅ |

## 4. Recommended approach + rejected alternatives

- Two number settings in Panel-By-Panel's settings, "Skip first images" and "Skip last images", both 0 by default.
- They apply per chapter folder, before Magi runs.
- Webtoons are joined into one strip, so the skip applies to the **image files** (the uploader's slices), not to panels.
- The Pipeline's settings review shows them when they aren't 0.
- The log says which files were skipped.

**Rejected:**

| Alternative | Why not |
|---|---|
| Detect credit pages automatically | No reliable signal (see §3). Removing an official page would break rule #1: every page of the story must stay. |
| Skip by default | Official chapters would lose real pages |

## 5. Files to change + what's reused

| File | Change |
|---|---|
| `gui_classes/MagiPanelByPanelView.py` | Two number fields (like the other settings), saved in client storage |
| `default_settings.py` | `skip_first_images: 0`, `skip_last_images: 0` |
| `gui_classes/PipelineView.py` | `get_settings_review`: mention them when set |
| `magi.py` | `get_panels_for_chapter`: drop the first N / last M pages after loading |
| Tests | `tests/test_panel_output.py`: with 1 and 1, a 4-page chapter only crops pages 2–3; 0 and 0 change nothing |

## 6. Steps

- [ ] Add the settings + defaults + review line.
- [ ] Drop the pages in `get_panels_for_chapter`, logging the file names.
- [ ] Tests; try it on Eleceed ch. 2 (skip first 1 → the credits page is gone).

## 7. How to test it

| Check | Pass |
|---|---|
| 0 and 0 (default) | Output identical to today |
| First 1 on Eleceed ch. 2 | The credits image is skipped; everything else identical |
| Values larger than the chapter | No crash; the chapter is skipped with a clear message |
| Fast tests | All pass |

## 8. Size, value, risks, open questions

| | |
|---|---|
| Size | Small |
| Value | Low: a convenience for readers of one scanlation group, who know how many credit pages it adds |
| Risk: skipping real pages | Off by default, and the label says it doesn't detect credits |
| Open question | Is it worth having at all? The user was unsure; do it only if still wanted after the other specs. |

## 9. Sources

- The user's description of scanlation credit pages (this project's planning chat, 2026-11-20).
- The 36 test chapters in `~/Documents/Panelyze/MangaDex Downloads/`.
