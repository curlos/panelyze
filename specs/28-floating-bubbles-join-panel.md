# 28. Join floating speech bubbles to the panel of the character who says them

Related: [benchmarks/webtoons.md](../benchmarks/webtoons.md) · [benchmarks/panel-cropping.md](../benchmarks/panel-cropping.md) · [#02 untested checks](02-untested-checks.md) and [#19 release](19-github-release-app.md) (the bundled model file changes)

New item, not on the roadmap yet. This is a plan only: no app code was changed. Researched 2026-11-20.

## 1. Summary

Webtoons put speech bubbles in the white space **between** panels. Magi boxes each one as its own "panel", so the reader sees the line on one swipe and the character saying it on the next (Eleceed's "MR. CAT!", many in Lookism).

Plan:
- Split each bubble-only panel into **one piece per bubble**, never through text.
- Attach each piece to the panel of the character who says it, using **Magi's own speaker links**.
- Those links come from three tiny parts of Magi (about 2 MB) that run on what the fast panels model already computes, so there's no slow model and no extra time.

## 2. Is it doable?

Yes. The hard part (who says what) is already learned by Magi. The rest is geometry this project already does: splitting at quiet rows, growing panels within limits.

## 3. What's already true (checked 2026-11-20)

| Claim | Check | Status |
|---|---|---|
| Only the slow full model can link text to characters | **No.** The full model's weights, by part: `ocr_model` 1,542 MB (reads text), `crop_embedding_model` 343 MB (same character across pages), `detection_transformer` 174 MB (in the fast model), **`text_character_matching_head` 1.1 MB**, **`text_tail_matching_head` 0.8 MB**, **`is_this_text_a_dialogue` ~0 MB** | ⚠️ |
| The small heads need only what the fast pass computes | Yes. In `magi_model/modelling_magiv2.py`: `_get_text_character_affinity_matrices` uses the per-box `obj` tokens + the `t2c` token; `_get_text_tail_affinity_matrices` uses `obj` tokens; `_get_text_classification` uses `obj` tokens. All come from the detection transformer the fast model already runs. | ✅ |
| Every character gets its own box | Yes: label 0, one box per character (a group of 10 → 10 boxes) | ✅ |
| How a speaker is picked | For each text box, the most likely character, kept if the score is over 0.35 (`text_character_matching_threshold`). Learned from training data, not a hand-written "tail points at character" rule. | ✅ |
| The fast model leaves these parts out | `PANELS_MODEL_PARTS = ("detection_transformer.", "bbox_predictor.", "class_labels_classifier.")` in `magi.py`; `panels_fp16.safetensors` is 87 MB | ✅ |
| Speaker accuracy | Reported in the Magi v2 paper; **not looked up yet** | ⚠️ open |

## 4. Recommended approach + rejected alternatives

**Main test case (from the user): Lookism ch. 553, panels 202–204,** originally in `~/Documents/Panelyze/Webtoon Test/…/Oemo Jisangjuui/Ch. 553 - DIVINE ORDER [02]/`. That folder is no longer kept (2026-11-21), so regenerate it; see §7.

| Panel | What's in it |
|---|---|
| 202 | Close-up of a smiling face, "WE GO WAY BACK", "?!", and at the bottom the top edge of the next bubble |
| 203 | **Bubble-only, with 3 separate texts**: "YOUR REACTION IS MAKING ME SAD..", the free text "THIS IS BAD" (no bubble: a thought or narration), "YOUR LITTLE BROTHER'S HERE" |
| 204 | The man in the green jacket, with the bottom of a bubble and its tail pointing at him, but **no words**: they're in 203 |

So a bubble-only panel can hold **several bubbles from different speakers**. Moving it whole into one neighbour would be wrong.

**Steps of the approach:**
1. **Add the 3 small heads to the fast model:** add `text_character_matching_head.`, `text_tail_matching_head.` and `is_this_text_a_dialogue.` to `PANELS_MODEL_PARTS`, and rebuild `panels_fp16.safetensors` with `build_panels_model_file`. In `find_panels`, also compute, from tokens it already has, the speaker (character index) for each text box, its tail, and whether it's dialogue.
2. **Find bubble-only panels:** text covers most of the panel and there's little other detail (reuse `get_detail`).
3. **One piece per bubble:** cut the bubble-only panel at the quiet rows *between* its text boxes (reuse the cut search in `split_tall_panel`, which never cuts through text).
4. **Attach each piece**, in this order:
   1. To the panel containing its **speaker's** character box.
   2. Else to the panel its **tail** points into.
   3. Else (webtoons) to the next panel below.
   4. Free text with no speaker, like "THIS IS BAD", stays with the nearest piece or as its own image.
5. **Limits:** never cut text; the merged crop stays under about 1 phone screen (`PHONE_SCREEN_HEIGHT_RATIO`) and takes no more than `PANEL_GROWTH_LIMIT` of any other panel. If a piece doesn't fit, it stays its own image. Nothing is ever lost.
6. **Webtoon mode first.** Manga already keeps bubbles with their panels through `get_grown_panels`.

**Bonus, as a follow-up:** `is_this_text_a_dialogue` lets the speech-bubble rules in `get_grown_panels` skip sound effects and margin captions directly. That could replace some of today's geometry checks.

**Rejected:**

| Alternative | Why not |
|---|---|
| Load the full model for speakers | It's slow every time: the 1.5 GB text reader runs on every text box. And the speaker link doesn't need it. |
| Merge the whole bubble-only panel into the panel below | Wrong when it holds bubbles from different speakers (Lookism 203) |
| A hand-written "follow the tail" rule | Magi's learned link already uses the tail and more, for free |

## 5. Files to change + what's reused

| File | Change |
|---|---|
| `magi.py` | `PANELS_MODEL_PARTS` (+3 heads); `find_panels` returns `speakers` / `tails` / `is_dialogue` per text box and the character boxes; new `join_floating_bubbles(panels, …)` called in `find_webtoon_panels` before `remove_repeated_webtoon_panels` |
| `magi_model/panels_fp16.safetensors` | Rebuilt (about 89 MB instead of 87). It's bundled in the Mac app, so check `build_mac_app.sh` / #02 / #19. |
| Reused | `split_tall_panel`'s quiet-row search, `get_detail`, `get_overlap_area`, `get_box_area`, `PANEL_GROWTH_LIMIT`, `PHONE_SCREEN_HEIGHT_RATIO` |
| Tests | `tests/test_webtoon.py`: a bubble-only panel with 2 bubbles and 2 speakers → each joins its speaker's panel; a bubble that doesn't fit stays alone; text never cut |

## 6. Steps

- [ ] Look up the speaker-link accuracy in the Magi v2 paper.
- [ ] Rebuild the panels model with the 3 heads; check that `load_panels_magi_model` loads it and that panel results are **identical** on Shachou ch. 3 (the heads don't change detection).
- [ ] Expose speakers/tails/dialogue from `find_panels`. Draw them on Lookism page images (lines from each text to its speaker) and check by eye on 2–3 chapters.
- [ ] Implement `join_floating_bubbles` with the limits above + tests.
- [ ] Before/after of Lookism 202–204 first, then all merges on Eleceed ch. 2 and Lookism ch. 553.
- [ ] Re-run the 10 webtoons; update `benchmarks/webtoons.md`.

## 7. How to test it

| Check | Pass |
|---|---|
| Lookism 202–204 | "YOUR LITTLE BROTHER'S HERE" is in the same image as the man in 204; no text cut; the leftover bubble edges at the bottom of 202 and the top of 204 are gone or whole |
| Eleceed "MR. CAT!" | Joined to the panel of whoever says it |
| Every merge (a before/after sheet, like `Everything left out.png`) | Checked by eye; no merged image over 2 phone screens tall |
| Panel detection unchanged | Same panels as before on Shachou ch. 3 with the rebuilt model file |
| Speed | Finding panels on Shachou ch. 3 still about 11 s |
| Fast + e2e tests | All pass |

The old Lookism folders in `~/Documents/Panelyze/` are no longer kept (2026-11-21). Download Lookism ("Oemo Jisangjuui") ch. 553 from MangaDex into the spec's own folder (`~/Documents/Panelyze/<worktree-folder>/`), run Panel-By-Panel in Webtoon mode, and find panels 202–204 again (the numbers can shift a little).

## 8. Size, value, risks, open questions

| | |
|---|---|
| Size | Medium (1–2 sessions) |
| Value | Medium–high: the user noticed it while reading; speaker + line on one screen reads naturally |
| Risk: wrong speaker links | A piece is only moved within the size limits; a wrong link can make an odd pairing but never loses text. Check accuracy by eye first. |
| Risk: model file change | The app bundles `panels_fp16.safetensors`; a stale file would be missing the heads. The existing check of required parts in `load_panels_magi_model` turns that into a clear error, and the rebuild runs automatically from source. |
| Open question | Also use `is_this_text_a_dialogue` to simplify the bubble rules in `get_grown_panels`? |
| Open question | Do the same for manga pages too, or only webtoons? |

## 9. Sources

- Measured: full model weights by part (`~/.cache/huggingface/hub/models--ragavsachdeva--magiv2/snapshots/fbc890…/pytorch_model.bin`).
- Code: `magi_model/modelling_magiv2.py` (`predict_detections_and_associations`, `_get_text_character_affinity_matrices`, `_get_text_tail_affinity_matrices`, `_get_text_classification`), `magi.py` (`PANELS_MODEL_PARTS`, `build_panels_model_file`, `find_panels`, `split_tall_panel`).
- Magi v2 paper (speaker accuracy): "Tails Tell Tales: Chapter-Wide Manga Transcriptions with Character Names" (Sachdeva et al., 2024).
