"""
The "Best" upscaler: MangaJaNai for black and white manga and IllustrationJaNai for color images, by the-database (https://github.com/the-database/MangaJaNai). The models are licensed CC BY-NC 4.0: free to use, but not for anything commercial.

On manga they look much better than waifu2x: they restore clean halftone dots (screentone) instead of blurring them. MangaJaNai only works on black and white images (it turns color into black and white dots), so color images get IllustrationJaNai.

On Apple Silicon Macs they run with Core ML: MangaJaNai on the Neural Engine (about 3.6x faster than the GPU with PyTorch) and IllustrationJaNai on the GPU (about 1.5x faster than PyTorch; Apple's Neural Engine compiler gets stuck on it). On other computers they run with PyTorch.
"""

import math
import os
import platform
import shutil
import sys
import urllib.request
import zipfile

import numpy
from PIL import Image
from PIL.PngImagePlugin import PngInfo

MODELS_FOLDER = os.path.expanduser("~/Library/Application Support/Panelyze/upscale-models")

# MangaJaNai has a model for each of the most common page heights of digital manga. The one closest to the page's height restores the halftone dots at the right size.
MANGA_MODEL_FILES = {
    1200: "2x_MangaJaNai_1200p_V1_ESRGAN_70k.pth",
    1300: "2x_MangaJaNai_1300p_V1_ESRGAN_75k.pth",
    1400: "2x_MangaJaNai_1400p_V1_ESRGAN_70k.pth",
    1500: "2x_MangaJaNai_1500p_V1_ESRGAN_90k.pth",
    1600: "2x_MangaJaNai_1600p_V1_ESRGAN_90k.pth",
    1920: "2x_MangaJaNai_1920p_V1_ESRGAN_70k.pth",
    2048: "2x_MangaJaNai_2048p_V1_ESRGAN_95k.pth",
}
MANGA_MODELS_ZIP_URL = "https://github.com/the-database/MangaJaNai/releases/download/1.0.0/MangaJaNai_V1_ModelsOnly.zip"
COLOR_MODEL_FILE = "2x_IllustrationJaNai_V2standard_FDAT_M_unshuffle_40k.safetensors"
COLOR_MODEL_ZIP_URL = "https://github.com/the-database/MangaJaNai/releases/download/2.0.0/4x_IllustrationJaNai_V2standard_ModelsOnly.zip"

# Panel-By-Panel saves the height of the page each panel came from in the panel's PNG file, because MangaJaNai's model is picked by the page's height, not the panel's.
PAGE_HEIGHT_KEY = "panelyze_page_height"

# The Neural Engine only runs one fixed image size, so images are upscaled in tiles of this size. Tiles overlap a little so their edges don't show.
COREML_TILE = 256
PYTORCH_TILE = 512
TILE_OVERLAP = 8

_loaded_upscalers = {}


def get_page_height_info(page_height):
    """
    PNG metadata that records the height of the page a panel was cut from.
    """
    info = PngInfo()
    info.add_text(PAGE_HEIGHT_KEY, str(page_height))
    return info


def get_page_height(image):
    """
    The height of the page the image came from: saved in the file by Panel-By-Panel, or else the image's own height (e.g. a whole page).
    """
    try:
        return int(image.info[PAGE_HEIGHT_KEY])
    except (KeyError, ValueError):
        return image.height


def get_manga_model_height(page_height):
    return min(MANGA_MODEL_FILES, key=lambda model_height: abs(model_height - page_height))


def is_color_image(image):
    """
    Whether the image has real color in it (a color page), not just black, white and gray (a scan can have a slight tint, so that doesn't count).
    """
    small = image.convert("RGB").resize((128, 128))
    hsv = numpy.asarray(small.convert("HSV"), dtype=numpy.float32) / 255
    colorful_pixels = (hsv[..., 1] > 0.25) & (hsv[..., 2] > 0.2)
    return colorful_pixels.mean() > 0.02


