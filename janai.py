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
import zipfile

import numpy
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from utils import (
    PartialDownloadNotSupported,
    check_free_space,
    download_file,
    open_remote_zip,
    save_zip_files,
)

MODELS_FOLDER = os.path.expanduser(
    "~/Library/Application Support/Panelyze/upscale-models"
)

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
# Where the models come from, shown when they're downloaded (and when that fails), so the user knows what's being downloaded and can check the page.
MODELS_PAGE_URL = "https://github.com/the-database/MangaJaNai/releases"
COLOR_MODEL_FILE = "2x_IllustrationJaNai_V2standard_FDAT_M_unshuffle_40k.safetensors"
COLOR_MODEL_ZIP_URL = "https://github.com/the-database/MangaJaNai/releases/download/2.0.0/4x_IllustrationJaNai_V2standard_ModelsOnly.zip"

# Panel-By-Panel saves the height of the page each panel came from in the panel's PNG file, because MangaJaNai's model is picked by the page's height, not the panel's.
PAGE_HEIGHT_KEY = "panelyze_page_height"

# The Neural Engine only runs one fixed image size, so images are upscaled in tiles of this size. Tiles overlap a little so their edges don't show.
COREML_TILE = 256
PYTORCH_TILE = 512
TILE_OVERLAP = 8

_loaded_upscalers = {}

# Under each step that gets a model ready, in the Status view, for anyone who wants to know what it's doing.
COREML_CONVERT_DETAIL = "Core ML, Apple's way to run AI models fast on the Mac's chip, can't read the downloaded model, so a copy is made for it."
COREML_LOAD_DETAIL = "Core ML is Apple's way to run AI models fast on the Mac's chip. This happens once each time the app is opened."


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
    return min(
        MANGA_MODEL_FILES, key=lambda model_height: abs(model_height - page_height)
    )


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

    from gui_classes.ProgressPanel import DOWNLOAD_ONCE_DETAIL, show_extra_stage

    with show_extra_stage(get_download_step(zip_url), DOWNLOAD_ONCE_DETAIL):
        return download_missing_model_file(file_name, zip_url, report)


def get_model_name(zip_url):
    return "IllustrationJaNai" if zip_url == COLOR_MODEL_ZIP_URL else "MangaJaNai"


def download_missing_model_file(file_name, zip_url, report=print):
    path = os.path.join(MODELS_FOLDER, file_name)
    os.makedirs(MODELS_FOLDER, exist_ok=True)
    report(
        f"Downloading the Best upscale model {file_name} (one time only) from {MODELS_PAGE_URL}..."
    )
    name = get_model_name(zip_url)
    from storage import COLOR_MODEL_DOWNLOAD_BYTES, MANGA_MODELS_DOWNLOAD_BYTES

    check_free_space(
        MODELS_FOLDER,
        COLOR_MODEL_DOWNLOAD_BYTES
        if zip_url == COLOR_MODEL_ZIP_URL
        else MANGA_MODELS_DOWNLOAD_BYTES,
        name,
    )
    try:
        try:
            # Only the 2x models are downloaded, straight out of the zip on GitHub: the zips also have 4x (and bigger) models that aren't used (MangaJaNai's 433 MB zip has 236 MB of 2x models, IllustrationJaNai's 159 MB zip has 16 MB).
            with open_remote_zip(zip_url) as models_zip:
                save_2x_models(models_zip, progress_name=name)
        except PartialDownloadNotSupported:
            download_whole_zip(zip_url, name)
    except (OSError, zipfile.BadZipFile) as error:
        # Still an "OSError", which stops the job (like no internet does), instead of downloading it again for every image.
        raise OSError(
            f"Couldn't download the Best upscale model {file_name} (check your internet connection): {error}. It comes from {MODELS_PAGE_URL}"
        ) from error

    if not os.path.exists(path):
        raise OSError(
            f"The download didn't have the Best upscale model {file_name}. It comes from {MODELS_PAGE_URL}"
        )

    return path


def download_whole_zip(zip_url, name):
    """
    For a server that only sends whole files: the whole zip is downloaded, and only its 2x models are kept.
    """
    zip_path = os.path.join(MODELS_FOLDER, "download.zip.tmp")
    try:
        download_file(zip_url, zip_path, name=name)
        # Not a zip, e.g. an error page saved instead.
        if not zipfile.is_zipfile(zip_path):
            raise OSError(
                f"The download wasn't the model. Check that {MODELS_PAGE_URL} opens in your browser, then try again."
            )
        with zipfile.ZipFile(zip_path) as models_zip:
            save_2x_models(models_zip)
    finally:
        # Also a half-downloaded zip (up to 433 MB).
        if os.path.exists(zip_path):
            os.remove(zip_path)


