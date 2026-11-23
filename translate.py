"""
Translate: turn manga pages in one language (Japanese, English or Spanish) into pages in another (English or Spanish), the way a scanlation does. See "specs/01-translate-japanese-pages.md".

1. Magi finds the text boxes.
2. A reader reads each box: Hayai OCR for Japanese, Magi's own reader for English and Spanish.
3. An LLM (Ollama on this Mac, Gemini, ChatGPT or Claude) gets the page with each box numbered, plus the text, and returns one translated line per number. It never edits the image.
4. The original text is erased: a flat bubble is filled with its own color, text on artwork is painted over by LaMa.
5. The translation is lettered into the bubble.
"""
import base64
import difflib
import io
import json
import os
import re
import shutil
import time
import unicodedata

import numpy
from PIL import Image, ImageDraw, ImageFont

from utils import READING_DIRECTION_FILE_NAME, utils_load_dotenv

# The fonts the translation can be lettered in, all free under the SIL Open Font License (their licenses are next to them).
FONTS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")
FONTS = {
    "Bubble Sans": "BubbleSans-Regular.otf",
    "Comic Neue Bold": "ComicNeue-Bold.ttf",
    "McLaren": "McLaren-Regular.ttf",
    "Patrick Hand": "PatrickHand-Regular.ttf",
    "DynaPuff": "DynaPuff.ttf",
    "Bangers": "Bangers-Regular.ttf",
}

SOURCE_LANGUAGES = {"japanese": "Japanese", "english": "English", "spanish": "Spanish"}
TARGET_LANGUAGES = {"english": "English", "spanish": "Spanish"}

ENGINES = {"ollama": "Ollama (free, runs on this computer)", "gemini": "Gemini", "chatgpt": "ChatGPT", "claude": "Claude"}
# Ollama's default depends on the computer and the languages (see "get_default_model").
DEFAULT_MODELS = {
    "gemini": "gemini-3.8-flash",
    "chatgpt": "gpt-6-sol",
    "claude": "claude-opus-5-5",
}
PLAMO_2B = "hf.co/pfnet/plamo-3-translate-2b-GGUF:Q4_K_M"
PLAMO_8B = "hf.co/pfnet/plamo-3-translate-8b-GGUF:Q4_K_M"
PLAMO_31B = "hf.co/pfnet/plamo-3-translate-31b-GGUF:Q4_K_M"
# The suggested Ollama models, all free and run on this computer, three for each size of computer memory, best first in the tests ("memory_gb": made for computers with at least that much). "size" is the download (and about the space it takes), in GB of 1,000,000,000 bytes like ollama.com (and the Mac's Finder). "about" says what it's good and bad at, from the spec 01 tests. "line_by_line": a pure translator that takes one line at a time in its own prompt format, can't see the page or answer in JSON (see "translate_line_by_line"). "only": the only language pair it knows.
OLLAMA_MODELS = {
    PLAMO_2B: {"name": "PLaMo 3 Translate 2B", "size": "1.8 GB", "memory_gb": 8, "line_by_line": True, "only": ("japanese", "english"),
               "about": "Japanese to English only. Fastest and smallest, made in Japan for Japanese. Doesn't see the page, so it may guess who's speaking wrong."},
    "qwen3-vl:4b-instruct": {"name": "Qwen3-VL 4B", "size": "3.3 GB", "memory_gb": 8,
                             "about": "Any language. Sees the page (who's speaking, sound effects to skip), but makes more mistakes than the 16 GB models."},
    "translategemma:4b": {"name": "TranslateGemma 4B", "size": "3.3 GB", "memory_gb": 8, "line_by_line": True,
                          "about": "Any language (55). Fast. Doesn't see the page, and gets more meanings and names wrong than the bigger models."},
    PLAMO_8B: {"name": "PLaMo 3 Translate 8B", "size": "5.3 GB", "memory_gb": 16, "line_by_line": True, "only": ("japanese", "english"),
               "about": "Japanese to English only. Fewest mistakes of the local models in the tests and 4 times faster than TranslateGemma 12B. Doesn't see the page."},
    "translategemma:12b": {"name": "TranslateGemma 12B", "size": "8.1 GB", "memory_gb": 16,
                           "about": "Any language (55). Sees the page. The best local model for every pair but Japanese to English (where PLaMo 8B made fewer mistakes). About 40 s a page."},
    "ministral-3:8b": {"name": "Ministral 3 8B", "size": "6.0 GB", "memory_gb": 16,
                       "about": "Any language. Sees the page. More mistakes than TranslateGemma 12B (it broke names and meanings more often)."},
    PLAMO_31B: {"name": "PLaMo 3 Translate 31B", "size": "19.5 GB", "memory_gb": 32, "line_by_line": True, "only": ("japanese", "english"),
                "about": "Japanese to English only. The biggest PLaMo, not tested yet. Doesn't see the page."},
    "translategemma:27b": {"name": "TranslateGemma 27B", "size": "17 GB", "memory_gb": 32,
                           "about": "Any language (55). Sees the page. The biggest TranslateGemma, not tested yet."},
    "ministral-3:14b": {"name": "Ministral 3 14B", "size": "9.1 GB", "memory_gb": 32,
                        "about": "Any language. Sees the page. Best local score on a Japanese translation benchmark; as good as Ministral 8B in our test, but slower."},
}
# Free disk space left over after downloading an Ollama model, so the computer isn't left with a full disk (the same margin as for the reading models).
DISK_MARGIN_GB = 2
# The language codes TranslateGemma's prompt uses.
LANGUAGE_CODES = {"japanese": "ja", "english": "en", "spanish": "es"}
OLLAMA_URL = "http://localhost:11434"
JAPANESE_LETTERS = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
API_KEY_NAMES = {"gemini": "GEMINI_API_KEY", "chatgpt": "OPENAI_API_KEY", "claude": "ANTHROPIC_API_KEY"}
# Gemini and ChatGPT both use the "openai" library, with a different address.
# How many times a request is tried again when the service is busy (e.g. Gemini's "high demand" errors), with growing waits in between.
API_RETRIES = 5
OPENAI_BASE_URLS = {"gemini": "https://generativelanguage.googleapis.com/v1beta/openai/", "chatgpt": None}

# Hayai OCR reads Japanese better than manga-ocr (spec 01, step 3). Pinned, because it runs its own model code.
HAYAI_MODEL = "JustANormalTinkerer/hayai-ocr-v2.7-supernova"
HAYAI_REVISION = "90fc61482c33858ee9ea227cd797f6fdff33345c"
# LaMa tuned on anime and manga (MIT license), which paints over text on artwork.
LAMA_MODEL = "dreMaz/AnimeMangaInpainting"
LAMA_FILE = "lama_large_512px.ckpt"
LAMA_REVISION = "2953a4e935bf01ad1471f6cbfd26ab81abeeb92d"

TRANSLATION_FILE_NAME = "translation.json"
# Names and character voices, kept in the series folder so they stay the same from chapter to chapter.
GLOSSARY_FILE_NAME = "translation-glossary.json"
# The page sent to the LLM is shrunk to this size on its longest side (the models shrink big images anyway, and a bigger one costs more).
SENT_PAGE_SIZE = 1600
# Seconds to wait before asking again when a translator says "too many requests". A per-minute limit (e.g. Gemini's free tier, about 5 a minute) clears within these; still refused after them, it's the daily limit.
RATE_LIMIT_WAITS = (20, 40, 60)
# A comfortable lettering size as a share of the page's height, used to tell the translator how much fits in each box.
READABLE_FONT_SHARE = 0.012
# The lettering shrinks as far as this (in pixels) rather than ever running past its bubble.
SMALLEST_FONT_SIZE = 6
# Text not in a bubble whose letters are bigger than this share of the page's height is a sound effect or a title logo (see "is_big_text_on_art").
BIG_LETTER_SHARE = 0.04
# Long words are split at syllables in these languages (pyphen's dictionaries).
HYPHENATION_LANGUAGES = {"english": "en_US", "spanish": "es"}

# The glossary entries the LLM may add (see "get_translation_schema").
GLOSSARY_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {"name": {"type": "string"}, "translation": {"type": "string"}, "note": {"type": "string"}},
        "required": ["name", "translation", "note"],
        "additionalProperties": False,
    },
}


def get_translation_schema(line_count):
    """
    What the LLM must answer with: one text for every line number ("1", "2", ...), all required so none can be skipped, and new glossary entries.
    """
    numbers = [str(number) for number in range(1, line_count + 1)]
    return {
        "type": "object",
        "properties": {
            "lines": {
                "type": "object",
                "properties": {number: {"type": "string"} for number in numbers},
                "required": numbers,
                "additionalProperties": False,
            },
            "new_glossary": GLOSSARY_SCHEMA,
        },
        "required": ["lines", "new_glossary"],
        "additionalProperties": False,
    }


