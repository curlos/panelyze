# 19 — A working app anyone can download from GitHub

> **Being built as part of [spec 40](40-housekeeping-and-release.md)** (2026-11-23). Where they differ, spec 40 is newer.

New roadmap idea. Researched 2026-11-19. Planning only.

## 1. Summary
The build script already makes an Apple Silicon `Panelyze.app` and a zip, and the README already links to "Download for Mac". But **the repo has no releases yet** (GitHub API: 0), so the link leads nowhere. The simplest path: build locally (after spec 02 passes), upload the zip to a GitHub Release by hand with `gh release create`, keep it unsigned with the "Open Anyway" steps the README already has. Automating it with GitHub Actions and paid signing are optional later steps.

## 2. Is it doable?
Yes. The zip is far under GitHub's limit. Mac (Apple Silicon) only is easy now. Windows/Linux are possible but are separate, bigger projects.

## 3. What's already true (claims checked)
| Claim | Check | Status |
|---|---|---|
| The build makes `dist/Panelyze.app` + `dist/Panelyze-macOS-AppleSilicon.zip` | Script yes. `dist/` today has the app (**690 MB**) and a duplicate `dist/Panelyze` folder (688 MB, PyInstaller's onedir output) but **no zip**. Zipping the current app with `ditto` gave **348 MB**. The next build adds ~25 MB (coremltools 17 MB, spandrel 3 MB, upconv_7 model). | ✅ (expect ~710 MB app, ~360 MB zip) |
| Upload the zip to a GitHub release | Repo `curlos/manga-panel-splitter` is **public**, **0 releases**. README's `releases/latest` link is broken today. | ⚠️ no release exists |
| GitHub file size limit | Docs: "Each file included in a release must be under **2 GiB**", up to 1000 assets per release, no total-size or bandwidth limit. | ✅ |
| "Only runs on Apple Silicon" | Executable is `Mach-O arm64` (thin), minimum macOS **11.0**. | ✅ |
| Intel Mac build is possible | PyTorch stopped Intel Mac wheels after **2.2.x**; the app needs torch **2.5.1**. | ⚠️ not without downgrading torch — skip Intel |
| Signed? | `codesign -dv`: **ad hoc**, no Team ID. | ✅ |
| README's install steps ("Done" → Privacy & Security → Open Anyway) | Matches current macOS: Sequoia removed the right-click → Open shortcut; Open Anyway in Privacy & Security is the way now. Apple Silicon needs at least an ad hoc signature (it has one). | ✅ |
| `xattr -d com.apple.quarantine` workaround | Still works (removes the flag Gatekeeper checks), but it's a Terminal step and experts advise against it for downloaded code. | ✅ works, keep as a footnote only |
| Signing + notarization cost | Apple Developer Program **$99/year**; notarization itself is free. Several 2026 forum reports of new accounts stuck for weeks with "Team is not yet configured for notarization". | ✅ |
| Models ship inside vs download on first run | Already split well: the **87 MB** panels Magi model and waifu2x (~34 MB) ship inside; the **2 GB** full Magi (video text) and the **592 MB** "Best" zips download on first use. | ✅ keep as is |
| Version in the app | Stale build's `Info.plist` says `0.0.0` though the script passes `--product-version 1.0.0`. | ⚠️ recheck after next build |
| Flet window app | Bundled as `flet_desktop/app/flet-macos.tar.gz` (47 MB), unpacked when the app first starts. | ✅ (risk: see 8) |
| No CI | No `.github/` folder. | ✅ |
| GitHub Actions macOS runners | Standard runners are **free and unlimited for public repos**. arm64: `macos-15` / `macos-26` / `macos-latest` (=26 since June 2026): **3-core M1, 7 GB RAM, 14 GB SSD, no MPS** (Apple Virtualization limit). Intel: `macos-15-intel`/`macos-26-intel`, x86_64 support ends fall 2027. `macos-14` is retired (Nov 2026). | ✅ |
| Windows/Linux builds | `flet pack` (PyInstaller) can't cross-compile: build on each OS. Most code is portable (`open_directory` handles all 3), but paths like `~/Library/Application Support` and `~/Library/Logs` are Mac-style, `get_waifu2x_path` looks for a name without `.exe`, and `build_mac_app.sh` uses Mac-only tools (`sips`, `iconutil`, `ditto`). waifu2x has Windows (35 MB) and Linux (37 MB) zips. | ✅ feasible, separate work |

## 4. Recommended approach + rejected alternatives
| Choice | Recommended | Rejected (why) |
|---|---|---|
| Where to build | **Locally** on the M1 with `./build_mac_app.sh` (it self-tests before zipping). | GitHub Actions first (more moving parts: the Magi panels model isn't in git, 14 GB disk, no MPS for the self-test — doable later). |
| How to publish | `gh release create v1.0.0 dist/Panelyze-macOS-AppleSilicon.zip --title ... --notes ...` | Git LFS / committing binaries (wrong tool; 100 MB file limit). |
| Signing | **Unsigned (ad hoc)** + the README's Open Anyway steps, already written. | Developer ID + notarization now ($99/yr, entitlements for torch/PyInstaller, possible weeks-long account setup). Good later if many non-technical users. `xattr` as the main instruction (Terminal step). |
| CPU type | **Apple Silicon only**. | Intel / universal2 (torch 2.5.1 has no Intel Mac wheel). |
| Models | Keep the current split (small ones inside, big ones on first use). | Shipping all models (zip would be ~1 GB+ with 592 MB of "Best" zips and 2 GB Magi → near the 2 GiB limit, mostly unused). |
| Windows/Linux | Separate roadmap item (users run from source until then). | Doing it now (path, `.exe`, build-script, and testing work on a machine the user doesn't test on). |
| Automation (later) | One `.github/workflows/release.yml` on `macos-15`, triggered by a `v*` tag: set up venv from `requirements-lock.txt`, fetch the panels model (cache it, or attach it once to a release and `curl` it), run `build_mac_app.sh`, upload the zip with `gh release upload`. | `xlarge` runners (paid, $0.102/min). |

## 5. Files to change + functions to reuse
| File | Change |
|---|---|
| none (step 1) | Release by hand with `gh`. |
| `README.md` | Only if needed: confirm the zip name and the Open Anyway steps; add one line "Terminal alternative: `xattr -dr com.apple.quarantine /Applications/Panelyze.app`". |
| `build_mac_app.sh` | Only if the `0.0.0` version persists: one line to set `CFBundleShortVersionString` with `plutil`. Optionally `rm -rf dist/Panelyze` (the 688 MB duplicate folder). |
| `.github/workflows/release.yml` | Later, new file, ~40 lines. |

| Reuse | Where |
|---|---|
| Whole build + self-test + zip | `build_mac_app.sh` |
| `run_self_test` | `self_test.py` (via `--self-test` in `gui.py`) |
| `magi.build_panels_model_file`, `PANELS_MODEL_FILE` | `magi.py` |
| `is_running_as_packaged_app`, `get_waifu2x_path` | `utils.py` |

## 6. Steps
- [ ] Finish spec 02 part A (build passes its self-test, "Best" works in the built app).
- [ ] Do spec 21's new-user-account test with the zip downloaded **through a browser** (so it has the quarantine flag, like a real user).
- [ ] Check the app version in `Info.plist`; fix with `plutil` in the script only if it's still `0.0.0`.
- [ ] User picks the version tag (suggest `v1.0.0`) and release notes (what works, Apple Silicon only, first-run downloads, non-commercial model licenses, Open Anyway steps).
- [ ] User runs (or OKs) `gh release create v1.0.0 dist/Panelyze-macOS-AppleSilicon.zip ...`.
- [ ] Click the README's Download link and confirm it reaches the zip.
- [ ] Later (optional): add `release.yml` for tag-triggered builds on `macos-15`.
- [ ] Later (optional): Apple Developer account, Developer ID signing + `notarytool` + `stapler`.
- [ ] Later (optional): new roadmap items for Windows and Linux builds.

## 7. How to test it
- Download the zip from the release page in Safari, in a new macOS user account (spec 21), unzip, drag to Applications, follow the README's steps exactly, and run: MangaDex download (Dragon Ball ch. 93, pages 1–3) → Panel-By-Panel → Upscale (Fast and Best) → Video.
- Check the log at `~/Library/Logs/Panelyze/panelyze.log` for errors.

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | Small for a manual release (an hour after spec 02). Medium for CI. Medium–large for signing. Large for Windows/Linux. |
| Value | High: it's the only way non-developers can try the app, and the README already promises it. |
| Risk | The Flet window app is unpacked from a tar.gz at first start; Gatekeeper's handling of that on a quarantined download is untested. The new-user test will show it. |
| Risk | Unsigned apps scare some users; the Open Anyway flow has changed between macOS versions (15.1 had a bug). |
| Risk | Model licenses (Magi, MangaJaNai: non-commercial). Fine for a free release; already in the README. |
| Risk | CI: 14 GB disk and 7 GB RAM on `macos-15`; Magi full model (2 GB) needed only to make the 87 MB panels model. |
| Open | Version number and who presses "publish"? |
| Open | Is $99/year for signing worth it now, or later? |
| Open | Remove the duplicate `dist/Panelyze` folder in the build script? |
| Open | Windows next (the user has a Windows PC), or not? |

## 9. Sources
- [GitHub Docs: About releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases) (2 GiB per file, 1000 assets)
- [GitHub Docs: GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) (specs, free for public repos, no nested virtualization / MPS)
- [GitHub changelog: macOS 14 runner retirement](https://github.blog/changelog/2026-10-01-github-actions-macos-14-runner-image-retirement), [macOS 26 GA](https://github.blog/changelog/2026-02-26-macos-26-is-now-generally-available-for-github-hosted-runners/)
- [GitHub Docs: Actions runner pricing](https://docs.github.com/en/billing/reference/actions-runner-pricing)
- [Sequoia removes Gatekeeper contextual-menu override (Michael Tsai)](https://mjtsai.com/blog/2024/07/05/sequoia-removes-gatekeeper-contextual-menu-override), [Eclectic Light: running code that hasn't been notarised (Aug 2026)](https://eclecticlight.co/2026/08/11/how-can-you-run-code-that-hasnt-been-notarised/)
- [Apple Developer forums: fee and notarization](https://developer.apple.com/forums/thread/746992), [stuck "Team is not yet configured" report](https://developer.apple.com/forums/thread/825151)
- [PyTorch macOS x86 deprecation](https://dev-discuss.pytorch.org/t/pytorch-macos-x86-builds-deprecation-starting-january-2024/1690)
- [Flet: Packaging with flet pack](https://flet.dev/docs/publish/using-pyinstaller)
- [waifu2x-ncnn-vulkan 20250915 release](https://github.com/nihui/waifu2x-ncnn-vulkan/releases/tag/20250915) (asset sizes via `gh`)
- Local: `dist/` inspected read-only (`du`, `codesign -dv`, `otool`, `plutil`), `gh api .../releases` → 0.
