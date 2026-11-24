"""Absolute Batman ch. 1, a few panels, "Best" to 4K with AMD's same-size tiles: before (the tile at an image's edge was upscaled a second time for its last few pixels) vs after (it isn't). Run: .\\venv\\Scripts\\python.exe experiments\\spec-10-benchmarks\\duplicate_tile.py [panel numbers...]"""
import os, sys, time
sys.path.insert(0, os.getcwd())
import numpy
from PIL import Image
import janai, utils
from janai import TILE_OVERLAP

panels = os.path.expanduser(r"~/Documents/Panelyze/10-amd-gaming-pc/Panel-By-Panel/absolute batman/Chapter_1_Absolute Batman, Vol. 1 The Zoo")
numbers = [int(n) for n in sys.argv[1:]] or [13, 14, 134, 143]


def old_upscale_in_tiles(upscale_tile, image, scale, tile_size, fixed_tile_size):
    # "upscale_in_tiles" as it was before the fix (same-size tiles only).
    channels, height, width = image.shape
    result = numpy.zeros((channels, height * scale, width * scale), dtype=numpy.float32)
    step = tile_size - 2 * TILE_OVERLAP
    for y in range(0, height, step):
        for x in range(0, width, step):
            tile_y, tile_x = max(min(y - TILE_OVERLAP, height - tile_size), 0), max(min(x - TILE_OVERLAP, width - tile_size), 0)
            tile = image[:, tile_y:tile_y + tile_size, tile_x:tile_x + tile_size]
            tile = numpy.pad(tile, ((0, 0), (0, tile_size - tile.shape[1]), (0, tile_size - tile.shape[2])), mode="edge")
            end_y, end_x = min(y + step, height), min(x + step, width)
            upscaled_tile = upscale_tile(numpy.ascontiguousarray(tile))
            result[:, y * scale:end_y * scale, x * scale:end_x * scale] = upscaled_tile[
                :, (y - tile_y) * scale:(end_y - tile_y) * scale, (x - tile_x) * scale:(end_x - tile_x) * scale
            ]
    return result


model_path = janai.download_model_file(janai.COLOR_MODEL_FILE, janai.COLOR_MODEL_ZIP_URL)
gpu_upscale_tile, _ = janai.get_pytorch_upscale_function(model_path)
tiles = 0


def upscale_tile(tile):
    global tiles
    tiles += 1
    return gpu_upscale_tile(tile)


# AMD works out how to run a 512x512 tile the first time: done here, so it's not in either time.
gpu_upscale_tile(numpy.zeros((3, 512, 512), numpy.float32))


def upscale(tiling, array, ratio):
    for _ in range(int(numpy.log2(ratio))):
        array = numpy.clip(tiling(upscale_tile, array, 2, janai.PYTORCH_TILE, True), 0, 1)
    return array


totals = {"before": 0.0, "after": 0.0}
for n in numbers:
    with Image.open(os.path.join(panels, f"panel_{n}.png")) as image:
        w, h = image.size
        array = numpy.asarray(image.convert("RGB"), dtype=numpy.float32).transpose(2, 0, 1) / 255
    ratio = utils.get_best_upscale_ratio(w, h, 32)
    results = {}
    for label, tiling in (("before", old_upscale_in_tiles), ("after", janai.upscale_in_tiles)):
        tiles = 0
        start = time.time()
        results[label] = upscale(tiling, array, ratio)
        seconds = time.time() - start
        totals[label] += seconds
        print(f"  panel_{n} {w}x{h} {ratio}x {label}: {seconds:.1f} s, {tiles} tiles", flush=True)
    print(f"  same image: {numpy.array_equal(results['before'], results['after'])}", flush=True)

for label, total in totals.items():
    print(f"{label}: {total:.1f} s for {len(numbers)} panels ({total / len(numbers):.1f} s each)")