def get_system_prompt(source_language, target_language, keep_honorifics, has_image=True):
    source, target = SOURCE_LANGUAGES[source_language], TARGET_LANGUAGES[target_language]
    honorifics = (
        "Keep Japanese honorifics (-san, -chan, -kun, senpai, sensei) as scanlations do."
        if source_language == "japanese" and keep_honorifics
        else f"Use natural {target} forms of address instead of honorifics."
    )
    return f"""You translate {source} manga pages into {target}, like an official {target} manga release.
- Short, natural lines that fit a speech bubble. Free to reword, but never add or drop meaning.
- Keep each character's voice (rough, polite, childish, dialect -> a light {target} equivalent).
- {honorifics}
- {"Each text box on the page has a red number. " if has_image else ""}Return the translation of every numbered line in "lines".
- A sentence may continue into the next box. Translate it as one sentence and split it naturally between those numbers.
- The {source} text came from OCR and may have mistakes.{" Trust the image when they disagree." if has_image else " Guess the intended words."}
{"- Check the picture for who is speaking and their gender." + chr(10) if has_image else ""}- The brackets after a line's number say whether it's in a speech bubble and about how many letters fit in its box at a readable size. Stay within that: pick shorter words and drop filler, but keep the meaning.
- Always translate a line in a speech bubble (dialogue, thoughts, narration boxes), even a single word or a sigh.
- End every spoken or narrated line with punctuation (. ! ? or …), as English lettering does. Names, titles and labels don't need it.
- Return "" for a box that shouldn't be translated: a sound effect, a sign, the manga's title logo, the author's or artist's name, or a box with no real text. Always translate narration and caption boxes (even one word) and the chapter title.
- In "new_glossary", list only proper names (characters, places, groups) and special terms that aren't in the glossary yet, with their {target} spelling and a one-line note (for a character: gender and how they talk). Usually there are none."""


def get_page_request(lines, previous_page, glossary, letters_that_fit=None, in_bubble=None, reminder=None):
    """
    The text sent with each page: the glossary, the previous page (so the story carries on), and this page's numbered lines, each marked if it's in a speech bubble and with about how many letters fit in its box. A "reminder" goes at the end (e.g. lines left out the first time).
    """
    parts = []
    if glossary:
        parts.append("Glossary:\n" + "\n".join(f"- {entry['name']}: {entry['translation']} ({entry['note']})" for entry in glossary))
    if previous_page:
        parts.append(
            "Previous page:\n" + "\n".join(f"{line['source']} -> {line['text']}" for line in previous_page if line["text"])
        )
    notes = []
    for index in range(len(lines)):
        note = (["speech bubble"] if in_bubble and in_bubble[index] else []) + ([f"~{letters_that_fit[index]} letters"] if letters_that_fit else [])
        notes.append(f" ({', '.join(note)})" if note else "")
    parts.append("This page:\n" + "\n".join(f"{number}{note}: {text}" for number, (text, note) in enumerate(zip(lines, notes), start=1)))
    if reminder:
        parts.append(reminder)
    return "\n\n".join(parts)


def get_numbered_page_image(page, boxes):
    """
    A copy of the page, shrunk to "SENT_PAGE_SIZE", with each text box outlined and numbered in red (1, 2, ... in reading order).
    """
    scale = min(1, SENT_PAGE_SIZE / max(page.size))
    image = page.convert("RGB").resize((round(page.width * scale), round(page.height * scale)))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(os.path.join(FONTS_FOLDER, FONTS["Comic Neue Bold"]), 26)
    for number, box in enumerate(boxes, start=1):
        x0, y0, x1, y1 = [value * scale for value in box]
        draw.rectangle((x0, y0, x1, y1), outline="red", width=2)
        # Above the box, or inside it when the box is at the top of the page, so the number is never cut off.
        label_x, label_y = max(0, x0 - 4), y0 - 30 if y0 >= 30 else y0
        draw.rounded_rectangle((label_x, label_y, label_x + 34, label_y + 30), radius=6, fill="red")
        draw.text((label_x + 17, label_y + 15), str(number), font=font, fill="white", anchor="mm")
    return image


def get_image_base64(image):
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def ask_ollama(model, system_prompt, request_text, image, schema):
    import requests

    message = {"role": "user", "content": request_text}
    if image is not None:
        message["images"] = [get_image_base64(image)]
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}, message],
        "format": schema,
        "stream": False,
        "options": {"temperature": 0},
        # Thinking makes every page several times slower, and the best translations in the tests didn't use it.
        "think": False,
    }
    response = requests.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=600)
    if response.status_code == 400 and "think" in response.text:
        # A model without a thinking mode refuses "think" altogether.
        del body["think"]
        response = requests.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=600)
    if response.status_code == 501:
        raise RuntimeError(f'Ollama can\'t use "{model}" for translating ({response.text.strip()}). Pick another model.')
    response.raise_for_status()
    return response.json()["message"]["content"]


def ask_openai_compatible(engine, model, api_key, system_prompt, request_text, image, schema):
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=OPENAI_BASE_URLS[engine], max_retries=API_RETRIES)
    content = [{"type": "text", "text": request_text}]
    if image is not None:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{get_image_base64(image)}"}})
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": content}],
        response_format={"type": "json_schema", "json_schema": {"name": "translation", "schema": schema, "strict": True}},
    )
    message = response.choices[0].message
    if message.content is None:
        raise RuntimeError(f"{ENGINES[engine]} declined to translate this page{': ' + message.refusal if message.refusal else ''}.")
    return message.content


