# 37. Better, more expressive voices

Related: [#38 character sheets](38-character-sheets.md), [#36 better text reading](36-better-text-reading.md)

New item, not on the roadmap yet. **Draft from the user's ideas (2026-11-22), not researched yet**: written from what's already known, to be checked and researched before building.

## 1. Summary

The voice-over is basic: one voice reads every line in the same tone. For videos people would watch (e.g. a chapter read out loud on YouTube), it should sound more like a performance: emotions, shouting and whispering, a narrator for captions, and different voices for different characters.

## 2. Is it doable?

Yes, in steps. Some of it works with today's engines; the bigger jumps need a newer voice engine. Reading emotion from the character's face is the most uncertain part and needs a test first.

## 3. What's already true

| Claim | Status |
|---|---|
| Engines | ✅ Edge (free, no key, plain voice only) and Azure (needs a key) |
| Emotions | ✅ Azure only: "Speaking style" → "Auto (emotion of each line)" uses an emotion model (`EmotionAnalyzer.py`, distilroberta, about 330 MB) to pick e.g. cheerful or sad for each line |
| Edge emotions | ❌ Edge voices can't change style. Changing only speed and pitch per emotion was offered in spec 17 and turned down for now. |
| Who says each line | ✅ Magi v2 (full model) links each bubble to a character, and groups the same character across a chapter (without names) |

## 4. Ideas + options (to research)

| Idea | How |
|---|---|
| A different voice per character | Magi's character groups give a consistent voice per character in a chapter, even without names. With spec 38, the same voice across chapters. |
| Narrator voice for captions | Captions (boxes, not bubbles) read by a narrator voice |
| Shouting and whispering | From the text (ALL CAPS, "!!!", "...") and, later, the bubble's shape or font size |
| Emotion from the text | Today's emotion model for every engine that supports styles; or engines that take a direction like "say it angrily" |
| **Emotion from the character's face** | Manga shows emotion in the drawing: an angry face, sweat drops, shaking lines, a big open mouth. Magi finds the speaker's box (full model), so the face can be cropped and given to an image emotion model, or to a vision LLM ("is this character angry, scared, happy?"). Then combine it with the text's emotion: an angry face with "I'm fine." should sound angry, not calm. Needs a test on manga faces: models trained on photos may not read drawn faces well. |
| Sound effects | Skip them (today they're mostly skipped, since only dialogue is read), or play real sound effects |
| More natural timing | Short pauses between speakers; a little longer between panels |

**Voice engines to compare** (from what's known):

| Engine | Notes |
|---|---|
| Azure (today) | Many styles, needs a key |
| OpenAI TTS (e.g. gpt-4o-mini-tts) | Takes directions ("whisper, scared"), paid |
| ElevenLabs | Very expressive, paid |
| Google Gemini TTS | Takes style directions, paid or free tier |
| Kokoro | Free, local, small and fast, good quality, little emotion control |
| XTTS-v2 / F5-TTS / StyleTTS2 | Free, local, can copy a voice from a short sample (so each character can have its own voice); slower |
| Bark | Free, local, can laugh or sigh; slow and less reliable |
| Piper | Free, local, very fast, plain |

## 5. Files to change

| File | Change |
|---|---|
| `TextToSpeech.py` | A new engine; voice per character; narrator voice; emotion/style per line |
| `VideoCreatorFromImages.py` | Pass who says each line (from Magi) to the voice |
| `gui_classes/TextToSpeechAzure.py` (Images To Video settings) | Engine, voices per character, narrator |
| `requirements.txt` + lock | The chosen engine (shared venv: install on purpose) |

## 6. Steps

- [ ] Pick 2–3 engines and make the same 30 seconds of a chapter with each; the user listens and picks.
- [ ] A voice per character (Magi's groups) with the picked engine.
- [ ] Narrator for captions; shouting and whispering.
- [ ] Emotion from the face: on ~50 lines with an obvious emotion, compare the text's emotion, the face's emotion and both together; keep it only if it's right clearly more often.

## 7. How to test

| Check | Pass |
|---|---|
| The user's listening test | The picked engine sounds clearly better than Edge |
| Characters | The same character keeps the same voice through a chapter |
| Cost | Known per chapter for paid engines |

## 8. Size, value, risks, open questions

| | |
|---|---|
| Size | Medium–Large |
| Value | High for videos people would watch |
| Risk | Paid engines cost money per chapter; local ones can be slow and large |
| Open questions | Free and local only, or paid options too? How much emotion is too much? Can a model read emotion from drawn faces well enough? |

## 9. Sources

- The user's ideas, 2026-11-22; what the app does today (`TextToSpeech.py`, `EmotionAnalyzer.py`)
