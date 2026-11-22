# Spec 10: Run Panelyze on the AMD gaming PC (Radeon RX 6700 XT)

Researched 2026-11-19. Planning only: no app code was changed.

## 1. Summary
Run Panelyze **from source** on the user's PC (Radeon RX 6700 XT, 12 GB, chip "gfx1031") so Magi and the "Best" upscaler use the AMD card. The good news since the roadmap note was written: AMD's **TheRock** PyTorch builds now build *and sanity-test* gfx1031 on **both Windows and Linux**, so no dual boot and no `HSA_OVERRIDE_GFX_VERSION` trick should be needed. The app's code already picks the card (AMD shows up in PyTorch as `"cuda"`). This is mostly a **setup guide**, not a code change.

## 2. Is it doable?
**Yes, probably.** Nothing here has been run on the actual card yet, so the first step is a 30-minute check on the PC.

| Part | Works on the 6700 XT? |
|---|---|
| Magi (panels + text reading) | Likely, via TheRock PyTorch (Windows or Linux) or official PyTorch 2.5.1 + ROCm 6.2 (Linux only, with the override) |
| "Best" upscaler (MangaJaNai via spandrel) | Likely, same PyTorch. Core ML is Mac-only, so it uses PyTorch on the card |
| waifu2x ("Fast"/"Better") | Yes. waifu2x-ncnn-vulkan uses **Vulkan**, which every AMD driver supports. Just needs the Windows/Linux download on the PATH |
| MangaDex download, video, TTS | Yes. Plain Python; `open_directory` already handles Windows/Linux |

## 3. What's already true (roadmap claims checked)

