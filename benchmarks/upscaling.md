# Upscaling benchmarks

waifu2x, Real-CUGAN, MangaJaNai and IllustrationJaNai. Every upscale here is 2×.

See [the overview](README.md) for the machine, the test chapters, and what "panels" and "pages" mean.

## waifu2x settings

| How | 48 Shachou panels | Same image as before? |
|---|---|---|
| One waifu2x run for each panel (before) | 43.6 s | — |
| **One run for the whole folder** | **23.5 s** | ✅ identical |
| More threads (2:2:2 or 2:4:4) | 25.2 s | ✅ identical, no faster |
| Tile size 128 / 256 / 400 | 29.0 / 26.0 / 25.4 s | no faster (128 and 256 change pixels slightly) |
| **Faster model** (`upconv_7` instead of `cunet`) | **10.4 s** | very slightly different (4 of 255 on average) |

The whole folder is faster because waifu2x loads its model and starts the GPU once, not 48 times.

## Every upscaler, black and white (Shachou ch. 3, 97 panels)

| Upscaler | Time | How it looks |
|---|---|---|
| Plain resize (no AI) | instant | soft and blurry |
| **waifu2x fast** (default) | **30 s** | sharp; gray shading a little busy |
| waifu2x cunet | 70 s | sharp; gray shading a little cleaner |
| Real-CUGAN se / pro | 78 s / 75 s | ❌ smears gray shading into a waxy texture (pro also tints it purple) |
| MangaJaNai with PyTorch on the GPU | 466 s | ✅ **by far the best**: crisp, even halftone dots, like a printed book |

## Every upscaler, color (One Piece ch. 567, 97 panels)

| Upscaler | Time | How it looks |
|---|---|---|
| Plain resize (no AI) | 5.0 s | soft |
| waifu2x fast | 8.7 s | sharp, with purple/blue fringes along some lines |
| waifu2x cunet | 26.0 s | cleaner, a few smudges |
| Real-CUGAN se / pro | 25.6 s / 25.3 s | good on color: clean flat colors |
| MangaJaNai | 109 s | ❌ turns color into black and white dots (it's a black-and-white model) |
| IllustrationJaNai with PyTorch on the GPU | 185 s | ✅ cleanest: smooth colors, crisp lines |

## Making MangaJaNai faster

| How | 20 Shachou panels, per panel | Looks the same? |
|---|---|---|
| PyTorch on the GPU (tiles fit each panel) | 1.60 s | — |
| Fixed-size tiles (384 / 512) | 3.08 s / 2.86 s | ✅ (slower: small panels get padded) |
| Half precision + fixed tiles (384 / 512 / 768) | 2.44 s / 2.21 s / 2.88 s | ✅ |
| Core ML on the GPU | 1.72 s | ✅ |
| **Core ML on the Neural Engine** | **0.44 s** (3.6× faster) | ✅ |
| *(waifu2x fast, for comparison)* | *about 0.31 s* | |
| **Core ML on the Neural Engine, all 92 B&W panels of the chapter** (re-measured, includes opening and saving each PNG) | **0.66 s** on average (66.8 s in total, of which the first panel took 7.1 s to load the model) | ✅ the 0.44 s above was only the 20-panel sample, so the whole chapter is about 2× slower than waifu2x fast (30 s) |

## Making MangaJaNai on the Neural Engine even faster

All 92 B&W Shachou panels, one fresh process per test. Model loading (about 6 s) isn't included.

| How | 92 panels | Looks the same? |
|---|---|---|
| Before (tiles overlap by 16 px) | 61.3 s: upscaling 56.2 s, saving 4.4 s, opening 0.7 s | — |
| Faster PNG saving | 62.0 s | ✅ identical, no faster |
| **Tiles overlap by 8 px (used)** | **50.9 s** (17% faster) | ✅ no seams; a few halftone dots shift (5.6% of pixels on the worst panel) |
| Tiles overlap by 4 px | 49.4 s | ✅ but changes a bit more than 8 px, for 1.5 s |
| Skip blank tiles | 66.9 s | ✅ identical, no faster (no tile was blank enough) |
| Batching tiles into one Core ML call | 62.0 s | ✅ identical, no faster |
| Neural Engine and GPU at the same time | 145.1 s | ❌ 2.4× slower |
| Shrinking panels to 75% first | 39.2 s | ❌ visibly softer and smaller |

The 8 px overlap also applies to IllustrationJaNai: the 5 color Shachou panels took 111 s instead of 125 s, and the output was nearly identical (0.06% of pixels visibly changed).

## Making IllustrationJaNai (color) faster

| How | Speed | Result |
|---|---|---|
| PyTorch on the GPU, half precision | 0.35 s per 256 px tile | ❌ broke some panels (numbers overflowed into blank pixels) |
| **Core ML on the GPU** | **0.23 s per 256 px tile** (1.5× faster) | ✅ same output as PyTorch |
| Core ML on the Neural Engine | — | ❌ Apple's compiler got stuck |
| Tiles fitted to each panel (PyTorch) vs fixed (Core ML) | 39.4 s vs 39.4 s for 20 panels | no faster |

| Why MangaJaNai runs on the Neural Engine and IllustrationJaNai doesn't | |
|---|---|
| MangaJaNai (ESRGAN design) | Almost all convolutions (small filters slid over the image), exactly what the Neural Engine is built for |
| IllustrationJaNai (FDAT design) | Transformer-style, with attention and lots of reshaping. Apple's Neural Engine compiler couldn't handle it. |

## "Best" upscale in the app (MangaJaNai for B&W + IllustrationJaNai for color)

| Ran on | First time ever (one-time model setup) | After that | waifu2x fast |
|---|---|---|---|
| Shachou ch. 3, 97 panels (92 B&W + 5 color cover panels) | 523 s | **138 s** | 31 s |
| One Piece ch. 567, 97 panels (96 color + 1 B&W) | 188 s | **142 s** | 10 s |

Color is the slow part, because IllustrationJaNai can't use the Neural Engine.

## Other upscaling findings

| Finding | Details |
|---|---|
| The right MangaJaNai model matters | There's one model per page height (1200p–2048p). On Shachou (1600 px pages), the 1600p model made clean, even dots. The 1200p model made finer dots with streaky lines. So Panel-By-Panel now saves each panel's page height inside the panel file. |
| Upscaling pages instead of panels is slower | Unlike Magi, upscalers work on every pixel, and pages also have the gutters and margins. Shachou: 27 pages = 63.6 million pixels vs 97 panels = 52.9 million (1.2×). One Piece: 18.7 vs 17.6 million (1.06×). |
| waifu2x can't fix blur | It sharpens enlarged pixels and removes noise, but a big, blurry image stays blurry. |
