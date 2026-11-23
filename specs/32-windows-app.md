# Spec 32: A downloadable Windows app

Researched 2026-11-22 on the user's Windows 11 PC (Ryzen 5 7600, Radeon RX 6700 XT). Planning only: no app code was changed. Builds on spec 10 (running from source on Windows), which has to be merged first.

## 1. Summary
Make a `Panelyze-Windows.zip` that anyone can download from GitHub, unzip and double-click, like the Mac app. Done in three parts:

- **Part A: ship PyTorch for the CPU.** One zip that works on every Windows 10/11 PC. Magi and the "Best" upscaler run on the CPU; "Fast" and "Better" (waifu2x) still use any GPU through Vulkan. A new `build_windows_app.ps1` does what `build_mac_app.sh` does.
- **Part B: find the user's GPU and install the right PyTorch for it.** The app checks which GPU the PC has (AMD or NVIDIA) and offers to download the matching GPU PyTorch (TheRock for AMD, with the right chip; CUDA for NVIDIA). The same check also powers a new `install_pytorch.py` for running from source, so nobody has to look up their chip by hand any more (spec 10 made people edit `gfx1031` themselves). No GPU found, an old or unsupported one, or the download fails: the app keeps using the CPU, as in Part A.
- **Part C: ONNX Runtime + DirectML (only if Part B turns out too fragile or too big).** Convert Magi and the "Best" models to ONNX, so they run on any GPU from a small download. Only if the converted models give the same results.

**Tested hardware (disclaimer):** Panelyze has only been tested on an **M1 MacBook Air (16 GB)** and an **AMD Radeon RX 6700 XT** (Windows 11). Other AMD and NVIDIA GPUs are supported in code and covered by tests with fake GPU names, but never run on a real card. The README and DEVELOPING.md say so.

