# 14. Folder structure: move the Python files out of the repo root

Related: [#15 format, lint and CI](15-format-lint-ci.md) · [#18 type-check fixes](18-type-check-fixes.md) · [#23 cleanup](23-cleanup.md) · [#25 full code review](25-full-code-review.md)

## 1. Summary
Today, 14 Python files sit loose in the repo root next to docs, scripts and data folders. The plan: put all app code in one `panelyze/` folder, with 3 subfolders (`core/`, `tools/`, `gui/`). `gui.py` stays in the root as the only entry point. It's one mechanical step: `git mv` the files, then update the import lines. No code logic changes.

## 2. Is it doable?
Yes. It's medium-sized but low-risk, because every break shows up right away as an `ImportError` in the 203 fast tests or the self-test. Keeping `gui.py` in the root means `flet run gui.py`, `flet pack gui.py`, `npm run …` and the hand-made Dock launcher (`venv/bin/python gui.py`) don't change.

## 3. What's already true (checked 2026-11-19)
| Fact | Number / detail |
|---|---|
| Python files in the root | 14: `gui.py`, `magi.py`, `janai.py`, `waifu2x.py`, `utils.py`, `default_settings.py`, `download_from_mangadex.py`, `copy_panels_to_one_level_directory.py`, `VideoCreatorFromImages.py`, `TextToSpeech.py`, `SpeechTextParser.py`, `EmotionAnalyzer.py`, `DrawBoxCoords.py`, `self_test.py` |
| `gui_classes/` | 23 files, **no `__init__.py`** (works as a "namespace package") |
| `magi_model/` | 4 vendored `.py` files + 2 configs + the 87 MB `panels_fp16.safetensors` (git-ignored) |
| Import lines that name a project module | **184 lines in 53 files** (the 14 root files, `gui_classes/`, `tests/`) |
| String patch targets in tests | 5: `"magi.get_magi"` ×2 (test_panel_output), `"gui.show_all_output_in_app"` (fake_gui), `"gui_classes.ProgressPanel.current_progress_panel"` and `"gui_classes.UpscaleImagesView.get_waifu2x_path"` (test_progress) |
| Paths built from `__file__` | 1: `magi.py:25` `MAGI_MODEL_DIRECTORY = dirname(__file__)/magi_model` |
| Tests find the code with | `tests/conftest.py:7` puts the repo root on `sys.path`. That stays. |
| PyInstaller (`build_mac_app.sh`) | `--paths=$REPO_DIR`, `--add-data magi_model:magi_model`, `--hidden-import=magi_model.modelling_magiv2`, and step 2 runs `python -c "import magi …"` |
| Docs that link `.py` files | DEVELOPING.md (3), HANDOFF.md (9), magi_model/README.md (1), plus prose mentions |

**Normal Python layouts:**

| Layout | What it is | Who uses it |
|---|---|---|
| Flat (today) | Modules in the repo root | Small scripts and quick apps. Gets messy after about 10 files. |
| Package | `repo/panelyze/…` with `__init__.py`, and an entry script or `python -m panelyze` | Most apps (Django projects, Flet examples, many PyInstaller apps) |
| src | `repo/src/panelyze/…`. Needs `pip install -e .` and a `[project]` build section in pyproject.toml | Libraries published to PyPI, to stop tests importing the un-installed copy |

## 4. Recommended approach
**A package layout, with `gui.py` kept in the root and file names unchanged.**

```
gui.py                      (stays: the entry point)
panelyze/
  __init__.py               (empty)
  core/      utils.py, default_settings.py, self_test.py
  tools/     magi.py, janai.py, waifu2x.py, download_from_mangadex.py,
             copy_panels_to_one_level_directory.py,
             VideoCreatorFromImages.py, TextToSpeech.py, SpeechTextParser.py,
             EmotionAnalyzer.py, DrawBoxCoords.py
  gui/       (all 23 files from gui_classes/)
  magi_model/ (moved as is, weights included)
tests/  (stays at the root, same files)
```

| Option | Verdict | Why |
|---|---|---|
| **Package, `gui.py` stays in the root, keep file names** | ✅ Recommended | One mechanical step. No change to how the app is run, packaged or launched. |
| Package and also rename files to snake_case (`video_creator.py`, …) | ❌ Not now | Doubles the diff and the risk. Could be a separate later step. |
| `src/` layout | ❌ | Needs an editable install and a build config. PyInstaller and `flet run` need extra path setup. No benefit for an app that isn't published to PyPI. |
| Move `gui.py` into the package too (`python -m panelyze`) | ❌ | Changes `flet run`, `flet pack`, package.json, the Dock launcher and the docs, for no real gain. |
| One package folder with no subfolders | 🟡 Fine too | Simpler (`panelyze/magi.py`), but 37 files in one folder. Pick this if `core/tools/gui` feels like too much. |
| Leave it flat | 🟡 | Works. The root just stays cluttered. |

## 5. Files to change, and file-by-file moves
| From | To | Imports to fix inside it |
|---|---|---|
| `utils.py` | `panelyze/core/utils.py` | 3 (`gui_classes.AppOutput` ×2, `janai`) |
| `default_settings.py` | `panelyze/core/default_settings.py` | 0 |
| `self_test.py` | `panelyze/core/self_test.py` | 5 |
| `magi.py` | `panelyze/tools/magi.py` | 11, **plus `MAGI_MODEL_DIRECTORY`** (now `dirname(dirname(__file__))/magi_model`) |
| `janai.py` | `panelyze/tools/janai.py` | 1 |
| `waifu2x.py` | `panelyze/tools/waifu2x.py` | 1 |
| `download_from_mangadex.py` | `panelyze/tools/` | 2 |
| `copy_panels_to_one_level_directory.py` | `panelyze/tools/` | 0 |
| `VideoCreatorFromImages.py` | `panelyze/tools/` | 5 |
| `TextToSpeech.py` | `panelyze/tools/` | 2 |
| `SpeechTextParser.py` | `panelyze/tools/` | 2 |
| `EmotionAnalyzer.py` | `panelyze/tools/` | 0 |
| `DrawBoxCoords.py` | `panelyze/tools/` | 2 |
| `gui_classes/*.py` (23) | `panelyze/gui/*.py` | about 85 lines in total (`from gui_classes.X` → `from panelyze.gui.X`) |
| `magi_model/` | `panelyze/magi_model/` | 0 (it uses relative imports) |
| `gui.py` | stays | 13 |
| `tests/*.py` | stay | about 60 lines + the 5 string patch targets |
| `build_mac_app.sh` | – | `--add-data "$REPO_DIR/panelyze/magi_model:panelyze/magi_model"`, `--hidden-import=panelyze.magi_model.modelling_magiv2`, step 2 → `import panelyze.tools.magi as magi` |
| `.gitignore` | – | `magi_model/*.safetensors` → `panelyze/magi_model/*.safetensors` |
| `package.json` `dev` | – | Nothing has to change. `experiments,tests,…` stay in `--ignore-dirs`. |
| DEVELOPING.md, HANDOFF.md, README.md, magi_model/README.md | – | Update the file paths in links |
| `pyproject.toml` (from #15), if it's done first | – | Exclude `panelyze/magi_model` instead of `magi_model` |

Import style: absolute everywhere (`from panelyze.core.utils import time_it`). No relative imports, so the files read the same as today.

**What's reused:** nothing new is written. `tests/conftest.py` already puts the root on `sys.path`, so `import panelyze` works in tests, Pylance and PyInstaller (`--paths=$REPO_DIR`).

## 6. Steps
- [ ] Do this right after #15's formatting commit (or before #15), never mixed with logic changes.
- [ ] `mkdir -p panelyze/core panelyze/tools` and add empty `__init__.py` files (`panelyze/`, `core/`, `tools/`, `gui/`).
- [ ] `git mv` each file as in the table (`git mv gui_classes panelyze/gui`, `git mv magi_model panelyze/magi_model`). The ignored weights file moves with the folder on disk.
- [ ] Rewrite the import lines with one scripted find-and-replace (a module-name map), then search the code for leftovers: `grep -rnE "^(from|import) (utils|magi|janai|gui_classes|…)\b"`.
- [ ] Fix `MAGI_MODEL_DIRECTORY` in `magi.py`.
- [ ] Update the 5 string patch targets in the tests.
- [ ] Update `build_mac_app.sh` (3 lines) and `.gitignore` (1 line).
- [ ] Update the doc links.
- [ ] Delete the stale `__pycache__/` folders (see #23), so old `.pyc` files can't hide a missed import.

## 7. How to test it
| Check | Expected |
|---|---|
| `npm run test` | 203 passed, as before |
| `npm run self-test` | Passes (loads Magi from the new `magi_model` path) |
| `npm run dev`, then click through every tab | No `ImportError` in Terminal Output |
| Flet web mode + Playwright screenshots (see #25) | Same screens as before |
| `git log --follow panelyze/tools/magi.py` | Shows the old history (`git mv` keeps it) |
| `./build_mac_app.sh` | Builds, and the built app passes its self-test (this also checks the `--add-data` path) |
| `npm run test:all` | 9 e2e tests pass |

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | Medium in lines (about 190 one-line changes), small in thinking. About 1–2 hours with testing. |
| Value | Medium: a cleaner root, a clear "where does this go" rule, and cleaner tool configs (#15 can just say `include = ["panelyze", "tests", "gui.py"]`). |
| Risk: lazy imports inside functions | `magi.py` and `utils.py` import inside functions (e.g. `from gui_classes.ProgressPanel import report_progress`). Those only fail when that code runs. The grep step and the e2e tests cover them. |
| Risk: the packaged app | The `magi_model` data path. Covered by the build's self-test. |
| Risk: open branches/stashes | 2 old stashes (see #23) won't apply cleanly afterwards. |
| Note | `utils.py` (core) imports `gui_classes.AppOutput` (gui). That's a small tangle worth fixing later, but not in this step. |
| Open question | 3 subfolders (`core/tools/gui`) or one flat `panelyze/` folder? |
| Open question | Rename to snake_case later, in a separate step? |

## 9. Sources
- Python Packaging User Guide, "src layout vs flat layout": https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/
- PyInstaller `--add-data` / `--paths`: https://pyinstaller.org/en/stable/usage.html
- Repo checks: `grep` of import lines, `build_mac_app.sh`, `tests/conftest.py`, `magi.py:25`
