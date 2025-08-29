# Downloads Pokemon card images from URLs and saves them with numbered prefixes.
import os
import requests
from urllib.parse import urlparse
from pathlib import Path
from full_art_image_urls import full_art_image_urls
from google_sheet_pokemon_card_image_url_objects import (
    google_sheet_pokemon_card_image_url_objects,
)


def download_images(image_objects, output_dir="images"):
    """
    Downloads images from a list of dicts with 'name' and 'imageUrl'.

    Parameters:
    - image_objects (list): List of dicts, each with 'name' and 'imageUrl'
    - output_dir (str): Directory where images will be saved
    """
    os.makedirs(output_dir, exist_ok=True)

    for i, item in enumerate(image_objects):
        try:
            name = item["name"].replace(" ", "_")
            url = item["imageUrl"]

            # Get image extension safely
            path = urlparse(url).path
            ext = Path(path).suffix or ".jpg"

            # Pad index to 3 digits
            num_label = f"{i+1:03}"
            filename = f"{num_label}_{name}{ext}"
            file_path = os.path.join(output_dir, filename)

            print(f"Downloading {url} → {filename}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            with open(file_path, "wb") as f:
                f.write(response.content)

        except Exception as e:
            print(f"❌ Failed to download {item.get('imageUrl')}: {e}")


# Example usage
if __name__ == "__main__":
    print("Hi!")

    full_art_image_url_objects = full_art_image_urls
    full_art_image_url_output = "full_art_pokemon_cards"

    google_sheets_image_url_objects = full_art_image_urls
    google_sheets_image_url_output = "full_art_pokemon_cards"

    google_sheet_image_url_objects = google_sheet_pokemon_card_image_url_objects
    google_sheet_image_url_output = "google_sheet_pokemon_cards_full_size"

    # download_images(full_art_image_url_objects, full_art_image_url_output)
    download_images(google_sheet_image_url_objects, google_sheet_image_url_output)
