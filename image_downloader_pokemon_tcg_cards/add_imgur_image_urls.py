import json
from imgur_image_urls_full_art_pokemon_cards import (
    imgur_image_urls_full_art_pokemon_cards,
)
from full_art_image_urls import full_art_image_urls

# Merge and rename
for i in range(
    min(len(full_art_image_urls), len(imgur_image_urls_full_art_pokemon_cards))
):
    entry = full_art_image_urls[i]
    entry["originalImageUrl"] = entry.pop("imageUrl")
    entry["imgurImageUrl"] = imgur_image_urls_full_art_pokemon_cards[i]

# Write to JSON file
with open("merged_images.json", "w", encoding="utf-8") as f:
    json.dump(full_art_image_urls, f, ensure_ascii=False, indent=4)

print("✅ JSON file saved as 'merged_images.json'")
