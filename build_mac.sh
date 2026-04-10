#!/bin/bash
# Build Veaja as a standalone macOS .app with PyInstaller
# Run once:  bash build_mac.sh
# Output:    dist/Veaja.app  (drag to /Applications)

set -e
cd "$(dirname "$0")"

echo "▶ Installing build tool..."
pip3 install pyinstaller --quiet

echo "▶ Building Veaja.app ..."
pyinstaller \
  --name "Veaja" \
  --windowed \
  --noconfirm \
  --add-data "assets:assets" \
  --add-data "styles:styles" \
  --hidden-import "pynput.keyboard._darwin" \
  --hidden-import "pynput.mouse._darwin" \
  --hidden-import "pyttsx3.drivers" \
  --hidden-import "pyttsx3.drivers.nsss" \
  main.py

echo ""
echo "✅  Done!  App is at:  dist/Veaja.app"
echo "   Drag it to /Applications to install."
echo ""
echo "   To add to Login Items:"
echo "   System Settings → General → Login Items → add dist/Veaja.app"