def ask_claude(model, api_key, system_prompt, request_text, image, schema):
    import anthropic

    content = [{"type": "text", "text": request_text}]
    if image is not None:
        content.insert(0, {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": get_image_base64(image)}})
    response = anthropic.Anthropic(api_key=api_key, max_retries=API_RETRIES).beta.messages.create(
        model=model,
        max_tokens=16000,
        system=system_prompt,
        messages=[{"role": "user", "content": content}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
        # If the model declines a page, the API tries another model instead of failing.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined to translate this page.")
    return next(block.text for block in response.content if block.type == "text")


def ask_llm(settings, system_prompt, request_text, image, schema):
    import anthropic
    import openai

    engine, model = settings["engine"], settings["model"]
    if engine == "ollama":
        return ask_ollama(model, system_prompt, request_text, image, schema)
    for wait in RATE_LIMIT_WAITS + (None,):
        try:
            if engine == "claude":
                return ask_claude(model, settings["api_key"], system_prompt, request_text, image, schema)
            return ask_openai_compatible(engine, model, settings["api_key"], system_prompt, request_text, image, schema)
        except (anthropic.RateLimitError, openai.RateLimitError):
            # E.g. Gemini's free tier allows only a few requests a minute, and a limited number a day. Its answer doesn't say which, so a per-minute limit is waited out.
            if wait is None:
                raise RuntimeError(f"{ENGINES[engine]} says you've reached your usage limit for {model} (free accounts have a daily limit). Translate again later (pages already done are kept), or pick another translator.")
            print(f"{ENGINES[engine]} says too many requests for now. Trying again in {wait} seconds.")
            time.sleep(wait)


def remove_japanese(text):
    """
    A translation without any Japanese copied back into it, which the bundled fonts can't draw ("▯"). Empty when no letters are left (e.g. a lone ド, or "ド.").
    """
    text = re.sub(r"\s+", " ", JAPANESE_LETTERS.sub("", text)).strip()
    return text if any(character.isalpha() for character in text) else ""


def ask_ollama_line(model, source_language, target_language, line, earlier_lines):
    """
    One line translated by a pure translation model, in the prompt format it was trained on. "earlier_lines" are (original, translation) pairs from just before it, which PLaMo takes as the conversation so far (TranslateGemma's format has no place for them).
    """
    import requests

    if model in (PLAMO_2B, PLAMO_8B, PLAMO_31B):
        # PLaMo's own format (PFML3), sent as is ("raw"): earlier lines first, then this one, then where its translation goes.
        tag, output = "<|plamo:tag|>", f"<|plamo:tag|>output<|plamo:key|>lang<|plamo:val|>{LANGUAGE_CODES[target_language]}<|plamo:msg|>"
        history = "".join(f"{tag}input<|plamo:msg|>{source}{output}{text}" for source, text in earlier_lines)
        body = {"model": model, "prompt": f"{tag}dataset<|plamo:msg|>translation{history}{tag}input<|plamo:msg|>{line}{output}", "raw": True,
                "stream": False, "options": {"temperature": 0, "num_predict": 200, "stop": ["<|plamo:tag|>", "<|plamo:bos|>"]}}
        response = requests.post(f"{OLLAMA_URL}/api/generate", json=body, timeout=600)
        response.raise_for_status()
        return response.json()["response"].strip()
    # TranslateGemma's documented prompt (ollama.com/library/translategemma), with the two blank lines before the text.
    source, target = SOURCE_LANGUAGES[source_language], TARGET_LANGUAGES[target_language]
    prompt = (
        f"You are a professional {source} ({LANGUAGE_CODES[source_language]}) to {target} ({LANGUAGE_CODES[target_language]}) translator. "
        f"Your goal is to accurately convey the meaning and nuances of the original {source} text while adhering to {target} grammar, vocabulary, and cultural sensitivities.\n"
        f"Produce only the {target} translation, without any additional explanations or commentary. Please translate the following {source} text into {target}:\n\n\n{line}"
    )
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False, "options": {"temperature": 0, "num_predict": 200}}
    response = requests.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=600)
    response.raise_for_status()
    return response.json()["message"]["content"].strip()


def translate_line_by_line(settings, source_lines, previous_page):
    """
    For the pure translation models (PLaMo, TranslateGemma 4B): each line asked for on its own, with up to 10 lines before it (from this page and the one before) as context for PLaMo. A line with no letters at all ("…", "?") isn't sent: these models answer it with junk.
    """
    earlier_lines = [(line["source"], line["text"]) for line in previous_page or [] if line["text"]]
    texts = []
    for line in source_lines:
        if not any(character.isalpha() for character in line):
            texts.append("")
            continue
        text = ask_ollama_line(settings["model"], settings["source_language"], settings["target_language"], line, earlier_lines[-10:])
        texts.append(text)
        if text:
            earlier_lines.append((line, text))
    return [remove_japanese(text) for text in texts], []


def translate_page(settings, page, boxes, source_lines, previous_page, glossary, letters_that_fit=None, in_bubble=None, reminder=None):
    """
    The translation of each line on one page (in the same order), and any new glossary entries.
    """
    if OLLAMA_MODELS.get(settings["model"], {}).get("line_by_line"):
        return translate_line_by_line(settings, source_lines, previous_page)
    image = get_numbered_page_image(page, boxes) if settings["send_page_image"] else None
    answer_text = ask_llm(
        settings,
        get_system_prompt(settings["source_language"], settings["target_language"], settings["keep_honorifics"], image is not None),
        get_page_request(source_lines, previous_page, glossary, letters_that_fit, in_bubble, reminder),
        image,
        get_translation_schema(len(source_lines)),
    )
    try:
        answer = json.loads(answer_text)
    except ValueError:
        raise RuntimeError(f"{settings['model']}'s answer for this page was cut off or wasn't valid. Try again, or try another model.")
    texts = [str(answer["lines"].get(str(number), "")).strip() for number in range(1, len(source_lines) + 1)]
    return [remove_japanese(text) for text in texts], answer.get("new_glossary", [])


def check_engine_ready(settings):
    """
    Stop with a clear message before any work is done if the picked engine can't be used.
    """
    engine, model = settings["engine"], settings["model"]
    if engine == "ollama":
        import requests

        if model.endswith(":cloud") or "-cloud" in model:
            raise RuntimeError(f'"{model}" runs on Ollama\'s servers, not on this computer. Pick a local model.')
        try:
            installed = [entry["name"] for entry in requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).json()["models"]]
        except Exception:
            raise RuntimeError("Ollama isn't running. Install it from https://ollama.com and open it, then try again.")
        if model not in installed and f"{model}:latest" not in installed:
            size = f" ({OLLAMA_MODELS[model]['size']})" if model in OLLAMA_MODELS else ""
            raise RuntimeError(f'The Ollama model "{model}" isn\'t downloaded yet{size}. Download it under "Manage Ollama models" in the Translate settings.')
        if not is_pair_supported(model, settings["source_language"], settings["target_language"]):
            raise RuntimeError(f"{OLLAMA_MODELS[model]['name']} only translates Japanese to English. Pick another model for {SOURCE_LANGUAGES[settings['source_language']]} to {TARGET_LANGUAGES[settings['target_language']]}.")
    elif not settings["api_key"]:
        raise RuntimeError(f"{ENGINES[engine]} needs an API key. Add it in the Translate settings, or as {API_KEY_NAMES[engine]} in a .env file.")


def is_pair_supported(model, source_language, target_language):
    """
    Whether a model can translate from "source_language" to "target_language" (PLaMo only knows Japanese to English).
    """
    only = OLLAMA_MODELS.get(model, {}).get("only")
    return only is None or only == (source_language, target_language)


def get_default_model(engine, source_language="japanese", target_language="english"):
    """
    The model picked until the user picks one. For Ollama: the best suggested model that knows the languages and can run here: it fits this computer's memory, and it's downloaded already or there's room to download it (PLaMo for Japanese to English, else TranslateGemma 12B, or their 8 GB picks). The 32 GB models aren't tested yet, so bigger computers get the 16 GB pick. Unknown memory counts as 16 GB.
    """
    if engine != "ollama":
        return DEFAULT_MODELS[engine]
    ram_gb, installed, free_gb = get_ram_gb(), list_installed_ollama_models() or {}, get_free_disk_gb()
    candidates = [model for memory_gb in (16, 8) for model, info in OLLAMA_MODELS.items() if info["memory_gb"] == memory_gb and is_pair_supported(model, source_language, target_language)]

    def can_run(model):
        return not is_too_big(get_model_size_gb(model), ram_gb) and (model in installed or get_room_for_model_error(model, free_gb) is None)

    # The smallest one if none can.
    return next((model for model in candidates if can_run(model)), candidates[-1])


def get_model_size_gb(model):
    return float(OLLAMA_MODELS[model]["size"].split()[0])


def get_free_disk_gb():
    """
    Free space on the disk Ollama keeps its models on by default (in the home folder: ~/.ollama/models, or C:\\Users\\<name>\\.ollama\\models on Windows; Ollama's OLLAMA_MODELS setting can move them).
    """
    return shutil.disk_usage(os.path.expanduser("~")).free / 1e9


def get_room_for_model_error(model, free_gb):
    """
    Why a model can't be downloaded for lack of disk space, or None if it fits. Ollama needs about the download's size (no unpacking, no second copy), plus "DISK_MARGIN_GB" so the computer isn't left with a full disk.
    """
    needed = get_model_size_gb(model) + DISK_MARGIN_GB
    if free_gb < needed:
        return f"Not enough free disk space for {OLLAMA_MODELS[model]['name']}: it needs {needed:.1f} GB ({OLLAMA_MODELS[model]['size']} plus {DISK_MARGIN_GB} GB to spare), and there are {free_gb:.1f} GB free."
    return None


def download_ollama_model(model, report=lambda done_gb, total_gb: None, is_cancelled=lambda: False):
    """
    Download a model through Ollama (like "ollama pull"), calling "report" with how many GB are done as it goes. Stops (and Ollama keeps what's done, so a later download carries on) when "is_cancelled" says so. Raises an error with a plain message if it fails.
    """
    import requests

    error = get_room_for_model_error(model, get_free_disk_gb()) if model in OLLAMA_MODELS else None
    if error:
        raise RuntimeError(error)
    # The model comes in parts (the model itself, then small files), each with its own size.
    totals, done = {}, {}
    with requests.post(f"{OLLAMA_URL}/api/pull", json={"model": model, "stream": True}, stream=True, timeout=(10, 900)) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if is_cancelled():
                return False
            if not line:
                continue
            update = json.loads(line)
            if "error" in update:
                raise RuntimeError(f"Ollama couldn't download {model}: {update['error']}")
            if update.get("total"):
                totals[update["digest"]] = update["total"]
                done[update["digest"]] = update.get("completed", 0)
                report(sum(done.values()) / 1e9, sum(totals.values()) / 1e9)
    return True


def delete_ollama_model(model):
    """
    Remove a downloaded model from this computer (like "ollama rm").
    """
    import requests

    response = requests.delete(f"{OLLAMA_URL}/api/delete", json={"model": model}, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(f"Ollama couldn't remove {model}: {response.text.strip()}")


def list_installed_ollama_models():
    """
    The models Ollama has downloaded, as {name: size in GB}, or None if Ollama isn't running.
    """
    import requests

    try:
        return {model["name"]: model["size"] / 1e9 for model in requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).json()["models"]}
    except (requests.RequestException, ValueError, KeyError):
        return None


def get_api_key(engine, saved_key):
    """
    The key typed in the settings, or else the one in the ".env" file.
    """
    if engine not in API_KEY_NAMES:
        return ""
    utils_load_dotenv()
    return saved_key or os.getenv(API_KEY_NAMES[engine]) or ""


def list_models(engine, api_key=""):
    """
    The models a translator offers for translating, to pick from in the settings: for Ollama the ones installed on this computer, for the others the ones the API key can use (text models only, newest first). Empty if they can't be listed (e.g. no key yet, a wrong key, offline, or Ollama not running).
    """
    import anthropic
    import openai
    import requests

    try:
        if engine == "ollama":
            return [model["name"] for model in requests.get(f"{OLLAMA_URL}/api/tags", timeout=5).json()["models"]]
        if not api_key:
            return []
        if engine == "gemini":
            response = requests.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": api_key, "pageSize": 1000}, timeout=10)
            response.raise_for_status()
            names = [model["name"].split("/")[-1] for model in response.json()["models"] if "generateContent" in model.get("supportedGenerationMethods", [])]
            return sorted((name for name in names if name.startswith("gemini") and not any(word in name for word in ("tts", "image", "embedding", "live", "audio"))), reverse=True)
        if engine == "chatgpt":
            ids = [model.id for model in openai.OpenAI(api_key=api_key, max_retries=0, timeout=10).models.list()]
            return sorted((id for id in ids if id.startswith("gpt-") and not any(word in id for word in ("audio", "realtime", "transcribe", "tts", "image", "search"))), reverse=True)
        if engine == "claude":
            return [model.id for model in anthropic.Anthropic(api_key=api_key, max_retries=0, timeout=10).models.list(limit=100)]
    except (requests.RequestException, openai.OpenAIError, anthropic.AnthropicError, KeyError, ValueError):
        pass
    return []


def reading_models_are_downloaded():
    """
    Whether Hayai OCR and LaMa are already downloaded (so no disk space is needed for them).
    """
    from huggingface_hub import try_to_load_from_cache

    return all(
        isinstance(try_to_load_from_cache(model, file, revision=revision), str)
        for model, file, revision in ((HAYAI_MODEL, "model.safetensors", HAYAI_REVISION), (LAMA_MODEL, LAMA_FILE, LAMA_REVISION))
    )


def get_ram_gb():
    """
    The computer's memory in GB (as the computer counts it, 1024³ bytes), or None if it can't be read.
    """
    try:
        if os.name == "nt":
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + [(name, ctypes.c_ulonglong) for name in (
                    "ullTotalPhys", "ullAvailPhys", "ullTotalPageFile", "ullAvailPageFile", "ullTotalVirtual", "ullAvailVirtual", "ullAvailExtendedVirtual")]

            status = MemoryStatus(dwLength=ctypes.sizeof(MemoryStatus))
            return status.ullTotalPhys / 1024**3 if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)) else None
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024**3
    except (AttributeError, ValueError, OSError):
        return None


