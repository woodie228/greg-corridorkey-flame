#!/bin/bash
set -euo pipefail

SHARED_ROOT="/Users/Shared/GregCorridorKey"
CONFIG_DIR="$SHARED_ROOT/config"
CONFIG_FILE="$CONFIG_DIR/corridorkey_root.txt"
TARGET="${1:-$SHARED_ROOT/EZ-CorridorKey}"
REPO_URL="${GREG_CORRIDORKEY_REPO_URL:-https://github.com/edenaion/EZ-CorridorKey.git}"

if [ "$(uname -s)" != "Darwin" ]; then
    echo "This helper is for macOS."
    exit 1
fi

if [ "$(uname -m)" != "arm64" ]; then
    echo "This helper is intended for Apple Silicon Macs."
    echo "Current architecture: $(uname -m)"
    exit 1
fi

mkdir -p "$SHARED_ROOT" "$CONFIG_DIR"

if [ ! -d "$TARGET/.git" ]; then
    if [ -d "$TARGET" ] && [ "$(find "$TARGET" -mindepth 1 -maxdepth 1 | wc -l | tr -d ' ')" != "0" ]; then
        echo "$TARGET exists and is not empty."
        echo "Move it aside or pass a different install folder as the first argument."
        exit 1
    fi

    echo "[1/4] Cloning EZ-CorridorKey..."
    rm -rf "$TARGET"
    git clone "$REPO_URL" "$TARGET"
else
    echo "[1/4] Updating EZ-CorridorKey..."
    git -C "$TARGET" pull --ff-only
fi

cd "$TARGET"

echo "[2/4] Running EZ-CorridorKey installer..."
chmod +x ./1-install.sh
CORRIDORKEY_INSTALL_SAM2="${CORRIDORKEY_INSTALL_SAM2:-y}" \
CORRIDORKEY_PREDOWNLOAD_SAM2="${CORRIDORKEY_PREDOWNLOAD_SAM2:-y}" \
CORRIDORKEY_INSTALL_FFMPEG="${CORRIDORKEY_INSTALL_FFMPEG:-n}" \
CORRIDORKEY_INSTALL_GVM="${CORRIDORKEY_INSTALL_GVM:-y}" \
CORRIDORKEY_INSTALL_VIDEOMAMA="${CORRIDORKEY_INSTALL_VIDEOMAMA:-y}" \
CORRIDORKEY_CREATE_SHORTCUT="${CORRIDORKEY_CREATE_SHORTCUT:-n}" \
./1-install.sh

echo "[3/4] Downloading optional model weights for Flame users..."
if [ -f ".venv/bin/python" ] && [ -f "scripts/setup_models.py" ]; then
    .venv/bin/python scripts/setup_models.py \
        --corridorkey-blue \
        --corridorkey-mlx \
        --birefnet \
        --matanyone2 \
        --sam2 base-plus \
        --gvm \
        --videomama || true
fi

echo "[4/4] Writing Greg Flame config..."
printf "%s\n" "$TARGET" > "$CONFIG_FILE"

echo ""
echo "Done."
echo "CorridorKey root:"
cat "$CONFIG_FILE"
echo ""
echo "In Flame, run Rescan Python Hooks or restart Flame."
