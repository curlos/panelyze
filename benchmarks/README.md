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

## The benchmarks

| Topic | What's in it |
|---|---|
| [Magi](magi.md) | GPU vs CPU, dialogue only, pages vs panels, gluing pages, images and lines at once, the Neural Engine |
| [Making the video](video.md) | Old code vs new, smaller speedups, the whole Pipeline timed |
| [Panel cropping](panel-cropping.md) | Keeping speech bubbles and characters whole, tested on 25 chapters from 17 series. The 4-koma reading order. |
| [Webtoons](webtoons.md) | Splitting vertical-scroll comics into panels with sliding windows, tested on 10 chapters from 10 series |
| [Upscaling](upscaling.md) | waifu2x settings, every upscaler on black and white and on color, making MangaJaNai and IllustrationJaNai faster, the "Best" model |
| [File sizes](file-sizes.md) | Formats and sizes for reading on a phone or iPad |
| [Translate](translate.md) | Every local translator against the official English and Spanish on three chapters and four language pairs, and the lettering problems found and fixed |
| [Test chapters](test-chapters.md) | Every chapter downloaded or imported for testing: manga, chapter, source (MangaDex, comix.to, Internet Archive, page URL or an imported file) with its link, date and what it was used for |

## Other questions that were looked into

| Question | Answer |
|---|---|
| Is a GPU always faster than a CPU here? | Almost always for AI models, because they're mostly matrix math. The M1's CPU is closer than you'd expect: it has a built-in matrix-math unit, and the M1's GPU is small. |
| Would an AMD RX 6700 XT help? | Probably 3–5× faster than the M1's GPU for Magi (an estimate), but only on that PC, not the Mac, and best under Linux (ROCm). AMD's new Windows builds ("TheRock") list its chip, but are still previews. VMs and WSL2 can't use it. |
| Could Panelyze translate raw Japanese pages? | Yes. Magi gives the text box positions. The plan is manga-ocr to read the Japanese, then Claude, ChatGPT, Gemini or a free local model through Ollama to translate, then erase the Japanese and letter the English into the bubbles. |
