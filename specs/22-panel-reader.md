# 22. How should users read the panels?

Checked on 2026-11-19. ✅ = checked today against the real code or the web, ⚠️ = an older note that's now out of date, 🟡 = not confirmed.

## 1. Summary
**Keep the .cbz of panel images the app already makes, and read it in the free *Panels* app on iPhone, iPad and Mac.** Every panel is its own "page", so any comic reader already reads it panel by panel: swipe once, see the next panel full screen. Nothing new needs to be built. The only changes recommended are small:
1. A short "How to read on your iPhone, iPad or Mac" section in the README.
2. A clearer hint under the comic-file setting.

A reader tab inside Panelyze, a web reader, or a full-page comic with panel coordinates for "smart panel" readers are all more work for a worse or Mac-only result (see 4).

## 2. Is it doable?
Yes, today. The .cbz files already work. The work left is wording, plus one check on a real iPhone.

## 3. What's already true
| Claim | Check |
|---|---|
| The app can save each chapter as a .cbz | ✅ `utils.save_folder_as_cbz(folder, size)` writes `<folder>.cbz` next to the folder, with images numbered `0001…` in reading order. It runs after Panel-By-Panel (`MagiPanelByPanelView.py`, line 82) and after Upscale |
| It's off by default | ✅ `save_as_cbz` is `""` in `default_settings.py`. The user has to pick "small" or "full" in Settings |
| "Small" files are about 15–25 MB per chapter | ✅ benchmarks/file-sizes.md: Shachou ch. 3 is 24.6 MB, One Piece ch. 567 is 15.3 MB (vs 217 / 144 MB of PNGs) |
| The app recommends Panels | ✅ The setting's hint text (`AppSettingsView.py`, line 80): "Open them in a comic reader app like Panels (iPhone and iPad) or Mihon (Android)." It leaves out that **Panels also runs on the Mac** |
| The .cbz has no ComicInfo.xml (title, series, reading direction) | ✅ Only images |
| Panels reads .cbz and WebP | ✅ App Store: CBR, CBZ, CB7, PDF, comic ePUB, WebP. iOS/iPadOS 15+, **macOS 13+**, visionOS. Version 3.13.11, 4.8★ (about 13K ratings). Free download; Panels+ costs $1.49/month or $14.99/year, Panels 3 is a $19.99 one-time purchase. Imports from iCloud Drive, AirDrop, Files, Dropbox, OneDrive, SMB, OPDS (Komga/Kavita). Reading progress syncs across devices |
| Which Panels features are free | 🟡 The listing says premium features need a subscription or a purchase, but not which ones. Opening and reading a local .cbz is believed to be free. Check on a real device |

