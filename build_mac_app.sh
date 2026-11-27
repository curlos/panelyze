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
# Another venv can be used with VENV_DIR=..., e.g. one installed from requirements-lock.txt when "venv" has newer packages.
VENV_DIR="${VENV_DIR:-$REPO_DIR/venv}"
PYTHON="$VENV_DIR/bin/python"
BUILD_ASSETS_DIR="$REPO_DIR/build-assets"
# "flet pack" deletes a "build" folder in whatever folder it runs from, so it runs from here instead of the repo.
PACK_DIR="$BUILD_ASSETS_DIR/pack"
DIST_DIR="$REPO_DIR/dist"
APP_PATH="$DIST_DIR/Panelyze.app"
WAIFU2X_VERSION="20250915"
# The version users see (Finder's "Get Info", and the GitHub release "v1.0.0").
APP_VERSION="1.0.0"
WAIFU2X_DIR="$BUILD_ASSETS_DIR/waifu2x"

if [ ! -x "$PYTHON" ]; then
    echo "ERROR: No virtual environment found at $VENV_DIR. Set it up first (see the README)."
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

# 3. App icon: macOS needs an ".icns" file made from the same image at several sizes. "assets/panelyze-icon.png" is "assets/panelyze-icon.svg" at 1024 px, with the tile at 824 px in the middle (Apple's icon grid), so it's the same size as other apps' icons in the Dock.
ICONSET_DIR="$BUILD_ASSETS_DIR/Panelyze.iconset"
rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"
for size in 16 32 128 256 512; do
    sips -z "$size" "$size" "$REPO_DIR/assets/panelyze-icon.png" --out "$ICONSET_DIR/icon_${size}x${size}.png" > /dev/null
    double_size=$((size * 2))
    sips -z "$double_size" "$double_size" "$REPO_DIR/assets/panelyze-icon.png" --out "$ICONSET_DIR/icon_${size}x${size}@2x.png" > /dev/null
done
iconutil -c icns "$ICONSET_DIR" -o "$BUILD_ASSETS_DIR/Panelyze.icns"

# 4. Package. "flet_web" (only used to run the app in a browser while developing) is left out of the app.
# "--onedir" (passed through to PyInstaller) makes a normal app folder, which opens much faster than a single file that has to unpack itself (torch alone is hundreds of MB) every time it's opened.
rm -rf "$PACK_DIR" "$APP_PATH"
mkdir -p "$PACK_DIR"
(
    cd "$PACK_DIR"
    "$VENV_DIR/bin/flet" pack "$REPO_DIR/gui.py" \
        --name Panelyze \
        --icon "$BUILD_ASSETS_DIR/Panelyze.icns" \
        --bundle-id com.curlos.panelyze \
        --product-name Panelyze \
        --product-version "$APP_VERSION" \
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
# Flet draws the window with a separate app ("Flet", with Flet's icon), so the Dock showed two icons: Panelyze and Flet. "flet pack" should rename it, but Flet 0.25.2 skips that (it looks for "flet-macos-amd64.tar.gz", which is now "flet-macos.tar.gz"). So a copy renamed "Panelyze", with the Panelyze icon, goes in "Contents/Resources/window" (gui.py tells Flet to use it, see "get_mac_window_app_folder" in utils.py), using flet_cli's own rename functions.
WINDOW_DIR="$APP_PATH/Contents/Resources/window"
mkdir -p "$WINDOW_DIR"
tar -xzf "$APP_PATH/Contents/Resources/flet_desktop/app/flet-macos.tar.gz" -C "$WINDOW_DIR"
# Flet only unpacks this archive when "FLET_VIEW_PATH" isn't set, so it's not needed anymore (47 MB).
rm "$APP_PATH/Contents/Resources/flet_desktop/app/flet-macos.tar.gz"
"$PYTHON" -c 'import sys; from flet_cli.__pyinstaller.macos_utils import update_flet_view_icon, update_flet_view_version_info; update_flet_view_icon(sys.argv[1], sys.argv[2]); update_flet_view_version_info(sys.argv[1], "com.curlos.panelyze.window", "Panelyze", sys.argv[3], None)' \
    "$WINDOW_DIR/Flet.app" "$BUILD_ASSETS_DIR/Panelyze.icns" "$APP_VERSION"
WINDOW_APP="$WINDOW_DIR/Panelyze.app"
# Panelyze starts the window with arguments (its address). Opened without any (or only with the "-psn_..." one macOS can add), e.g. from a pinned Dock icon, the window would have no app behind it and stay empty, so the whole app is opened instead (it's 6 folders up).
cat > "$WINDOW_APP/Contents/MacOS/start-window" << 'EOF'
#!/bin/bash
if [ $# -eq 0 ] || [[ "$1" == -psn_* ]]; then
    exec open "$(dirname "$0")/../../../../../.."
fi
exec "$(dirname "$0")/Flet" "$@"
EOF
chmod +x "$WINDOW_APP/Contents/MacOS/start-window"
plutil -replace CFBundleExecutable -string start-window "$WINDOW_APP/Contents/Info.plist"
codesign --force --deep --sign - "$WINDOW_APP"
# The app itself (Python, with no window of its own) gets no Dock icon, so the Dock shows only the window's one.
plutil -replace LSUIElement -bool true "$APP_PATH/Contents/Info.plist"

# "--product-version" doesn't reach the Mac app's Info.plist (it says 0.0.0), so it's set here. Changing Info.plist breaks the app's ad-hoc signature, so it's signed again.
plutil -replace CFBundleShortVersionString -string "$APP_VERSION" "$APP_PATH/Contents/Info.plist"
codesign --force --deep --sign - "$APP_PATH"

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
