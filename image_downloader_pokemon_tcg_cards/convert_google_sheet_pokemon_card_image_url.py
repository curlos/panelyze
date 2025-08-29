# Converts Pokemon card URLs from Google Sheets into structured Python objects
from pathlib import Path
from google_sheet_pokemon_card_image_urls import google_sheet_pokemon_card_image_urls

# Transform into array of objects
transformed = []

for url in google_sheet_pokemon_card_image_urls:
    filename = Path(url).name  # e.g. Flareon-V.SWSH.179.40962.png
    name = Path(filename).stem  # remove .png → Flareon-V.SWSH.179.40962
    transformed.append({"name": name, "url": url})

# Write to a new Python file
output_file = "google_sheet_pokemon_card_image_url_objects.py"
with open(output_file, "w", encoding="utf-8") as f:
    f.write("google_sheet_pokemon_card_image_url_objects = [\n")
    for obj in transformed:
        f.write(f'    {{"name": "{obj["name"]}", "imageUrl": "{obj["url"]}"}},\n')
    f.write("]\n")

print(f"✅ Wrote {len(transformed)} cards to {output_file}")
