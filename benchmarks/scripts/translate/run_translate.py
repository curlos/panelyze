# Translate the first N pages of a chapter with one engine/model and time it. Args: repo chapter_dir out_dir engine model N [send_image]
import sys, os, time, json
sys.path.insert(0, sys.argv[1])
import translate
from utils import list_images
chapter, out, engine, model, n = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], int(sys.argv[6])
send_image = (sys.argv[7] if len(sys.argv) > 7 else "1") == "1"
names = [os.path.basename(p) for p in list_images(chapter)][:n]
settings = {"engine": engine, "model": model, "source_language": "japanese", "target_language": "english", "keep_honorifics": True,
            "font": "Bubble Sans", "send_page_image": send_image, "api_key": translate.get_api_key(engine, "")}
translate.check_engine_ready(settings)
times = {}
orig = translate.translate_page
def timed(*a, **k):
    t = time.time(); r = orig(*a, **k); times.setdefault("llm", []).append(round(time.time() - t, 1)); return r
translate.translate_page = timed
t = time.time()
translate.translate_chapter(chapter, names, out, settings, report_progress=lambda **f: print("progress", {k: v for k, v in f.items() if v is not None}) if f.get("stage") else None)
print("total", round(time.time() - t, 1), "s; LLM per page", times.get("llm"))
