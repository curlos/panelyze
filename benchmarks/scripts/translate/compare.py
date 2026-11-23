# Side-by-side comparison image. Args: out.jpg label=path label=path ...
import sys
from PIL import Image, ImageDraw, ImageFont
height, label_height, gap = 1300, 50, 16
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
except OSError:
    # Not a Mac (e.g. the Windows PC).
    font = ImageFont.load_default(size=30)
columns = []
for arg in sys.argv[2:]:
    label, path = arg.split("=", 1)
    image = Image.open(path).convert("RGB")
    columns.append((label, image.resize((round(image.width * height / image.height), height), Image.LANCZOS)))
sheet = Image.new("RGB", (sum(i.width for _, i in columns) + gap * (len(columns) - 1), height + label_height), "white")
draw, x = ImageDraw.Draw(sheet), 0
for label, image in columns:
    draw.text((x + 4, 8), label, fill=(20, 60, 140), font=font)
    sheet.paste(image, (x, label_height))
    x += image.width + gap
sheet.save(sys.argv[1], quality=90)
