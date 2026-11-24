"""Absolute Batman ch. 1, 20 panels, "Best" to 4K: before (tiles fit each panel, full passes) vs after (fixed tiles, stop short + resize)."""
import os, sys, time
sys.path.insert(0, os.getcwd())
import numpy
from PIL import Image
import janai, utils

panels = os.path.expanduser(r"~/Documents/Panelyze/10-amd-gaming-pc/Panel-By-Panel/absolute batman/Chapter_1_Absolute Batman, Vol. 1 The Zoo")
out = os.path.expanduser(r"~/Documents/Panelyze/10-amd-gaming-pc/benchmark-absolute-batman-ch1-best-4k")
os.makedirs(out, exist_ok=True)
numbers = range(30, 50)
model_path = janai.download_model_file(janai.COLOR_MODEL_FILE, janai.COLOR_MODEL_ZIP_URL)
upscale_tile, _ = janai.get_pytorch_upscale_function(model_path)
upscale_tile(numpy.zeros((3, 64, 64), numpy.float32))

def upscale(array, ratio, fixed):
    for _ in range(int(numpy.log2(ratio))):
        array = numpy.clip(janai.upscale_in_tiles(upscale_tile, array, 2, janai.PYTORCH_TILE, fixed), 0, 1)
    return Image.fromarray((array.transpose(1, 2, 0) * 255).round().astype(numpy.uint8))

def to_4k(image):
    scale = utils.MAX_UPSCALED_IMAGE_SIDE / max(image.size)
    return image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)

def run(label, fixed, best_ratio):
    total = 0
    for n in numbers:
        with Image.open(os.path.join(panels, f"panel_{n}.png")) as image:
            w, h = image.size
            array = numpy.asarray(image.convert("RGB"), dtype=numpy.float32).transpose(2, 0, 1) / 255
        ratio = (utils.get_best_upscale_ratio if best_ratio else utils.get_capped_upscale_ratio)(w, h, 32)
        start = time.time()
        result = to_4k(upscale(array, ratio, fixed))
        seconds = time.time() - start
        total += seconds
        result.save(os.path.join(out, f"panel_{n}-{'after' if best_ratio else 'before'}.png"))
        print(f"  {label} panel_{n} {w}x{h} {ratio}x: {seconds:.1f} s", flush=True)
    print(f"{label}: {total:.0f} s for {len(numbers)} panels ({total / len(numbers):.1f} s each)", flush=True)

run("AFTER (fixed tiles, stop short + resize)", True, True)
run("BEFORE (tiles fit each panel, full passes)", False, False)