def is_too_big(model_size_gb, ram_gb):
    """
    Whether an Ollama model clearly won't fit in this computer's memory: only about 70% of it can go to the model, and a model needs about 2 GB more than its download while it runs. Unknown memory counts as fitting (the check after loading catches it).
    """
    return ram_gb is not None and model_size_gb + 2 > ram_gb * 0.7


def get_ollama_gpu_share(model):
    """
    How much of a loaded Ollama model is on the graphics card (0 to 1), or None if Ollama doesn't say. The rest runs on the processor, several times slower (e.g. a graphics card with too little memory of its own).
    """
    import requests

    try:
        for loaded in requests.get(f"{OLLAMA_URL}/api/ps", timeout=5).json().get("models", []):
            if model in (loaded.get("name"), loaded.get("model")) or f"{model}:latest" == loaded.get("name"):
                return loaded["size_vram"] / loaded["size"]
    except (requests.RequestException, ValueError, KeyError, ZeroDivisionError):
        pass
    return None


_hayai = None


def get_hayai():
    """
    Hayai OCR and its processor, loaded the first time. Its tokenizer file is in a newer format than this transformers reads, so the tokenizer is built from "tokenizer.json" directly.
    """
    global _hayai
    if _hayai is None:
        from huggingface_hub import hf_hub_download
        from transformers import AutoModel, PreTrainedTokenizerFast
        from transformers.dynamic_module_utils import get_class_from_dynamic_module
        from magi import get_device

        model = AutoModel.from_pretrained(HAYAI_MODEL, revision=HAYAI_REVISION, trust_remote_code=True).to(get_device()).eval()
        processor_class = get_class_from_dynamic_module("processing_hayai.HayaiProcessor", HAYAI_MODEL, revision=HAYAI_REVISION)
        image_processor_class = get_class_from_dynamic_module("processing_hayai.HayaiImageProcessor", HAYAI_MODEL, revision=HAYAI_REVISION)
        tokenizer = PreTrainedTokenizerFast(
            tokenizer_file=hf_hub_download(HAYAI_MODEL, "tokenizer.json", revision=HAYAI_REVISION),
            bos_token="<bos>", eos_token="<eos>", pad_token="<pad>", unk_token="<unk>",
        )
        processor = processor_class(image_processor=image_processor_class.from_pretrained(HAYAI_MODEL, revision=HAYAI_REVISION), tokenizer=tokenizer)
        _hayai = (model, processor)
    return _hayai


def clean_japanese(text):
    # Hayai's own suggested clean-up: full-width letters to normal ones, and no spaces between Japanese characters. Spaces between English words (a sign saying "YUICHI'S ROOM") stay.
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"(?<=[^\x00-\x7f])\s+|\s+(?=[^\x00-\x7f])", "", text).strip()


def read_japanese(pages, boxes_on_each_page):
    """
    The Japanese in each box, read by Hayai OCR from a crop of the box.
    """
    model, processor = get_hayai()
    crops = [
        page.crop((max(0, x0 - 4), max(0, y0 - 4), min(page.width, x1 + 4), min(page.height, y1 + 4)))
        for page, boxes in zip(pages, boxes_on_each_page)
        for x0, y0, x1, y1 in boxes
    ]
    texts = iter(model.ocr(crops, processor, max_patches="auto", batch_size=16, escalate=False, max_new_tokens=128) if crops else [])
    return [[clean_japanese(next(texts)) for _ in boxes] for boxes in boxes_on_each_page]


def read_latin(magi, pages, boxes_on_each_page):
    """
    The English or Spanish in each box, read by Magi's own reader.
    """
    import torch

    # Only pages that have text boxes are read.
    pages_with_text = [index for index, boxes in enumerate(boxes_on_each_page) if boxes]

    def read():
        with torch.no_grad():
            return magi.full_model.predict_ocr(
                [numpy.array(pages[index]) for index in pages_with_text], [boxes_on_each_page[index] for index in pages_with_text]
            )

    texts = dict(zip(pages_with_text, magi.run_with_cpu_fallback("_full_model", read) if pages_with_text else []))
    return [texts.get(index, []) for index in range(len(pages))]


_lama = None


def get_lama():
    global _lama
    if _lama is None:
        import spandrel
        import torch
        from huggingface_hub import hf_hub_download

        weights = torch.load(hf_hub_download(LAMA_MODEL, LAMA_FILE, revision=LAMA_REVISION), map_location="cpu", weights_only=True)
        # This file leaves out the "model." that spandrel looks for.
        state_dict = {f"model.{name}": value for name, value in weights["gen_state_dict"].items()}
        _lama = spandrel.ModelLoader().load_from_state_dict(state_dict).model.eval()
    return _lama


def get_ring(array, box, ring_width=6):
    """
    The values in a band "ring_width" pixels wide all around the box (what's just outside it).
    """
    x0, y0, x1, y1 = box
    height, width = array.shape[:2]
    outer = array[max(0, y0 - ring_width) : min(height, y1 + ring_width), max(0, x0 - ring_width) : min(width, x1 + ring_width)]
    inner_mask = numpy.zeros(outer.shape[:2], bool)
    inner_mask[min(ring_width, y0) : min(ring_width, y0) + (y1 - y0), min(ring_width, x0) : min(ring_width, x0) + (x1 - x0)] = True
    return outer[~inner_mask]


def get_flat_color(page_array, box, tolerance=30):
    """
    The color around a text box if it's one flat color (a speech bubble or a caption box), else None (the text is on artwork).
    """
    ring = get_ring(page_array, box).astype(int)
    if len(ring) == 0:
        return None
    color = numpy.median(ring, axis=0)
    close = numpy.abs(ring - color).max(axis=1) <= tolerance
    return tuple(int(value) for value in color) if close.mean() >= 0.9 else None


