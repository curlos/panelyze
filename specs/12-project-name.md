# 12. Should the project still be called "Panelyze"?

> **Being built as part of [spec 40](40-housekeeping-and-release.md)** (2026-11-23). Where they differ, spec 40 is newer.

Checked on 2026-11-19. ✅ = checked today against the real code or the web, ⚠️ = an older note that's now out of date.

## 1. Summary
**Keep "Panelyze".** No app, company or trademark in the manga or comics world uses the name. The only other "panelyze" is a small Python data-table add-on on PyPI. The name still fits: every tool in the app works from the panels Magi finds (cutting, reading the text, timing the video, and later translating). A short tagline can cover the newer tools:

> **Panelyze: a manga toolkit for your Mac. Download, split into panels, upscale, make videos, translate.**

The note that "the repo is still named manga-panel-splitter" is ⚠️ out of date: the GitHub repo **is already `curlos/panelyze`**. The old address redirects to it. Only the local folder name, the git remote URL and 3 links in the docs still use the old name.

## 2. Is it doable?
Yes, either way. Keeping it costs nothing. Adding the tagline is a one-line change to the README. A full rename is doable but touches about 150 places, plus folders on users' Macs (see 8).

## 3. What's already true
| Claim | Check |
|---|---|
| The app is called Panelyze everywhere a user sees it | ✅ window title, Dock launcher, `Panelyze.app`, `~/Documents/Panelyze`, `~/Library/Application Support/Panelyze`, `~/Library/Logs/Panelyze` |
| The repo is still named `manga-panel-splitter` | ⚠️ **Out of date.** `gh api repos/curlos/manga-panel-splitter` answers with `curlos/panelyze`, and `https://github.com/curlos/manga-panel-splitter` gives a 301 redirect to `https://github.com/curlos/panelyze`. The GitHub description already reads "Desktop app that uses AI to convert manga/comics into panel-based reading formats." |
| Old name still in use | ✅ local folder `~/Desktop/Github-Repos/manga-panel-splitter`; `git remote` URL; 7 mentions in 4 tracked files (README.md, DEVELOPING.md, HANDOFF.md, and an old Colab notebook) |
| Mentions of "Panelyze" in tracked files | ✅ **148 mentions in 24 files** (`git grep -i -o panelyze`). The most: tests/test_output_folders.py (22), AppSettingsView.py (14), build_mac_app.sh (13), default_settings.py (12) |

### Name clash check
| Where | What uses "Panelyze" (or close) | Clash? |
|---|---|---|
| Web search | Nothing in manga or comics. "Panelizer" (Drupal module), PCB "panelization" tools | ✅ No |
| PyPI | `panelyze` 0.2.0 (Nov 2025, Saeed Raad): a spreadsheet-style DataFrame viewer for Jupyter | 🟡 The name is taken on PyPI, but Panelyze isn't published to PyPI and doesn't need to be |
| GitHub | `curlos/panelyze` (this app), 2 empty repos named Panelyze, `panelyzer` (time-series formulas), `panelyzer` (flow-cytometry panels) | ✅ No real clash |
| App Store | Panels, Panelz, PanelVue Builder, Panel Flow. None is called Panelyze | ✅ No. "Panels" (the comic reader) is close, but it's a different word |
| Trademarks (Justia search) | No PANELYZE mark. Close: PANELYTICS (data-analysis software, filed 2020), PANELYZER (dead, 2004, machinery) | ✅ No. Not a USPTO search, though (see 8) |
| Domains | `panelyze.com` registered since 2017 (Namecheap, nothing loads). `panelyze.io` is free | 🟡 Only matters for a website |