| Claim (ROADMAP #10 / benchmarks README) | Status | What's true now |
|---|---|---|
| "Linux with ROCm is the most proven route; needs `HSA_OVERRIDE_GFX_VERSION=10.3.0`" | ⚠️ partly out of date | Still true for **official** PyTorch wheels (AMD's official Linux list is RX 7000/9000 only, ROCm 7.2.1 + PyTorch 2.9.1). But TheRock now builds gfx1031 natively, marked Build ✅ / Sanity tested ✅ / Release ready ✅ on Linux. Override not needed there |
| "Windows TheRock builds list gfx1031 but are previews; nobody tested this card" | ⚠️ out of date | TheRock's SUPPORTED_GPUS table now marks **Windows gfx1031 sanity tested ✅**. Install is `pip install --index-url https://nightly.repo.amd.com/rocm/whl-next/ "torch[device-gfx1031]" "torchvision[device-gfx1031]"`. Still a nightly channel ("may be unstable"). AMD's *official* Windows PyTorch list (ROCm 7.2.1, PyTorch 2.9, Python 3.12) still has no RX 6000 cards |
| "VM or WSL2 can't use the card" | ✅ verified (WSL2) | AMD's WSL2 matrix (ROCm 7.2.1, librocdxg) lists only RX 7000/9000 + Pro cards. No RDNA2 |
| "DirectML is unmaintained, stuck on PyTorch 2.0" | ⚠️ number wrong, conclusion right | Latest `torch-directml` is 0.2.5.dev240914 (Sept 2024), needs **torch 2.4.1**. No release in over 2 years. Still not worth it |
| "AMD shows up as `cuda`, so the GPU picker needs no code change" | ✅ verified | There's no GPU picker in Settings; `get_device()` in `magi.py` picks mps → cuda → cpu automatically. ROCm PyTorch answers `torch.cuda.is_available() == True`. Only cosmetic issue: `DEVICE_NAMES["cuda"]` prints "the NVIDIA GPU" |
| "Runs from source there, not the Mac app; waifu2x needs its Windows/Linux download" | ✅ verified | `get_waifu2x_path()` (utils.py) uses `shutil.which("waifu2x-ncnn-vulkan")`, which finds `.exe` on Windows too. `coremltools` is already marked Mac-only in requirements.txt |
| "3–5× faster than the M1" | ⚠️ unmeasured estimate | Still just a guess. Needs a real benchmark |

**Pinned versions vs. the PyTorch builds (tested today on this Mac, CPU):**

| PyTorch | transformers 4.34.0 + Magi panels | Full Magi (text reading) | MangaJaNai via spandrel 0.4.2 |
|---|---|---|---|
| 2.5.1 (current pin) | ✅ 3 of 3 panels, 10.6 s | ✅ 12.0 s | ✅ (in use today) |
| 2.11.0 (oldest TheRock offers; it offers 2.11–2.14) | ✅ 3 of 3 panels, 7.2 s | ✅ 8.7 s | ✅ 0.72 s on a 64 px test tile |

So the pinned `transformers==4.34.0` works with the newer PyTorch TheRock needs. (Times include first-run loading; they show "it works", not speed.) Torch 2.12–2.14 were not tried.

Also: official `torch==2.5.1+rocm6.2` exists for Linux, Python 3.12 (checked on download.pytorch.org), so the Linux route can keep the exact pin.

**Checked on the PC itself (2026-11-22):** Windows 11 Pro, AMD Radeon RX 6700 XT (driver 32.0.21045), Python 3.10.11 only (install 3.12 to match the Mac), git 2.44, no venv, no waifu2x. `magi_model/panels_fp16.safetensors` isn't there (not in git); `build_panels_model_file` in `magi.py` builds it from the full Magi download the first time.

**Missed in the first review:**
- `.cbr` import doesn't work on Windows: `save_rar_pages` (`utils.py`) looks only for `bsdtar` or `/usr/bin/bsdtar`. Windows 11's built-in `C:\Windows\System32\tar.exe` *is* bsdtar (3.8.9, opens RAR), so a 1-line fallback to `shutil.which("tar")` fixes it.
- Logs go to `~/Library/Logs/Panelyze` (`gui_classes/AppOutput.py`, `self_test.py`). On Windows that's `C:\Users\<you>\Library\Logs\Panelyze`. Odd place, but it works; left as is.
- The worktree setup in CLAUDE.md uses `ln -s`, which in Git Bash on Windows copies instead of linking (unless Developer Mode is on). On Windows, link the venv with a directory junction (`mklink /J`) instead.

## 4. Recommended approach + rejected alternatives

| Option | Verdict | Why |
|---|---|---|
| **Windows + TheRock nightly PyTorch (`torch[device-gfx1031]`)** | ✅ **Recommended** | No dual boot. gfx1031 is built and sanity-tested for Windows. Pinned transformers works with torch 2.11. Only the torch install line differs |
| Linux dual boot + `torch==2.5.1+rocm6.2` + `HSA_OVERRIDE_GFX_VERSION=10.3.0` | Backup | Keeps exact pins and is the long-proven community route, but needs a Linux install |
| Linux + TheRock | Backup | Same as Windows route, if the user ever has Linux |
| WSL2 | ❌ | RDNA2 not supported in AMD's WSL matrix |
| DirectML | ❌ | Dead since Sept 2024, torch 2.4.1 only |
| CPU only on the PC | Fallback | Always works; useful to separate "app works on Windows" from "GPU works" |

## 5. Files to change + existing functions to reuse

| File | Change | Size |
|---|---|---|
| `DEVELOPING.md` | New short section "Running from source on a Windows/Linux PC (AMD or NVIDIA)": install steps below | ~20 lines |
| `magi.py` | `DEVICE_NAMES["cuda"]` from "the NVIDIA GPU" to "the GPU" (AMD also reports as cuda) | 1 line |
| `utils.py` | `save_rar_pages`: also find Windows' built-in `tar` (it's bsdtar), so `.cbr` import works | 1–2 lines |
| `ROADMAP.md` | Update #10 table with the findings above | ~6 lines |

Reuse, no changes: `get_device()` and `run_with_cpu_fallback()` in `magi.py`; `get_pytorch_upscale_function()` / `can_use_coreml()` in `janai.py` (already uses PyTorch off-Mac); `get_waifu2x_path()` and `open_directory` in `utils.py`; `python gui.py --self-test` (`self_test.py`) as the first check.

## 6. Steps (todo)
- [ ] On the PC: install Python 3.12 and git; clone the repo; make a venv
- [ ] `pip install -r requirements.txt` **without** the `torch`/`torchvision` lines (e.g. install those two first from TheRock, then the rest with `--no-deps` for torch, or filter them out)
- [ ] `pip install --index-url https://nightly.repo.amd.com/rocm/whl-next/ "torch[device-gfx1031]" "torchvision[device-gfx1031]"`
- [ ] Check: `python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"` → `True`, RX 6700 XT
- [ ] Download waifu2x-ncnn-vulkan for Windows, put its folder on the PATH
- [ ] `python gui.py --self-test` → SELF-TEST PASSED
- [ ] Benchmark Dragon Ball ch. 93: Panel-By-Panel, Best upscale, Fast upscale, vs the M1 numbers in `benchmarks/README.md`
- [ ] If Windows fails: try Linux with `torch==2.5.1+rocm6.2` and `HSA_OVERRIDE_GFX_VERSION=10.3.0`
- [ ] Fix `.cbr` import on Windows (`save_rar_pages` falls back to `tar`) and the `DEVICE_NAMES["cuda"]` wording
- [ ] Write the DEVELOPING.md section with what actually worked; update ROADMAP #10

## 7. How to test it
- Existing test suite on the PC: `pytest` (should pass unchanged; `tests/test_magi.py` already covers mps/cuda/cpu picking).
- `python gui.py --self-test`.
- Real run: Dragon Ball ch. 93 through the Pipeline; compare panel count and output with the Mac run; record times in a table.
- Watch for silent CPU fallback: the log line "Magi failed on the GPU (...). Running it on the CPU instead." means the card didn't work.

## 8. Size, value, risks, open questions

| | |
|---|---|
| Size | Small for code (0–1 line). Medium for setup and testing on the PC (1–2 hours) |
| Value | Low–Medium: only helps when working on the PC. Becomes Medium if whole-series runs (#3) happen |
| Risk: nightly builds | TheRock nightlies can break between days. Pin the exact wheel that works |
| Risk: newer torch | Only 2.11 was tested with transformers 4.34; if TheRock drops 2.11, retest |
| Risk: app on Windows at all | README says "Mac only, Windows planned". Flet desktop works on Windows, but Panelyze itself has never been run there; path or subprocess bugs may show up (separate from the GPU) |
| Risk: 12 GB VRAM | Full Magi is ~2 GB; fine. CPU fallback already handles out-of-memory |

**Open questions for the user**
1. ~~Is the PC on Windows 10 or 11?~~ Windows 11 Pro (checked 2026-11-22).
2. Is a Linux dual boot acceptable as a backup, or Windows only?
3. Want the 1-line "the GPU" wording fix in `magi.py`, or leave code untouched?
4. Is this still wanted now that spec 20 (free NVIDIA options) exists?

## 9. Sources
- TheRock releases / install + device extras: https://github.com/ROCm/TheRock/blob/main/RELEASES.md
- TheRock supported GPUs (gfx1031 Linux + Windows ✅): https://github.com/ROCm/TheRock/blob/main/SUPPORTED_GPUS.md
- AMD Windows PyTorch support matrix (RX 7000/9000 only): https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/windows/windows_compatibility.html
- AMD native Linux matrix (ROCm 7.2.1 + PyTorch 2.9.1, no RDNA2): https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/native_linux/native_linux_compatibility.html
- AMD WSL matrix: https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/wsl/wsl_compatibility.html
- HSA override for gfx1031 (10.3.0): https://localaimaster.com/blog/rocm-unsupported-gpu-hsa-override , https://github.com/ROCm/ROCm/issues/2527
- Community Windows ROCm on RX 6750 XT (gfx1031): https://forum.level1techs.com/t/native-vllm-rocm-7-15-runtime-for-rx-6000-rdna2-on-windows-11-26-tflops-fp16-62-tok-s-one-click-install-no-wsl2-rx-6750-xt-gfx1031-verified/254042
- torch-directml on PyPI: https://pypi.org/project/torch-directml/
- PyTorch ROCm 6.2 wheels: https://download.pytorch.org/whl/rocm6.2/torch/
- Local check: scratch venv with torch 2.11.0 + transformers 4.34.0 running `magi.Magi().predict_panels`, `get_per_page_results` and `janai.get_pytorch_upscale_function` (2026-11-19)
