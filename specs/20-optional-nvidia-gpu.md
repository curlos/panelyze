# Spec 20 (new): Optional, free NVIDIA GPU for big jobs

Researched 2026-11-19. Planning only: no app code was changed.

## 1. Summary
Give the user an **optional**, **free** way to run the heavy AI steps (Magi Panel-By-Panel + text reading, "Best" upscaling) on an NVIDIA GPU, for big jobs like whole-series runs (#3). The **default stays the same**: the app runs locally on the M1 (GPU/Neural Engine/CPU). Recommended: **one notebook file** in the repo that runs on **Kaggle** (or Google Colab). You upload a zip of chapter folders, it runs the app's *existing* Python functions with no window, and gives back a zip. No changes to the GUI.

## 2. Is it doable?
**Yes.** The heavy code already runs with no window, and already uses an NVIDIA GPU when there is one.

| Needed | Already there? |
|---|---|
| Runs with no GUI | ✅ `python gui.py --self-test` runs Magi with no window; `Magi().get_panels_for_chapter(...)` and `janai.upscale_image_with_janai(...)` are plain functions. `report_progress` does nothing when no progress panel is shown |
| Uses NVIDIA GPU | ✅ `get_device()` (magi.py) returns `"cuda"` when there's no Mac GPU; `janai.py` uses PyTorch (not Core ML) off-Mac |
| Pinned PyTorch on Linux/Windows + CUDA | ✅ `torch==2.5.1+cu124` and `+cu121` wheels exist for Python 3.12, Linux and Windows (checked on download.pytorch.org) |
| A ready CLI command for "process this folder" | ❌ none. `gui.py` only has `--self-test` and `--run-mangadex`. A notebook cell can call the functions directly instead, so no CLI is needed |
| waifu2x ("Fast"/"Better") on a cloud GPU | ⚠️ unknown: needs Vulkan in the cloud machine. Keep waifu2x on the Mac (it's already fast there) or use "Best" in the cloud |

## 3. What's already true (claims checked)

| Claim | Status | Notes |
|---|---|---|
| "CUDA works out of the box with PyTorch on a local NVIDIA PC" | ✅ | Pinned torch 2.5.1 has CUDA 12.1/12.4 wheels for Windows + Linux. `get_device()` picks it, `run_with_cpu_fallback` covers out-of-memory |
| "waifu2x works on NVIDIA via Vulkan" | ✅ on a normal PC (NVIDIA drivers ship Vulkan). ⚠️ unverified on Colab/Kaggle |
| DEVELOPING.md: "Both Magi models run on the GPU when there is one (the Mac GPU or an NVIDIA GPU)" | ✅ matches `magi.py` |
| "Panel-By-Panel takes about 15–20 s per chapter on the M1 GPU" (ROADMAP #3) | ⚠️ estimate, not measured per chapter here |

**Free options (late 2026):**

| Option | GPU | Free limit | Rules that matter | How Panelyze would hand off work |
|---|---|---|---|---|
| **Kaggle Notebooks** | 2× T4 (16 GB each) or 1× P100 | ~30 h/week (Kaggle doesn't publish it), sessions ~9–12 h | Phone verification for GPU + internet. Normal ToS | Notebook: upload zip as a Dataset or file, run cells, download output |
| **Google Colab (free)** | Usually T4 16 GB (not promised) | Not published; ≤12 h per session, ~90 min idle timeout | Free tier forbids SSH/remote desktop, "bypassing the notebook UI to interact primarily via a web UI", "distributed computing workers". So **no remote worker the GUI talks to** | Notebook: upload zip (or Google Drive), run cells, download zip |
| Lightning AI | T4/L4/L40S/A100… | One-time "up to 30" credits (5 on sign-up, +25 with a card), "~50 GPU hours on interruptible machines"; not monthly | Phone number required | Studio (a cloud VS Code / terminal): clone repo, run a script |
| Modal | T4 ($0.59/h) up to A100/H100 | $30/month free credits on Starter (≈50 T4 h or ≈14 A100-40GB h) | Needs Modal-specific Python code; may need a card | A small Modal script calls the same functions; could even be called from the GUI later |
| Hugging Face ZeroGPU | H200 slice | ~3.5 min/day for free accounts (docs disagree: 3.5–5 min) | Must be a Gradio Space | ❌ far too little time, and needs a Gradio app |
| A friend's / own NVIDIA PC | Whatever it has (e.g. RTX 4090 24 GB) | Free | None | Run the full app from source, exactly like spec 10 but with `torch==2.5.1+cu124`. Everything works, including waifu2x |

## 4. Recommended approach + rejected alternatives

| Approach | Verdict | Why |
|---|---|---|
| **One notebook (`notebooks/panelyze_gpu.ipynb`) for Kaggle + Colab: upload zip → run existing functions → download zip** | ✅ **Recommended** | Free, allowed by both sites' rules, zero changes to app code, same code = same results. Kaggle first (more hours, 2 GPUs, 16 GB each) |
| Local NVIDIA PC from source | ✅ Recommended when one is available | Best experience: whole GUI, waifu2x, no upload/download. Just a setup guide (shared with spec 10) |
| Remote worker the GUI sends jobs to (Colab/Kaggle + tunnel) | ❌ | Against Colab's free-tier rules, needs a server + tunnel + new GUI code. Big change |
| Modal function called from the GUI | Later, maybe | Nice "button in the app", but needs a Modal account, Modal-specific code and GUI work. Not simple |
| Hugging Face ZeroGPU Space | ❌ | ~3.5 min of GPU a day; would need a Gradio rewrite |
| Lightning AI | Backup | Credits are one-time, not monthly |
| A new `--run-chapter` CLI flag in `gui.py` | Not needed now | Notebook cells can call the functions directly. Add only if the notebook gets messy |

## 5. Files to change + existing functions to reuse

| File | Change |
|---|---|
| `notebooks/panelyze_gpu.ipynb` (new) | ~6 short cells (below) |
| `DEVELOPING.md` | A few lines: "Optional: use a free NVIDIA GPU on Kaggle/Colab" + "Running on an NVIDIA PC" |
| `ROADMAP.md` | Add row #20 |

No app code changes.

Reuse (unchanged):
- `magi.py`: `Magi().get_panels_for_chapter(input_directory, output_directory, selected_input_directory, reading_direction, group_by_page, read_text)` — saves panels in the same Panelyze folder layout; `get_device()`; `run_with_cpu_fallback()`.
- `janai.py`: `upscale_image_with_janai(input_image, output_image, upscale_ratio)` — "Best" upscaling; downloads its models on first use.
- `self_test.py` / `python gui.py --self-test` — quick "is the GPU working" check.
- `utils.py`: `list_images`, `get_relative_output_path`.

Notebook cells:
1. `!git clone` the repo (or upload a zip of it if the repo is private) and `pip install` requirements.txt with the torch line swapped to `torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu124`; skip `coremltools`, `flet-web`, `fastapi`.
2. Check: `torch.cuda.is_available()` and the GPU name; run `python gui.py --self-test`.
3. Unzip the uploaded chapters (e.g. `chapters.zip` made on the Mac from the Download output).
4. For each chapter folder: `Magi().get_panels_for_chapter(..., read_text=True)`.
5. Optional: "Best" upscale each panel with `upscale_image_with_janai`.
6. Zip the output folder for download.

## 6. Steps (todo)
- [ ] Write the notebook (6 cells above) and run it on Kaggle with Dragon Ball ch. 93
- [ ] Compare output with the Mac run: same number of panels, same `panel-text` file
- [ ] Time it: Magi per chapter and Best upscale per panel on T4, vs the M1 numbers in `benchmarks/`
- [ ] Try the same notebook on Colab free
- [ ] Optional: check whether waifu2x-ncnn-vulkan (Linux build) runs on Kaggle/Colab
- [ ] Add the short DEVELOPING.md section and ROADMAP #20 row
- [ ] (If a local NVIDIA PC is available) run from source with `torch==2.5.1+cu124`, `--self-test`, then a full Pipeline run

## 7. How to test it
- Kaggle: run all cells on Dragon Ball ch. 93; `--self-test` passes; the log says "Magi will read the text on the NVIDIA GPU."; no "Running it on the CPU instead" line.
- Unzip the result on the Mac and open it in Images To Video: the panels and text should look like a local run.
- Local test suite is unaffected (no app code changes): `pytest` still passes.

## 8. Size, value, risks, open questions

| | |
|---|---|
| Size | Small: one notebook + a few doc lines. About 1–2 hours including a test run |
| Value | Medium for whole-series runs (#3); Low for single chapters (the M1 is already fine) |
| Speed | Unmeasured. A T4 is likely a few times faster than the M1 GPU for Magi, but each session also spends a few minutes installing and downloading the 2 GB Magi model |
| Risk: transfers | Upscaled PNGs are ~2.4 MB per panel; a full series would be 200+ GB to download. Do Magi in the cloud, and upscale on the Mac or only keep small comic files |
| Risk: limits change | Colab and Kaggle don't publish exact quotas; they can change any time |
| Risk: private repo | If the GitHub repo is private, the notebook needs a token or an uploaded zip of the code |
| Risk: copyright | Uploading manga pages to cloud services: fine for personal use, but keep notebooks/datasets **private** on Kaggle |

**Open questions for the user**
1. Kaggle first, or Colab first? (Kaggle: more hours, needs phone verification.)
2. Is the GitHub repo public? (Decides clone vs uploaded zip.)
3. In the cloud: Magi only, or also "Best" upscaling?
4. Do you have access to a local NVIDIA PC (friend's or your own)? If so, that's the simplest of all.
5. Is a "Run in the cloud" button in the GUI wanted later (Modal), or is a notebook enough?

## 9. Sources
- Colab FAQ (limits, disallowed uses on free tier): https://research.google.com/colaboratory/faq.html
- Kaggle notebooks docs: https://www.kaggle.com/docs/notebooks ; quota roundups: https://gpuperhour.com/blog/free-cloud-gpus-and-credits , https://amitpandeytiktok.github.io/awesome-free-compute-2026/compute.html
- Lightning AI pricing: https://lightning.ai/pricing
- Modal pricing: https://modal.com/pricing
- Hugging Face ZeroGPU: https://huggingface.co/docs/hub/spaces-zerogpu , https://discuss.huggingface.co/t/what-is-the-free-zerogpu-quota-for-1-space/178610
- PyTorch CUDA wheels (2.5.1, cp312, Linux + Windows): https://download.pytorch.org/whl/cu124/torch/ , https://download.pytorch.org/whl/cu121/torch/
- Code checked: `magi.py` (`get_device`, `get_panels_for_chapter`), `janai.py` (`can_use_coreml`, `upscale_image_with_janai`), `gui.py` (argv flags), `self_test.py`, `utils.py` (`get_waifu2x_path`, `open_directory`)
