"""
Makes a sample of every kind of input Panelyze can take, so each one can be tested without real comics: a comic file in every format, loose images in every image format, folders (a series with chapters, one chapter, pages named so that page_10 comes after page_2, one with no images) and files that are broken on purpose.

The tests use it in a temporary folder (see "tests/test_every_input.py"). To try the same inputs by hand in the app, run this from the repo:

    ./venv/bin/python tests/make_test_inputs.py [a folder of real pages to use instead of the numbered ones]

They're saved in "~/Documents/Panelyze/<repo folder>/test-inputs/" (the repo's own folder, like everything else made while developing).
"""

import io
import os
import re
import sys
import zipfile

from PIL import Image, ImageDraw, ImageFont

PAGE_SIZE = (800, 1200)
PAGE_COUNT = 5
# One color per page, far apart, so a test can tell which page an image is from its corner.
PAGE_COLORS = [
    (200, 40, 40),
    (40, 160, 60),
    (40, 70, 200),
    (220, 180, 30),
    (150, 50, 170),
    (30, 170, 170),
]


def get_page_color(number):
    return PAGE_COLORS[(number - 1) % len(PAGE_COLORS)]


def make_page(number):
    """
    A page with its number in big letters on its own color.
    """
    page = Image.new("RGB", PAGE_SIZE, get_page_color(number))
    ImageDraw.Draw(page).text(
        (PAGE_SIZE[0] // 2, PAGE_SIZE[1] // 2),
        f"Page {number}",
        fill="white",
        font=ImageFont.load_default(size=120),
        anchor="mm",
    )
    return page


def load_real_pages(folder, count=PAGE_COUNT):
    """
    The first "count" images in a folder, in natural order (page_2 before page_10).
    """
    names = sorted(
        (
            name
            for name in os.listdir(folder)
            if name.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        ),
        key=lambda name: [
            int(part) if part.isdigit() else part for part in re.split(r"(\d+)", name)
        ],
    )
    return [
        Image.open(os.path.join(folder, name)).convert("RGB") for name in names[:count]
    ]


def get_image_bytes(page, image_format):
    image_bytes = io.BytesIO()
    page.save(image_bytes, image_format)
    return image_bytes.getvalue()


def make_cbz(path, pages):
    # A .cbz is a zip file of the pages, often with a ComicInfo.xml about the comic.
    with zipfile.ZipFile(path, "w") as comic_file:
        comic_file.writestr(
            "ComicInfo.xml", "<ComicInfo><Title>Sample</Title></ComicInfo>"
        )
        for number, page in enumerate(pages, start=1):
            comic_file.writestr(f"{number:03d}.png", get_image_bytes(page, "PNG"))


def make_zip(path, pages):
    # A plain zip with the pages in a folder, and a macOS metadata folder that must be left out.
    with zipfile.ZipFile(path, "w") as comic_file:
        for number, page in enumerate(pages, start=1):
            comic_file.writestr(
                f"pages/page {number}.png", get_image_bytes(page, "PNG")
            )
            comic_file.writestr(f"__MACOSX/pages/._page {number}.png", b"metadata")
        comic_file.writestr(".DS_Store", b"finder")


def make_epub(path, pages):
    # An .epub is a zip too: a book with a picture on each page.
    with zipfile.ZipFile(path, "w") as epub:
        epub.writestr(
            "mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED
        )
        epub.writestr(
            "META-INF/container.xml",
            '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
            '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
        )
        epub.writestr("OEBPS/content.opf", "<package/>")
        for number, page in enumerate(pages, start=1):
            epub.writestr(
                f"OEBPS/images/page_{number:03d}.jpg", get_image_bytes(page, "JPEG")
            )
            epub.writestr(
                f"OEBPS/page_{number:03d}.xhtml",
                f'<html><body><img src="images/page_{number:03d}.jpg"/></body></html>',
            )


def make_pdf(path, pages):
    pages[0].save(path, save_all=True, append_images=pages[1:])


def make_comic_files(folder, pages):
    os.makedirs(folder, exist_ok=True)
    paths = {
        name: os.path.join(folder, name)
        for name in (
            "sample.cbz",
            "sample.zip",
            "sample.epub",
            "sample.pdf",
            "sample.cbr",
        )
    }
    make_cbz(paths["sample.cbz"], pages)
    make_zip(paths["sample.zip"], pages)
    make_epub(paths["sample.epub"], pages)
    make_pdf(paths["sample.pdf"], pages)
    # Many .cbr files are really zip files (bsdtar opens those too). A real RAR file can't be made without the RAR program: tests/manual-test-links.md has one to download.
    make_cbz(paths["sample.cbr"], pages)
    return paths


def make_loose_images(folder, pages):
    """
    One image in each image format Panelyze accepts, to pick with "Pick Input Image(s)".
    """
    os.makedirs(folder, exist_ok=True)
    formats = [
        ("page_1.png", "PNG"),
        ("page_2.jpg", "JPEG"),
        ("page_3.jpeg", "JPEG"),
        ("page_4.webp", "WEBP"),
    ]
    paths = []
    for (name, image_format), page in zip(formats, pages):
        path = os.path.join(folder, name)
        page.save(path, image_format)
        paths.append(path)
    return paths


def save_pages(folder, pages, names):
    os.makedirs(folder, exist_ok=True)
    for name, page in zip(names, pages):
        page.save(os.path.join(folder, name))
    return folder


def make_folders(folder, pages):
    """
    The folders to pick with "Pick Input Folder".
    """
    folders = {}
    folders["one chapter"] = save_pages(
        os.path.join(folder, "one chapter"),
        pages[:4],
        [f"page_{number}.png" for number in range(1, 5)],
    )
    # A series: a folder with a folder for each chapter.
    series = os.path.join(folder, "series with 2 chapters")
    save_pages(
        os.path.join(series, "Ch 1"),
        pages[:3],
        [f"page_{number}.png" for number in range(1, 4)],
    )
    save_pages(
        os.path.join(series, "Ch 2"),
        pages[3:5],
        [f"page_{number}.png" for number in range(1, 3)],
    )
    folders["series with 2 chapters"] = series
    # page_10 has to come after page_2, not after page_1.
    folders["natural order"] = save_pages(
        os.path.join(folder, "natural order"),
        pages[:3],
        ["page_1.png", "page_2.png", "page_10.png"],
    )
    folders["no images"] = os.path.join(folder, "no images")
    os.makedirs(folders["no images"], exist_ok=True)
    with open(os.path.join(folders["no images"], "notes.txt"), "w") as notes_file:
        notes_file.write("There are no images in this folder.")
    return folders


def make_broken_files(folder):
    """
    Files that can't be used, to check the error messages.
    """
    os.makedirs(folder, exist_ok=True)
    broken = {
        "broken.cbz": os.path.join(folder, "broken.cbz"),
        "notes.txt": os.path.join(folder, "notes.txt"),
    }
    with open(broken["broken.cbz"], "wb") as broken_file:
        broken_file.write(b"This is not a zip file.")
    with open(broken["notes.txt"], "w") as notes_file:
        notes_file.write("Not a comic file.")
    return broken


def make_test_inputs(root, real_pages_folder=None):
    """
    Makes every sample input in "root" and returns where they are: {"comic files": {name: path}, "loose images": [paths], "folders": {name: path}, "broken": {name: path}}. With "real_pages_folder", its images are the pages (so Panel-By-Panel finds real panels) instead of the numbered ones.
    """
    pages = (
        load_real_pages(real_pages_folder, PAGE_COUNT)
        if real_pages_folder
        else [make_page(number) for number in range(1, PAGE_COUNT + 1)]
    )
    return {
        "comic files": make_comic_files(os.path.join(root, "1 comic files"), pages),
        "loose images": make_loose_images(os.path.join(root, "2 loose images"), pages),
        "folders": make_folders(os.path.join(root, "3 folders"), pages),
        "broken": make_broken_files(os.path.join(root, "4 broken files")),
    }


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    import default_settings

    root = os.path.join(
        default_settings.DEV_OUTPUT_FOLDER or default_settings.PANELYZE_FOLDER,
        "test-inputs",
    )
    inputs = make_test_inputs(root, sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"Saved the test inputs in {root}")
    for kind, items in inputs.items():
        for item in items.values() if isinstance(items, dict) else items:
            print(f"  {kind}: {os.path.relpath(item, root)}")