def save_2x_models(models_zip, progress_name=None):
    """
    Save every 2x model in the zip (e.g. all of MangaJaNai's page heights, so it never has to be downloaded again). With "progress_name", the Status view shows how much is done (the zip is on GitHub, so this is the download).
    """
    save_zip_files(
        models_zip,
        [
            (member, os.path.join(MODELS_FOLDER, os.path.basename(member.filename)))
            for member in models_zip.infolist()
            if os.path.basename(member.filename).startswith("2x_")
            and member.filename.endswith((".pth", ".safetensors"))
        ],
        progress_name,
    )


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


def get_coreml_upscale_function(model_path, use_neural_engine, name, report=print):
    """
    An "upscale this tile" function that runs with Core ML, on the Neural Engine or else the GPU. The model is converted to Core ML the first time (about 12 seconds for IllustrationJaNai on an M1) and saved next to it. Each is a step of its own in the Status view.
    """
    import coremltools as ct

    from gui_classes.ProgressPanel import show_extra_stage

    coreml_path = f"{os.path.splitext(model_path)[0]}-{COREML_TILE}.mlpackage"
    if not os.path.exists(coreml_path):
        with show_extra_stage(get_convert_step(name), COREML_CONVERT_DETAIL):
            convert_to_coreml(model_path, coreml_path, report)

    compute_units = (
        ct.ComputeUnit.ALL if use_neural_engine else ct.ComputeUnit.CPU_AND_GPU
    )
    # About 2.5 seconds for IllustrationJaNai on an M1, each time the app is opened.
    with show_extra_stage(get_load_step(name, "Core ML"), COREML_LOAD_DETAIL):
        coreml_model = ct.models.MLModel(coreml_path, compute_units=compute_units)

        def upscale_tile(tile):
            return coreml_model.predict({"image": tile[None].astype(numpy.float32)})[
                "upscaled"
            ][0]

        # Core ML gets ready on the first tile (about 4 seconds the first time), so it's done here instead of in the middle of the first image.
        upscale_tile(numpy.zeros((3, COREML_TILE, COREML_TILE), numpy.float32))
    return upscale_tile


def convert_to_coreml(model_path, coreml_path, report=print):
    """
    Save a Core ML copy of the model at "coreml_path" (Core ML can't read PyTorch's files): the model is run once on a blank tile to record what it does, turned into Core ML's operations, made smaller and faster for the Mac (16-bit numbers), and saved.
    """
    import coremltools as ct
    import torch

    report(f"Converting {os.path.basename(model_path)} for Core ML (one time only)...")
    traced_model = torch.jit.trace(
        load_pytorch_model(model_path), torch.rand(1, 3, COREML_TILE, COREML_TILE)
    )
    coreml_model = ct.convert(
        traced_model,
        inputs=[ct.TensorType(name="image", shape=(1, 3, COREML_TILE, COREML_TILE))],
        outputs=[ct.TensorType(name="upscaled")],
        compute_precision=ct.precision.FLOAT16,
        minimum_deployment_target=ct.target.macOS13,
        convert_to="mlprogram",
        # Only saved here, and loaded afterwards with the chips it should run on (see "get_coreml_upscale_function"). Loading it here would use every chip, so macOS would first prepare it for the Neural Engine: for IllustrationJaNai (which runs on the GPU) that takes many minutes, with the app frozen.
        skip_model_load=True,
    )
    # Saved under a temporary name first, so quitting halfway can't leave a broken model behind. Core ML needs the name to end in ".mlpackage".
    temporary_path = f"{os.path.splitext(coreml_path)[0]}-unfinished.mlpackage"
    shutil.rmtree(temporary_path, ignore_errors=True)
    coreml_model.save(temporary_path)  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]
    os.replace(temporary_path, coreml_path)


def get_pytorch_upscale_function(model_path):
    """
    An "upscale this tile" function that runs on the GPU (or the CPU without one), with PyTorch, and the device it runs on.
    """
    import torch
    from magi import get_device

    device = get_device()
    # Full precision: half precision is about 20% faster, but IllustrationJaNai's numbers overflow on some images, which ruins them.
    model = load_pytorch_model(model_path).to(device)

    def upscale_tile(tile):
        with torch.no_grad():
            return model(torch.from_numpy(tile)[None].to(device))[0].cpu().numpy()

    return upscale_tile, device


