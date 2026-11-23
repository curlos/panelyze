# Translate pages [start, start+n) of a chapter with one Ollama model and language pair, timing the translator. Args: repo chapter_dir out_dir model from to start n
import sys, os, time
sys.path.insert(0, sys.argv[1])
import translate
from utils import list_images
chapter, out, model, source, target, start, n = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], int(sys.argv[7]), int(sys.argv[8])
names = [os.path.basename(p) for p in list_images(chapter)][start:start + n]
settings = {"engine": "ollama", "model": model, "source_language": source, "target_language": target, "keep_honorifics": True,
            "font": "Bubble Sans", "send_page_image": True, "api_key": ""}
translate.check_engine_ready(settings)
times = []
original = translate.translate_page
def timed(*args, **kwargs):
    started = time.time(); result = original(*args, **kwargs); times.append(round(time.time() - started, 1)); return result
translate.translate_page = timed
translate.translate_chapter(chapter, names, out, settings)
print("LLM per page", times)
