from pathlib import Path

from google_sheet_pokemon_card_image_url_objects import (
    google_sheet_pokemon_card_image_url_objects,
)

# Clean objects
for obj in google_sheet_pokemon_card_image_url_objects:
    if obj["name"].endswith(".thumb"):
        obj["name"] = obj["name"].replace(".thumb", "")
    if ".thumb" in obj["imageUrl"]:
        obj["imageUrl"] = obj["imageUrl"].replace(".thumb", "")

# Write cleaned data to new Python file
output_file = Path("pokemon_cards_cleaned.py")

with output_file.open("w", encoding="utf-8") as f:
    f.write("pokemon_cards_cleaned = [\n")
    for obj in google_sheet_pokemon_card_image_url_objects:
        f.write(f'    {{"name": "{obj["name"]}", "imageUrl": "{obj["imageUrl"]}"}},\n')
    f.write("]\n")

print(f"✅ Cleaned data written to {output_file}")
