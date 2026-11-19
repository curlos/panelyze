# Magi v2 model code

These 4 `.py` files are copied unchanged from the [Magi v2 model on Hugging Face](https://huggingface.co/ragavsachdeva/magiv2) by Ragav Sachdeva, at revision `fbc890fec52977142e8ee00bfe26e9458b65517c`. Keeping them here (instead of letting `transformers` download them with `trust_remote_code`) means the app never downloads code at run time and can be packaged into a standalone app.

- `panels_config.json`: Magi without its text reading (OCR) and character parts. Used by Panel-By-Panel with the small `panels_fp16.safetensors` weights file (87 MB). That file isn't in git; `magi.py` builds it from the full model the first time it's needed (see `build_panels_model_file`), and the Mac app build bundles it.
- `full_config.json`: the full Magi, used by Images To Video to read the text. Its weights (about 2 GB) are downloaded from Hugging Face the first time they're needed.

Magi's license: free for personal, research, non-commercial and not-for-profit use. See the model page for details.