### The readers, checked
| Reader | Mac | iPhone/iPad | Price | Reads our panel .cbz? | Own "smart panel" mode on full pages? |
|---|---|---|---|---|---|
| **Panels** | ✅ macOS 13+ | ✅ | Free + optional paid | ✅ | Experimental "panel-by-panel guided view" (Settings → Panels Labs), maybe premium. Reviews say it misses panels on some pages |
| xiComic | ✅ (M1+, macOS 14.6+) | ✅ | Free, no in-app purchases | ✅ CBZ + WebP | ❌ |
| YACReader | ✅ desktop app free | ✅ $4.99 | | ✅ (WebP not listed; AVIF is) | ❌ |
| Smart Comic Reader | ✅ (iPad app on Mac) | ✅ | $1.99 | ✅ | ✅ automatic panel zoom |
| Panel Flow / Yomu | | ✅ iPhone | Free / premium | | ✅ AI panel detection on full pages (competitors to Panel-By-Panel, really) |
| Mihon (Android) | ❌ | ❌ | Free | ✅ (local source) | ❌ (no panel mode found) |
| Komga / Kavita (self-hosted web) | browser | browser, or via Panels (OPDS) | Free | ✅ | ❌. Kavita has an open idea (#2826): a fork proof of concept from Aug 2026 is not merged |
| Apple Books | | | Free | 🟡 No Apple documentation says it opens .cbz. It needs EPUB | ❌ |
| Kindle "Panel View" / "Guided View" | | | | ❌ Needs a book made in Kindle Create, with each panel marked by hand | ✅ but not for our files |
| CDisplayEx, Perfect Viewer, ComicRack | ❌ Windows / Android only | ❌ | | ✅ | ❌ |
| ACBF Viewer | ❌ Linux, Windows, Android | ❌ | Free | ✅ | ✅ (needs ACBF files) |

## 4. Recommended approach and the alternatives
| Option | Mac | iPhone/iPad | Work | Verdict |
|---|---|---|---|---|
| **A. .cbz of panel images + Panels (or any reader)** | ✅ | ✅ | Docs only | ✅ **Recommended.** Already works, one file per chapter, syncs over iCloud, reading progress saved |
| B. A "Reader" tab inside Panelyze (Flet) | ✅ | ❌ (Flet desktop doesn't run on iPhone) | 1 new view file (about 100–150 lines: an `ft.Image`, ←/→ keys through the existing `handle_keyboard_shortcut`, a folder picker), add it to `TAB_NAMES` in `AppBar.py`, tests | ❌ Not now. Mac only, and a worse reader than Panels. Maybe later, as a "check the panels" preview |
| C. A small web reader (an HTML page next to the panels, or Flet's web mode) | ✅ | 🟡 only while the Mac is on and on the same Wi-Fi | A static page or a server | ❌ Needs the Mac running. Panels already does this better |
| D. Full-page .cbz + panel coordinates for "smart panel" readers | | | | ❌ No standard that Apple readers use: **ComicInfo.xml has no panel fields** (pages only: Image, Type, DoublePage, ImageSize, Key, Bookmark, ImageWidth/Height). **ACBF** has panel frames, but only ACBF Viewer (no Mac or iOS) reads them. **EPUB Region-Based Navigation** (IDPF, 2015) leaves the behavior to each reader, and Apple's Books guide doesn't mention it. **Kindle Guided View** is made in Kindle Create by hand. **Kavita** support is only a fork. So the coordinates would be thrown away |
| E. Make an EPUB (fixed layout) for Apple Books | ✅ | ✅ | A new writer (OPF, XHTML page per panel) | ❌ Not now. More work, and Apple Books has no panel features to gain from it |

## 5. Files to change
| File | Change |
|---|---|
| `README.md` | New short section "Read on your iPhone, iPad or Mac": turn on Settings → comic file → Small; send the `.cbz` with AirDrop or save it to iCloud Drive; open it in Panels; pick the horizontal "one page at a time" reading mode with the image fitted to the screen. Each swipe is the next panel |
| `gui_classes/AppSettingsView.py` (line 80) | Hint text: "…in a comic reader app like Panels (iPhone, iPad and Mac) or Mihon (Android)." |

To reuse: nothing new. `utils.save_folder_as_cbz` stays as it is.

**Not part of this spec, but related:** making "small" the default comic file (roadmap #8, "Smaller files by default") would mean every run already gives a phone-ready file.

## 6. Steps
- [ ] Copy one "small" .cbz (e.g. Shachou ch. 3, 24.6 MB) to the iPhone and the Mac, and read it in Panels. Note which reading mode feels best, and whether anything needs Panels+
- [ ] Add the README section with what worked
- [ ] Change the hint text in `AppSettingsView.py` to say Panels also runs on the Mac
- [ ] Run the fast tests (`npm test`), in case a GUI test checks the hint text

## 7. How to test it
- On a real iPhone and Mac: open the .cbz in Panels. Check that panels come in reading order, swiping goes to the next panel, it fits the screen, and reading progress syncs.
- Try one other free reader (xiComic) to confirm the file isn't tied to Panels.
- `npm test`: 184 fast tests should still pass.

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | Tiny (two text edits) |
| Value | Medium: answers "how do I actually read this?" for new users |
| Risks | Panels may put some reading modes behind Panels+ (🟡). Very small panels (a lone sound effect) get enlarged to full screen, which is fine with "Best" upscaling, a bit soft without it. Swipe direction: the files are in reading order, so read them left-to-right in the reader. A reader set to "manga, right to left" just swipes the other way; the order stays right |
| Open questions | 1. Which Panels reading mode does the user like best (one at a time vs vertical scroll)? 2. Add a small ComicInfo.xml (series, chapter title, number) so the library shows nice names? Panels' support for it is 🟡 not confirmed. 3. Make "small" .cbz the default (roadmap #8)? 4. A Mac-only "preview the panels" tab later? |

## 9. Sources
- Panels on the App Store: https://apps.apple.com/us/app/panels-comic-reader/id1236567663
- xiComic: https://apps.apple.com/ae/app/id6749070576 · YACReader: https://apps.apple.com/app/id635717885 · Smart Comic Reader: https://apps.apple.com/us/app/app/id1511175212 · Panel Flow: https://apps.apple.com/us/app/id6755895197 · Yomu: https://apps.apple.com/us/app/id6760745234
- ComicInfo.xml fields (Anansi project): https://anansi-project.github.io/docs/comicinfo/documentation
- ACBF: https://wiki.mobileread.com/wiki/ACBF, https://acbf.fandom.com/wiki/Specifications
- EPUB Region-Based Navigation 1.0: https://idpf.org/epub/renditions/region-nav/
- Kavita panel-reading idea #2826: https://github.com/Kareadita/Kavita/discussions/2826
- Kindle Guided View (Kindle Create): https://kdp.amazon.com/en_US/help/topic/G201562880
- In the repo: `utils.py` (`save_folder_as_cbz`), `gui_classes/AppSettingsView.py`, `default_settings.py`, `benchmarks/file-sizes.md`
