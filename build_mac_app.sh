#!/bin/bash
# Builds the standalone "Panelyze.app" (and a zip of it to upload to GitHub Releases), so users can download it and double-click it. They don't need Python, a terminal or anything else.
#
# This is for developers only. Run it from the repo with the venv set up (see the README):
#   ./build_mac_app.sh
#
# What it does:
#   1. Downloads waifu2x (the image upscaler) to bundle it with the app.
#   2. Builds the small panels-only Magi model if it hasn't been built yet.
#   3. Packages everything with "flet pack" (PyInstaller) into dist/Panelyze.app.
#   4. Runs the app's self-test ("--self-test") on the built app, and only zips it if everything works.
#
# The app only runs on Apple Silicon Macs (it's built on one).

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$REPO_DIR/venv/bin/python"
BUILD_ASSETS_DIR="$REPO_DIR/build-assets"
# "flet pack" deletes a "build" folder in whatever folder it runs from, so it runs from here instead of the repo.
PACK_DIR="$BUILD_ASSETS_DIR/pack"
DIST_DIR="$REPO_DIR/dist"
APP_PATH="$DIST_DIR/Panelyze.app"
WAIFU2X_VERSION="20250915"
WAIFU2X_DIR="$BUILD_ASSETS_DIR/waifu2x"

if [ ! -x "$PYTHON" ]; then
    echo "ERROR: No virtual environment found at $REPO_DIR/venv. Set it up first (see the README)."
    exit 1
fi

# PyInstaller is only needed to build the app, so it's not in requirements.txt.
if ! "$PYTHON" -c "import PyInstaller" 2>/dev/null; then
    echo "Installing PyInstaller (only needed for building)..."
    if command -v uv > /dev/null; then
        uv pip install --python "$PYTHON" "pyinstaller==6.11.1"
    else
        "$PYTHON" -m pip install "pyinstaller==6.11.1"
    fi
fi

mkdir -p "$BUILD_ASSETS_DIR"

# 1. waifu2x: only the program and the two models the app uses (the default fast one and the best-quality one).
if [ ! -x "$WAIFU2X_DIR/waifu2x-ncnn-vulkan" ] || [ ! -d "$WAIFU2X_DIR/models-upconv_7_anime_style_art_rgb" ]; then
    echo "Downloading waifu2x $WAIFU2X_VERSION..."
    DOWNLOAD_DIR="$(mktemp -d)"
    curl -L --fail -o "$DOWNLOAD_DIR/waifu2x.zip" "https://github.com/nihui/waifu2x-ncnn-vulkan/releases/download/$WAIFU2X_VERSION/waifu2x-ncnn-vulkan-$WAIFU2X_VERSION-macos.zip"
    unzip -q "$DOWNLOAD_DIR/waifu2x.zip" -d "$DOWNLOAD_DIR"
    rm -rf "$WAIFU2X_DIR"
    mkdir -p "$WAIFU2X_DIR"
    cp "$DOWNLOAD_DIR/waifu2x-ncnn-vulkan-$WAIFU2X_VERSION-macos/waifu2x-ncnn-vulkan" "$WAIFU2X_DIR/"
    cp -R "$DOWNLOAD_DIR/waifu2x-ncnn-vulkan-$WAIFU2X_VERSION-macos/models-cunet" "$WAIFU2X_DIR/"
    cp -R "$DOWNLOAD_DIR/waifu2x-ncnn-vulkan-$WAIFU2X_VERSION-macos/models-upconv_7_anime_style_art_rgb" "$WAIFU2X_DIR/"
    cp "$DOWNLOAD_DIR/waifu2x-ncnn-vulkan-$WAIFU2X_VERSION-macos/LICENSE" "$WAIFU2X_DIR/"
    rm -rf "$DOWNLOAD_DIR"
fi

# 2. The small panels-only Magi model (built from the full model the first time; this downloads about 2 GB once).
(cd "$REPO_DIR" && "$PYTHON" -c "import magi, os; os.path.exists(magi.PANELS_MODEL_FILE) or magi.build_panels_model_file()")

