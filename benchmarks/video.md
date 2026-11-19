# Video benchmarks

Making a voiced video with Images To Video, and the whole Pipeline.

See [the overview](README.md) for the machine, the test chapters, and what "panels" and "pages" mean.

## 5 panels (Shachou panels 14–18), old code vs new

| Step | Before | After |
|---|---|---|
| Reading the text (Magi) | 36.1 s | 19.4 s |
| Voice-over | 1.8 s | 1.3 s |
| Writing the video | 5.6 s | 1.6 s |
| **Total** | **43.9 s** | **22.7 s** |

Panel 16 has only "...!", which used to crash the voice-over. It's now skipped and shown for 1 second.

## Pipeline: 2 pages → 14 panels → video, old code vs new

| Step | Before | After |
|---|---|---|
| Panel-By-Panel | 4.6 s | 30.2 s (now also reads the text on the 2 pages) |
| Video: reading the text | 86.2 s (reads the 14 panels) | 0 s (uses what Panel-By-Panel read) |
| Video: voice-over | 14.7 s | 4.8 s |
| Video: writing | 21.3 s | 5.1 s |
| **Total** | **128.9 s** | **42.3 s** |

## Smaller video speedups

| What | Ran on | Before | After |
|---|---|---|---|
| Joining clips (`compose` → `chain`; every clip is already the full frame size) | 97 panels | 45.2 s | 18.3 s |
| Voice-over (4 lines at a time) | 6 lines | about 4 s (0.67 s each) | 1.0 s |
| Making the same video again (saved Magi results) | 5 panels | 39 s | 8 s |

| Not changed | Ran on | medium (default) | veryfast | ultrafast |
|---|---|---|---|---|
| Video encoder preset | 20 panels | 3.5 s, 5.8 MB | 3.1 s, 5.4 MB | 3.0 s, 16.4 MB |

## The whole Pipeline (Shachou ch. 3: 27 pages → 97 panels, 1080p voiced video)

| Step | Time |
|---|---|
| MangaDex download (27 pages) | 5 s |
| Panel-By-Panel (97 panels + reading the text on the 27 pages) | 4 min 5 s |
| Upscale (97 panels; before the upscale speedups) | 2 min 0 s |
| Images To Video | 1 min 40 s |
| **Total** | **7 min 49 s** |

After this run, Panel-By-Panel got faster (8 lines at a time), and Upscale got about 4× faster (31 s). The download isn't worth speeding up.
