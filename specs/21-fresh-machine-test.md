# 21 — Test on a clean machine

New roadmap idea. Researched 2026-11-19. Planning only.

## 1. Summary
Prove that a new user gets everything installed: (a) from source with `requirements.txt`, and (b) from the packaged app. Recommendation: **two simple tests, no VM.**
1. **Packaged app → a new macOS user account** on the M1. It has a fresh `~/Library`, no Hugging Face cache, no upscale models, and a browser download gets the real quarantine flag. This is the closest thing to a real user, with the real GPU and Neural Engine.
2. **From source → a GitHub Actions `macos-15` runner** (free for this public repo): new venv from `requirements.txt`, the fast tests, and `--self-test`. Docker (Linux) is an optional extra for "does it install off-Mac".

## 2. Is it doable?
Yes. The account test needs no code. The CI test needs one new ~30-line workflow file. A macOS VM is the "cleanest" but is blocked in practice by the 27 GB of free disk.

## 3. What's already true (claims checked)
| Claim | Check | Status |
|---|---|---|
| The app can run headless for checks | `gui.py --self-test` runs `self_test.py` before any window opens. So a clean-machine check **doesn't need the GUI at all**. | ✅ |
| Web mode for GUI checks | `flet-web==0.25.2` + `fastapi==0.115.6` are pinned in requirements (newer FastAPI breaks it). Headless Playwright screenshots worked before (memory note). | ✅ |
| Docker on a Mac has no GPU | Docker runs a Linux VM; Metal/MPS isn't passed through. Torch runs on CPU; `can_use_coreml()` is False (Linux). | ✅ |
| Docker on Apple Silicon pulls a small torch | Containers are `linux/arm64`; PyPI's torch for aarch64 Linux is CPU-only (no 2–3 GB of CUDA libs). On x86 Linux (e.g. `ubuntu-latest`) torch pulls CUDA libs unless the CPU index is used. | ✅ (from PyPI wheel layout; confirm on first run) |
| waifu2x in Docker | waifu2x-ncnn-vulkan needs a Vulkan device; there's no GPU. Mesa's CPU Vulkan (`mesa-vulkan-drivers`) may work. | ⚠️ untested |
| macOS VMs (Tart, UTM, Apple Virtualization) | Apple's license allows 2 macOS VMs per Mac. VMs get paravirtualized Metal, but GitHub's docs say MPS isn't supported in Apple Virtualization VMs, and no source shows PyTorch MPS working in a guest. A macOS VM image is tens of GB. Tart is free for personal use. Neither Tart nor UTM is installed. | ✅ facts; ⚠️ **only 27 GB free** — not practical |
| GitHub Actions clean runners | `macos-15` arm64: 3-core M1, 7 GB RAM, **14 GB SSD**, **no MPS**, free and unlimited for public repos. Fresh VM every run (but with Homebrew, Python etc. preinstalled). Repo is public. | ✅ |
| New macOS user account | Separate `~/Library`, `~/.cache/huggingface`, `~/Documents`, login keychain. Shares `/opt/homebrew`, `/Applications` and uv/system Pythons only if on PATH. Real GPU + Neural Engine. | ✅ good for the **app**, weak for **source** (shared Homebrew) |
| Things a fresh machine will download | Full Magi (~2 GB, Hugging Face, via the pinned `huggingface-hub==0.17.3`), "Best" zips (592 MB), waifu2x for source runs (42 MB). `huggingface.co/ragavsachdeva/magiv2` answers 200 today. | ✅ (but the 2-year-old `huggingface-hub` download path is only proven from cache — that's why this test matters) |
| Python version | Docs say 3.12; the venv is 3.12.11 (uv). | ✅ |
| Local files to note | `~/.cache/huggingface` is **3.1 GB**, `upscale-models` **314 MB**: the user's account is "warm", so it can't prove a clean install. | ✅ |

## 4. Recommended approach + rejected alternatives
| Option | Proves source install? | Proves packaged app? | GPU / Neural Engine | Effort | Verdict |
|---|---|---|---|---|---|
| **New macOS user account** | Partly (shared Homebrew) | **Yes**, incl. quarantine + first-run downloads | Real | 15 min, no code | ✅ **Use for the app** |
| **GitHub Actions `macos-15`** | **Yes**, every push | Yes, if it also builds (spec 19) | None (CPU only, no MPS, no ANE) | 1 new workflow file | ✅ **Use for source** |
| Docker (Linux arm64) | Yes, for Linux | No | None | Dockerfile + apt libs (libasound2, Vulkan) | Optional: proves off-Mac install + the real "no Core ML" path (spec 02 C) |
| macOS VM (Tart / UTM) | Yes | Yes | Weak (no MPS) | Large image vs 27 GB free | ❌ not now |
| Ask a friend's Mac | Yes | Yes | Real | Depends on them | Good final check before a big release |

## 5. Files to change + functions to reuse
| File | Change |
|---|---|
| `.github/workflows/test.yml` | New, ~30 lines: `macos-15`, `actions/setup-python` 3.12, `pip install -r requirements.txt`, `pytest -m "not e2e"`, download waifu2x (same URL as DEVELOPING.md), cache `magi_model/panels_fp16.safetensors` and `~/.cache/huggingface`, run `python gui.py --self-test`, upload `~/Library/Logs/Panelyze/*.log` as an artifact. |
| `DEVELOPING.md` | One line: what CI runs. |
| (optional) `Dockerfile` | Only if the user wants the Linux check. Could stay in the scratchpad instead of the repo. |

| Reuse | Where |
|---|---|
| `run_self_test` (and spec 02's new Best check) | `self_test.py` |
| `magi.build_panels_model_file` (auto-builds the panels model on first use) | `magi.py` |
| Fast test suite, Finder-blocking fixture | `tests/`, `tests/conftest.py` |
| waifu2x download steps | `DEVELOPING.md`, `build_mac_app.sh` step 1 |
| Web-mode wrapper + Playwright (only if a GUI screenshot is wanted) | memory note "Flet web mode testing" |

## 6. Steps
**A. Packaged app in a new macOS user account (manual, the user does the account parts)**
- [ ] After spec 02 A: upload the zip to a **draft** GitHub release (or any link), so it's downloaded through Safari like a real user.
- [ ] User creates a standard (non-admin) account, e.g. "Panelyze Test", in System Settings → Users & Groups.
- [ ] Log in, download the zip in Safari, unzip, drag to Applications, follow the README's install steps word for word. Note anything confusing.
- [ ] Check the Flet window opens (it unpacks from a tar.gz on first start).
- [ ] Run: MangaDex Dragon Ball ch. 93 (pages 1–3) → Panel-By-Panel → Upscale **Fast**, then **Best** (first-time 592 MB download, real) → Video with text (first-time 2 GB Magi download).
- [ ] Run `/Applications/Panelyze.app/Contents/MacOS/Panelyze --self-test` in Terminal for that account.
- [ ] Save `~/Library/Logs/Panelyze/panelyze.log` to a shared place (e.g. /Users/Shared) and note times and sizes.
- [ ] User deletes the test account afterwards (frees its ~3 GB of downloads).

**B. From source on a GitHub Actions runner**
- [ ] Write `.github/workflows/test.yml` (manual trigger + push to main).
- [ ] User OKs pushing it (it's a commit, which the user does).
- [ ] First run: note install time, disk used, which step fails (likely candidates: Magi download with old `huggingface-hub`, MPS detected but failing → CPU fallback, 7 GB RAM).
- [ ] Fix only what's broken, in the smallest way.
- [ ] Optional: add the build step from spec 19 so the packaged app is self-tested on a clean machine too.

**C. Optional: Linux in Docker**
- [ ] Scratchpad Dockerfile: `python:3.12-slim`, `apt-get install libasound2 libssl3 ca-certificates libgl1 mesa-vulkan-drivers`, `pip install -r requirements.txt` (the coremltools line is skipped on Linux).
- [ ] Run `pytest -m "not e2e"` and `python gui.py --self-test` in the container.
- [ ] Run spec 02 C's "no Core ML" upscale for real.
- [ ] Optional GUI check: serve web mode in the container, screenshot with Playwright from the host.

## 7. How to test it
Success = in each clean place, `--self-test` prints `SELF-TEST PASSED` (6 checks with spec 02), and in the user account the full pipeline finishes with both first-time downloads. Results go in a small table: place, install time, download sizes, pass/fail, notes.

## 8. Size, value, risks, open questions
| | |
|---|---|
| Size | Small: A is manual (~1 h incl. downloads); B is one new file; C optional. |
| Value | High: the user's own account is "warm" (3.1 GB HF cache, models present), so today nothing proves a new user can install. |
| Risk | CI has no MPS: if torch reports MPS available but it fails, Magi relies on `run_with_cpu_fallback`. |
| Risk | CI disk (14 GB) and RAM (7 GB): venv (~1–2 GB) + Magi 2 GB fits; the full Magi on CPU with 7 GB RAM is tight — keep the self-test to the panels model (it already is). |
| Risk | Old pinned `huggingface-hub==0.17.3` may fail to download on a clean machine; good to find now. |
| Open | OK for the user to create (and later delete) a test macOS account? |
| Open | OK to add `.github/workflows/test.yml` (needs a commit/push by the user)? |
| Open | Want the Linux Docker check, or skip it until Windows/Linux builds are planned? |

## 9. Sources
- [GitHub Docs: GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) (specs, free for public repos, "Nested-virtualization is not supported", MPS not supported)
- [Eclectic Light: GPU access for Apple silicon VMs](https://eclecticlight.co/2023/10/26/how-good-is-gpu-access-for-apple-silicon-virtual-machines/)
- [Tart (Apple Virtualization based VMs)](https://github.com/tuist/tart)
- [PyTorch forum: MPS in Docker/Podman](https://dev-discuss.pytorch.org/t/how-to-install-mps-backend-on-docker-podman-container/3015)
- [Apple: Accelerated PyTorch on Mac](https://developer.apple.com/metal/pytorch)
- Local: `df -h` (27 GB free), `du` of `~/.cache/huggingface` (3.1 GB), `which tart utm docker` (Docker only), `gh repo view` (public), `curl -I` to Hugging Face (200).