# 3. App icon: macOS needs an ".icns" file made from the same image at several sizes.
ICONSET_DIR="$BUILD_ASSETS_DIR/Panelyze.iconset"
rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"
for size in 16 32 128 256 512; do
    sips -z "$size" "$size" "$REPO_DIR/assets/no-face.png" --out "$ICONSET_DIR/icon_${size}x${size}.png" > /dev/null
    double_size=$((size * 2))
    sips -z "$double_size" "$double_size" "$REPO_DIR/assets/no-face.png" --out "$ICONSET_DIR/icon_${size}x${size}@2x.png" > /dev/null
done
iconutil -c icns "$ICONSET_DIR" -o "$BUILD_ASSETS_DIR/Panelyze.icns"

# 4. Package. "flet_web" (only used to run the app in a browser while developing) is left out of the app.
# "--onedir" (passed through to PyInstaller) makes a normal app folder, which opens much faster than a single file that has to unpack itself (torch alone is hundreds of MB) every time it's opened.
rm -rf "$PACK_DIR" "$APP_PATH"
mkdir -p "$PACK_DIR"
(
    cd "$PACK_DIR"
    "$REPO_DIR/venv/bin/flet" pack "$REPO_DIR/gui.py" \
        --name Panelyze \
        --icon "$BUILD_ASSETS_DIR/Panelyze.icns" \
        --bundle-id com.curlos.panelyze \
        --product-name Panelyze \
        --product-version 1.0.0 \
        --distpath "$DIST_DIR" \
        --add-data "$REPO_DIR/magi_model:magi_model" \
        --add-data "$WAIFU2X_DIR:waifu2x" \
        --pyinstaller-build-args=--onedir \
        "--pyinstaller-build-args=--workpath=$PACK_DIR/work" \
        "--pyinstaller-build-args=--specpath=$PACK_DIR" \
        "--pyinstaller-build-args=--paths=$REPO_DIR" \
        "--pyinstaller-build-args=--paths=$REPO_DIR/comix_downloader" \
        --pyinstaller-build-args=--collect-submodules=src \
        --pyinstaller-build-args=--collect-all=nodriver \
        --pyinstaller-build-args=--collect-all=pypdfium2 \
        --pyinstaller-build-args=--collect-all=pypdfium2_raw \
        --pyinstaller-build-args=--collect-data=spellchecker \
        --pyinstaller-build-args=--collect-all=transformers \
        --pyinstaller-build-args=--collect-all=timm \
        --pyinstaller-build-args=--collect-all=pulp \
        --pyinstaller-build-args=--collect-all=imageio_ffmpeg \
        --pyinstaller-build-args=--collect-all=azure.cognitiveservices.speech \
        --pyinstaller-build-args=--collect-all=mangadex_downloader \
        --pyinstaller-build-args=--collect-all=edge_tts \
        --pyinstaller-build-args=--collect-all=spandrel \
        --pyinstaller-build-args=--collect-all=coremltools \
        --pyinstaller-build-args=--hidden-import=magi_model.modelling_magiv2 \
        --pyinstaller-build-args=--exclude-module=flet_web \
        --yes
)

# 5. Check the built app really works before sharing it.
echo "Running the self-test on the built app (it's stopped if it takes longer than 10 minutes)..."
# macOS has no "timeout" command, so Perl's "alarm" is used to stop it.
if ! perl -e 'alarm 600; exec @ARGV' "$APP_PATH/Contents/MacOS/Panelyze" --self-test; then
    echo "ERROR: The built app failed its self-test:"
    cat "$HOME/Library/Logs/Panelyze/self-test.log"
    exit 1
fi
cat "$HOME/Library/Logs/Panelyze/self-test.log"

# 6. Zip it for GitHub Releases ("ditto" keeps the app's macOS file details intact).
ZIP_PATH="$DIST_DIR/Panelyze-macOS-AppleSilicon.zip"
rm -f "$ZIP_PATH"
ditto -c -k --keepParent "$APP_PATH" "$ZIP_PATH"

echo ""
echo "Built: $APP_PATH ($(du -sh "$APP_PATH" | cut -f1))"
echo "Zip to upload to GitHub Releases: $ZIP_PATH ($(du -sh "$ZIP_PATH" | cut -f1))"