def download_model_file(file_name, zip_url, report=print):
    """
    The path of a model file, downloaded the first time (the models are only released inside zip files).
    """
    path = os.path.join(MODELS_FOLDER, file_name)
    if os.path.exists(path):
        return path

    os.makedirs(MODELS_FOLDER, exist_ok=True)
    zip_path = os.path.join(MODELS_FOLDER, "download.zip.tmp")
    report(f"Downloading the upscale model {file_name} (one time only)...")
    urllib.request.urlretrieve(zip_url, zip_path)

    try:
        with zipfile.ZipFile(zip_path) as models_zip:
            # Keep every 2x model from the zip (e.g. MangaJaNai's other page heights), so it never has to be downloaded again.
            for member in models_zip.namelist():
                member_name = os.path.basename(member)
                if member_name.startswith("2x_") and member_name.endswith((".pth", ".safetensors")):
                    with models_zip.open(member) as source, open(os.path.join(MODELS_FOLDER, f"{member_name}.tmp"), "wb") as target:
                        shutil.copyfileobj(source, target)
                    os.replace(os.path.join(MODELS_FOLDER, f"{member_name}.tmp"), os.path.join(MODELS_FOLDER, member_name))
    finally:
        os.remove(zip_path)

    if not os.path.exists(path):
        raise RuntimeError(f"The download didn't have the upscale model {file_name}.")

    return path


def load_pytorch_model(path):
    import torch
    import spandrel

    if path.endswith(".pth"):
        # "weights_only" so the file can't run any code when it's loaded.
        state_dict = torch.load(path, map_location="cpu", weights_only=True)
        state_dict = state_dict.get("params_ema", state_dict.get("params", state_dict))
        return spandrel.ModelLoader().load_from_state_dict(state_dict).model.eval()

    return spandrel.ModelLoader().load_from_file(path).model.eval()


def can_use_coreml():
    if sys.platform != "darwin" or platform.machine() != "arm64":
        return False

    try:
        import coremltools  # noqa: F401
    except ImportError:
        return False

    return True


def get_coreml_upscale_function(model_path, use_neural_engine, report=print):
    """
    An "upscale this tile" function that runs with Core ML, on the Neural Engine or else the GPU. The model is converted to Core ML the first time (about 10 seconds) and saved next to it.
    """
    import coremltools as ct

    coreml_path = f"{os.path.splitext(model_path)[0]}-{COREML_TILE}.mlpackage"
    if not os.path.exists(coreml_path):
        import torch

        report("Getting the upscale model ready for this Mac (one time only)...")
        traced_model = torch.jit.trace(load_pytorch_model(model_path), torch.rand(1, 3, COREML_TILE, COREML_TILE))
        coreml_model = ct.convert(
            traced_model,
            inputs=[ct.TensorType(name="image", shape=(1, 3, COREML_TILE, COREML_TILE))],
            outputs=[ct.TensorType(name="upscaled")],
            compute_precision=ct.precision.FLOAT16,
            minimum_deployment_target=ct.target.macOS13,
            convert_to="mlprogram",
        )
        # Saved under a temporary name first, so quitting halfway can't leave a broken model behind. Core ML needs the name to end in ".mlpackage".
        temporary_path = f"{os.path.splitext(coreml_path)[0]}-unfinished.mlpackage"
        shutil.rmtree(temporary_path, ignore_errors=True)
        coreml_model.save(temporary_path)
        os.replace(temporary_path, coreml_path)

    compute_units = ct.ComputeUnit.ALL if use_neural_engine else ct.ComputeUnit.CPU_AND_GPU
    coreml_model = ct.models.MLModel(coreml_path, compute_units=compute_units)
    return lambda tile: coreml_model.predict({"image": tile[None].astype(numpy.float32)})["upscaled"][0]


def get_pytorch_upscale_function(model_path):
    """
    An "upscale this tile" function that runs on the GPU (or the CPU without one), with PyTorch.
    """
    import torch
    from magi import get_device

    device = get_device()
    # Full precision: half precision is about 20% faster, but IllustrationJaNai's numbers overflow on some images, which ruins them.
    model = load_pytorch_model(model_path).to(device)

    def upscale_tile(tile):
        with torch.no_grad():
            return model(torch.from_numpy(tile)[None].to(device))[0].cpu().numpy()

    return upscale_tile