## 2. Is it doable?
**Part A: yes.** Spec 10 showed every tab works on Windows from source, and `flet pack` (PyInstaller) builds Windows apps (it has to run on Windows; it can't build one from the Mac).

**Part B: yes for the detection, probably for the install.** Windows lists the GPUs with their name and PCI vendor ID (`Get-CimInstance Win32_VideoController`: `PNPDeviceID` starts `PCI\VEN_1002` for AMD, `PCI\VEN_10DE` for NVIDIA), and spec 10 showed TheRock's install works on gfx1031. The hard part is installing a different PyTorch next to a packaged (PyInstaller) app, which has no `pip` of its own; see section 4.

**Part C: probably, for the panels; unknown for the text reading.** Magi's panel finder is a standard detection model, which usually converts to ONNX. The text reader generates text word by word, which is harder to convert. Nothing here has been tried yet.

## 3. What's already true (checked)

| Claim | Status | What's true |
|---|---|---|
| A Windows build can't bundle GPU PyTorch for everyone | ✅ measured | NVIDIA (CUDA 12.4) PyTorch for Windows is a **2,394 MB** download, over GitHub's 2 GiB limit per file. AMD's (TheRock) is one package per chip family (~30 of them: `rocm-sdk-device-gfx1031`, `-gfx1100`, ...) and took **3.8 GB** installed for one chip |
| CPU PyTorch is small | ✅ | `torch-2.5.1-cp311-cp311-win_amd64.whl` on PyPI is the CPU build, **194 MB**. So on Windows, plain `pip install -r requirements.txt` with Python 3.11 already installs it; no special line needed |
| Python 3.11, not 3.12 | ✅ (spec 10) | `tokenizers==0.14.1` has no Windows build for 3.12 |
| CPU is much slower for Magi | ✅ measured | Panel-By-Panel on Shachou ch. 3 (27 pages): **76–80 s** on the Ryzen 5 7600, vs **6.6 s** on the RX 6700 XT and 11.3 s on the M1's GPU. "Best" upscale on the CPU: not measured, expect several minutes per chapter |
| waifu2x uses the GPU without PyTorch | ✅ | waifu2x-ncnn-vulkan uses Vulkan. `waifu2x-ncnn-vulkan-20250915-windows.zip` is 34 MB (same version the Mac build uses) |
| The packaged app finds the bundled waifu2x | ❌ | `get_waifu2x_path()` (utils.py) looks for `waifu2x/waifu2x-ncnn-vulkan` inside the app, without `.exe`, so it isn't found on Windows |
| Mac-style folders | ⚠️ | Logs go to `~/Library/Logs/Panelyze` (`gui_classes/AppOutput.py`, `self_test.py`), "Best" models to `~/Library/Application Support/Panelyze/upscale-models` (`janai.py`). They work on Windows (`C:\Users\<you>\Library\...`) but aren't where Windows apps keep things. Use `%LOCALAPPDATA%\Panelyze\...` on Windows. Also the comix.to cookie file: `~/Library/Application Support/Panelyze/cf_cookies.dat` (`comix_downloader/src/api/comix.py:26`) |
| "Documents" is where Explorer shows it | ❌ (found by spec 10's Windows review) | `default_settings.py:7` uses `~\Documents\Panelyze`. Most Windows 11 PCs signed in with a Microsoft account move Documents into OneDrive (this PC: `C:\Users\Curlo\OneDrive\Documents`), so the app's folder isn't in the Documents folder Explorer shows. Windows can say where Documents really is (`SHGetKnownFolderPath(FOLDERID_Documents)` through `ctypes`). But inside OneDrive, gigabytes of panels and videos would sync to the cloud, and files can be locked while they sync. **Decide with the user** before changing it |
| Paths under 260 letters | ⚠️ (spec 10's review) | Windows' old path limit is 260 letters, and long paths are off by default (this PC has them on). Output paths can pass it: the output folder (~60–80) + a comix.to title (up to 100, `comix_downloader/src/core/models.py:88`) + a chapter folder (up to ~110) + `images-with-highlighted-text-boxes\panel_12-3.png` (49) ≈ 340. MangaDex folder names can be 255 letters each. Python then gives `FileNotFoundError`. Cap title and chapter folder names at about 60–80 letters, and say in the docs how to turn long paths on |
| No console windows | ❌ (spec 10's review) | A packaged (windowed) app flashes a black console window every time it starts `waifu2x-ncnn-vulkan.exe`, `tar.exe` or the MangaDex downloader (`utils.py`: `ProcessManager`'s `Popen`, `save_rar_pages`). Pass `creationflags=subprocess.CREATE_NO_WINDOW` on Windows. MoviePy's ffmpeg already does |
| Packaged app can start its own subprocesses | ✅ | `gui.py` calls `multiprocessing.freeze_support()`, and `is_running_as_packaged_app()` already handles `sys.frozen` |
| Build script is Mac-only | ✅ | `build_mac_app.sh` uses bash, `sips`, `iconutil`, `ditto`, `perl`. A Windows one is needed (PowerShell); `.ico` icons can be made with Pillow (already installed) |
| comix.to downloader finds a browser | ✅ (spec 10) | Edge's Windows path was added; Edge comes with Windows |
| Unsigned apps on Windows | ⚠️ | SmartScreen shows "Windows protected your PC" for unsigned downloads: **More info → Run anyway**. Code signing is paid; optional later |
| Which PyTorch build each GPU needs | ✅ checked 2026-11-22 (except card names) | See "GPU → PyTorch table" below. TheRock's SUPPORTED_GPUS.md marks every chip in it Build ✅ / Sanity tested ✅ / Release ready ✅ on **Windows**, including RX 5000 (gfx1010–1012). Its package index has `rocm-sdk-device-gfx…` for each. It doesn't name the cards, so the card → chip matches are the commonly used ones, unchecked. NVIDIA: `torch-2.5.1+cu124` and `torchvision-0.20.1+cu124` exist for cp311 win_amd64 (same version as the pin). RTX 50 needs cu128 (newest there: torch 2.11, torchvision 0.26) |
| Built-in graphics shows up too | ✅ (spec 10) | The Ryzen's built-in "AMD Radeon(TM) Graphics" is listed next to the RX 6700 XT. The detection has to prefer the graphics card and ignore built-in graphics when choosing what to install (`get_device()` already skips it at run time) |
| DirectML is the way to use any GPU from ONNX Runtime | ⚠️ to check | `onnxruntime-directml` runs on any DirectX 12 GPU. Microsoft's newer "Windows ML" may replace it; check which is maintained before Part B |

**GPU → PyTorch table** (for `gpu_detection.py` and `install_pytorch.py`; only the RX 6700 XT tested)

| Card (name from `Win32_VideoController`) | Install |
|---|---|
| RX 9070, 9070 XT | AMD `gfx1201` |
| RX 9060 XT | AMD `gfx1200` |
| RX 7900 XTX, 7900 XT, 7900 GRE | AMD `gfx1100` |
| RX 7800 XT, 7700 XT | AMD `gfx1101` |
| RX 7600, 7600 XT | AMD `gfx1102` |
| RX 6800, 6800 XT, 6900 XT, 6950 XT | AMD `gfx1030` |
| RX 6700, **6700 XT** (tested), 6750 XT | AMD `gfx1031` |
| RX 6600, 6600 XT, 6650 XT | AMD `gfx1032` |
| RX 6500 XT, 6400 | AMD `gfx1034` |
| RX 5700, 5700 XT, 5600 XT | AMD `gfx1010` |
| RX 5500, 5500 XT | AMD `gfx1012` |
| NVIDIA GTX 900 up to RTX 40 | CUDA 12.4: `torch==2.5.1 torchvision==0.20.1` |
| NVIDIA RTX 50 | CUDA 12.8: newest `torch torchvision` |
| Older AMD (RX 500, Vega), Intel, built-in graphics only, unknown | CPU (the normal `requirements.txt`) |

Install lines (from source; the app does the same with its bundled `pip`):
- AMD: `pip install --index-url https://nightly.repo.amd.com/rocm/whl-next/ "torch[device-<chip>]" "torchvision[device-<chip>]"`
- NVIDIA: `pip install --index-url https://download.pytorch.org/whl/cu124 torch==2.5.1 torchvision==0.20.1` (RTX 50: `.../whl/cu128 torch torchvision`)
- Then `requirements.txt` without its `torch`/`torchvision` lines.
- Check: `magi.get_device()` gives `cuda:N`, and `torch.cuda.get_device_name(N)` is the card.

## 4. Recommended approach + rejected alternatives

| Option | Verdict | Why |
|---|---|---|
| **A. One Windows zip with CPU PyTorch** | ✅ **First** | Works on every PC, one download, simplest. waifu2x keeps the GPU for Fast/Better |
| **B. Detect the GPU, then download its PyTorch** | ✅ **Second** | The user's choice: full speed on any supported AMD or NVIDIA card, and the GitHub zip stays small (PyTorch comes from AMD's and PyTorch's own servers). How: bundle `pip` in the app and run it in-process with `--target %LOCALAPPDATA%\Panelyze\gpu-pytorch`; at startup, before anything imports `torch`, put that folder first on `sys.path` if it's there. Bundled CPU PyTorch stays as the fallback. Risky part: PyInstaller apps and a second PyTorch; try it early in Part B and fall back to Part C if it can't be made reliable |
| C. ONNX Runtime + DirectML for Magi and "Best" | Fallback | Any GPU (also Intel), small download. Needs the models converted and checked |
| Separate NVIDIA and AMD zips with GPU PyTorch | ❌ | NVIDIA's is over GitHub's 2 GiB limit; AMD's needs a zip per chip family |
| An installer (.msi / Inno Setup) | Later | A zip is simplest and matches the Mac release |
| WSL2 / Docker | ❌ | Not for normal users |

## 5. Files to change + existing functions to reuse

**Part A**

| File | Change | Size |
|---|---|---|
| `build_windows_app.ps1` (new) | Same steps as `build_mac_app.sh`: its own build venv (`venv-windows-build`, Python 3.11, CPU torch from `requirements.txt`, so the dev venv's AMD PyTorch never goes in the app), PyInstaller, waifu2x 20250915 Windows, panels model, `.ico` icon, `flet pack --onedir`, self-test on the built `Panelyze.exe` (10-minute limit), zip to `dist/Panelyze-Windows.zip` | ~100 lines |
| `utils.py` | `get_waifu2x_path()`: add `.exe` to the bundled name on Windows | 1–2 lines |
| `gui_classes/AppOutput.py`, `self_test.py`, `janai.py`, `comix_downloader/src/api/comix.py` | On Windows, logs, "Best" models and the comix.to cookie file in `%LOCALAPPDATA%\Panelyze\...` (one small shared helper, e.g. in `default_settings.py`) | ~10 lines |
| `default_settings.py` | Only if the user agrees: the real Documents folder on Windows (it may be in OneDrive) | ~10 lines |
| `utils.py` | `creationflags=subprocess.CREATE_NO_WINDOW` on Windows for the `Popen` and `tar.exe` calls | ~4 lines |
| `comix_downloader/src/core/models.py`, `download_pages_from_url.py`, MangaDex folder names | Shorter title and chapter folder names (about 60–80 letters), so paths stay under 260 | ~5 lines |
| `self_test.py` | Write the report with `encoding="utf-8"` (a path with letters Windows' old encoding can't store would fail) | 1 line |
| `package.json` | `build-windows-app` shortcut | 1 line |
| `README.md` | "Download for Windows" + SmartScreen steps; what runs on the CPU | ~10 lines |
| `DEVELOPING.md` | How to build the Windows app | ~10 lines |

**Part B**

| File | Change | Size |
|---|---|---|
| `gpu_detection.py` (new) | `list_gpus()`: name + vendor of each GPU (Windows: `Win32_VideoController` through PowerShell; other systems: empty list). `choose_pytorch_build(gpus)`: a pure function that turns that list into what to install: `{"kind": "amd", "chip": "gfx1031", ...}`, `{"kind": "nvidia", "cuda": "cu128"}` or `None` (CPU). Prefers a graphics card over built-in graphics, ignores Intel and unknown cards. One small table of AMD names → chip | ~60 lines |
| `install_pytorch.py` (new) | For running from source: detects the GPU and runs the right `pip install` (TheRock with the chip, CUDA, or the plain CPU wheel), then `requirements.txt` without the torch lines. Replaces the hand-edited line in DEVELOPING.md | ~30 lines |
| `gui_classes/` (Settings) | "Use my GPU" button in the packaged Windows app: shows the GPU found, the download size, downloads with progress, asks to restart. Hidden on the Mac and when no supported GPU is found | ~40 lines |
| `gui.py` | Before anything imports `torch`: put `%LOCALAPPDATA%\Panelyze\gpu-pytorch` first on `sys.path` when it exists (packaged Windows app only) | ~5 lines |
| `tests/test_gpu_detection.py` (new) | Fake GPU lists: RX 6700 XT + Ryzen built-in → gfx1031; RX 7900 XTX → gfx1100; RX 9070 XT → gfx1201; RTX 4070 → CUDA; RTX 5080 → CUDA 12.8; GTX 1060 → CUDA (or CPU, whatever the table says); RX 580 → CPU; Intel only → CPU; no GPU → CPU; NVIDIA + AMD built-in → NVIDIA; the PowerShell output parsed correctly; PowerShell missing or failing → empty list | ~80 lines |
| `README.md`, `DEVELOPING.md` | The tested-hardware disclaimer (spec 10 added a "Tested on" table to the README; update it); in DEVELOPING.md, `install_pytorch.py` replaces the hand-edited chip and NVIDIA lines | ~10 lines |

**Part C**

| File | Change |
|---|---|
| `experiments/onnx/` (new) | Export scripts: Magi panels → ONNX, MangaJaNai/IllustrationJaNai → ONNX (or download their ONNX releases if they exist), compare results with PyTorch |
| `magi.py`, `janai.py` | If the results match: use ONNX Runtime when it's available (Windows app), PyTorch otherwise (Mac, source). Keep `run_with_cpu_fallback()` |
| `requirements.txt` | `onnxruntime-directml` (Windows only, `sys_platform == "win32"`) |
| `build_windows_app.ps1` | Bundle the `.onnx` files; drop PyTorch only if every PyTorch part was converted |

Reuse: `run_self_test()` (`self_test.py`), `is_running_as_packaged_app()` and `get_waifu2x_path()` (`utils.py`), `magi.build_panels_model_file()`, `get_device()` (picks the best GPU, spec 10), `can_use_coreml()` in `janai.py` (the same "use the fast path if it's there" pattern for ONNX).

## 6. Steps (todo)

**Part A**
- [ ] Merge spec 10 into `main` first, then `git merge main` here
- [ ] `utils.py`: bundled waifu2x name with `.exe` on Windows; test
- [ ] Windows folders for logs, "Best" models and the comix.to cookie file (`%LOCALAPPDATA%\Panelyze`); tests
- [ ] Ask the user: keep `~\Documents\Panelyze`, or use the real Documents folder (inside OneDrive on many PCs)?
- [ ] No console windows: `CREATE_NO_WINDOW` for waifu2x, `tar.exe` and the MangaDex downloader
- [ ] Paths under 260 letters: shorter title and chapter folder names; test with a very long title. DEVELOPING.md/README: how to turn long paths on
- [ ] `self_test.py` report in UTF-8
- [ ] `build_windows_app.ps1`: build venv, waifu2x, panels model, icon, `flet pack`, self-test, zip
- [ ] Build it; record the app and zip sizes
- [ ] Test the built app on this PC: Download (Dragon Ball ch. 93, pages 1–3) → Panel-By-Panel → Upscale Fast and Best → Video; time Shachou ch. 3 on the CPU build vs the source run
- [ ] Test on a Windows account that has never had Python (new local user, like spec 21), downloading the zip through a browser so SmartScreen shows up
- [ ] README (download + SmartScreen steps), DEVELOPING.md, `package.json`
- [ ] Upload: only when the user says so (same as spec 19)

**Part B**
- [ ] Re-check the "GPU → PyTorch table" (section 3) against TheRock's SUPPORTED_GPUS.md and pytorch.org (it may have changed), and check the card → chip names; write it in `gpu_detection.py`
- [ ] `gpu_detection.py` (`list_gpus`, `choose_pytorch_build`) + `tests/test_gpu_detection.py` with the fake GPU lists above
- [ ] Check `list_gpus()` on this PC finds the RX 6700 XT and the built-in graphics, and chooses gfx1031
- [ ] `install_pytorch.py` for running from source; try it in a fresh venv on this PC; DEVELOPING.md uses it
- [ ] Early check: in the built app, bundled `pip` installs TheRock PyTorch into `%LOCALAPPDATA%\Panelyze\gpu-pytorch` and the app uses it after a restart (`get_device()` says `cuda:1`). If this can't be made reliable, stop Part B and go to Part C
- [ ] "Use my GPU" in Settings (packaged Windows app only), with progress and a restart prompt; a failed or cancelled download leaves the CPU build working
- [ ] Time Shachou ch. 3 in the built app before and after "Use my GPU"
- [ ] Tested-hardware disclaimer in README.md and DEVELOPING.md

**Part C** (only if Part B is dropped)
- [ ] Check whether DirectML or Windows ML is the maintained way to run ONNX on any GPU
- [ ] Export Magi's panel finder to ONNX; compare panels with PyTorch on Shachou ch. 3 and Dragon Ball ch. 93 (same panels, corners within 1 px); time it on the RX 6700 XT (DirectML) and the CPU
- [ ] The same for MangaJaNai and IllustrationJaNai ("Best"): same pixels within a small difference; time it
- [ ] Try the full Magi (text reading). If it doesn't convert, keep it on CPU PyTorch
- [ ] Use ONNX in the app where it matched; rebuild; compare size and speed with Part A
- [ ] Update README, DEVELOPING.md, benchmarks

## 7. How to test it
- Fast tests on Windows and the Mac (`python -m pytest`): the waifu2x path and folder changes must not change the Mac.
- `Panelyze.exe --self-test` on the built app (the build script does this).
- A real run in the built app on this PC, and on a fresh Windows user account.
- Part B: `tests/test_gpu_detection.py` covers AMD, NVIDIA and no-GPU cases with fake GPU lists, since only the RX 6700 XT can be tried for real. On this PC: "Use my GPU" in the built app, then Panel-By-Panel runs on `cuda:1`. Turning off the network mid-download leaves the app working on the CPU.
- Part C: panels and upscaled images compared with PyTorch's, on the same chapters; times in `benchmarks/README.md`.

## 8. Size, value, risks, open questions

| | |
|---|---|
| Size | Part A: Medium (build script + a few small fixes + testing). Part B: Medium (detection and tests are small; the in-app install is the work). Part C: Medium–Large, mostly checking that results match |
| Value | High: anyone on Windows can use Panelyze without Python. Part B makes it fast on supported AMD and NVIDIA cards |
| Risk: CPU speed | Magi is ~11× slower on the CPU (78 s vs 6.6 s a chapter here), and "Best" much more. Fine to start; Part B fixes it |
| Risk: untested GPUs | Only the M1 and the RX 6700 XT have been tried. A wrong row in the chip table means the CPU (slow, but it works: `get_device()` checks each GPU). The disclaimer says so; fix rows when users report them |
| Risk: download size | TheRock was 3.8 GB installed for one chip, NVIDIA's CUDA PyTorch ~2.4 GB. Show the size before downloading |
| Risk: nightly builds | TheRock is a nightly channel; pin the exact version that worked here |
| Risk: zip size | Estimate ~1 GB app, ~400–500 MB zip (CPU torch, transformers, scipy, flet). Measure |
| Risk: more Windows quirks | Spec 10's review found and fixed 5 Windows bugs (locked audio files, encodings, folder names ending in a space, `.cbr` with Japanese names). Others may show up on other PCs: Windows 10's older `tar.exe` may not open every RAR file, and a RAR whose inner folders have Japanese names loses its pages (Windows' `tar.exe` can't read those names; 7-Zip could) |
| Risk: first Windows build | PyInstaller may miss files on Windows that it found on the Mac (DLLs for pypdfium2, azure speech, nodriver). The self-test catches most |
| Risk: SmartScreen | Unsigned downloads look scary. Clear README steps; signing later if needed |
| Risk: Part B results | ONNX Runtime can give slightly different numbers; panels have to match closely or it isn't used |
| Open | Upload Part A as a separate release, or together with the Mac app (spec 19)? |
| Open | Is signing worth paying for later? |
| Open | Offer "Use my GPU" on first launch, or only in Settings? |
| Open | Intel Arc GPUs: PyTorch has an Intel (XPU) build; support it too, or leave Intel on the CPU? |

## 9. Sources
- Local measurements on this PC (2026-11-22): installed package sizes in the dev venv (`_rocm_sdk_core` 2,389 MB, `_rocm_sdk_libraries` 834 MB, `torch` 583 MB); Panel-By-Panel on the CPU (`HIP_VISIBLE_DEVICES=-1`) vs the GPU
- PyPI torch 2.5.1 files (Windows wheel = CPU, 194 MB): https://pypi.org/project/torch/2.5.1/#files
- PyTorch CUDA 12.4 Windows wheel (2,394 MB): https://download.pytorch.org/whl/cu124/torch/
- AMD TheRock package index (per-chip device packages): https://nightly.repo.amd.com/rocm/whl-next/
- waifu2x-ncnn-vulkan releases (20250915 Windows zip, 34 MB): https://github.com/nihui/waifu2x-ncnn-vulkan/releases
- GitHub release limit (2 GiB per file): https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
- Flet packaging with PyInstaller: https://flet.dev/docs/publish/using-pyinstaller
- TheRock supported GPUs (chip per card family): https://github.com/ROCm/TheRock/blob/main/SUPPORTED_GPUS.md
- PyTorch install matrix (CUDA versions): https://pytorch.org/get-started/locally/
- ONNX Runtime DirectML: https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html
- Spec 10 (`specs/10-amd-gaming-pc.md`) and spec 19 (`specs/19-github-release-app.md`)
