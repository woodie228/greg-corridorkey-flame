#!/bin/bash
set -euo pipefail
export COPYFILE_DISABLE=1

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${1:-0.1.0}"
IDENTIFIER="com.greg.flame.corridorkey"
PKG_NAME="GregCorridorKeyFlame"
BUILD_DIR="$ROOT/dist/pkgbuild/$PKG_NAME"
PAYLOAD="$BUILD_DIR/payload"
OUT_DIR="$ROOT/dist/installers"
APP_ROOT="$PAYLOAD/Library/Application Support/Greg/CorridorKeyFlame"

HOOK_SRC="$ROOT/dist/flame_corridor_key_matchbox/greg_corridor_key_roundtrip.py"
MATCHBOX_SRC="$ROOT/dist/flame_corridor_key_matchbox/greg_corridor_key.mx"
GLSL_SRC="$ROOT/dist/flame_corridor_key_matchbox/greg_corridor_key.glsl"
XML_SRC="$ROOT/dist/flame_corridor_key_matchbox/greg_corridor_key.xml"
README_SRC="$ROOT/packaging/greg_corridorkey/README.txt"
HELPER_SRC="$ROOT/packaging/greg_corridorkey/install_or_update_corridorkey.sh"

for required in "$HOOK_SRC" "$MATCHBOX_SRC" "$GLSL_SRC" "$XML_SRC" "$README_SRC" "$HELPER_SRC"; do
    if [ ! -f "$required" ]; then
        echo "Missing required file: $required" >&2
        exit 1
    fi
done

rm -rf "$BUILD_DIR"
mkdir -p "$APP_ROOT" "$PAYLOAD/opt/Autodesk/shared/python" "$OUT_DIR"

python3 -m py_compile "$HOOK_SRC"

cp "$HOOK_SRC" "$APP_ROOT/greg_corridor_key_roundtrip.py"
cp "$HOOK_SRC" "$PAYLOAD/opt/Autodesk/shared/python/greg_corridor_key_roundtrip.py"
cp "$MATCHBOX_SRC" "$APP_ROOT/GregCorridorKey.mx"
cp "$GLSL_SRC" "$APP_ROOT/greg_corridor_key.glsl"
cp "$XML_SRC" "$APP_ROOT/greg_corridor_key.xml"
cp "$README_SRC" "$APP_ROOT/README.txt"
cp "$HELPER_SRC" "$APP_ROOT/install_or_update_corridorkey.sh"
chmod 0755 "$APP_ROOT/install_or_update_corridorkey.sh"

find "$PAYLOAD" -name '._*' -delete
xattr -rc "$PAYLOAD" 2>/dev/null || true

pkgbuild \
    --root "$PAYLOAD" \
    --scripts "$ROOT/packaging/greg_corridorkey/scripts" \
    --filter '(^|/)\.DS_Store$' \
    --filter '(^|/)\._.*' \
    --identifier "$IDENTIFIER" \
    --version "$VERSION" \
    --install-location "/" \
    "$OUT_DIR/$PKG_NAME-$VERSION.pkg"

pkgbuild \
    --nopayload \
    --scripts "$ROOT/packaging/greg_corridorkey/uninstall_pkg_scripts" \
    --identifier "$IDENTIFIER.uninstall" \
    --version "$VERSION" \
    "$OUT_DIR/$PKG_NAME-Uninstall-$VERSION.pkg"

echo "Built:"
echo "$OUT_DIR/$PKG_NAME-$VERSION.pkg"
echo "$OUT_DIR/$PKG_NAME-Uninstall-$VERSION.pkg"
