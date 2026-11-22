# 35. Show every speech bubble once, read the text in the right order, and closer "shots" inside big panels

Related: [#28 floating bubbles](28-floating-bubbles-join-panel.md), [#36 better text reading](36-better-text-reading.md), [#39 highlighter style](39-highlighter-text-highlighting.md)

New item, not on the roadmap yet. **Draft from the user's ideas (2026-11-22), not researched yet**: written from what's already known, to be checked and researched before building. Part A is the main one; part B is experimental.

## 1. Summary

**Part A: no speech bubble in two panels.** Sometimes the same speech bubble ends up in two panel images. In a video that's awkward: the same bubble is shown twice, and (before spec 17) the voice said it twice. Every panel and every text box must still show up **at least once**, and nothing may be cut too much.

**Part C: the order of the text inside a panel.** Sometimes the lines are read in an order a reader wouldn't use. Example (Shachou ch. 3, user's screenshot, 2026-11-22): a wide panel with "I wonder why the boss…" (right), "Uh… huh?" (top middle), "I don't think that's her end goal here…" (top left) and the caption "Izutsu Printing, Section Chief Kenichi Ishizumi (37)" (bottom left). It reads "Uh… huh?", then the **caption**, then "I don't think…". A reader finishes the top row first (right to left), then the caption.

**Part B (experimental): closer shots inside a panel.** Big or wide panels hold several speakers. For videos meant to feel more like an anime (e.g. a chapter read out loud on YouTube), the camera could move inside a panel: the whole panel first, then closer to the bubble being read and the character saying it.

## 2. Is it doable?

- **Part A:** probably, with care. The hard part is deciding which panel a shared bubble belongs to without cutting real art.
- **Part B:** yes as a video effect (zoom and pan with MoviePy). Hard to make look good every time, so it's optional and experimental.

## 3. What's already true

| Claim | Status |
|---|---|
| A bubble can be in two panel images | ✅ Seen in Shachou ch. 3, page 1 (`00.png`): Magi's boxes for the first two panels **overlap by 343 px** (x 412–755). Three bubbles sit in the overlap ("It's been half a year…", "Don't give me that…", "Your report is late!"), so both crops have them. Our "keep text whole" growing didn't change these boxes; Magi found them overlapping. |
| Other overlaps | ✅ `benchmarks/panel-cropping.md`: "Panels inside panels: 15–17 overlapping pairs" (One Piece, Kingdom) |
| Bubbles split between two panels | ✅ Already shown whole in only **one** of them, the first in reading order (`get_grown_panels` in `magi.py`) |
| The voice and transcript say a repeated bubble twice | ✅ Fixed in spec 17: a long line that's the same as one in the panel just before is skipped (`remove_lines_said_in_the_image_before`). The **images** still show it twice. |
| In a Pipeline, each bubble's text goes to one panel | ✅ `get_dialogue_for_each_panel` gives each text box to the panel it overlaps most |
| Magi finds characters and who says each bubble | ✅ The full model finds characters and links text to its speaker (Magi v2); the fast panels-only model doesn't |
| The repeated-line skip (spec 17) compares each line with **every** line of the image before | ✅ Not only its last line. In the ch. 3 video made 2026-11-22 08:49, image 2's transcript doesn't repeat image 1's two lines. |
| The voice repeated with "Highlight Text Boxes In Images" on | ✅ Fixed in spec 17 (2026-11-22): the repeated line is marked as not dialogue, so its highlighted frame and audio are both skipped. Comparing with more than the one image before was judged not needed. |
| Where the order of text in a panel comes from | ✅ Magi's `sort_texts_within_panel` (`magi_model/utils.py`, bundled with Panelyze): text boxes are sorted by their distance from the panel's **top-right corner**. A wide caption at the bottom left can be closer to that corner than a bubble at the top left (in the example, about 590 px vs 640 px), so it's read first. |

## 4. Recommended approach + alternatives

### Part A

