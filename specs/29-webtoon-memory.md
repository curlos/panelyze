# 29. Use less memory for webtoon chapters

Related: [benchmarks/webtoons.md](../benchmarks/webtoons.md)

New item, not on the roadmap yet. This is a plan only: no app code was changed. Researched 2026-11-20.

## 1. Summary

Webtoon mode joins the whole chapter into **one image** (`join_webtoon_strip`) before finding panels. Lookism ch. 553 is a 282,000 px strip, and the run peaked at **3.2 GB** of memory. On an 8 GB Mac, a very long chapter (or several at once in the Pipeline) could run out of memory and swap heavily, as happened during this project's own tests.

Plan: never build the full strip. Keep the list of images plus where each one starts, and build each window and each crop from only the images it touches.

## 2. Is it doable?

Yes. Every step only ever needs a small part of the strip: the windows are 2 screens tall, and crops are one panel. The safety net already works at 1/4 size.

## 3. What's already true (checked 2026-11-20)

| Claim | Check | Status |
|---|---|---|
| Peak memory per chapter | Measured with `resource.getrusage`: 1.3–3.2 GB across the 10 test webtoons (Lookism 3.2, Under the Oak Tree 3.1) | ✅ |
| The full strip is held in memory | `get_panels_using_local_cpu` replaces the pages with `[join_webtoon_strip(pages)]`, and the strip is used by `find_webtoon_panels`, `get_webtoon_safety_net`, `remove_repeated_webtoon_panels`, `split_tall_panel`, `remove_junk_panels` and `save_cropped_panels` | ✅ |
| Windows only need a part | `find_webtoon_panels` slices `strip[top : top + 2 × width]` | ✅ |

## 4. Recommended approach + rejected alternatives

**A small "lazy strip" object** with the same interface the code uses today:
- It holds the chapter's images (or their file paths) and the top of each one in strip coordinates, all scaled to the common width.
- `.shape` gives the full (height, width, 3).
- Slicing `strip[y0:y1, x0:x1]` builds only that part, by pasting from the images that overlap it.
- The safety net builds its 1/4-size grayscale strip image by image (small: 282,000 / 4 × 1080 / 4 ≈ 19 MB).

So `find_webtoon_panels`, the cleanup rules and the panel saving keep working with almost no changes.

**Rejected:**

| Alternative | Why not |
|---|---|
| Process the chapter in separate parts, one image at a time | Panels split between two image files would be cut again, which is the reason the strip is joined |
| Memory-mapped numpy file on disk | Works, but writes a multi-GB temp file; the lazy strip is simpler |

## 5. Files to change + what's reused

| File | Change |
|---|---|
| `magi.py` | `join_webtoon_strip` returns the lazy strip; check that each user of the strip only slices it (`find_webtoon_panels`, `get_webtoon_safety_net`, `remove_repeated_webtoon_panels`, `split_tall_panel`, `remove_junk_panels`, `get_panel_crop_box`, `save_cropped_panels`) |
| Tests | `tests/test_webtoon.py`: the lazy strip slices exactly like the joined array (same pixels), including slices across image edges |

## 6. Steps

- [ ] Record the current peak memory and panel counts on all 10 webtoons (the baseline).
- [ ] Add the lazy strip + a pixel-for-pixel test against `numpy.concatenate`.
- [ ] Switch the users over one by one; fast tests after each.
- [ ] Re-run all 10 webtoons: same panel counts and same saved images; lower peak memory.
- [ ] Add the before/after memory numbers to `benchmarks/webtoons.md`.

## 7. How to test it

| Check | Pass |
|---|---|
| Panels on the 10 webtoons | **Exactly** the same count and the same image files as before (compare hashes) |
| Peak memory | Clearly lower on Lookism and Under the Oak Tree (target: under 1.5 GB) |
| Speed | No slower than now (±10%) |
| Fast + e2e tests | All pass |

## 8. Size, value, risks, open questions

| | |
|---|---|
| Size | Medium (one session) |
| Value | Medium: protects 8 GB Macs and whole-series runs ([#03](03-whole-series-runs.md)) |
| Risk: subtle off-by-one at image edges | The pixel-for-pixel test + identical output hashes catch it |
| Risk: slower (images opened more than once) | Keep the images decoded in memory (as compressed arrays, or just the list of numpy pages, which is what's loaded today anyway) and only avoid the giant joined copy |
| Open question | Is the joined copy the main cost, or the decoded pages themselves? Measure first: if it's the pages, load them lazily from disk too. |

## 9. Sources

- Measured peak memory: the 10-webtoon runs in this project (`benchmarks/webtoons.md`, "Results").
- Code: `magi.py` (`join_webtoon_strip`, `find_webtoon_panels`, `get_webtoon_safety_net`, `get_panels_using_local_cpu`).
