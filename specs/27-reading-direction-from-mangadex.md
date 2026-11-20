# 27. Pick the reading direction automatically (MangaDex + image shape)

Related: [benchmarks/panel-cropping.md](../benchmarks/panel-cropping.md) (4-koma) · [benchmarks/webtoons.md](../benchmarks/webtoons.md) · [#16 MangaDex options](16-mangadex-options.md)

New item, not on the roadmap yet. This is a plan only: no app code was changed. Researched 2026-11-20.

## 1. Summary

Today the user has to pick the Reading Direction (manga, comics, 4-koma, webtoon) by hand. If they don't, a Korean or Chinese **page-format** comic (like *Nán Hào Shàng Fēng*) is read right to left, which is the wrong order. Webtoons are already detected from their image shape (`looks_like_webtoon`).

Plan:
- When a chapter comes from MangaDex, look up the series' **original language and format tags**, decide the direction, and save it next to the chapter.
- Panel-By-Panel uses that hint unless the user picked a direction.
- When there's no hint, guess from the images: webtoon (exists) and a new 4-koma check.
- Add a **left-strip-first 4-koma** order, because 4-koma isn't only Japanese.

## 2. Is it doable?

Yes. The MangaDex API already gives everything needed. The only new ordering logic is the left-to-right 4-koma, which is a one-line change to an existing function.

## 3. What's already true (checked 2026-11-20)

| Claim | Check | Status |
|---|---|---|
| MangaDex tells you the reading direction | **No such field.** The manga attributes are `altTitles, availableTranslatedLanguages, contentRating, description, lastChapter, links, originalLanguage, publicationDemographic, status, tags, title, year, …` | ⚠️ |
| …but it gives language + format tags | `originalLanguage` (`ja`, `ko`, `zh`, `en`…) and the "format" tag group: **Long Strip, 4-Koma, Web Comic, Full Color, Official Colored, Fan Colored, Oneshot, Anthology, Adaptation, Award Winning, Doujinshi, Self-Published** | ✅ |
| "Long Strip" = webtoon, in every language | Long Strip series by original language: ja 893, ko 7,452, zh 4,583, en 670. So the tag must win over the language. | ✅ |
| 4-koma is only Japanese | **No.** 4-Koma series: ja 2,165, ko 26, zh 41, en 59. Non-Japanese 4-koma are read **left strip first**. | ⚠️ |
| The tags are reliable | **No.** *Bocchi the Rock!* (a 4-koma) has **no format tags at all**. So the tags are a hint; image checks are the fallback. | ⚠️ |
| Webtoons are detected from the images | `looks_like_webtoon` in `magi.py`: most images more than 2.5× taller than wide → webtoon | ✅ |
| 4-koma order exists | `get_four_koma_panel_order` in `magi.py` groups panels into columns, **right column first** | ✅ (right first only) |
| A chapter can be linked to its series | `GET https://api.mangadex.org/chapter/{id}` → `relationships` with `type: "manga"` → `GET /manga/{id}` | ✅ |

## 4. Recommended approach + rejected alternatives

**Decide the direction, highest priority first:**

| # | Source | Result |
|---|---|---|
| 1 | The user picked a direction in the dropdown | Use it. Always wins. |
| 2 | MangaDex "Long Strip" tag | `webtoon` |
| 3 | MangaDex "4-Koma" tag | `4koma` if `originalLanguage` is `ja`, otherwise `4koma-ltr` (new) |
| 4 | MangaDex `originalLanguage` | `ja` → `rtl`; anything else → `ltr` |
| 5 | No hint (not from MangaDex) | `looks_like_webtoon` → `webtoon`; new `looks_like_four_koma` → `4koma`; otherwise the old default `rtl` |

- **Where the hint lives:** a small `reading-direction.txt` next to the downloaded chapter's images, written by the downloader. It survives restarts and is visible to the user. Panel-By-Panel reads it.
- **Dropdown:** add a first choice, "Automatic (from the download, or the images)", as the new default. The existing choices stay as explicit overrides.
- **`looks_like_four_koma`:** most pages have panels in 1–2 columns, each column 3–5 panels of nearly equal width (reuse the column grouping inside `get_four_koma_panel_order`). Japanese order by default.

**Rejected:**

| Alternative | Why not |
|---|---|
| Only the original language | Misses Japanese long strips (893) and every 4-koma |
| Only the tags | Bocchi has none; most series aren't tagged with every format |
| Asking the user every time | Already possible today; the point is a good default |

## 5. Files to change + what's reused

| File | Change |
|---|---|
| `download_from_mangadex.py` | After the download (`tidy_chapter_folder_names`), fetch the series' language + tags once and write `reading-direction.txt` into each chapter folder |
| `magi.py` | `get_four_koma_panel_order(panels, strips_left_to_right=False)`; `get_panel_reading_order` and `apply_reading_direction` handle `4koma-ltr`; new `looks_like_four_koma`; `get_panels_using_local_cpu` resolves "automatic" |
| `gui_classes/ReadingDirectionSetting.py` | New choices: "Automatic", "4-koma (Strips, left strip first)" |
| `default_settings.py` | Default `reading_direction` becomes `"auto"` |
| `SpeechTextParser.py` / `VideoCreatorFromImages.py` | Use the same resolved direction for the video text |
| Reused | `looks_like_webtoon`, `get_four_koma_panel_order`, the MangaDex calls already used in the downloader |
| Tests | `tests/test_reading_direction.py` (4-koma left first), a new test with a **fake API response** (no network), and auto-detection on fake pages |

## 6. Steps

- [ ] Add `4koma-ltr` (the order + dropdown choice) with a test: a fake 2×4 page → left column top to bottom, then right.
- [ ] Add `looks_like_four_koma` with tests (Bocchi-like page → yes; a normal manga page → no).
- [ ] Add the MangaDex lookup + `reading-direction.txt` in the downloader (fake response in tests).
- [ ] Add "Automatic" as the default and resolve it in Panel-By-Panel: user pick → file → images → `rtl`.
- [ ] Make Images To Video use the same direction.
- [ ] Run on real chapters (below), then update `benchmarks/panel-cropping.md` (4-koma) and `README.md`.

## 7. How to test it

| Check | Pass |
|---|---|
| Fast tests | All pass, including the new ones |
| Shachou ch. 3 (ja, no format tags) downloaded through the app | Hint file says `rtl`; panels in manga order |
| Nán Hào Shàng Fēng ch. 3 (zh, page format) | `ltr`; panels left to right |
| A Long Strip series (e.g. Eleceed) | `webtoon` |
| Bocchi ch. 2 (ja, untagged 4-koma) | No tag, so `looks_like_four_koma` → `4koma` |
| A Korean or English 4-koma from MangaDex | `4koma-ltr`; left strip read first |
| The user picks a direction | It overrides everything |

## 8. Size, value, risks, open questions

| | |
|---|---|
| Size | Small–medium (one session) |
| Value | High: the right order with no settings for most MangaDex chapters |
| Risk: wrong tags on MangaDex | The user's pick always wins; the log says where the direction came from |
| Risk: chapters not from MangaDex | Falls back to the image checks, then `rtl` (today's behavior) |
| Risk: an old saved setting | Users who saved `rtl` explicitly keep it; only the default changes |
| Open question | Should "Automatic" be the default, or an opt-in? |
| Open question | Is `4koma-ltr` also right for English 4-koma? Most likely (left to right), but check one. |

## 9. Sources

- MangaDex API: `GET /manga/tag` (format tags), `GET /manga?includedTags[]=…&originalLanguage[]=…` (the counts above), `GET /manga/{id}`, `GET /chapter/{id}`. Checked live 2026-11-20.
- Code: `magi.py` (`looks_like_webtoon`, `get_four_koma_panel_order`, `get_panel_reading_order`, `apply_reading_direction`), `gui_classes/ReadingDirectionSetting.py`.
