# Panelyze benchmarks

What was measured while speeding up Panelyze (November 2026), and what was learned. Every number comes from a real run on the same machine, unless it's marked as an estimate.

**Panels vs pages:** a **page** is a whole manga page (a group of panels). **Panels** are the single panels Panel-By-Panel cuts out of the pages. Every table says which one it ran on.

| Setup | Details |
|---|---|
| Machine | MacBook with an Apple M1. Its CPU has 8 cores (4 fast, 4 efficient), its GPU has 8 cores, and its Neural Engine is built for AI. All three share 16 GB of memory. |
| Test chapter 1 | **Shachou to Sake to Hoshi, ch. 3:** black and white, **27 pages → 97 panels**, about 218 lines of dialogue. |
| Test chapter 2 | **One Piece (Official Colored), ch. 567:** color, **17 pages → 97 small panels**. |

## The headline (Shachou ch. 3)

| What | Before | After |
|---|---|---|
| Reading the text + making a voiced video | about 17 min (from the original run's log) | **5 min 4 s** |
| Whole Pipeline: download → panels → upscale → video | never timed in one go | **7 min 49 s** |
| Upscaling the 97 panels (default model) | 119 s | **31 s** |

## Windows PC with an AMD RX 6700 XT vs the M1

Measured 2026-11-22 on a Windows 11 PC with a Radeon RX 6700 XT (12 GB) and a Ryzen 5 7600, run from source with AMD's TheRock PyTorch (`torch 2.15.0+rocm10.3.0a20261122`, see `DEVELOPING.md`). Each tab ran on its own, with the app's default settings, through the app's Submit buttons, with the GPU picked by the app (no `HIP_VISIBLE_DEVICES`). Everything ran on the GPU (no CPU fallback). Each chapter was run twice; the table has the second run.

**The first time is much slower.** A GPU is fast because thousands of small workers do the math at once, but the work has to be split between them, and the best way to split it depends on the image's exact size in pixels. The first time AMD's GPU software (MIOpen, under PyTorch) sees a size, it builds a few ways of doing it for this chip, times them, keeps the fastest and saves that on disk. After that, the same size starts right away. It's about the size, not the picture:

- **Panel-By-Panel and video (Magi):** the size after Magi resizes the page (short side 800 px). Dragon Ball ch. 93's pages become 800×1231, One Piece ch. 567's 800×1263, so each is new the first time.
- **"Best" upscale:** the size of its tiles. Since 2026-11-23 every tile is 512×512 with AMD's PyTorch (the edges are padded), so there's only one size to work out. Before, the tiles at the edges fitted each image (1560×2400, 760×1200, ...), and comics, whose panels are all different sizes, paid the slow first time on nearly every panel (see "Comics" below). Each "Best" model (one per page height) is still new the first time. The "Best" times in the tables below are from before that change.
- Pages from the same source are usually the same size, so the next chapter of a series is fast. Same magazine isn't enough: digital files differ in size by who scanned or published them.

The CPU has nothing to work out (a few cores, no saved plans), so its times are the same every run. Even the GPU's slow first run beat the CPU here (Panel-By-Panel: 21.8 s vs about 78 s).

| First run vs second | Shachou ch. 3 | One Piece ch. 567 | Dragon Ball ch. 93 |
|---|---|---|---|
| Upscale "Best" | 298 s (incl. downloading the models) → 51–56 s | 104 s → 27 s | 202 s → 63 s |
| Images To Video | 153 s → 62 s | 111 s → 33 s | 104 s → 39 s |
| Panel-By-Panel | 21.8 s → 6.5 s | 33.3 s → 12.1 s | 14.2 s → 6.0 s |

**Second runs, vs the M1** (the M1's numbers are after its first run too):

| What | Shachou ch. 3 (27 pages → 97 panels, B&W) | One Piece ch. 567 (17 pages → 97 panels, color) | Dragon Ball ch. 93 (16 pages → 83 panels, color) |
|---|---|---|---|
| Panels found | 97 (M1: 97) | 97 (M1: 97) | 83 (M1: 83) |
| Download | 5.3 s | 7.0 s | 5.5 s |
| Panel-By-Panel | **6.5 s** (M1: 11.3 s, 1.7×); 11.7 s as the first job after starting the app (loading Magi) | **12.1 s** (first job after starting the app, so it includes loading Magi: not comparable with the others) | **6.0 s** |
| Upscale "Fast" (waifu2x) | **10.4 s** (M1: 31 s, 3×) | **3.1 s** (M1: 8.7–10 s, 3×) | **7.0 s** |
| Upscale "Best" (MangaJaNai + IllustrationJaNai) | **51–56 s** (M1: 138 s with Core ML, 2.5×; 466 s with PyTorch on the Mac GPU) | **26.7 s** (M1: 142 s, 5×) | **62.6 s** |
| Images To Video (read the text + voice, 1080p) | **62 s** (M1: 5 min 4 s, 5×) | **32.6 s** | **38.6 s** |

The M1 has no times for One Piece's and Dragon Ball's Panel-By-Panel and video, or for Dragon Ball's upscaling. On the CPU alone (Ryzen 5 7600), Panel-By-Panel on Shachou took 76–80 s.

### Comics: Absolute Batman ch. 1 (45 pages, 318 panels of every size, color), 2026-11-23

| What | Time |
|---|---|
| Panel-By-Panel | 27.2 s, then 27.6 s (the pages are nearly all 1326×2038, so no slow first time) |
| Images To Video (read the text + voice, 1080p) | 546 s, then 302 s: reading the text runs Magi on each panel, and every panel size is new the first time |
| "Best" to 4K, 20 panels (30–49), the same code without the app | **391 s before → 98 s after** (19.5 → 4.9 s a panel) |
| The same 20 panels to 4K through the Upscale tab | "Fast" 39.5 s, "Better" 88.8 s, "Best" 130.4 s; every image exactly 3840 px on its longest side (with the old stretch to 4K) |
| The same, again, without the stretch | "Fast" 39.5 s, "Better" 88.8 s, "Best" **120.0 s**; "Best"'s 12 stopped-short panels end at 2608–3776 px. The stretch (and saving the bigger PNG again) cost about 0.8 s a panel |

Two changes made "Best" to 4K about 4× faster here:
- **Same-size tiles with AMD's PyTorch** (`janai.py`; NVIDIA and the CPU keep tiles that fit each image, since padding would only add work there): see "The first time is much slower" above. On their own, about 2× faster on new panel sizes (1.4 s → 0.3–0.8 s a panel for one 2× pass).
- **Stopping short of 4K** (`get_best_upscale_ratio` in `utils.py`): "Best" doubles the size with each pass, so a 429 px panel needed 16× (6864 px, almost 3× the pixels of 4K) before being shrunk back. Now it does 8× (3432 px) when that's at most 1.5× short of 4K, and the image stays at that size: stretching it to 4K would add no detail (a 4K video stretches it to fit its frame anyway). The 391 s → 98 s benchmark above still did that stretch, so without it "Best" is a little faster still. The user compared all 20 before/after pairs side by side on 2026-11-24 (including the 12 that stop short) and was happy with the quality, so the 1.5× cutoff stays.

## The benchmarks

| Topic | What's in it |
|---|---|
| [Magi](magi.md) | GPU vs CPU, dialogue only, pages vs panels, gluing pages, images and lines at once, the Neural Engine |
| [Making the video](video.md) | Old code vs new, smaller speedups, the whole Pipeline timed |
| [Panel cropping](panel-cropping.md) | Keeping speech bubbles and characters whole, tested on 25 chapters from 17 series. The 4-koma reading order. |
| [Webtoons](webtoons.md) | Splitting vertical-scroll comics into panels with sliding windows, tested on 10 chapters from 10 series |
| [Upscaling](upscaling.md) | waifu2x settings, every upscaler on black and white and on color, making MangaJaNai and IllustrationJaNai faster, the "Best" model |
| [File sizes](file-sizes.md) | Formats and sizes for reading on a phone or iPad |
| [Test chapters](test-chapters.md) | Every chapter downloaded or imported for testing: manga, chapter, source (MangaDex, comix.to, Internet Archive, page URL or an imported file) with its link, date and what it was used for |

## Other questions that were looked into

| Question | Answer |
|---|---|
| Is a GPU always faster than a CPU here? | Almost always for AI models, because they're mostly matrix math. The M1's CPU is closer than you'd expect: it has a built-in matrix-math unit, and the M1's GPU is small. |
| Would an AMD RX 6700 XT help? | Yes, on that PC: 1.7× (Panel-By-Panel) to 2.5–5× ("Best" upscale, the video) faster than the M1, measured on Windows 11 with AMD's TheRock PyTorch builds (see above). The first run of each new image size is 2–4× slower (see "The first time is much slower" above). No Linux needed. VMs and WSL2 can't use it. |
| Could Panelyze translate raw Japanese pages? | Yes. Magi gives the text box positions. The plan is manga-ocr to read the Japanese, then Claude, ChatGPT, Gemini or a free local model through Ollama to translate, then erase the Japanese and letter the English into the bubbles. |
