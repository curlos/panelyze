# Experiments

Things that were tried but aren't part of the app. Kept here in case they're useful later.

## `colab/` — running Magi on Google Colab's free GPU

`Magi_V2_Model_Analyze_Images_(Manga_Panel_Splitter).ipynb` is a Google Colab notebook that runs a small Flask server with the Magi model on Colab's GPU and exposes it to the internet with ngrok. The idea: the app sends manga pages to it and gets Magi's results back, so the heavy AI work runs on a fast GPU instead of the user's computer.

**Status: not used.** The app side of this (a `using_google_colab` switch in `magi.py`) was removed, because panel splitting now takes about 1–2 seconds per page on a Mac. It could be worth revisiting, with Colab or a similar free or cheap cloud GPU, for the video step's text reading (OCR), which takes about 20 seconds per page on a CPU.

What it needed: a Google account, an [ngrok](https://ngrok.com) auth token (`NGROK_AUTH_TOKEN` in a `.env` file on Google Drive), and the notebook left running. The old app code sent one page at a time as base64-encoded arrays in a JSON request (Flask's limit was 16 MB per request). To see how the app used to call it, look in git history for `get_panels_using_google_colab` in `magi.py`.
