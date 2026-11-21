# 11. Smaller ideas

Checked on 2026-11-19 on the user's Mac: a **MacBook Air M1** (`MacBookAir10,1`, no fan, 16 GB). ✅ = checked today against the real code or a new measurement, ⚠️ = an older note that's out of date or couldn't be confirmed.

| # | Idea | Verdict | Size | Value |
|---|---|---|---|---|
| A | [Faster video writing](#a-faster-video-writing) | 🟢 one-line change worth trying; a bigger win is possible later | Tiny | Low–Medium |
| B | [A launcher script in the repo](#b-a-launcher-script-in-the-repo) | 🟢 | Small | Low–Medium |
| C | [The unexplained GPU outlier](#c-the-unexplained-gpu-outlier) | ⚪ close it: still unreliable, and it barely matters now | — | Low |
| D | [Heat during long runs](#d-heat-during-long-runs) | 🟢 log the time per chapter, and measure during the first whole-series test | Tiny | Medium (for whole-series runs) |

---

## A. Faster video writing

**1. Summary.** Writing the video file has two parts: drawing the frames, and mixing the voice-over audio. New measurements show **the audio is the bigger part** (about 24 s for an 11-minute video), not the frame rate. Going from 5 to 2 frames per second still saves about 8 s of frame writing. It's a one-line change, but only safe when the video doesn't highlight text boxes.

**2. Is it doable?** Yes. The frame rate is set in one place.

**3. What's already true**
| Claim (ROADMAP) | Check |
|---|---|
| 5 frames per second is used with a voice-over | ✅ `VideoCreatorFromImages.py` lines 247–250: `fps = 1`, or `fps = 5` when highlighting text boxes or using text-to-speech |
| "Writing the video took about 48 s for a 10-minute video at 5 fps" | ⚠️ Not in benchmarks/ and no log found, so it can't be traced. Today's measurement is in the same range: **62 s for an 11.2-minute video at 5 fps, with audio** |
| Why 5 fps | The picture can only change on a frame. At 5 fps the panel changes within 0.2 s of its voice line; at 1 fps it can be up to 1 s off. With highlighting, each line gets its own image, so that matters most |

**New measurement** (throwaway script; 97 Shachou ch. 3 panels on a 1080p frame, moviepy 2.2.1, each panel 6.2–7.7 s, 11 min 12 s in total; a short tone as each panel's "voice-over"):

| How | Without audio | With audio (round 1) | With audio (round 2) |
|---|---|---|---|
| moviepy, 5 fps (now) | 15.5 s | 62.2 s | 200.1 s (an outlier, see D) |
| moviepy, 2 fps | 7.3 s | 31.4 s | — |
| moviepy, 1 fps | 5.5 s | 70.6 s | 34.5 s |
| Writing only the audio track (moviepy) | — | 24.2 s | — |
| ffmpeg directly, still images ("concat", no moviepy) | **2.5 s** (8.1 MB vs 12.1 MB) | not tried | — |

The runs with audio vary a lot from round to round (34–71 s for the same 1 fps video), and the Mac was busy with other work at the time, so only the no-audio numbers are reliable. The audio track alone took 24 s.

**4. Recommended approach and the alternatives**
| Option | Saves | Verdict |
|---|---|---|
| **5 → 2 fps when there's a voice-over but no highlighting** | About 8 s per 11-minute video (15.5 → 7.3 s for the frames). A panel change can be up to 0.5 s off its voice line | ✅ **Try first**: one line. Keep 5 fps when highlighting |
| Keep 5 fps, change nothing | — | ✅ Also fine: the gain is small next to Magi (minutes) |
| Write the video with ffmpeg directly (each panel shown for its exact time, no frames in between) | Frames 15.5 → 2.5 s, exact timing, smaller file | 🟡 Later. Replaces `get_clips` + `write_videofile`, and the audio would need its own ffmpeg step too. Not a small change |
| Build the audio track faster (join the mp3 files with ffmpeg instead of mixing them in moviepy) | Up to about 24 s | 🟡 Later, together with the row above |
| A faster encoder preset | 3.5 → 3.1 s on 20 panels | ❌ Already rejected (benchmarks/video.md) |

**5. Files to change.** `VideoCreatorFromImages.py`, lines 247–250 (the `fps` choice in the method that ends with `video.write_videofile`). Nothing else.

**6. Steps**
- [ ] Use `fps = 5` only when `self.highlight_text_boxes_in_images`, `fps = 2` for a voice-over without highlighting, and `fps = 1` otherwise
- [ ] Update the comment above it
- [ ] Run `npm test` (184 fast tests) and `-m e2e`
- [ ] Make one voiced Shachou ch. 3 video at 2 fps and watch whether panel changes still match the voice

**7. How to test it.** Time "Writing the video file..." on Shachou ch. 3 (97 panels, voiced, no highlighting) before and after, in fresh processes, one at a time. Watch the video for panels changing late.

**8. Size, value, risks, open questions**
| | |
|---|---|
| Size / value | Tiny / low (about 8 s per chapter; about 35 min over a 278-chapter series) |
| Risk | Panel changes up to 0.5 s off the voice. Low |
| Open questions | Is 0.5 s noticeable to the user? Is a bigger ffmpeg rewrite worth it later (about 30 s per chapter)? |

**9. Sources.** `VideoCreatorFromImages.py`; benchmarks/video.md; throwaway scripts in the session scratchpad (`vid/bench.py`, `vid/bench_audio.py`, `vid/bench_audio2.py`); moviepy 2.2.1 `write_videofile` (`venv/.../moviepy/video/VideoClip.py`).

---

## B. A launcher script in the repo

**1. Summary.** A small script, `make_mac_launcher.sh`, that rebuilds the one-icon Dock launcher `~/Applications/Panelyze.app`. Today it only exists on this Mac, made by hand, and the backup is gone.

**2. Is it doable?** Yes. Everything it needs is already in the venv and the repo.

**3. What's already true**
| Claim | Check |
|---|---|
| The launcher exists and was made by hand | ✅ `~/Applications/Panelyze.app`: `Contents/MacOS/Panelyze` is a bash script that exports `PATH` (venv + waifu2x), sets `FLET_VIEW_PATH` to `Contents/Resources/window`, `cd`s into the repo and runs `./venv/bin/python gui.py`. Info.plist: `com.curlos.panelyze`, `LSUIElement=true`, icon `Panelyze` |
| Flet's window app can be renamed and re-iconed with flet_cli | ✅ `venv/.../flet_cli/__pyinstaller/macos_utils.py` has `update_flet_view_icon(app_path, icon_path)` and `update_flet_view_version_info(app_path, bundle_id, product_name, product_version, copyright)`. Flet's window app ships as `venv/.../flet_desktop/app/flet-macos.tar.gz` |
| The icon file | ✅ `build_mac_app.sh` makes `build-assets/Panelyze.icns` with `iconutil` (not tracked in git, so the script must make it the same way if it's missing) |
| A backup | ⚠️ "A backup was in the old session's scratchpad": gone |
| Small oddity found | The launcher logs to `~/Library/Logs/Panelyze.log`, while the app itself logs to `~/Library/Logs/Panelyze/panelyze.log`. Two log files |
| Hard-coded paths | The launcher has the repo path and a long copy of the user's `PATH` built in |

**4. Recommended approach and the alternatives**
| Option | Verdict |
|---|---|
| **One bash script in the repo** that writes the bundle: the run script (repo path taken from where the script lives; `PATH` = `venv/bin` + `~/Downloads/waifu2x-ncnn-vulkan`), Info.plist, the icon, and Flet's window app unpacked from `flet-macos.tar.gz`, renamed and re-iconed with the two flet_cli functions, then `codesign --force --deep -s -` | ✅ **Recommended.** Same steps as last time, written down |
| `osacompile` / Automator app | ❌ Shows a second "Flet" icon in the Dock, the problem the hand-made launcher solved |
| Use the built `dist/Panelyze.app` | ❌ Runs the packaged copy, not the live code, and takes minutes to build |

**5. Files to change.** New: `make_mac_launcher.sh` (repo root, next to `build_mac_app.sh`, about 40 lines). Edit: `package.json` (a `make-launcher` script), `DEVELOPING.md` (one line). Reuse: `update_flet_view_icon` and `update_flet_view_version_info` (flet_cli `macos_utils.py`), the `iconutil` step from `build_mac_app.sh`.

**6. Steps**
- [ ] Write the script, with the destination as an option (default `~/Applications/Panelyze.app`)
- [ ] Build it into the scratchpad first and compare with the current launcher (same files, same Info.plist)
- [ ] Only then, with the user's OK, rebuild the real one (keep the old one as `Panelyze.app.bak`)
- [ ] Add `npm run make-launcher` and the DEVELOPING.md line
- [ ] Decide on the log-file question (below)

**7. How to test it.** Build it in the scratchpad, start it with `open`, check that the Dock shows one Panelyze icon and the app opens, then quit it. No Finder windows are needed.

**8. Size, value, risks, open questions**
| | |
|---|---|
| Size / value | Small / low–medium (a lost launcher today means redoing it by hand) |
| Risk | Overwriting the working launcher: avoided by building into a temporary folder first and keeping a backup |
| Open questions | 1. Keep the launcher's own `~/Library/Logs/Panelyze.log`, or drop it, since the app already logs to `~/Library/Logs/Panelyze/panelyze.log`? 2. Should a Flet upgrade re-run the script automatically? (No, keep it manual.) |

**9. Sources.** `~/Applications/Panelyze.app/Contents/MacOS/Panelyze` and `Info.plist`; `venv/lib/python3.12/site-packages/flet_cli/__pyinstaller/macos_utils.py`; `build_mac_app.sh`; HANDOFF.md ("Other").

---

## C. The unexplained GPU outlier

**1. Summary.** It was re-measured today, and the GPU is still unreliable on these 6 panels: 53–166 s, vs about 62–65 s on the CPU. So it's no one-off. The likely cause is the GPU's setup cost for every new image size (6 small, oddly shaped panels = 6 setups), plus whatever else the Mac is doing at the time. It barely matters now: the Pipeline reads text on **pages** (where the GPU wins clearly: 10.8 s vs 19.1 s), and only "highlight text boxes" still reads panels. **Recommendation: close it, with no code change.** Roadmap #7 (page reading with highlighting) removes the last case where it matters.

**2. Is it doable?** There's nothing to fix in Panelyze's code. A "use the CPU for small batches of panels" rule would be guesswork.

**3. What's already true**
| Claim | Check |
|---|---|
| "6 Shachou panels (17–22) once took 50.4 s on the GPU vs 40.0 s on the CPU" | ✅ benchmarks/magi.md, "Pages vs panels" table. One run only |
| "The GPU won everywhere else" | ✅ Same table: page 02 10.8 vs 19.1 s, its 8 panels 24.9 vs 52.6 s, page 03 11.1 vs 23.4 s |
| Why a new image size costs time on the GPU | ✅ benchmarks/magi.md explains it: the Mac GPU builds a program for each exact image size the first time it sees it |
| The 6 panels | ✅ Sizes (height × width): 427×942, 337×283, 336×176, 334×483, 617×260, 721×720. Small and all different |

**New measurement** (throwaway script calling `Magi.find_and_read_dialogue` on panels 17–22 from `~/Documents/Panelyze/Speed Test 2 - Shachou Ch 3 Full Pipeline` (that folder may be gone: to measure again, download Shachou ch. 3 from `https://mangadex.org/chapter/f54fb875-d732-42d2-9926-b25767ee4cda` into the spec's own folder (`~/Documents/Panelyze/<worktree-folder>/`) and run Panel-By-Panel); each run is a fresh process, then a second run in the same process; 14 lines read every time):

| Run | First time | Again, same process |
|---|---|---|
| GPU 1 | 166.1 s | 82.6 s |
| GPU 2 | 67.3 s | 81.5 s |
| GPU 3 | 71.4 s | 53.1 s |
| CPU | 64.5 s | 61.6 s |

⚠️ **Caveat:** all of these are slower than in Nov 2026's benchmark (50.4 / 40.0 s). The Mac was busy: the load average was about 20 during the runs (other work was running at the same time, probably other agents), and it came right after the video tests. So the absolute numbers aren't fair, but the pattern holds: on these panels the GPU swings widely and isn't faster than the CPU.

**4. Recommended approach and the alternatives**
| Option | Verdict |
|---|---|
| **Close it. Add one line to benchmarks/magi.md with today's numbers** | ✅ **Recommended** |
| Pick the CPU for small groups of different-sized panels | ❌ Guesswork, and the case is rare now |
| Pad panels to a few fixed sizes so the GPU reuses its setup | ❌ Magi shrinks every image itself; this would change the model's input and needs its own testing. Not worth it for a rare case |
| Do roadmap #7 (page reading with highlighting) | ✅ Removes the last case where panels are read. Planned separately |

**5. Files to change.** Only `benchmarks/magi.md` (one note under the table) and the roadmap row. No code.

**6. Steps**
- [ ] Add today's numbers and the caveat to benchmarks/magi.md
- [ ] Mark the roadmap row as ⚪ "looked into"
- [ ] (Optional) Re-run on an idle, cool Mac to get clean numbers: same script, one run at a time, nothing else running

**7. How to test it.** Nothing to test. To re-measure: the scratchpad script `outlier/run.py <mps|cpu> <panel folder>`.

**8. Size, value, risks, open questions**
| | |
|---|---|
| Size / value | Tiny / low |
| Risk | None |
| Open question | Does the user want a clean re-run on an idle Mac before closing it? |

**9. Sources.** benchmarks/magi.md; `magi.py` (`get_device`, `Magi.find_and_read_dialogue`); throwaway script in the session scratchpad (`outlier/run.py`).

---

## D. Heat during long runs

**1. Summary.** The Mac is a **fanless MacBook Air M1**, so it *will* slow itself down when it gets hot during long runs. That's expected, not a bug. The simple step: print how long each chapter took, so a long run shows any slowdown, and measure it once during the first whole-series test (roadmap #3).

**2. Is it doable?** Yes. Two lines in one place.

**3. What's already true**
| Claim | Check |
|---|---|
| "Benchmarks slowed down after long stretches of work" | ✅ benchmarks/magi.md: the same 27 pages took 162 s, then 179 s (+11%) in round 2; the old settings 173 → 216 s (+25%). Today's video test also gave 34.5 s, then 200.1 s for nearly the same work late in a long session |
| The Mac | ✅ `MacBookAir10,1` (MacBook Air M1). No fan, so it lowers its speed to stay cool |
| `pmset -g therm` | ✅ Works without sudo, but showed "No thermal warning level has been recorded" right after a long test session, so it doesn't catch this kind of slowdown. `powermetrics` would, but needs sudo |
| The app already logs per-chapter times | ❌ No timing is printed anywhere (`JobView.start_job` loops over chapters without timing) |

**4. Recommended approach and the alternatives**
| Option | Verdict |
|---|---|
| **Print "Chapter x of y took N s" in `JobView.start_job`** (shows in Terminal Output and the log file) | ✅ **Recommended.** Every tab and the Pipeline use it. It makes slowdowns visible in long runs at no cost |
| Measure during the #3 test run (3 chapters, then a volume) and write the numbers in benchmarks/ | ✅ Do it then. No code |
| Tips in the README for long runs (plugged in, on a hard surface or a stand, Low Power Mode off) | 🟡 Only if the measurement shows a big slowdown |
| A "cool-down pause" between chapters | ❌ Makes runs slower overall. The Mac already manages its own heat |
| Reading the temperature with `powermetrics` | ❌ Needs sudo |

**5. Files to change.** `gui_classes/JobView.py`, `start_job` (add `import time`, note the time before `self.process_image_folder(...)`, print how long it took after). Reuse: the existing `print` → Terminal Output → log file path.

**6. Steps**
- [ ] Add the per-chapter time line in `JobView.start_job`
- [ ] Check that a GUI test doesn't compare the exact Terminal Output text, then run `npm test`
- [ ] During roadmap #3's first test run, copy the per-chapter times into benchmarks/ (first chapters vs last)

**7. How to test it.** Run Panel-By-Panel on a 2-chapter folder and check the two "took N s" lines in Terminal Output and in `~/Library/Logs/Panelyze/panelyze.log`.

**8. Size, value, risks, open questions**
| | |
|---|---|
| Size / value | Tiny / medium for whole-series runs (it's how you'd notice a 10–25% slowdown) |
| Risk | None |
| Open questions | Is the user OK with one extra line per chapter in the Terminal Output? |

**9. Sources.** benchmarks/magi.md ("Final check"); `sysctl hw.model`; `pmset -g therm`; `gui_classes/JobView.py`.