def upscale_in_tiles(upscale_tile, image, scale, tile_size, fixed_tile_size):
    """
    Upscale "image" (channels, height, width, values from 0 to 1) one tile at a time. "fixed_tile_size" pads the tiles at the edges to "tile_size" (the Neural Engine only runs one size). Otherwise the tiles fit the image, so a small image is done in one go.
    """
    channels, height, width = image.shape
    result = numpy.zeros((channels, height * scale, width * scale), dtype=numpy.float32)
    step = tile_size - 2 * TILE_OVERLAP if fixed_tile_size else tile_size

    def get_tile_start(start, length):
        # A full tile that starts a little before "start", pulled back so it doesn't go past the image's edge.
        return max(min(start - TILE_OVERLAP, length - tile_size), 0)

    def reaches_edge(start, length):
        # A full tile that reaches the image's edge keeps everything up to it: there's no tile after it to cover its edge. Without this, the next tile was the same one again, upscaled only for its last few pixels.
        return fixed_tile_size and get_tile_start(start, length) + tile_size >= length

    for y in range(0, height, step):
        if y > 0 and reaches_edge(y - step, height):
            break
        for x in range(0, width, step):
            if x > 0 and reaches_edge(x - step, width):
                break
            if fixed_tile_size:
                tile_y, tile_x = get_tile_start(y, height), get_tile_start(x, width)
                tile = image[
                    :, tile_y : tile_y + tile_size, tile_x : tile_x + tile_size
                ]
                tile = numpy.pad(
                    tile,
                    (
                        (0, 0),
                        (0, tile_size - tile.shape[1]),
                        (0, tile_size - tile.shape[2]),
                    ),
                    mode="edge",
                )
            else:
                tile_y, tile_x = max(y - TILE_OVERLAP, 0), max(x - TILE_OVERLAP, 0)
                tile = image[
                    :,
                    tile_y : min(y + step + TILE_OVERLAP, height),
                    tile_x : min(x + step + TILE_OVERLAP, width),
                ]

            end_y = height if reaches_edge(y, height) else min(y + step, height)
            end_x = width if reaches_edge(x, width) else min(x + step, width)
            upscaled_tile = upscale_tile(numpy.ascontiguousarray(tile))
            # Only the middle of each tile is kept. Its edges are covered by the tiles next to it.
            result[:, y * scale : end_y * scale, x * scale : end_x * scale] = (
                upscaled_tile[
                    :,
                    (y - tile_y) * scale : (end_y - tile_y) * scale,
                    (x - tile_x) * scale : (end_x - tile_x) * scale,
                ]
            )

    return result


def get_upscaler(model_path, use_neural_engine, report=print):
    """
    "upscale(image)" for a model, loaded once and then reused. Core ML when it's available, or else PyTorch. Where it runs is shown in the Status view.
    """
    from gui_classes.ProgressPanel import report_progress

    key = (model_path, use_neural_engine)
    if key not in _loaded_upscalers:
        _loaded_upscalers[key] = load_upscaler(model_path, use_neural_engine, report)

    upscale, device_name = _loaded_upscalers[key]
    report_progress(device=device_name)
    return upscale


def load_upscaler(model_path, use_neural_engine, report=print):
    """
    "upscale(image)" for a model, and the name of what it runs on. Core ML when it's available, or else PyTorch. Getting it ready is a step of its own in the Status view (two the first time on a Mac: it's converted for Core ML).
    """
    from gui_classes.ProgressPanel import PYTORCH_LOAD_DETAIL, show_extra_stage
    from magi import get_device_name, get_mac_chip_name

    name = get_upscaler_name(model_path)
    if can_use_coreml():
        try:
            upscale_tile = get_coreml_upscale_function(
                model_path, use_neural_engine, name, report
            )
            # Core ML runs on the Mac's chip (its GPU and Neural Engine).
            return (
                lambda image: upscale_in_tiles(
                    upscale_tile, image, 2, COREML_TILE, fixed_tile_size=True
                ),
                get_mac_chip_name(),
            )
        except Exception as error:
            report(
                f"Couldn't use Core ML for the upscale model ({error}). Using PyTorch instead (slower)."
            )

    import torch

    # About 1.5 seconds for IllustrationJaNai on an M1, each time the app is opened.
    with show_extra_stage(get_load_step(name, "PyTorch"), PYTORCH_LOAD_DETAIL):
        upscale_tile, device = get_pytorch_upscale_function(model_path)
    # With AMD's PyTorch (ROCm, "hip"), every tile is the same size: AMD's GPU software works out how to run each new image size the first time it sees it (slow), and comic panels are all different sizes, so tiles that fit each panel were about 2x slower there. Elsewhere (NVIDIA, the CPU), padding small images to a full tile would only add work.
    fixed_tile_size = torch.version.hip is not None
    return (
        lambda image: upscale_in_tiles(
            upscale_tile, image, 2, PYTORCH_TILE, fixed_tile_size
        ),
        get_device_name(device),
    )