def paint_over_with_lama(page, box):
    """
    Paint over the box with LaMa, using a crop around it so it sees the artwork nearby.
    """
    import torch

    x0, y0, x1, y1 = box
    margin = max(32, (x1 - x0) // 2, (y1 - y0) // 2)
    crop_box = (max(0, x0 - margin), max(0, y0 - margin), min(page.width, x1 + margin), min(page.height, y1 + margin))
    crop = page.crop(crop_box)
    # LaMa was trained at 512 px; bigger crops are shrunk, then the result is scaled back.
    scale = min(1, 512 / max(crop.size))
    size = (max(8, round(crop.width * scale) // 8 * 8), max(8, round(crop.height * scale) // 8 * 8))
    image = torch.from_numpy(numpy.asarray(crop.resize(size), dtype=numpy.float32) / 255).permute(2, 0, 1)[None]
    mask = torch.zeros(1, 1, size[1], size[0])
    mask_x0, mask_y0 = (x0 - crop_box[0] - 3) * size[0] / crop.width, (y0 - crop_box[1] - 3) * size[1] / crop.height
    mask_x1, mask_y1 = (x1 - crop_box[0] + 3) * size[0] / crop.width, (y1 - crop_box[1] + 3) * size[1] / crop.height
    mask[..., max(0, int(mask_y0)) : int(mask_y1) + 1, max(0, int(mask_x0)) : int(mask_x1) + 1] = 1
    with torch.no_grad():
        result = get_lama()(image, mask)[0].permute(1, 2, 0).clamp(0, 1).numpy()
    painted = Image.fromarray((result * 255).astype(numpy.uint8)).resize(crop.size)
    # Only the box itself is replaced, so the artwork around it stays sharp.
    left, top, right, bottom = max(0, x0 - 3), max(0, y0 - 3), min(page.width, x1 + 3), min(page.height, y1 + 3)
    page.paste(painted.crop((left - crop_box[0], top - crop_box[1], right - crop_box[0], bottom - crop_box[1])), (left, top))


# A pixel at least this bright counts as the paper of a speech bubble.
BUBBLE_BRIGHTNESS = 200
# A light area bigger than this share of the page isn't a bubble (it's the page's background).
MAX_BUBBLE_SHARE = 0.25


def get_light_areas(page):
    """
    Every light area of the page, numbered (0 where it's dark), and each one's size. A speech bubble is one light area, with its text as holes in it.
    """
    from scipy import ndimage

    labels, count = ndimage.label(numpy.asarray(page.convert("L")) >= BUBBLE_BRIGHTNESS)
    return labels, numpy.bincount(labels.ravel(), minlength=count + 1)


def get_bubble(light_areas, box):
    """
    The number of the speech bubble a text box is in (the light area all around it), or None if it's on artwork or on the page's background.
    """
    labels, sizes = light_areas
    ring = get_ring(labels, box)
    if len(ring) == 0:
        return None
    bubble = numpy.bincount(ring).argmax()
    is_around_box = (ring == bubble).mean() >= 0.6
    if bubble == 0 or not is_around_box or sizes[bubble] > MAX_BUBBLE_SHARE * labels.size:
        return None
    return int(bubble)


def get_overlap_share(box, other_box):
    """
    How much of the smaller box is covered by the other one (0 to 1).
    """
    width = min(box[2], other_box[2]) - max(box[0], other_box[0])
    height = min(box[3], other_box[3]) - max(box[1], other_box[1])
    smaller_area = min((box[2] - box[0]) * (box[3] - box[1]), (other_box[2] - other_box[0]) * (other_box[3] - other_box[1]))
    return max(0, width) * max(0, height) / max(1, smaller_area)


def remove_repeated_boxes(boxes, bubbles, get_share_inside=lambda bubble, box: 1, get_size=lambda bubble: 0):
    """
    Below Magi's own threshold, the same text is sometimes found twice (one box mostly inside another). They become one box around both, returned with each box's bubble. Text on the artwork whose boxes overlap by a quarter becomes one line too (e.g. two captions Magi's boxes run into). When a box on the art overlaps a box in a light area:
    - a speech bubble at least half inside the box on the art (a big sound effect drawn around it) stays its own line;
    - a light area not much bigger than the box on the art is the bubble that text belongs to, so they become one line in that bubble;
    - a bigger light area (e.g. a white panel background the text is written on) isn't a bubble: they become one line on the art, and so does any other text in that light area.
    "get_share_inside(bubble, box)" says how much of a light area lies inside a box, "get_size(bubble)" how many pixels it has.
    """
    kept = []
    not_bubbles = set()
    for box, bubble in zip(boxes, bubbles):
        if bubble in not_bubbles:
            bubble = None
        repeat, joined_bubble = None, bubble
        for index, (kept_box, kept_bubble) in enumerate(kept):
            share = get_overlap_share(box, kept_box)
            if kept_bubble == bubble and share >= (0.5 if bubble is not None else 0.25):
                repeat = index
            elif None in (bubble, kept_bubble) and share >= 0.25:
                light_area, box_on_art = (bubble, kept_box) if kept_bubble is None else (kept_bubble, box)
                if get_share_inside(light_area, box_on_art) < 0.5:
                    repeat = index
                    if get_size(light_area) <= 2.5 * (box_on_art[2] - box_on_art[0]) * (box_on_art[3] - box_on_art[1]):
                        joined_bubble = light_area
                    else:
                        joined_bubble = None
                        not_bubbles.add(light_area)
            if repeat is not None:
                break
        if repeat is None:
            kept.append((box, bubble))
        else:
            # The box around both, so no text is cut off.
            kept_box = kept[repeat][0]
            kept[repeat] = ((min(box[0], kept_box[0]), min(box[1], kept_box[1]), max(box[2], kept_box[2]), max(box[3], kept_box[3])), joined_bubble)
    return [box for box, _ in kept], [bubble for _, bubble in kept]


def are_next_to_each_other(box, other_box, gap=20):
    return box[0] - gap <= other_box[2] and other_box[0] - gap <= box[2] and box[1] - gap <= other_box[3] and other_box[1] - gap <= box[3]


def group_by_bubble(boxes, bubbles):
    """
    Boxes right next to each other in the same speech bubble become one line (Magi sometimes splits a bubble's text in two), as (box around them all, bubble). Boxes further apart in one light area (e.g. two bubbles that touch) stay separate lines.
    """
    groups = []
    for box, bubble in zip(boxes, bubbles):
        group = next((group for group in groups if bubble is not None and group[1] == bubble and are_next_to_each_other(group[0], box)), None)
        if group:
            old_box = group[0]
            group[0] = (min(old_box[0], box[0]), min(old_box[1], box[1]), max(old_box[2], box[2]), max(old_box[3], box[3]))
        else:
            groups.append([box, bubble])
    return [tuple(group) for group in groups]


def get_distance_to_box(rows, columns, box):
    x0, y0, x1, y1 = box
    return numpy.hypot(numpy.maximum(0, numpy.maximum(x0 - columns, columns - x1)), numpy.maximum(0, numpy.maximum(y0 - rows, rows - y1)))


def get_inside_rectangles(mask, text_box):
    """
    The biggest rectangle inside "mask" of each of a few shapes from tall to wide, as (left, top, right, bottom) in the mask's own coordinates. They're centered on the point deepest inside the mask (so a bubble's tail doesn't pull them aside), and reach at most half the text box's longer side past it ("text_box", in the mask's coordinates). If that point isn't in the text's own box (text written on a big white background, or a bubble with no outline on one side running into a white face), they're centered in the text's box instead, so the English stays where the Japanese was. The lettering picks the one its text fits biggest in. They may cross a few stray pixels (e.g. where a letter touched the outline).
    """
    from scipy import ndimage

    height, width = mask.shape
    text_left, text_top = max(0, min(width - 1, text_box[0])), max(0, min(height - 1, text_box[1]))
    text_right, text_bottom = max(text_left + 1, min(width, text_box[2])), max(text_top + 1, min(height, text_box[3]))
    reach = max(text_right - text_left, text_bottom - text_top) // 2
    limit_left, limit_top, limit_right, limit_bottom = text_left - reach, text_top - reach, text_right + reach, text_bottom + reach
    # Padded so the mask's own edge counts as outside.
    depth = ndimage.distance_transform_edt(numpy.pad(mask, 1))[1:-1, 1:-1]

    def get_center(depth_part, offset_x, offset_y):
        # The middle of the deepest part, so a caption's rectangles are centered along its length too.
        rows, columns = numpy.nonzero(depth_part >= depth_part.max() * 0.9)
        center_y, center_x = offset_y + int(rows.mean()), offset_x + int(columns.mean())
        if not mask[center_y, center_x]:
            center_y, center_x = (int(value) for value in numpy.unravel_index(depth_part.argmax(), depth_part.shape))
            center_y, center_x = center_y + offset_y, center_x + offset_x
        return center_x, center_y

    center_x, center_y = get_center(depth, 0, 0)
    margin = reach // 5
    if not (text_left - margin <= center_x < text_right + margin and text_top - margin <= center_y < text_bottom + margin):
        center_x, center_y = get_center(depth[text_top:text_bottom, text_left:text_right], text_left, text_top)
    rectangles = []
    for shape in (0.5, 0.7, 1, 1.4, 2, 2.8):
        rectangle = (center_x, center_y, center_x, center_y)
        for half_height in range(1, height):
            half_width = int(half_height * shape)
            left, top, right, bottom = center_x - half_width, center_y - half_height, center_x + half_width, center_y + half_height
            is_outside = left < max(0, limit_left) or top < max(0, limit_top) or right >= min(width, limit_right) or bottom >= min(height, limit_bottom)
            if is_outside or mask[top : bottom + 1, left : right + 1].mean() < 0.98:
                break
            rectangle = (left, top, right, bottom)
        rectangles.append(rectangle)
    return rectangles


def get_bubble_part(light_areas, bubble, box, boxes_in_bubble):
    """
    The inside of the speech bubble that belongs to one line, as (top, left, paper, part) where "paper" is the light pixels and "part" is that line's part of the inside (its text included), both cut to the bubble's box. When several lines share one light area (e.g. two bubbles that touch), each gets the part closest to its own box.
    """
    from scipy import ndimage

    labels = light_areas[0]
    rows, columns = numpy.nonzero(labels == bubble)
    top, bottom, left, right = rows.min(), rows.max() + 1, columns.min(), columns.max() + 1
    sizes = light_areas[1]
    crop = labels[top:bottom, left:right]
    own = crop == bubble
    # Another light area inside this one big enough to be a bubble (e.g. a small speech bubble drawn on a white panel background), with everything in it, belongs to that one: it's never erased or lettered over here. Its outline is a ring, which "get_text_in_part" skips. The tiny light areas inside letters (口, の) don't count.
    big_enough = [number for number in numpy.unique(crop) if number not in (0, bubble) and sizes[number] > max(1000, 0.02 * sizes[bubble])]
    others = numpy.isin(crop, big_enough)
    part = ndimage.binary_fill_holes(own) & ~ndimage.binary_fill_holes(others)
    # Every light pixel counts as paper, so only dark pixels can be letters.
    paper = labels[top:bottom, left:right] != 0
    if len(boxes_in_bubble) > 1:
        grid_rows, grid_columns = numpy.mgrid[top:bottom, left:right]
        distances = [get_distance_to_box(grid_rows, grid_columns, other_box) for other_box in boxes_in_bubble]
        part &= numpy.argmin(distances, axis=0) == boxes_in_bubble.index(box)
    return top, left, paper, part


def get_text_in_part(paper, part, box, top, left):
    """
    Which dark pixels in a line's part of a bubble are its text: letter-sized shapes, chained to Magi's box with gaps of at most half a letter (so a whole caption is found even when Magi's box covers only its end). A drawing in a light area (e.g. a character on a plain white panel) is one big shape, so it's left alone.
    """
    from scipy import ndimage

    x0, y0, x1, y1 = box
    shapes, _ = ndimage.label(part & ~paper)
    objects = ndimage.find_objects(shapes)
    # Magi's box is one letter wide for a single column of Japanese, but several for a block of columns, so the shapes inside it cap the letter size (else the chaining below jumps across a whole panel).
    sizes_in_box = [
        max(rows.stop - rows.start, columns.stop - columns.start)
        for rows, columns in objects
        if rows.start >= y0 - top and rows.stop <= y1 - top and columns.start >= x0 - left and columns.stop <= x1 - left
    ]
    letter_size = max(8, min(x1 - x0, y1 - y0))
    if sizes_in_box:
        letter_size = min(letter_size, max(8, int(1.5 * numpy.median(sizes_in_box))))
    letters = numpy.zeros(paper.shape, bool)
    for number, (rows, columns) in enumerate(objects, start=1):
        if rows.stop - rows.start <= 3 * letter_size and columns.stop - columns.start <= 3 * letter_size:
            shape = shapes[rows, columns] == number
            # A ring around a much bigger space is another bubble's outline (or a frame), not a letter.
            if ndimage.binary_fill_holes(shape).sum() <= 5 * shape.sum():
                letters[rows, columns] |= shape
    clusters, _ = ndimage.label(ndimage.binary_dilation(letters, iterations=max(2, letter_size // 2)))
    in_box = clusters[max(0, y0 - top) : max(0, y1 - top), max(0, x0 - left) : max(0, x1 - left)]
    return letters & numpy.isin(clusters, numpy.unique(in_box[in_box > 0]))


def get_text_box_in_bubble(light_areas, bubble, box, boxes_in_bubble):
    """
    The box around all the text in a line's part of its bubble. Magi's box sometimes covers only part of it (e.g. the last two characters of a caption), so the whole text is read and erased.
    """
    top, left, paper, part = get_bubble_part(light_areas, bubble, box, boxes_in_bubble)
    rows, columns = numpy.nonzero(get_text_in_part(paper, part, box, top, left))
    if len(rows) == 0:
        return box
    return (
        int(min(box[0], left + columns.min())),
        int(min(box[1], top + rows.min())),
        int(max(box[2], left + columns.max() + 1)),
        int(max(box[3], top + rows.max() + 1)),
    )


def erase_in_bubble(page, light_areas, bubble, box, boxes_in_bubble):
    """
    Erase the text of one line in a speech bubble (changed in place), including furigana and any text Magi's box cut off, but not the outline. Returns the bubble's color and the areas the text may be lettered in.
    """
    from scipy import ndimage

    top, left, paper, part = get_bubble_part(light_areas, bubble, box, boxes_in_bubble)
    bottom, right = top + paper.shape[0], left + paper.shape[1]
    text = get_text_in_part(paper, part, box, top, left)
    # Text touching the outline isn't a hole in the paper, so Magi's box is cleared too (but only inside the bubble).
    x0, y0, x1, y1 = box
    text[max(0, y0 - top - 1) : max(0, y1 - top + 1), max(0, x0 - left - 1) : max(0, x1 - left + 1)] = True
    # Two pixels more, so the soft grey edges of the letters go too.
    text = ndimage.binary_dilation(text, iterations=2) & part
    pixels = numpy.asarray(page).copy()
    region = pixels[top:bottom, left:right]
    color = tuple(int(value) for value in numpy.median(region[paper], axis=0))
    region[text] = color
    page.paste(Image.fromarray(pixels))
    rows, columns = numpy.nonzero(text)
    text_box = (int(columns.min()), int(rows.min()), int(columns.max()) + 1, int(rows.max()) + 1)
    return color, [(left + inside_left, top + inside_top, left + inside_right, top + inside_bottom) for inside_left, inside_top, inside_right, inside_bottom in get_inside_rectangles(part, text_box)]


def grow_over_flat_color(page_array, box, color, tolerance=40, margin=6):
    """
    The box made wider (up to its own width on each side) and a little taller, but only over the flat color around it, so it stops at e.g. a caption box's border. Japanese boxes are tall and narrow, so the translation needs the room.
    """
    x0, y0, x1, y1 = box
    height, width = page_array.shape[:2]
    is_flat = numpy.abs(page_array.astype(int) - numpy.array(color)).max(axis=2) <= tolerance

    def grow(strips):
        # How many strips (columns or rows, nearest first) are flat all the way along, minus a margin from whatever comes next.
        steps = next((index for index, strip in enumerate(strips) if not strip.all()), len(strips))
        return max(0, steps - margin) if steps < len(strips) else steps

    reach_x, reach_y = x1 - x0, (y1 - y0) // 4
    left = grow([is_flat[y0:y1, x] for x in range(x0 - 1, max(-1, x0 - 1 - reach_x), -1)])
    right = grow([is_flat[y0:y1, x] for x in range(x1, min(width, x1 + reach_x))])
    top = grow([is_flat[y, x0 - left : x1 + right] for y in range(y0 - 1, max(-1, y0 - 1 - reach_y), -1)])
    bottom = grow([is_flat[y, x0 - left : x1 + right] for y in range(y1, min(height, y1 + reach_y))])
    return (x0 - left, y0 - top, x1 + right, y1 + bottom)


def get_text_box_on_flat_color(page_array, box, color, tolerance=40):
    """
    The box around all the text next to a box on flat color, e.g. a caption's "…" that Magi's box cut off. Like in a speech bubble, the text is the letters that are holes in the flat area around the box. They're looked for up to half a letter past the box's ends (below and above a column of Japanese, left and right of a line) but only an eighth of a letter to its sides, so a caption next to it isn't taken in.
    """
    from scipy import ndimage

    x0, y0, x1, y1 = box
    margin = max(8, min(x1 - x0, y1 - y0)) // 2
    margin_x, margin_y = (margin // 4, margin) if y1 - y0 >= x1 - x0 else (margin, margin // 4)
    top, left = max(0, y0 - margin_y), max(0, x0 - margin_x)
    window = page_array[top : y1 + margin_y, left : x1 + margin_x].astype(int)
    areas, _ = ndimage.label(numpy.abs(window - numpy.array(color)).max(axis=2) <= tolerance)
    ring = get_ring(areas, (x0 - left, y0 - top, x1 - left, y1 - top))
    ring = ring[ring > 0]
    if len(ring) == 0:
        return box
    paper = areas == numpy.bincount(ring).argmax()
    rows, columns = numpy.nonzero(get_text_in_part(paper, ndimage.binary_fill_holes(paper), box, top, left))
    if len(rows) == 0:
        return box
    return (min(x0, left + int(columns.min())), min(y0, top + int(rows.min())), max(x1, left + int(columns.max()) + 1), max(y1, top + int(rows.max()) + 1))


def erase_box(page, box):
    """
    Erase text that isn't in a speech bubble (changed in place): fill it with the color around it if that's flat, else paint over it with LaMa. Returns that color (None on artwork) and the areas the text may be lettered in (here just one).
    """
    x0, y0, x1, y1 = box
    page_array = numpy.asarray(page)
    color = get_flat_color(page_array, box)
    if color is None:
        paint_over_with_lama(page, box)
        # Only a little wider than the Japanese, so it doesn't spread over the art (and it's kept in its panel later).
        extra = (x1 - x0) // 10
        return None, [(max(0, x0 - extra), y0, min(page.width, x1 + extra), y1)]
    box = x0, y0, x1, y1 = get_text_box_on_flat_color(page_array, box, color)
    area = grow_over_flat_color(page_array, box, color)
    ImageDraw.Draw(page).rectangle((x0 - 1, y0 - 1, x1 + 1, y1 + 1), fill=color)
    return color, [area]


def wrap_text(draw, text, font, max_width, hyphenator=None, split_anywhere=False):
    """
    Word-wrap "text" to "max_width". With a "hyphenator" (pyphen), a word that doesn't fit is split at a syllable with "-" (INTER-PERSONAL) when it's too long for a line of its own, or when it's a long word (8+ letters) and the line would otherwise stay less than half full.
    """
    lines, line = [], ""
    words = text.split()
    while words:
        word = words.pop(0)
        candidate = f"{line} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            line = candidate
            continue
        if hyphenator and ((len(word) >= 8 and draw.textlength(line, font=font) < max_width / 2) or draw.textlength(word, font=font) > max_width):
            # The longest first part that still fits.
            split = next((parts for parts in hyphenator.iterate(word) if draw.textlength(f"{line} {parts[0]}-".strip(), font=font) <= max_width), None)
            if split:
                lines.append(f"{line} {split[0]}-".strip())
                line = ""
                words.insert(0, split[1])
                continue
        if line:
            # The word starts the next line, where it's tried again (it may still need splitting).
            lines.append(line)
            line = ""
            words.insert(0, word)
            continue
        if split_anywhere and len(word) > 1:
            # Last resort at the smallest size: the most letters that fit, then "-".
            letters = max(1, next((count for count in range(len(word) - 1, 0, -1) if draw.textlength(word[:count] + "-", font=font) <= max_width), 1))
            lines.append(word[:letters] + "-")
            words.insert(0, word[letters:])
            continue
        # A word too long for a line of its own that can't be split: "fit_text" shrinks the font until it fits.
        line = word
    return lines + [line] if line else lines


def fit_text(draw, text, font_path, area, max_font_size, hyphenator=None, outlined=False):
    """
    The biggest font size (and its lines) that "text" fits in "area" at, less some padding so it never touches the bubble's edge, and that inner area. It always fits: the font shrinks as far as needed (down to "SMALLEST_FONT_SIZE"). With "outlined", the white outline drawn around each letter counts too.
    """
    left, top, right, bottom = area
    padding = max(3, round(min(right - left, bottom - top) * 0.06))
    left, top, right, bottom = left + padding, top + padding, right - padding, bottom - padding
    for size in range(max(max_font_size, SMALLEST_FONT_SIZE), SMALLEST_FONT_SIZE - 1, -1):
        font = ImageFont.truetype(font_path, size)
        outline = get_outline_width(size) if outlined else 0
        lines = wrap_text(draw, text, font, right - left - 2 * outline, hyphenator)
        if len(lines) * size * 1.15 + 2 * outline <= bottom - top and all(draw.textlength(line, font=font) + 2 * outline <= right - left for line in lines):
            return size, font, lines, (left, top, right, bottom)
    # Still too wide at the smallest size (a very narrow box): words may be split anywhere.
    lines = wrap_text(draw, text, font, right - left - 2 * outline, hyphenator, split_anywhere=True)
    return size, font, lines, (left, top, right, bottom)


def get_outline_width(font_size):
    return max(2, font_size // 5)


def fit_and_draw_text(page, areas, text, font_path, color, max_font_size=60, language="english"):
    """
    Letter "text" in capitals, word-wrapped (long words split at syllables), centered in whichever of "areas" it fits in biggest. It never runs past its area: the font shrinks until it fits. Dark text on a light bubble and light text on a dark one; on artwork, black with a thick white outline so it can be read.
    """
    import pyphen

    draw = ImageDraw.Draw(page)
    text = text.upper()
    outlined = color is None
    hyphenator = pyphen.Pyphen(lang=HYPHENATION_LANGUAGES[language], left=3, right=3) if language in HYPHENATION_LANGUAGES else None
    size, font, lines, (left, top, right, bottom) = max(
        (fit_text(draw, text, font_path, area, max_font_size, hyphenator, outlined) for area in areas), key=lambda fit: fit[0]
    )
    line_height = size * 1.15
    is_dark = color is not None and sum(color) / 3 < 100
    fill = "white" if is_dark else "black"
    outline = {"stroke_width": get_outline_width(size), "stroke_fill": "white"} if outlined else {}
    first_line_y = (top + bottom) / 2 - len(lines) * line_height / 2 + line_height / 2
    for number, line in enumerate(lines):
        draw.text(((left + right) / 2, first_line_y + number * line_height), line, font=font, fill=fill, anchor="mm", **outline)


def end_with_punctuation(text):
    """
    A line of dialogue that ends in a letter or number gets a period, since English lettering always ends a sentence (closing quotes stay after it). A line ending in ")" (e.g. a name card's age) is left as it is.
    """
    core = text.rstrip("\"'”’」")
    if core and core[-1].isalnum():
        return core + "." + text[len(core):]
    return text


def get_letter_size(box, source):
    """
    About how tall each letter is, guessed from the box's area for each character read.
    """
    x0, y0, x1, y1 = box
    characters = max(1, len("".join(source.split())))
    return ((x1 - x0) * (y1 - y0) / characters) ** 0.5


def is_big_text_on_art(page_array, box, source):
    """
    Whether text that isn't in a speech bubble is drawn much bigger than dialogue, on the artwork rather than in a flat caption box: a sound effect or a title logo. It's left alone without asking the translator, since English lettered over it would cover the art (and maybe a bubble).
    """
    return get_letter_size(box, source) > BIG_LETTER_SHARE * page_array.shape[0] and get_flat_color(page_array, box) is None


def is_left_alone(page_array, box, source, bubble):
    """
    Whether a line is left as it is, whatever the translator says:
    - text on the art that's a big sound effect or logo, or only marks and a single letter (ド, ッ, "…", "〜" on a TV screen), which a translator turns into junk like "Doh..." or "Tsu.";
    - in a light area, letters twice the sound-effect size: a sound effect drawn on a white wall or sky (Dragon Tofu ch. 24's ウオオオオオ), not dialogue (the biggest in the tests was 6% of the page's height). Erasing it as a bubble would wipe the drawings in that white area.
    """
    if bubble is None:
        return is_big_text_on_art(page_array, box, source) or sum(character.isalpha() for character in source) < 2
    return get_letter_size(box, source) > 2 * BIG_LETTER_SHARE * page_array.shape[0]


def clip_to_panel(area, panels):
    """
    The area cut to the panel its middle is in (from Magi), so text on the art stays in its panel. Unchanged if it's in none.
    """
    middle_x, middle_y = (area[0] + area[2]) / 2, (area[1] + area[3]) / 2
    for left, top, right, bottom in panels:
        if left <= middle_x <= right and top <= middle_y <= bottom:
            return (max(area[0], left), max(area[1], top), min(area[2], right), min(area[3], bottom))
    return area


def get_letters_that_fit(page, light_areas, page_lines, panels):
    """
    About how many letters fit in each line's space at a readable size, so the translator can keep lines short where the space is tight.
    """
    size = READABLE_FONT_SHARE * page.height
    counts = []
    for text_box, magi_box, bubble in page_lines:
        if bubble is None:
            areas = [clip_to_panel(text_box, panels)]
        else:
            boxes_in_bubble = [other_box for _, other_box, other_bubble in page_lines if other_bubble == bubble]
            top, left, _, part = get_bubble_part(light_areas, bubble, magi_box, boxes_in_bubble)
            areas = get_inside_rectangles(part, (text_box[0] - left, text_box[1] - top, text_box[2] - left, text_box[3] - top))
        room = max((right - left) * (bottom - top) for left, top, right, bottom in areas)
        # A capital letter is about 0.6 of the font size wide, a line 1.15 tall; 0.8 leaves room for padding and line ends.
        counts.append(max(5, round(0.8 * room / (0.6 * size * 1.15 * size))))
    return counts


def get_bubbles_inside(light_areas, page_lines, box):
    """
    A mask of the page's speech bubbles (with everything in them) that lie inside "box", e.g. bubbles a big sound effect is drawn around.
    """
    from scipy import ndimage

    labels = light_areas[0]
    x0, y0, x1, y1 = box
    inside = numpy.zeros(labels.shape, bool)
    for bubble in {bubble for _, _, bubble in page_lines if bubble is not None}:
        rows, columns = numpy.nonzero(labels == bubble)
        if columns.min() >= x0 - 10 and rows.min() >= y0 - 10 and columns.max() <= x1 + 10 and rows.max() <= y1 + 10:
            inside |= ndimage.binary_fill_holes(labels == bubble)
    return inside


def get_box(box):
    return tuple(int(round(float(value))) for value in box)


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    except (OSError, ValueError):
        return default


def save_page(page, path):
    extension = os.path.splitext(path)[1].lower()
    if extension in (".jpg", ".jpeg", ".webp"):
        page.save(path, quality=95)
    else:
        page.save(path)


def free_reading_models(magi):
    """
    Unload the models that found and read the text (about 3 GB), so a translator running on this computer (Ollama) has the memory. They're loaded again the next time they're needed.
    """
    import gc
    import torch

    global _hayai
    _hayai = None
    magi._full_model = None
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()


def get_lines(page, magi_boxes):
    """
    The lines of one page, as (box around its text, Magi's box, bubble), in reading order. Boxes found twice are joined, boxes in one bubble become one line, and a line's box grows to all the text in its part of the bubble.
    """
    light_areas = get_light_areas(page)
    labels, sizes = light_areas

    def get_share_inside(bubble, box):
        x0, y0, x1, y1 = box
        return (labels[max(0, y0) : y1, max(0, x0) : x1] == bubble).sum() / sizes[bubble]

    boxes, bubbles = remove_repeated_boxes(magi_boxes, [get_bubble(light_areas, box) for box in magi_boxes], get_share_inside, lambda bubble: sizes[bubble])
    groups = group_by_bubble(boxes, bubbles)
    lines = []
    for box, bubble in groups:
        if bubble is None:
            lines.append((box, box, None))
        else:
            boxes_in_bubble = [other_box for other_box, other_bubble in groups if other_bubble == bubble]
            lines.append((get_text_box_in_bubble(light_areas, bubble, box, boxes_in_bubble), box, bubble))
    return lines


def remove_repeated_lines(page_lines, sources):
    """
    The same text found twice, once in its speech bubble and once as text on the art (so "remove_repeated_boxes" kept both), would be lettered twice on top of itself. Of two lines whose boxes overlap by half and whose text is almost the same (one OCR slip, e.g. チャンホ and チャンボ), only one is kept: the one in a bubble, or else the bigger one.
    """

    def get_area(line):
        x0, y0, x1, y1 = line[0]
        return (x1 - x0) * (y1 - y0)

    kept = []
    for line, source in zip(page_lines, sources):
        repeat = next(
            (
                index
                for index, (kept_line, kept_source) in enumerate(kept)
                if get_overlap_share(line[0], kept_line[0]) >= 0.5 and difflib.SequenceMatcher(None, source, kept_source).ratio() >= 0.8
            ),
            None,
        )
        if repeat is None:
            kept.append((line, source))
        elif (line[2] is not None, get_area(line)) > (kept[repeat][0][2] is not None, get_area(kept[repeat][0])):
            kept[repeat] = (line, source)
    return [line for line, _ in kept], [source for _, source in kept]


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=1)


def translate_chapter(image_folder, image_names, output_folder, settings, glossary_folder=None, report_progress=lambda **fields: None, raise_if_cancelled=lambda: None):
    """
    Translate the pages in "image_folder" and save them (same file names) in "output_folder", with "translation.json" (every box, its original text and its translation), saved after every page so a cancelled or failed run keeps what's done. A page whose text was already translated in an earlier run (same languages and model) is lettered again without asking the LLM, so a line fixed by hand in "translation.json" is kept. The series' glossary is kept in "glossary_folder" (by default the folder the chapter is in).
    """
    from magi import get_magi

    os.makedirs(output_folder, exist_ok=True)
    pages = [Image.open(os.path.join(image_folder, name)).convert("RGB") for name in image_names]
    magi = get_magi()
    # Japanese: well below Magi's own 0.3, so fewer bubbles and captions are missed (Shachou ch. 3 page 1 needed 0.1 for two captions); the extra boxes on the art read as lone marks and are left alone. English and Spanish: Magi's own 0.3, since its English reader makes up a whole sentence for an extra box with no text (Soul Anomaly ch. 1: "I have a few more of the" lettered on a roof).
    threshold = 0.1 if settings["source_language"] == "japanese" else 0.3
    results = magi.run_with_cpu_fallback(
        "_full_model", lambda: magi.find_text_boxes([numpy.array(page) for page in pages], text_detection_threshold=threshold)
    )
    lines_on_each_page = [get_lines(page, [get_box(box) for box in result["texts"]]) for page, result in zip(pages, results)]
    panels_on_each_page = [[get_box(panel) for panel in result["panels"]] for result in results]
    text_boxes_on_each_page = [[text_box for text_box, _, _ in lines] for lines in lines_on_each_page]

    report_progress(stage="Reading the text", pages_done=None, pages_total=None, detail="Reading the text")
    if settings["source_language"] == "japanese":
        source_on_each_page = read_japanese(pages, text_boxes_on_each_page)
    else:
        source_on_each_page = read_latin(magi, pages, text_boxes_on_each_page)
    lines_on_each_page, source_on_each_page = zip(*[remove_repeated_lines(lines, sources) for lines, sources in zip(lines_on_each_page, source_on_each_page)]) if pages else ([], [])

    if settings["engine"] == "ollama":
        free_reading_models(magi)

    translation_path = os.path.join(output_folder, TRANSLATION_FILE_NAME)
    saved = load_json(translation_path, {})
    translation_info = {"engine": settings["engine"], "model": settings["model"], "from": settings["source_language"], "to": settings["target_language"]}
    # Translations into another language, or by another model, are made again.
    is_same_translation = all(saved.get(key) == value for key, value in translation_info.items())
    saved_pages = {page["file"]: page["lines"] for page in saved.get("pages", [])} if is_same_translation else {}
    glossary_path = os.path.join(glossary_folder or os.path.dirname(os.path.normpath(output_folder)), GLOSSARY_FILE_NAME)
    glossary = load_json(glossary_path, [])
    font_path = os.path.join(FONTS_FOLDER, FONTS.get(settings["font"], FONTS["Bubble Sans"]))

    translated_pages = []
    previous_page = None
    checked_graphics_card = False
    report_progress(stage="Translating", pages_done=0, pages_total=len(pages), unit="pages", detail=f"Translating with {settings['model']}")
    for page_number, (name, page, page_lines, sources, panels) in enumerate(
        zip(image_names, pages, lines_on_each_page, source_on_each_page, panels_on_each_page), start=1
    ):
        raise_if_cancelled()
        boxes = [text_box for text_box, _, _ in page_lines]
        # Found again on the page as it was (erasing only starts below).
        light_areas = get_light_areas(page)
        page_array = numpy.asarray(page)
        left_alone = [is_left_alone(page_array, text_box, source, bubble) for source, (text_box, _, bubble) in zip(sources, page_lines)]
        saved_lines = saved_pages.get(name)
        if saved_lines and [line["source"] for line in saved_lines] == sources:
            texts = [line["text"] for line in saved_lines]
        elif boxes:
            letters_that_fit = get_letters_that_fit(page, light_areas, page_lines, panels)
            in_bubble = [bubble is not None for _, _, bubble in page_lines]
            texts, new_glossary = translate_page(settings, page, boxes, sources, previous_page, glossary, letters_that_fit=letters_that_fit, in_bubble=in_bubble)
            # A line in a speech bubble is never left in the original language: lines left out are asked for once more.
            left_out = [index for index, (text, source) in enumerate(zip(texts, sources)) if in_bubble[index] and not text and not left_alone[index] and any(character.isalnum() for character in source)]
            # A line-by-line model would only give the same answer again.
            if left_out and not OLLAMA_MODELS.get(settings["model"], {}).get("line_by_line"):
                reminder = f"Lines {', '.join(str(index + 1) for index in left_out)} are in speech bubbles but were left empty: translate every one of them this time."
                retried, _ = translate_page(settings, page, boxes, sources, previous_page, glossary, letters_that_fit=letters_that_fit, in_bubble=in_bubble, reminder=reminder)
                for index in left_out:
                    texts[index] = retried[index]
            texts = [end_with_punctuation(text) if is_in_bubble else text for text, is_in_bubble in zip(texts, in_bubble)]
            # Sound effects, logos and lone marks are left as they are, whatever the translator said (never a line of dialogue). Only new translations: a line fixed by hand in "translation.json" is kept.
            texts = ["" if alone else text for text, alone in zip(texts, left_alone)]
            if settings["engine"] == "ollama" and not checked_graphics_card:
                # Only once it's loaded can Ollama say whether the model fits on the graphics card.
                checked_graphics_card = True
                gpu_share = get_ollama_gpu_share(settings["model"])
                if gpu_share is not None and gpu_share < 0.9:
                    report_progress(detail=f"Translating with {settings['model']}. Only {gpu_share:.0%} of it fits on the graphics card, so it's slow: a smaller model would be faster")
            for entry in new_glossary:
                if entry["name"] not in {known["name"] for known in glossary}:
                    glossary.append(entry)
        else:
            texts = []

        lines = [{"box": list(box), "source": source, "text": text} for box, source, text in zip(boxes, sources, texts)]
        # Text on the art first, so the speech bubbles are lettered last and always end up on top.
        for line, (text_box, magi_box, bubble) in sorted(zip(lines, page_lines), key=lambda pair: pair[1][2] is not None):
            if line["text"]:
                if bubble is None:
                    before = numpy.asarray(page).copy()
                    color, areas = erase_box(page, text_box)
                    fit_and_draw_text(page, [clip_to_panel(area, panels) for area in areas], line["text"], font_path, color, language=settings["target_language"])
                    # Speech bubbles inside it are put back as they were: text on the art never erases or covers a bubble.
                    after = numpy.asarray(page).copy()
                    protected = get_bubbles_inside(light_areas, page_lines, text_box)
                    after[protected] = before[protected]
                    page.paste(Image.fromarray(after))
                else:
                    boxes_in_bubble = [other_box for _, other_box, other_bubble in page_lines if other_bubble == bubble]
                    color, areas = erase_in_bubble(page, light_areas, bubble, magi_box, boxes_in_bubble)
                    fit_and_draw_text(page, areas, line["text"], font_path, color, language=settings["target_language"])
        save_page(page, os.path.join(output_folder, name))
        translated_pages.append({"file": name, "lines": lines})
        previous_page = lines
        # Saved after every page. Pages not reached yet keep what an earlier run saved for them.
        done = {page["file"] for page in translated_pages}
        save_json(translation_path, {**translation_info, "pages": translated_pages + [{"file": file, "lines": old_lines} for file, old_lines in saved_pages.items() if file not in done]})
        if glossary:
            save_json(glossary_path, glossary)
        report_progress(pages_done=page_number)

    # The reading direction saved by the MangaDex download goes along, so "Automatic" still works in Panel-By-Panel (spec 27).
    reading_direction_file = os.path.join(image_folder, READING_DIRECTION_FILE_NAME)
    if os.path.exists(reading_direction_file):
        shutil.copy(reading_direction_file, os.path.join(output_folder, READING_DIRECTION_FILE_NAME))
