# Numbered page images + line list for a blind reference. Args: repo chapter_dir translation.json out_dir
import sys, json, os
sys.path.insert(0, sys.argv[1])
import translate
from PIL import Image
chapter, saved, out = sys.argv[2], json.load(open(sys.argv[3])), sys.argv[4]
lines = {}
for p in saved["pages"]:
    page = Image.open(os.path.join(chapter, p["file"])).convert("RGB")
    translate.get_numbered_page_image(page, [l["box"] for l in p["lines"]]).save(os.path.join(out, p["file"].rsplit(".", 1)[0] + "-numbered.png"))
    lines[p["file"]] = [l["source"] for l in p["lines"]]
json.dump(lines, open(os.path.join(out, "lines.json"), "w"), ensure_ascii=False, indent=1)
