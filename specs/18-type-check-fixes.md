# 18. Type-check fixes: the red Pylance lines

Related: [#14 folder structure](14-folder-structure.md) · [#15 format, lint and CI](15-format-lint-ci.md) · [#23 cleanup](23-cleanup.md) · [#25 full code review](25-full-code-review.md)

## 1. Summary
The red lines come from Pylance (Pyright) in **"standard"** mode, which is set in the user's VS Code settings. A read-only Pyright run found **163 errors**:
- **75** are in `magi_model/`. That's model code copied unchanged from Hugging Face, so it should simply be excluded.
- **88** are in the app code. **About 20 point at something worth fixing**: a value that can really be `None`, a wrong Flet enum, or an argument typed without `None` in its signature.
- The rest come from loose library type info (torch, transformers, PIL, matplotlib, moviepy, coremltools) and Flet's `control.page` being "maybe None". Those get small fixes or a config setting.

The goal: **0 errors**, with as few code changes as possible, so the Pyright step in CI (#15) can block bad changes.

## 2. Is it doable?
Yes. Most fixes are one line each: add `| None` to a signature, add a guard, use the right enum. No logic changes. The rest is config.

## 3. What's already true (measured 2026-11-19, Pyright 1.1.414, `--pythonpath venv/bin/python`)
| Fact | Number |
|---|---|
| User's Pylance mode | `"standard"` (VS Code user settings). Nothing in the repo sets a mode. |
| Errors, all tracked `.py` files | 163 errors, 0 warnings, 62 files, 8 s |
| …in vendored `magi_model/` | 75 (`modelling_magiv2.py` 56, `utils.py` 7, `configuration_magiv2.py` 6, `processing_magiv2.py` 6) |
| …in the app code | **88** (the same in basic mode: 82, so it's not because "standard" is strict) |
| Missing imports / missing stubs | **0**. Everything resolves with the venv. The red lines are not "library not found". |

**App-code errors by file:** magi.py 10 · SettingsBase.py 8 · EmotionAnalyzer.py 8 · janai.py 5 · tests/test_utils.py 5 · utils.py 4 · tests/test_magi.py 4 · 3 each: DrawBoxCoords, VideoCreatorFromImages, MangaDexDownloaderView, PickInputAndOutputDirectories, PipelineView, UpscaleImagesView, test_panel_output · 2 each: TextToSpeech, gui.py, HighlightTextBoxesInImages, SettingsUpscaleImages, TerminalOutput, test_layout, waifu2x · 1 each: 10 other files.

**App-code errors by kind:**

| # | Category | Count | Real problem? | Example | Fix |
|---|---|---|---|---|---|
| A | Flet `control.page` (and the app's slots) may be `None` | 18 | Mostly no. They run after the control is on screen. But HANDOFF warns that controls not on screen have `page == None`, so each one is a crash if it's ever called early. | `SettingsBase.py:20` `self.page.client_storage.set(...)` | One small helper in `SettingsBase` (e.g. a `client_storage` property that uses `self.page`, else `parent_gui.page`), or `assert self.page`. Or set the rule to warning (see below). |
| B | Wrong Flet enum or type passed | 6 | **Yes, small.** They work by luck: the values match as text. | `HighlightTextBoxesInImages.py:64,101` `vertical_alignment=ft.VerticalAlignment.CENTER` on a `Row` (should be `ft.CrossAxisAlignment.CENTER`). `gui.py:49` `theme_mode = "dark"` (should be `ft.ThemeMode.DARK`). `SettingsUpscaleImages.py:72,89` `Option(int)` (should be `str(...)`). `SettingsBase.py:61` `inner_content` isn't declared on the base. | Use the right enum, `str()`, or declare the attribute |
| C | Library type info (torch, transformers, PIL, matplotlib, moviepy, coremltools) | 26 | No | `magi.py:359` `.to(get_device())`, `EmotionAnalyzer.py:78` pipeline result, `Image.LANCZOS` ×4, `add_axes([..])`, `with_position` | `Image.Resampling.LANCZOS` (4 lines, the new Pillow name). A tuple for `add_axes`. The rest get `# pyright: ignore[rule]` on the line, or `cast(...)`. |
| D | `= None` default but the type says it can't be `None` | 6 | **Yes (wrong annotation)**, harmless at runtime | `download_from_mangadex.py:169` `terminal_output_list_view: ft.ListView = None`, `utils.py:182`, `magi.py:453` `float | None` passed on as `float` | Add `| None` to the signature (2 signatures fix all 6) |
| E | Possibly unbound variable | 5 | No in janai/Pipeline (the logic guarantees it). Test 1 is harmless. | `janai.py:238` `tile_size`, `PipelineView.py:540` `step` | Set the variable before the `if`/loop (1 line each) |
| F | A value may be `None` (`str | None`, `IO | None`) | 18 | **Partly real** | `waifu2x.py:39` `realpath(get_waifu2x_path())` crashes if waifu2x is missing (callers check first, so it's only a guard). `VideoCreatorFromImages.py:170` `full_output_directory=None` default but then `os.path.join(None…)`. `TextToSpeech.py:261,264` the Azure `result` may be `None`. `PipelineView.py:555` the URL `str | None`. `utils.py:205` `process.stdout`. Tests: 9. | A guard or `assert` with a clear message. In tests, `assert x is not None`. |
| G | Tests: fakes and mocks | 7 | No | `fake_gui.py:96` `FakePage` passed as `Page`, `test_layout.py:23` `.on_click` on `Control` | `cast(...)`, or turn these rules off only for `tests/` |
| H | Windows-only `os.startfile` | 1 | No | `utils.py:21` | `# pyright: ignore[reportAttributeAccessIssue]` |
| I | The base method's return type is guessed as `None` | 1 | No | `JobView.get_next_tab_input_directory` returns `None`. The `MagiPanelByPanelView` override returns `str`. | Annotate the base `-> str | None` |

**Real-problem total: about 20** (B 6, D 6, the real part of F about 8). The rest (about 68) are noise to configure or quiet with tiny edits.

## 4. Recommended approach + rejected alternatives
**Exclude the vendored code, fix B, D, E, F, H and I in the code, fix A with one helper, quiet C and G line by line.** Keep "standard" mode, so CI and the user's Pylance agree.

| Option | Verdict | Why |
|---|---|---|
| **Exclude `magi_model/`, fix about 40 lines, `# pyright: ignore[rule]` on about 25 library lines** | ✅ | Gets to 0 errors with small, readable changes. Each ignore names its rule, so it's clear why it's there. |
| Set `typeCheckingMode = "basic"` | ❌ | Still 82 errors. Almost no change. |
| `"off"` | ❌ | Hides the real ones too |
| Turn `reportOptionalMemberAccess` and `reportArgumentType` down to "warning" for the whole repo | 🟡 Fallback | 1 config line instead of about 18 edits for category A. But yellow lines would stay, and real `None` bugs (F) would show as warnings only. Could be used just for `tests/` via `executionEnvironments`. |
| Add type annotations everywhere | ❌ | A massive change, against CLAUDE.md's "simplicity" |
| Fix the vendored `magi_model/` code | ❌ | It's meant to stay identical to the upstream copy (`magi_model/README.md`) |
| Install extra stub packages | ❌ | There are no missing-stub errors |

## 5. Files to change + what's reused
| File | Change | Errors fixed |
|---|---|---|
| `pyproject.toml` (from #15) | `exclude` adds `magi_model`, `experiments`. Mode `"standard"`. | 75 |
| `gui_classes/SettingsBase.py` | One `client_storage` property (reuses the `parent_gui.page` pattern already used across the views). `inner_content = None` declared in `__init__`. | 8 |
| `gui_classes/MangaDexDownloaderView.py`, `PickInputAndOutputDirectories.py`, `SettingsMangaDexDownloader.py`, `TextToSpeechAzure.py`, `TerminalOutput.py`, `gui.py` | Use the helper, or `assert self.page` | 11 |
| `gui_classes/HighlightTextBoxesInImages.py` | `ft.CrossAxisAlignment.CENTER` ×2 | 2 |
| `gui.py:49` | `ft.ThemeMode.DARK` | 1 |
| `gui_classes/SettingsUpscaleImages.py` | `ft.dropdown.Option(str(x))` ×2 (check that the saved setting stays a string) | 2 |
| `download_from_mangadex.py`, `utils.py`, `magi.py` (`get_grown_panels`) | `| None` in signatures | 6 |
| `janai.py`, `gui_classes/PipelineView.py` | Set variables before the `if` or loop | 4 |
| `gui_classes/JobView.py` | `-> str | None` | 1 |
| `waifu2x.py`, `VideoCreatorFromImages.py`, `TextToSpeech.py`, `utils.py`, `PipelineView.py:555`, `janai.py:160,270` | Guards or asserts | about 9 |
| `UpscaleImagesView.py`, `utils.py` | `Image.Resampling.LANCZOS` | 4 |
| `magi.py`, `EmotionAnalyzer.py`, `DrawBoxCoords.py`, `VideoCreatorFromImages.py:421`, `utils.py:21` | `# pyright: ignore[...]`, or a tuple / `cast` | about 23 |
| `tests/*` (8 files) | `assert x is not None`, `cast`, or ignores | 16 |

## 6. Steps
- [ ] Do it after #15's formatting commit, so the diff only shows real changes.
- [ ] Add the `[tool.pyright]` section (#15 draft) and check: about 88 errors left.
- [ ] Fix category B (the wrong enums), then run the fast tests and look at the UI in web mode.
- [ ] Fix D, E and I (annotations and variable setup).
- [ ] Fix F (guards or asserts with clear messages).
- [ ] Add the `SettingsBase` helper for A, and use it in the views.
- [ ] Use `Image.Resampling.LANCZOS`, then add the line ignores for C and H.
- [ ] Tests (G and the test part of F).
- [ ] `npx pyright` shows 0 errors. In #15's CI, remove `continue-on-error`.
- [ ] Check in VS Code: the red lines are gone (reload the window once).

## 7. How to test it
| Check | Expected |
|---|---|
| `npx --yes pyright@1.1.414 --pythonpath venv/bin/python` | `0 errors` |
| `npm run test` | 203 passed |
| `npm run self-test` | Passes |
| Flet web mode + Playwright screenshots of Settings and Images To Video (highlight row) | Alignment unchanged |
| Upscale tab: pick each upscale ratio, restart the app | The choice is remembered (checks the `Option(str(...))` change) |
| Pylance in VS Code | No red lines in the app files |

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | Small–medium: about 60 one-line edits in about 30 files, plus config. About 2 hours. |
| Value | Medium–high: the editor stops crying wolf, about 20 small real issues get fixed, and CI can block new type bugs. |
| Risk | Changing a dropdown option from int to str could change what's saved in settings. Test that settings are remembered. |
| Risk | The `assert`s run in the packaged app too. Use clear messages, and only assert things that are always true. |
| Open question | Category A: the helper (18 edits, recommended) or turn `reportOptionalMemberAccess` down to warning (1 line)? |
| Open question | Tests: fix them (16 small edits) or relax the rules only for `tests/`? |

## 9. Sources
- Pyright configuration and rule defaults by mode: https://github.com/microsoft/pyright/blob/main/docs/configuration.md
- Pyright comment-based ignores: https://github.com/microsoft/pyright/blob/main/docs/comments.md
- Pillow `Image.Resampling`: https://pillow.readthedocs.io/en/stable/reference/Image.html#resampling-filters
- Measured: `npx pyright@1.1.414 --outputjson` on all tracked `.py` files and on the app code only (basic and standard). Classification script and outputs in the session scratchpad.
