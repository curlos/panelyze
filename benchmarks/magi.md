# Magi benchmarks

Magi finds the panels and the text boxes, and reads the text.

See [the overview](README.md) for the machine, the test chapters, and what "panels" and "pages" mean.

## GPU vs CPU

| What | Ran on | CPU | Mac GPU | Faster by |
|---|---|---|---|---|
| Finding text boxes | 24 panels | 59.9 s | 51.9 s | 13% |
| Reading the text (63 text boxes) | 24 panels | 96.2 s | 65.8 s | 32% |
| Reading the text (110 lines, 8 at a time) | 17 One Piece pages | 133.5 s | 60.9 s | 2.2× |
| Finding panels (Panel-By-Panel's model; old code on the CPU vs new code on the GPU) | 27 pages | 22.1 s | 9.2 s | 2.4× |

| Did the GPU change the results? | Answer |
|---|---|
| Text boxes and text | Exactly the same |
| Panels | The same 97 panels, with corners at most 0.002 px apart |

## Dialogue only

| What | Result |
|---|---|
| Before | Magi read every text box, but Panelyze only used the dialogue |
| After | Only dialogue boxes are read (Magi marks sound effects and background text separately) |
| Text boxes skipped | 2% on the first 24 Shachou panels (1 of 63 boxes); about 10–20% across the whole chapter (an estimate from 229 dialogue lines out of about 260–290 boxes) |
| Dialogue | Exactly the same |

## Pages vs panels (finding + reading text)

| Ran on | CPU total | GPU total |
|---|---|---|
| **Page 02** (1 page) | **19.1 s** | **10.8 s** |
| The same page as 8 panels (panels 9–16) | 52.6 s | 24.9 s |
| **Page 03** (1 page) | **23.4 s** | **11.1 s** |
| The same page as 6 panels (panels 17–22) | 40.0 s | 50.4 s (an outlier that was never explained) |

| Why pages win | |
|---|---|
| Finding | Magi shrinks every image to the same size first, so 1 page costs about as much as 1 panel. Fewer images, less work. |
| Reading | About the same either way: the cost is per text box, and a page has the same text boxes as its panels. |
| Quality | Pages avoid speech bubbles cut in half at panel edges, which made junk lines like "she-she-she is con-tioned*...". |

## Gluing pages into one big image

| Ran on | Finding | Reading | Text boxes found |
|---|---|---|---|
| 4 pages, one at a time | 7.0 s | 83.3 s | 50 (45 dialogue) |
| The same 4 pages glued 2×2 | 4.4 s | 165.5 s | 43 (36 dialogue) |

| Result | |
|---|---|
| Finding | ✅ 2.6 s faster |
| Accuracy | ❌ 9 lines of dialogue missed: the glued image is shrunk, so small bubbles become too small to spot |
| Reading | ❌ Twice as slow, even with fewer boxes. Likely because some boxes were badly shaped and Magi read long, garbled lines (not confirmed; a single run on the CPU). |
| Verdict | Not worth it |

## How many images at once (finding text)

The panels are upscaled One Piece panels, all 50 a different size. The pages are One Piece pages in 4 different sizes, because of double-page spreads.

| Images at once | 50 panels, GPU | 50 panels, CPU | 17 pages, GPU | 17 pages, CPU |
|---|---|---|---|---|
| **1** (chosen) | **59.6 s** | **43.5 s** | **16.9 s** | **25.1 s** |
| 4 | 174.9 s | — | — | — |
| 8 (Magi's default) | 163.3 s | 133.5 s | 20.9 s | 37.6 s |
| 12 | 148.0 s | — | — | — |
| 16 | 98.5 s | — | — | — |
| 17 (all pages) | — | — | 31.7 s | — |
| 25 or 50 | out of GPU memory | 50: 398.9 s | — | — |

| Why | |
|---|---|
| Why 1 at a time wins | Images looked at together are padded to the size of the biggest one. A wide panel next to a tall panel becomes a huge, mostly blank square. |
| Why pages benefit less | Most pages are already the same size, so there's little padding to save. |
| Why the CPU beat the GPU on panels | The GPU has to get ready for every new image size (see below), and these 50 panels were all different sizes. |

**Why the GPU has to "get ready" and the CPU doesn't:** when PyTorch runs Magi on the Mac GPU, it builds a GPU program for each step of the model that's made for the **exact image size**. Building it takes time, then it's saved and reused for that size. The CPU's code handles any size as it goes, so it has nothing to prepare. It's slower per calculation, but has no warm-up cost. It's like a factory that re-tools its machines for every new box size and then works very fast, vs a craftsman who builds any size by hand.

| Finding text, GPU vs CPU | GPU | CPU |
|---|---|---|
| 50 panels, all different sizes, first time | 59.6 s (builds new programs for every panel) | **43.5 s** |
| The same 50 panels again | **28.8 s** (programs already built) | 47.0 s |
| 17 pages, mostly the same size | **16.9 s** (few rebuilds) | 25.1 s |

This is also why the Neural Engine needs a **fixed** size: its programs are built once, ahead of time, for exactly one size.

## How many lines read at once (reading text)

| Lines at once | 110 lines from 17 One Piece pages, GPU |
|---|---|
| 1 | 65.8 s |
| 4 | 59.8 s |
| **8** (chosen) | **60.9 s** |
| 16 | 76.6 s |
| 32 (Magi's default) | 93.6 s |
| 64 | 147.8 s |

| Why | |
|---|---|
| Why smaller groups win | Magi writes each line one word-piece at a time, and lines read together all wait for the longest one. |
| Text | The same at every setting |
| 4 vs 8 | A tie (within run-to-run noise). 8 is safer on bigger GPUs. |

## Final check: old vs new settings (finding + reading, 27 Shachou pages)

| Settings | Round 1 | Round 2 |
|---|---|---|
| Old (8 pages, then 32 lines at a time) | 173.1 s | 216.0 s |
| **New (1 page, then 8 lines at a time)** | **162.2 s** | **179.3 s** |

Both read identical text. Round 2 was slower for everything, probably because the Mac gets hot after a long stretch of work.

## Magi on the Neural Engine (an experiment, not used yet)

| Finding text boxes, Magi converted to Core ML | Ran on | Per page |
|---|---|---|
| PyTorch on the GPU (what the app uses) | 8 Shachou pages | 0.31 s |
| Core ML on the GPU | 8 Shachou pages | 0.14 s |
| **Core ML on the Neural Engine** | 8 Shachou pages | **0.08 s** |

| Why it isn't used yet | |
|---|---|
| Small gain | Finding text boxes is now only about 10–20 s of a chapter. |
| Reading can't move | Reading writes one word-piece at a time, which is a poor fit for the Neural Engine. |
| Fixed sizes only | Each page shape needs its own one-time conversion (27 s), and panels (all different sizes) can't use it. |
