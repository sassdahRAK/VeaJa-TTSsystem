#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Veaja — Linux build script
# Produces: dist/veaja-1.0.0-linux-x86_64.tar.gz
#
# Usage:
#   chmod +x build_linux.sh
#   ./build_linux.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

VERSION="1.0.0"
ARCH=$(uname -m)
OUTPUT="veaja-${VERSION}-linux-${ARCH}"

echo "==> Activating venv..."
source venv/bin/activate

echo "==> Cleaning previous build..."
rm -rf build dist

echo "==> Building with PyInstaller..."
pyinstaller veaja.spec --clean --noconfirm

echo "==> Packaging..."
cd dist
mv veaja "$OUTPUT"
tar -czf "${OUTPUT}.tar.gz" "$OUTPUT"
cd ..

echo ""
echo "✅ Build complete: dist/${OUTPUT}.tar.gz"
echo ""
echo "To install on another Linux machine:"
echo "  1. Extract: tar -xzf ${OUTPUT}.tar.gz"
echo "  2. Install espeak: sudo apt install espeak espeak-ng"
echo "  3. Run: ./${OUTPUT}/veaja"
