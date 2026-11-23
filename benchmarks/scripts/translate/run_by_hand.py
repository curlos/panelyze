# Letter my own translations ({page file: [[source, translation], ...]}). The source lines must match what the pipeline reads, in the same order. Args: repo chapter_dir out_dir lines.json N
import sys, os, json
sys.path.insert(0, sys.argv[1])
import translate
from utils import list_images
chapter, out, lines_path, n = sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
all_pages = json.load(open(lines_path))
pages_iter = iter(sorted(all_pages))
last = [None]
def fake_translate_page(settings, page, boxes, source_lines, previous_page, glossary, **kwargs):
    got = [str(s) for s in source_lines]
    if kwargs.get("reminder"):  # the pipeline asking again for an empty bubble line: same answer
        return [t for _, t in last[0]], []
    mine = last[0] = all_pages[next(pages_iter)]
    print("pipeline read:", json.dumps(got, ensure_ascii=False))
    assert [s for s, _ in mine] == got, "line order/text differs; redo the by-hand list"
    return [t for _, t in mine], []
translate.translate_page = fake_translate_page
names = [os.path.basename(p) for p in list_images(chapter)][:n]
settings = {"engine": "claude", "model": "by-hand", "source_language": "japanese", "target_language": "english", "keep_honorifics": True,
            "font": "Bubble Sans", "send_page_image": True, "api_key": "x"}
translate.translate_chapter(chapter, names, out, settings)
