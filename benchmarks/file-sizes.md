# File size benchmarks

How small panels can get for reading on a phone or iPad, while still looking good.

See [the overview](README.md) for the machine, the test chapters, and what "panels" and "pages" mean.

| Term | What it means |
|---|---|
| PNG vs WebP | PNG is **lossless** (it stores every pixel exactly, so busy screentone barely shrinks). WebP is **lossy** (it throws away detail the eye barely notices), so it's about 10× smaller here, while changing pixels by only about 3 out of 255 on average. |
| WebP 80% / 85% | The **quality setting** (0–100), not the size: how much fine detail WebP may throw away. Higher means better quality and a bigger file. |
| Grayscale | Only for black-and-white images (color pages are detected and keep their color). It barely changes the size (see below); it mainly removes the slight color tint some scans have. |
| iPhone width | The iPhone 13's screen is 1170 px wide, so pixels beyond that can't be seen (except when zooming in). |

The "per panel" sizes are the average of 20 sample panels. The chapter totals are measured on all 97 panels where marked; the rest are the sample average × 97.

| Format | Shachou ch. 3, per panel | Per chapter (97 panels) |
|---|---|---|
| Original panels (PNG) | 484 KB | about 47 MB |
| Upscaled panels (PNG) | 2,435 KB | 217 MB (measured) |
| Upscaled → WebP 80%, grayscale | 250 KB | 22 MB (measured) |
| Upscaled → WebP 80%, grayscale, iPhone width (1170 px) | 141 KB | about 14 MB |

| "Small" comic file (WebP 85%, gray for B&W) | Shachou ch. 3 (97 panels) | One Piece ch. 567 (97 panels) |
|---|---|---|
| Sized for phones (up to 1440 px wide) | 19.5 MB | 14.5 MB |
| **Sized for tablets (up to 2048 px wide; used)** | **24.6 MB** | **15.3 MB** |
| Upscaled PNGs, for comparison | 217 MB | 144 MB |

The tablet size was only 5–25% bigger than the phone size, so one "small" file covers both.

## Does grayscale make files smaller?

Barely. The big saving is WebP itself. All 97 upscaled panels of each chapter, WebP 80%:

| Chapter | PNG | WebP, color kept | WebP, made gray | Grayscale saves |
|---|---|---|---|---|
| Shachou ch. 3 (B&W; 5 color cover panels) | 217 MB | 22.1 MB | 21.7 MB | 2% |
| One Piece ch. 567 (color) | 144 MB | 13.7 MB | 12.1 MB | 12%, but it would lose the color, so the app never does this |

Color detection found 96 of 97 One Piece panels to be color (the other is a black-and-white credits panel), and 5 of 97 Shachou panels (its color cover).
