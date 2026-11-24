# Experiments

Things that were tried but aren't part of the app. Kept here in case they're useful later.

## `colab/` — running Magi on Google Colab's free GPU

`Magi_V2_Model_Analyze_Images_(Manga_Panel_Splitter).ipynb` is a Google Colab notebook that runs a small Flask server with the Magi model on Colab's GPU and exposes it to the internet with ngrok. The idea: the app sends manga pages to it and gets Magi's results back, so the heavy AI work runs on a fast GPU instead of the user's computer.

**Status: not used.** The app side of this (a `using_google_colab` switch in `magi.py`) was removed, because panel splitting now takes about 1–2 seconds per page on a Mac. It could be worth revisiting, with Colab or a similar free or cheap cloud GPU, for the video step's text reading (OCR), which takes about 20 seconds per page on a CPU.

What it needed: a Google account, an [ngrok](https://ngrok.com) auth token (`NGROK_AUTH_TOKEN` in a `.env` file on Google Drive), and the notebook left running. The old app code sent one page at a time as base64-encoded arrays in a JSON request (Flask's limit was 16 MB per request). To see how the app used to call it, look in git history for `get_panels_using_google_colab` in `magi.py`.

## `spec-10-benchmarks/` — the Windows PC + RX 6700 XT timings on Absolute Batman ch. 1

The scripts behind the "Comics" section of `benchmarks/README.md` (spec 10, 2026-11-23). They read Absolute Batman ch. 1 from `~/Documents/Panelyze/10-amd-gaming-pc/` (downloaded with the app from comix.to, see `benchmarks/test-chapters.md`) and save into that folder too. Run them from the repo folder, one at a time (they all use the GPU):

- `best_4k_before_after.py`: "Best" to 4K on panels 30–49, the new way (same-size tiles, stopping short of 4K) and the old way, with the times. Saves `panel_N-before.png` / `panel_N-after.png` into `benchmark-absolute-batman-ch1-best-4k/`. Run: `.\venv\Scripts\python.exe experiments\spec-10-benchmarks\best_4k_before_after.py`
- `duplicate_tile.py`: "Best" to 4K on a few panels with the edge-tile fix (2026-11-24) and without it, with the times and the number of tiles. Before the fix, a same-size tile that reached an image's edge was sometimes upscaled a second time for its last few pixels. It saved about 1.5% of the tiles on comic panels (Absolute Batman ch. 1, Shachou ch. 3's panels) and none on Shachou ch. 3's pages. Run: `.env\Scripts\python.exe experiments\spec-10-benchmarks\duplicate_tile.py [panel numbers]`
- `test_panels_and_video.py`: Panel-By-Panel (twice) and Images To Video with a voice (twice) through the app's own Submit buttons. Run: `.\venv\Scripts\python.exe -m pytest -p tests.fake_gui -s -o "addopts=" experiments\spec-10-benchmarks\test_panels_and_video.py`
- `test_upscale_4k.py`: the same 20 panels to 4K with "Fast", "Better" and "Best" through the Upscale tab. Run like the one above.