def get_8_bit_rgb_image(image):
    """
    The image as 8-bit RGB, which the models take.
    """
    # 16-bit grayscale scans: "convert" would cut every value above 255 to white.
    if image.mode in ("I", "I;16", "I;16B", "I;16L"):
        gray = numpy.asarray(image, dtype=numpy.float32)
        # Some 32-bit images only hold 0-255.
        if gray.max() > 255:
            gray = gray / 257
        gray = gray.clip(0, 255).round().astype(numpy.uint8)
        return Image.fromarray(gray).convert("RGB")
    # Transparent parts become white, like a page (they'd turn black).
    if image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info:
        image = image.convert("RGBA")
        return Image.alpha_composite(
            Image.new("RGBA", image.size, "white"), image
        ).convert("RGB")
    return image.convert("RGB")


# The Status view's steps for getting a model ready. The same names are listed ahead ("get_steps_to_get_ready") and ticked off as they run, so they're made in one place.
def get_download_step(zip_url):
    # "One time only" on every download, so a slow first run isn't taken for a slow app.
    return f"Downloading {get_model_name(zip_url)} (one time only)"


def get_convert_step(name):
    return f"Converting {name} for Core ML (one time only)"


def get_load_step(name, engine):
    return f"Loading {name} into {engine}"


def get_upscaler_name(model_path):
    """
    The name of a model in the Status view: "IllustrationJaNai", or "MangaJaNai 1600p" (there are 7, one for each page height, and a 4x upscale can use two).
    """
    file_name = os.path.basename(model_path)
    if file_name == COLOR_MODEL_FILE:
        return "IllustrationJaNai"
    height = next(
        (height for height, name in MANGA_MODEL_FILES.items() if name == file_name),
        None,
    )
    return f"MangaJaNai {height}p" if height else "MangaJaNai"


def get_steps_to_get_ready(model_path, zip_url, use_neural_engine):
    """
    The Status view's steps a model still needs before it can upscale, in order, from what's on the disk and in memory: downloading it, converting it for Core ML (on an Apple Silicon Mac, the first time) and loading it. None when it's ready.
    """
    name = get_upscaler_name(model_path)
    steps = []
    if not os.path.exists(model_path):
        steps.append(get_download_step(zip_url))
    if (model_path, use_neural_engine) in _loaded_upscalers:
        return steps
    if can_use_coreml():
        if not os.path.exists(
            f"{os.path.splitext(model_path)[0]}-{COREML_TILE}.mlpackage"
        ):
            steps.append(get_convert_step(name))
        steps.append(get_load_step(name, "Core ML"))
    else:
        steps.append(get_load_step(name, "PyTorch"))
    return steps


def upscale_image_with_janai(input_image, output_image, upscale_ratio, report=print):
    """
    Upscale one image by "upscale_ratio" (2, 4, 8, ...: the models make images 2x bigger, so 4x is two times 2x) with MangaJaNai, or IllustrationJaNai for a color image. Saved in the format of "output_image"'s extension.
    """
    from gui_classes.ProgressPanel import show_upcoming_stages

    with Image.open(input_image) as image:
        page_height = get_page_height(image)
        rgb_image = get_8_bit_rgb_image(image)
        is_color = is_color_image(rgb_image)
        array = numpy.asarray(rgb_image, dtype=numpy.float32).transpose(2, 0, 1) / 255

    # The model for each 2x pass: IllustrationJaNai for color, or the MangaJaNai for the page's height (it's twice as tall after each pass). On the Neural Engine for MangaJaNai only (Apple's compiler gets stuck on IllustrationJaNai).
    passes = [
        (COLOR_MODEL_FILE, COLOR_MODEL_ZIP_URL, False)
        if is_color
        else (
            MANGA_MODEL_FILES[get_manga_model_height(page_height * 2**upscale_pass)],
            MANGA_MODELS_ZIP_URL,
            True,
        )
        for upscale_pass in range(int(math.log2(int(upscale_ratio))))
    ]
    # Everything the models still need is listed in the Status view before the first step starts.
    show_upcoming_stages(
        step
        for model_file, zip_url, use_neural_engine in passes
        for step in get_steps_to_get_ready(
            os.path.join(MODELS_FOLDER, model_file), zip_url, use_neural_engine
        )
    )

    for model_file, zip_url, use_neural_engine in passes:
        model_path = download_model_file(model_file, zip_url, report)
        upscale = get_upscaler(model_path, use_neural_engine, report=report)
        array = numpy.clip(upscale(array), 0, 1)

    result = Image.fromarray(
        (array.transpose(1, 2, 0) * 255).round().astype(numpy.uint8)
    )
    # Black and white stays black and white (and the file is about 3x smaller).
    if not is_color:
        result = result.convert("L")

    save_options: dict = (
        {"quality": 95}
        if output_image.lower().endswith((".jpg", ".jpeg", ".webp"))
        else {}
    )
    result.save(output_image, **save_options)
