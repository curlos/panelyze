from PIL import Image
import numpy
from transformers import AutoModel
import torch

model = AutoModel.from_pretrained("ragavsachdeva/magiv2", trust_remote_code=True).cuda().eval()

print(model)

# def read_image(path_to_image):
#     with open(path_to_image, "rb") as file:
#         # Converts the image to grayscale (most manga are black and white) and I'm guessing this is necessary for the AI to properly detect the different panels, characters, and text.
#         image = Image.open(file).convert("L").convert("RGB")
#         image = numpy.array(image)
#     return image

# chapter_pages = ["goku-vs-vegeta.jpg"]
# character_bank = {
#     "images": [],
#     "names": []
# }

# chapter_pages = [read_image(x) for x in chapter_pages]
# character_bank["images"] = [read_image(x) for x in character_bank["images"]]

# print(chapter_pages)

# with torch.no_grad():
#     per_page_results = model.do_chapter_wide_prediction(chapter_pages, character_bank, use_tqdm=True, do_ocr=True)

# transcript = []
# for i, (image, page_result) in enumerate(zip(chapter_pages, per_page_results)):
#     model.visualise_single_image_prediction(image, page_result, f"page_{i}.png")
#     speaker_name = {
#         text_idx: page_result["character_names"][char_idx] for text_idx, char_idx in page_result["text_character_associations"]
#     }
#     for j in range(len(page_result["ocr"])):
#         if not page_result["is_essential_text"][j]:
#             continue
#         name = speaker_name.get(j, "unsure") 
#         transcript.append(f"<{name}>: {page_result['ocr'][j]}")
# with open(f"transcript.txt", "w") as fh:
#     for line in transcript:
#         fh.write(line + "\n")