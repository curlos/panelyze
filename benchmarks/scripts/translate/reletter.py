# Letter a chapter again from a saved translation.json (looked up by the Japanese text), without asking any LLM. Args: repo chapter_dir out_dir saved.json N
import sys, os, json
sys.path.insert(0, sys.argv[1])
import translate
from utils import list_images
chapter, out, saved, n = sys.argv[2], sys.argv[3], json.load(open(sys.argv[4])), int(sys.argv[5])
known = {}
for p in saved["pages"]:
    for l in p["lines"]:
        if l["text"] or l["source"] not in known:
            known[l["source"]] = l["text"]
import difflib
def look_up(source):
    if known.get(source):
        return known[source]
    similar = [t for s, t in known.items() if t and difflib.SequenceMatcher(None, s, source).ratio() >= 0.8]
    return similar[0] if similar else ""
def fake(settings, page, boxes, sources, previous_page, glossary, **kwargs):
    return ["" if translate.JAPANESE_LETTERS.search(look_up(s)) else look_up(s) for s in sources], []
translate.translate_page = fake
names = [os.path.basename(p) for p in list_images(chapter)][:n]
settings = {"engine": "claude", "model": "re-lettered", "source_language": "japanese", "target_language": "english", "keep_honorifics": True,
            "font": "Bubble Sans", "send_page_image": True, "api_key": "x"}
translate.translate_chapter(chapter, names, out, settings)
