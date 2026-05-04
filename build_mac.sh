#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Veaja — macOS build script
# Produces: dist/Veaja.app  and  dist/veaja-1.0.0-macos.dmg
#
# Requirements:
#   - macOS 12+
#   - Python 3.10+ with venv at ./venv
#   - Optional: brew install create-dmg  (for DMG packaging)
#
# Usage:
#   chmod +x build_mac.sh
#   ./build_mac.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")"

VERSION="1.0.0"

echo "==> Activating venv..."
source venv/bin/activate

echo "==> Installing PyInstaller..."
pip install pyinstaller --quiet

echo "==> Cleaning previous build..."
rm -rf build dist/Veaja.app dist/veaja-*.dmg

echo "==> Building Veaja.app..."
pyinstaller \
  --name "Veaja" \
  --windowed \
  --noconfirm \
  --clean \
  --add-data "assets:assets" \
  --add-data "styles:styles" \
  --add-data "i18n:i18n" \
  --add-data "config:config" \
  --hidden-import "pynput.keyboard._darwin" \
  --hidden-import "pynput.mouse._darwin" \
  --hidden-import "pyttsx3.drivers" \
  --hidden-import "pyttsx3.drivers.nsss" \
  --hidden-import "PyQt6.QtSvg" \
  --hidden-import "edge_tts" \
  --hidden-import "pygame.mixer" \
  --icon "assets/veaja.ico" \
  main.py

echo ""
echo "==> App built: dist/Veaja.app"

# ── Package as DMG (optional — requires create-dmg) ──────────────────────────
if command -v create-dmg &>/dev/null; then
    echo "==> Creating DMG..."
    create-dmg \
        --volname "Veaja ${VERSION}" \
        --volicon "assets/veaja.ico" \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "Veaja.app" 150 200 \
        --app-drop-link 450 200 \
        --no-internet-enable \
        "dist/veaja-${VERSION}-macos.dmg" \
        "dist/Veaja.app"
    echo "==> DMG created: dist/veaja-${VERSION}-macos.dmg"
else
    echo "==> Skipping DMG (create-dmg not found)"
    echo "    Install with: brew install create-dmg"
    echo "    Then re-run this script."
fi

echo ""
echo "✅ Done!"
echo ""
echo "   App:  dist/Veaja.app"
echo "   → Drag to /Applications to install"
echo ""
echo "   If macOS blocks it (Gatekeeper):"
echo "   → Right-click Veaja.app → Open → Open anyway"
echo "   OR: xattr -cr dist/Veaja.app"