## 4. Recommended approach and the alternatives
| Option | What | Verdict |
|---|---|---|
| **Keep "Panelyze" + a tagline** | One README line under the logo | ✅ **Recommended.** Nothing to change, no clash, the user likes it |
| Keep it, no tagline | Change nothing | ✅ Also fine |
| **Panelize** | Plain spelling | ❌ An existing tech word (PCB and Drupal panelizing). 92 GitHub repos. Harder to search for |
| **Panelwise** | "Panel by panel, wisely" | 🟡 Free on PyPI, 4 GitHub repos. Fine, but no better |
| **MangaKit** | Says "a bundle of manga tools" | 🟡 Free on PyPI, 9 GitHub repos. Generic, loses the panel idea |
| **KomaKit** | *Koma* (コマ) is Japanese for a manga panel | 🟡 Free on PyPI, 1 GitHub repo. Clever, but most users won't get it |
| **InkPanel** | | 🟡 Free on PyPI, 7 GitHub repos. Sounds like a drawing app |
| **PanelPal** | | 🟡 Free on PyPI, 17 GitHub repos. Sounds like a solar-panel or survey app |
| **PanelKit** | | ❌ Taken on PyPI, 25 GitHub repos |

(PyPI = a direct check of `pypi.org/pypi/<name>/json`; GitHub = repos with the name in their name. Neither is a trademark search.)

## 5. Files to change
For the recommended option, only one:

| File | Change |
|---|---|
| `README.md` | The tagline under the logo (it currently reads "Turn manga pages into easy-to-read panels, upscale them, and make videos from them…"). Mention translation once it ships |
| (optional) `README.md`, `DEVELOPING.md` | Change the 3 `github.com/curlos/manga-panel-splitter/...` links to `curlos/panelyze`. They work now through the redirect, but the redirect breaks if a new repo named `manga-panel-splitter` is ever made |
| (optional, outside the code) | `git remote set-url origin https://github.com/curlos/panelyze.git` |

Nothing to reuse: these are text edits.

## 6. Steps
- [ ] User decides: keep the name (recommended) or pick another
- [ ] Update the tagline in README.md
- [ ] (Optional) Point the 3 old GitHub links at `curlos/panelyze`
- [ ] (Optional, user's call) Update the git remote URL, and rename the local folder. That needs the `~/Applications/Panelyze.app` launcher (which hard-codes the folder path) and the VS Code workspace updated too

## 7. How to test it
- Open README.md on GitHub and check the tagline.
- If the links changed: `curl -sI <link>` gives 200, not 301.
- If the local folder is renamed: start the Dock launcher, and run `npm test` (184 fast tests).

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | Keeping it: tiny (1 line). A full rename: medium |
| Value | Low. The name already works |
| What a full rename would cost | About 148 mentions in 24 files. **Users' data folders**: `~/Documents/Panelyze` (their results), `~/Library/Application Support/Panelyze/upscale-models` (240 MB of models plus Core ML conversions, about 27 s each to redo), `~/Library/Logs/Panelyze`. A rename would need code to move these, or users would lose them. Also the `panelyze_page_height` key saved inside panel PNGs (old panels would lose the page height that "Best" uses), the `com.curlos.panelyze` bundle id (macOS would treat it as a new app and ask for permissions again), the icon files, the GitHub repo, the release zip name and the Dock launcher |
| Risks of keeping it | Tiny. The PyPI name is taken, which only matters if Panelyze is ever published to PyPI (not planned). Not a legal search |
| Open questions | 1. Which tagline wording? 2. Update the old `manga-panel-splitter` links and git remote now, or leave them on the redirect? 3. For certainty before any public launch, do a real USPTO search for "PANELYZE" (tmsearch.uspto.gov) |

## 9. Sources
- PyPI `panelyze`: https://pypi.org/project/panelyze/ (0.1.0 on 2025-05-27, 0.2.0 on 2025-11-16)
- GitHub repo search "panelyze", and `gh api repos/curlos/manga-panel-splitter` → `curlos/panelyze`
- Drupal Panelizer: https://drupal.org/project/panelizer
- Trademark lookalikes: https://trademark.justia.com/907/18/panelytics-90718592.html, https://markinton.com/trademark/panelyzer-78510773
- App Store lookalikes: https://apps.apple.com/us/app/panelz/id6450021718, https://apps.apple.com/us/app/panelvue-builder/id1457648018
- `whois panelyze.com` (created 2017-10-30), `whois panelyze.io` (not found)
- In the repo: `git grep -i panelyze`, `git grep -i manga-panel-splitter`, `~/Applications/Panelyze.app/Contents/Info.plist`