1. **Measure first.** Across the test chapters (`benchmarks/test-chapters.md`), count the overlapping panel pairs, how much they overlap, and how many text boxes sit in the overlaps. If it's rare, a simple rule is enough.
2. **Give each shared text box to one panel**: the one it overlaps most, or the first in reading order when it's inside both.
3. **Trim the other panel**, only if all of this holds:
   - it keeps most of its area (e.g. at least 70%);
   - it doesn't cut through its own text or a character's face;
   - the trim is a straight cut along the overlap's edge.
   Otherwise, leave both as they are.
4. When two panels overlap a lot (e.g. more than half of the smaller one), it's probably one panel found twice: **merge** them.

| Alternative | Why not (for now) |
|---|---|
| Paint over the repeated bubble in the second panel (white or blur) | Keeps the art, but an empty bubble looks odd. Maybe as a fallback when trimming would cut too much. |
| Always cut the overlap | Cuts real art and characters (the user's worry about overcutting) |
| Only fix the video (already done for the voice) | The images still show the bubble twice |

### Part C

Replace the distance-to-a-corner rule with a reading-order rule like the one used for panels: group text boxes into **rows** (boxes whose heights overlap), read the rows top to bottom, and each row right to left (left to right for comics, see the reading direction). Check it on many panels before switching, since it changes the order of every chapter: keep a list of panels where the order looked wrong (like this one) as tests.

### Part B (experimental)

A **video** effect, not more image crops, so the context isn't lost (a crop of one character misses what's going on):

- Show the whole panel, then move the camera closer to the bubble being read and the character saying it, then on to the next one, then back out.
- Only for big or wide panels with 2 or more bubbles. Small panels stay still.
- Uses Magi's character boxes and its "who says this bubble" links (full model), and the voice's timing per line.
- An option in Images To Video ("Camera: still / move to each speaker"), off by default.

The user noted this is rare to need and hard to get right (each panel is usually its own scene), so it's the last part to try.

## 5. Files to change

| File | Change |
|---|---|
| `magi_model/utils.py` (`sort_texts_within_panel`) or our own sort in `magi.py` | Part C: the row rule |
| `magi.py` | Part A: after `get_grown_panels`, a step that trims or merges overlapping panels (`remove_overlapping_text`?). Keep the "every text box at least once" rule as a check. |
| `VideoCreatorFromImages.py` | Part B: a camera move per line (MoviePy `resize`/`crop` over time), using the text and character boxes |
| `gui_classes/SettingsImagesToVideo.py`, `default_settings.py` | Part B's option |
| Tests | Part A: the Shachou ch. 3 page 1 boxes as a fixed test; every text box is in exactly one panel; no panel loses more than the limit |

## 6. Steps

- [ ] Part A: measure overlaps on the test chapters; write the numbers in `benchmarks/panel-cropping.md`.
- [ ] Part A: pick the rule (trim / merge / leave), build it, and check it by eye on the overlapping pages found.
- [ ] Part C: collect panels where the text order looks wrong; try the row rule on them and on a few whole chapters; compare by ear in the video.
- [ ] Part B (later): a scratch video of one wide panel with 3 bubbles, to see if it's worth it.

## 7. How to test

| Check | Pass |
|---|---|
| Shachou ch. 3, page 1 | The three bubbles are in only one panel image; both panels still have all their art except the trimmed strip |
| Every text box | In exactly one panel image (a script over the test chapters) |
| Pages without overlaps | Identical to today |
| Part C, Shachou ch. 3 example | Read in the order: "I wonder why…", "Uh… huh?", "I don't think…", then the caption (the small side remarks "I'm jealous…", "Stop it…", "I want to be pressured…" in a sensible place) |
| Part B | A wide panel with 3 bubbles: the camera moves to each speaker as the voice reads them, and nothing jumps |

## 8. Size, value, risks, open questions

| | |
|---|---|
| Size | Part A: Small–Medium. Part B: Medium–Large (experimental) |
| Value | Part A: Medium (videos look cleaner). Part B: Low–Medium (nice for YouTube-style videos) |
| Risk | Overcutting a panel; picking the wrong panel for a bubble |
| Open questions | How common are overlaps? Trim, merge or paint over? Is Part B worth it at all? |

## 9. Sources

- Shachou to Sake to Hoshi ch. 3, page 1, measured 2026-11-21 (spec 17 session)
- `benchmarks/panel-cropping.md` (overlapping pairs)