def upscale_in_tiles(upscale_tile, image, scale, tile_size, fixed_tile_size):
    """
    Upscale "image" (channels, height, width, values from 0 to 1) one tile at a time. "fixed_tile_size" pads the tiles at the edges to "tile_size" (the Neural Engine only runs one size). Otherwise the tiles fit the image, so a small image is done in one go.
    """
    channels, height, width = image.shape
    result = numpy.zeros((channels, height * scale, width * scale), dtype=numpy.float32)
    step = tile_size - 2 * TILE_OVERLAP if fixed_tile_size else tile_size

    for y in range(0, height, step):
        for x in range(0, width, step):
            if fixed_tile_size:
                tile_y, tile_x = max(min(y - TILE_OVERLAP, height - tile_size), 0), max(min(x - TILE_OVERLAP, width - tile_size), 0)
                tile = image[:, tile_y:tile_y + tile_size, tile_x:tile_x + tile_size]
                tile = numpy.pad(
                    tile,
                    ((0, 0), (0, tile_size - tile.shape[1]), (0, tile_size - tile.shape[2])),
                    mode="edge",
                )
            else:
                tile_y, tile_x = max(y - TILE_OVERLAP, 0), max(x - TILE_OVERLAP, 0)
                tile = image[:, tile_y:min(y + step + TILE_OVERLAP, height), tile_x:min(x + step + TILE_OVERLAP, width)]

            end_y, end_x = min(y + step, height), min(x + step, width)
            upscaled_tile = upscale_tile(numpy.ascontiguousarray(tile))
            # Only the middle of each tile is kept. Its edges are covered by the tiles next to it.
            result[:, y * scale:end_y * scale, x * scale:end_x * scale] = upscaled_tile[
                :,
                (y - tile_y) * scale:(end_y - tile_y) * scale,
                (x - tile_x) * scale:(end_x - tile_x) * scale,
            ]

    return result


def get_upscaler(model_path, use_neural_engine, report=print):
    """
    "upscale(image)" for a model, loaded once and then reused. Core ML when it's available, or else PyTorch.
    """
    key = (model_path, use_neural_engine)
    if key not in _loaded_upscalers:
        upscale_tile = None
        if can_use_coreml():
            try:
                upscale_tile = get_coreml_upscale_function(model_path, use_neural_engine, report)
                tile_size, fixed_tile_size = COREML_TILE, True
            except Exception as error:
                report(f"Couldn't use Core ML for the upscale model ({error}). Using PyTorch instead (slower).")

        if upscale_tile is None:
            upscale_tile = get_pytorch_upscale_function(model_path)
            tile_size, fixed_tile_size = PYTORCH_TILE, False

        _loaded_upscalers[key] = lambda image: upscale_in_tiles(upscale_tile, image, 2, tile_size, fixed_tile_size)

    return _loaded_upscalers[key]


def upscale_image_with_janai(input_image, output_image, upscale_ratio, report=print):
    """
    Upscale one image by "upscale_ratio" (2, 4, 8, ...: the models make images 2x bigger, so 4x is two times 2x) with MangaJaNai, or IllustrationJaNai for a color image. Saved in the format of "output_image"'s extension.
    """
    with Image.open(input_image) as image:
        page_height = get_page_height(image)
        is_color = is_color_image(image)
        array = numpy.asarray(image.convert("RGB"), dtype=numpy.float32).transpose(2, 0, 1) / 255

    for upscale_pass in range(int(math.log2(int(upscale_ratio)))):
        if is_color:
            model_path = download_model_file(COLOR_MODEL_FILE, COLOR_MODEL_ZIP_URL, report)
            upscale = get_upscaler(model_path, use_neural_engine=False, report=report)
        else:
            # The page is twice as tall after each pass.
            model_file = MANGA_MODEL_FILES[get_manga_model_height(page_height * 2**upscale_pass)]
            model_path = download_model_file(model_file, MANGA_MODELS_ZIP_URL, report)
            upscale = get_upscaler(model_path, use_neural_engine=True, report=report)

        array = numpy.clip(upscale(array), 0, 1)

    result = Image.fromarray((array.transpose(1, 2, 0) * 255).round().astype(numpy.uint8))
    # Black and white stays black and white (and the file is about 3x smaller).
    if not is_color:
        result = result.convert("L")

    save_options = {"quality": 95} if output_image.lower().endswith((".jpg", ".jpeg", ".webp")) else {}
    result.save(output_image, **save_options)
