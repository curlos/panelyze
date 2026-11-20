# 15. Automatic formatting, linting, type checks and CI

Related: [#14 folder structure](14-folder-structure.md) · [#18 type-check fixes](18-type-check-fixes.md) · [#23 cleanup](23-cleanup.md) · [#25 full code review](25-full-code-review.md)

## 1. Summary
Add the Python version of "Prettier plus ESLint":
- **Ruff** formats the code and finds simple bugs.
- **Pyright** type-checks it. It's the same engine as the Pylance red lines in VS Code.
- **pytest** runs the fast tests.

They run in 3 places: when you save in VS Code, on every `git commit` (the pre-commit framework), and on every push in GitHub Actions CI. One `pyproject.toml` holds the settings for all of them.

## 2. Is it doable?
Yes, and it's small. The first formatting run changes a lot of lines, so it should be its own commit with nothing else in it. Pyright has 88 errors in the app code today (see #18), so in CI it only warns, and doesn't block, until #18 is done.

## 3. What's already true (measured 2026-11-19)
| Fact | Detail |
|---|---|
| Configs | No `pyproject.toml`, no `.pre-commit-config.yaml`, no `.github/workflows/`. `pytest.ini` exists. |
| VS Code (user settings) | `editor.formatOnSave: true` for Python, but **no Python default formatter set**. The Black extension is installed but isn't being used: the code isn't Black-formatted. `python.analysis.typeCheckingMode: "standard"`. |
| Repo `.vscode/settings.json` | Sets the venv interpreter, Pylance excludes and pytest |
| Tools | `uvx ruff` 0.17.6 and `npx pyright` 1.1.414 both run without installing anything into the venv |
| **First format diff** (app code; `magi_model/` and `experiments/` left out) | **line-length 120: 44 of 57 files change, about 1,320 lines (+/-)**. With line-length 88: 48 files, about 1,730 lines. Including the vendored `magi_model/` and the notebook: 53 files. |
| What the diff is | Mostly re-wrapping calls and brackets. Long comments and docstrings aren't touched (753 lines are over 88 characters, 243 over 120, most of them comments). |
| Ruff lint, classic rules (`E4,E7,E9,F`) on the app code | 15 findings: 14× E402 (on purpose: `gui.py` handles `--run-mangadex` and `--self-test` before importing Flet, and `tests/test_video.py`), plus 1× E712 (`gui.py:226` `!= False`). **No unused imports or undefined names.** |
| Plus bugbear (`B`) | 9× B905 (`zip()` without `strict=`, 7 of them in `magi.py`) |
| Ruff 0.16+ default rules | Ruff 0.16 expanded its default set to about 400 rules. With no config: 155 findings, many of them opinionated (BLE001 blind except ×22, RUF059 ×24, I001 ×49). **So the config must list `select` explicitly.** |
| Import sorting (`I`) | 44 files would be reordered. Risky in 2 spots: `DrawBoxCoords.py` calls `matplotlib.use("Agg")` between imports, and `gui.py` runs code before its imports. Left out at first. |
| Pyright | 163 errors in total. 75 are in the vendored `magi_model/`; **88 are in the app code** (details in #18). No missing-import errors when it uses `venv/bin/python`. |
| Fast tests | `pytest -m "not e2e"`: **203 passed, 9 deselected, 9.2 s**. The slowest test takes 0.33 s. |
| Tests that need models, GPU, internet or waifu2x | Only the 9 in `tests/test_e2e.py` (`pytestmark = pytest.mark.e2e`; `pytest.ini` has `addopts = -m "not e2e"`, so they're skipped by default). The fast tests fake Magi, waifu2x, edge-tts and MangaDex. |
| GitHub repo | `curlos/manga-panel-splitter` is **public**, so standard GitHub-hosted runners (macOS included) are free |

## 4. Recommended approach + rejected alternatives
**Ruff format + Ruff lint (a small rule set) + Pyright + pytest, in all 3 places:**

| Where | What runs | When |
|---|---|---|
| VS Code | The Ruff extension formats on save. Pylance shows the types (already on). | Every save |
| pre-commit (git hook) | `ruff check`, `ruff format` (only the staged files, under 1 s) | Every `git commit` |
| GitHub Actions | Ruff format check + lint on Ubuntu (about 10 s). pytest + Pyright on `macos-15` (Apple Silicon, like the app). | Every push and PR |

| Option | Verdict | Why |
|---|---|---|
| **pre-commit framework + CI + VS Code format-on-save** | ✅ | The commit hook catches what the editor missed, and CI catches what skipped the hook. That's the standard setup. |
| Claude Code `PostToolUse` hook (format after every Edit/Write) | 🟡 Optional extra | It keeps Claude's edits formatted, but not the user's own edits or commits. It's a 5-line `.claude/settings.json` entry, shown below. It's not needed if pre-commit is used, since pre-commit formats everything anyway. |
| CI only | ❌ | Formatting problems would only show up after pushing, as failed builds. |
| Black + isort + flake8 | ❌ | 3 tools instead of 1. Ruff's formatter matches Black's style and is much faster. |
| mypy instead of Pyright | ❌ | Pylance (what the user sees) is Pyright. Using the same engine means CI and the editor agree. |
| Pyright in the pre-commit hook | ❌ | About 11 s per commit and it needs the venv. Better in CI, and in VS Code where it's already running. |
| pytest in the pre-commit hook | 🟡 Optional, at `pre-push` | It takes 9 s. That's fine before a push, but annoying on every commit. |
| Line length 88 (Black's default) | 🟡 | More common, but about 400 more changed lines, and long calls get wrapped more often. |
| **Line length 120** | ✅ | A smaller first diff, and it's closer to how the code is written now |
| Turning on `I` (import sorting) and `UP` now | ❌ Later | 44 files re-ordered, with side-effect order risks. A separate later commit. |

## 5. Files to change + what's reused
| File | Change |
|---|---|
| `pyproject.toml` (new) | Only `[tool.ruff]` and `[tool.pyright]`. No `[project]` section, so nothing about installing changes. `pytest.ini` stays. |
| `.pre-commit-config.yaml` (new) | Ruff hooks |
| `.github/workflows/ci.yml` (new) | 2 jobs |
| `.vscode/settings.json` (existing) | Add `"[python]": {"editor.defaultFormatter": "charliermarsh.ruff"}` and recommend the extension |
| `.vscode/extensions.json` (new, optional) | `{"recommendations": ["charliermarsh.ruff", "ms-python.vscode-pylance"]}` |
| `requirements.txt` | Nothing. Ruff, pre-commit and Pyright run through `uvx`/`npx`, or pinned in CI. |
| `package.json` | Add `"lint": "uvx ruff check . && uvx ruff format --check ."`, `"format": "uvx ruff format ."`, `"typecheck": "npx --yes pyright@1.1.414 --pythonpath venv/bin/python"` |
| DEVELOPING.md | A short "Formatting and checks" section |
| Every `.py` file | The one formatting commit (`ruff format .`), done by the tool |

If #14 is done first, swap `magi_model` for `panelyze/magi_model` in the excludes.

### Draft `pyproject.toml`
```toml
# Settings for the code checkers only (Panelyze isn't installed as a package).
[tool.ruff]
line-length = 120
target-version = "py312"
extend-exclude = ["magi_model", "experiments", "venv-*", "testing-output", "build-assets", "dist", "storage", "test-chapter-cache"]

[tool.ruff.lint]
# Spelled out, because Ruff 0.16+ turns on ~400 rules by default.
select = ["E4", "E7", "E9", "F", "B"]
ignore = ["B905"]  # zip(strict=) — turn on later if wanted (#25)

[tool.ruff.lint.per-file-ignores]
"gui.py" = ["E402"]              # must handle --run-mangadex / --self-test before importing Flet
"tests/test_video.py" = ["E402"]

[tool.pyright]
include = ["."]
exclude = ["**/venv", "**/venv-*", "dist", "build-assets", "testing-output", "storage", "experiments", "magi_model", "**/__pycache__", "test-chapter-cache"]
pythonVersion = "3.12"
typeCheckingMode = "standard"    # same as the user's Pylance setting
# Rules turned down after #18 decides (examples):
# reportOptionalMemberAccess = "warning"
```

### Draft `.pre-commit-config.yaml`
```yaml
# Install once: uvx pre-commit install   (adds .git/hooks/pre-commit; nothing goes in the venv)
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.17.6
    hooks:
      - id: ruff-check
        args: [--fix]       # only safe fixes (e.g. unused imports)
      - id: ruff-format
  # Optional: fast tests before every push
  - repo: local
    hooks:
      - id: pytest-fast
        name: fast tests
        entry: venv/bin/python -m pytest -q
        language: system
        pass_filenames: false
        stages: [pre-push]
```

### Draft `.github/workflows/ci.yml`
```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/ruff-action@v3
        with:
          version: "0.17.6"
          args: "format --check"
      - uses: astral-sh/ruff-action@v3
        with:
          version: "0.17.6"
          args: "check"

  test:
    runs-on: macos-15          # Apple Silicon, same as the app (Core ML, MPS code paths import fine)
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: requirements-lock.txt
      - run: pip install -r requirements-lock.txt
      - name: Fast tests (pytest.ini skips the e2e ones that need models, waifu2x and the internet)
        run: python -m pytest -q
      - name: Type check
        run: npx --yes pyright@1.1.414
        continue-on-error: true   # remove once #18 brings errors to 0
```

### Optional Claude Code hook (`.claude/settings.json`)
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          { "type": "command",
            "command": "f=$(jq -r '.tool_input.file_path // empty'); case \"$f\" in *.py) uvx ruff format --quiet \"$f\";; esac; exit 0" }
        ]
      }
    ]
  }
}
```

## 6. Steps
- [ ] Agree on line length 120 vs 88 (open question).
- [ ] Add `pyproject.toml`.
- [ ] Run `uvx ruff format .` once, then the fast tests. **Commit 1: formatting only** (about 44 files).
- [ ] Add a `.git-blame-ignore-revs` file containing that commit's hash, so `git blame` skips it (GitHub reads it automatically).
- [ ] Fix the 1× E712 (`gui.py:226`) by hand, or ignore it. Then `uvx ruff check .` shows 0.
- [ ] Add `.pre-commit-config.yaml`, then run `uvx pre-commit install` and `uvx pre-commit run --all-files`.
- [ ] Add the Ruff default formatter to `.vscode/settings.json`, plus `extensions.json`.
- [ ] Add `.github/workflows/ci.yml`. Push a branch and check that both jobs go green (Pyright warns only).
- [ ] Add the `lint`, `format` and `typecheck` scripts to package.json, and a section to DEVELOPING.md.
- [ ] After #18: remove `continue-on-error` from the Pyright step.
- [ ] Later (optional): turn on `I`, then `UP`, each in its own commit.

## 7. How to test it
| Check | Expected |
|---|---|
| `uvx ruff format --check .` after commit 1 | "All files already formatted" |
| `npm run test` after formatting | 203 passed (formatting must not change behavior) |
| `npm run self-test` | Passes |
| Commit a badly formatted file | The hook reformats it and stops the commit. Running `git add` and committing again works. |
| Save a messy `.py` file in VS Code | It gets formatted |
| CI on a test branch | `lint` ✅, `test` ✅, Pyright shows its errors without failing the build |
| CI time | lint about 15 s. test: about 2–4 min for pip install the first time (torch about 70 MB on macOS arm64), less once cached, plus about 10 s for tests. *Estimate, not measured.* |

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | Small: 3 new config files, 2 small edits, 1 tool-made formatting commit. About 1 hour. |
| Value | High: no more style noise in diffs and reviews (#25), simple bugs caught before commit, and a CI badge. |
| Risk: big first diff | It conflicts with any uncommitted work. **Do it when `git status` is clean.** There are 13 uncommitted files right now. |
| Risk: the fast tests haven't been run on a clean machine | They might rely on something that's only on this Mac (e.g. the 87 MB Magi weights file, or the HF cache). The first CI run will show it. If so, mark that test `e2e`. |
| Risk: `requirements-lock.txt` on CI | It pins `coremltools==8.1` without a Mac-only marker. That's fine on macOS runners, but it would matter if CI ever moves to Linux. |
| Risk: GitHub pricing | Public repos: standard runners stay free (confirmed in GitHub's Dec 2025 pricing update). Larger runners are always billed, so don't use them. |
| Open question | Line length 120 (recommended, smaller diff) or 88 (the common default)? |
| Open question | Add the optional Claude Code hook, the pre-push test hook, or both? |
| Open question | Do #14 (folder move) before or after the formatting commit? Recommended: formatting first, then #14, so each diff is easy to read. |

## 9. Sources
- Ruff formatter and the Black style: https://docs.astral.sh/ruff/formatter/
- Ruff 0.16 default rule set: https://astral.sh/blog/ruff-v0.16.0, https://pydevtools.com/blog/ruff-0-16-0-default-rules/
- ruff-pre-commit: https://github.com/astral-sh/ruff-pre-commit
- ruff-action: https://github.com/astral-sh/ruff-action
- Pyright configuration: https://github.com/microsoft/pyright/blob/main/docs/configuration.md
- pre-commit: https://pre-commit.com
- Claude Code hooks: https://docs.claude.com/en/docs/claude-code/hooks
- GitHub Actions billing (free standard runners on public repos): https://docs.github.com/en/billing/managing-billing-for-github-actions/about-billing-for-github-actions, https://github.blog/changelog/2025-12-16-coming-soon-simpler-pricing-and-a-better-experience-for-github-actions/
- Measured locally: `uvx ruff format --diff`, `uvx ruff check --statistics`, `npx pyright --outputjson`, `pytest` (outputs in the session scratchpad)
