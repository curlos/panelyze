#!/bin/bash
# Running from source on a Mac, Flet draws the window with its own app, which the Dock shows as "Flet" with Flet's icon. This makes a copy named "Panelyze", with the Panelyze icon, and prints its folder for Flet's "FLET_VIEW_PATH" ("npm run run" and "npm run dev" use it, see package.json). The packaged app has its own copy (see build_mac_app.sh).
#
# It's made once for each Flet version, in ~/Library/Application Support/Panelyze/dev-window, and shared by every worktree. Delete that folder to make it again (e.g. after the icon changes). It keeps Flet's bundle ID, so the app's saved settings stay the same.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$REPO_DIR/venv/bin/python"
FLET_VERSION="$("$PYTHON" -c 'import flet_desktop.version; print(flet_desktop.version.version)')"
# The tests make it in a temporary folder instead.
WINDOW_DIR="${PANELYZE_DEV_WINDOW_DIR:-$HOME/Library/Application Support/Panelyze/dev-window}/flet-$FLET_VERSION"

if [ ! -d "$WINDOW_DIR/Panelyze.app" ]; then
    # Made next to its final folder, then moved in at once, so a run started at the same time (e.g. in another worktree) never sees a half-made copy. Cleaned up if anything fails.
    mkdir -p "$(dirname "$WINDOW_DIR")"
    TEMP_DIR="$(mktemp -d "$(dirname "$WINDOW_DIR")/tmp.XXXXXX")"
    trap 'rm -rf "$TEMP_DIR"' EXIT
    tar -xzf "$("$PYTHON" -c 'import flet_desktop, os; print(os.path.join(os.path.dirname(flet_desktop.__file__), "app", "flet-macos.tar.gz"))')" -C "$TEMP_DIR"
    APP="$TEMP_DIR/Flet.app"

    # The icon, made from the same image as the packaged app's (see build_mac_app.sh). Plain sips, iconutil and plutil: flet_cli's rename functions (used by build_mac_app.sh) need PyInstaller, which the dev venv doesn't have.
    ICONSET_DIR="$TEMP_DIR/Panelyze.iconset"
    mkdir -p "$ICONSET_DIR"
    for size in 16 32 128 256 512; do
        sips -z "$size" "$size" "$REPO_DIR/assets/panelyze-icon.png" --out "$ICONSET_DIR/icon_${size}x${size}.png" > /dev/null
        double_size=$((size * 2))
        sips -z "$double_size" "$double_size" "$REPO_DIR/assets/panelyze-icon.png" --out "$ICONSET_DIR/icon_${size}x${size}@2x.png" > /dev/null
    done
    iconutil -c icns "$ICONSET_DIR" -o "$APP/Contents/Resources/AppIcon.icns"
    rm -rf "$ICONSET_DIR"

    plutil -replace CFBundleName -string Panelyze "$APP/Contents/Info.plist"
    plutil -replace CFBundleDisplayName -string Panelyze "$APP/Contents/Info.plist"
    plutil -replace CFBundleIconFile -string AppIcon "$APP/Contents/Info.plist"
    # Without this, macOS shows the icon built into the app (Flet's) instead of AppIcon.icns.
    plutil -remove CFBundleIconName "$APP/Contents/Info.plist" 2> /dev/null || true
    mv "$APP" "$TEMP_DIR/Panelyze.app"
    codesign --force --deep --sign - "$TEMP_DIR/Panelyze.app" 2> /dev/null || {
        echo "make_dev_window_app.sh: couldn't sign the window app" >&2
        exit 1
    }

    # Another run may have finished first: then its copy is kept.
    [ -e "$WINDOW_DIR" ] || mv "$TEMP_DIR" "$WINDOW_DIR"
fi

echo "$WINDOW_DIR"
