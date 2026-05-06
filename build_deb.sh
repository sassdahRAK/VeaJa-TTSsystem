#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Veaja — .deb package builder
#
# Produces: dist/veaja_1.1.0_amd64.deb
#
# The .deb installs:
#   /opt/veaja/              — app files + bundled venv
#   /usr/bin/veaja           — launcher script
#   /usr/share/applications/veaja.desktop  — app menu entry
#   /usr/share/icons/...     — app icon
#
# Dependencies declared in the package (auto-installed by apt):
#   python3, espeak, espeak-ng, libportaudio2
#
# Usage:
#   chmod +x build_deb.sh
#   ./build_deb.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

VERSION="1.1.0"
ARCH="amd64"
PKG_NAME="veaja"
PKG_DIR="dist/deb_build/${PKG_NAME}_${VERSION}_${ARCH}"

echo "==> Cleaning previous build..."
rm -rf dist/deb_build
mkdir -p "$PKG_DIR"

# ── 1. Create directory structure ─────────────────────────────────────────────
echo "==> Creating package structure..."

mkdir -p "${PKG_DIR}/DEBIAN"
mkdir -p "${PKG_DIR}/opt/veaja"
mkdir -p "${PKG_DIR}/usr/bin"
mkdir -p "${PKG_DIR}/usr/share/applications"
mkdir -p "${PKG_DIR}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${PKG_DIR}/usr/share/icons/hicolor/scalable/apps"

# ── 2. Copy app files ─────────────────────────────────────────────────────────
echo "==> Copying app files..."

cp -r assets config core gui i18n platform_adapters runtime services styles \
      main.py requirements.txt run_veaja.sh \
      "${PKG_DIR}/opt/veaja/"

# ── 3. Create a clean venv inside the package ─────────────────────────────────
echo "==> Creating bundled venv (this may take a minute)..."

python3 -m venv "${PKG_DIR}/opt/veaja/venv"
"${PKG_DIR}/opt/veaja/venv/bin/pip" install --quiet --upgrade pip
"${PKG_DIR}/opt/veaja/venv/bin/pip" install --quiet -r requirements.txt

# ── 4. Create the launcher script ─────────────────────────────────────────────
echo "==> Creating launcher..."

cat > "${PKG_DIR}/usr/bin/veaja" << 'EOF'
#!/bin/bash
# Veaja launcher — uses the bundled venv
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
exec /opt/veaja/venv/bin/python /opt/veaja/main.py "$@"
EOF

chmod 755 "${PKG_DIR}/usr/bin/veaja"

# ── 5. Copy icons ─────────────────────────────────────────────────────────────
echo "==> Copying icons..."

if [ -f "assets/logo_dark.png" ]; then
    cp assets/logo_dark.png \
       "${PKG_DIR}/usr/share/icons/hicolor/256x256/apps/veaja.png"
fi

# ── 6. Create .desktop file (app menu entry) ──────────────────────────────────
echo "==> Creating .desktop entry..."

cat > "${PKG_DIR}/usr/share/applications/veaja.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Veaja
GenericName=Text to Speech
Comment=Select text anywhere and hear it spoken aloud
Exec=veaja
Icon=veaja
Terminal=false
Categories=Utility;Accessibility;Audio;
Keywords=tts;text;speech;read;accessibility;
StartupNotify=false
StartupWMClass=veaja
EOF

# ── 7. Create DEBIAN/control (package metadata) ───────────────────────────────
echo "==> Writing package metadata..."

INSTALLED_SIZE=$(du -sk "${PKG_DIR}/opt" | cut -f1)

cat > "${PKG_DIR}/DEBIAN/control" << EOF
Package: veaja
Version: ${VERSION}
Architecture: ${ARCH}
Maintainer: Sassdah <sassdah@example.com>
Installed-Size: ${INSTALLED_SIZE}
Depends: python3 (>= 3.10), espeak | espeak-ng, libportaudio2
Recommends: espeak-ng
Section: utils
Priority: optional
Homepage: https://github.com/sassdahRAK/VeaJa-TTSsystem
Description: Text-to-speech desktop app
 Veaja turns selected text into speech. Select text in any app,
 press Ctrl+C, and a floating pill appears near your cursor.
 Click it to hear the text read aloud using neural voices (online)
 or system voices (offline).
 .
 Features:
  - Online mode: Microsoft neural voices via edge-tts
  - Offline mode: espeak system voices
  - Floating overlay pill with karaoke word highlighting
  - Pause, resume, and restart support
  - Dark and light themes
  - System tray integration
EOF

# ── 8. Create postinst script (runs after install) ────────────────────────────
cat > "${PKG_DIR}/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

# Update icon cache so the app icon appears in the menu
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
fi

# Update desktop database
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
fi

echo ""
echo "✅ Veaja installed successfully!"
echo "   Run from terminal: veaja"
echo "   Or find it in your application menu."
echo ""
EOF

chmod 755 "${PKG_DIR}/DEBIAN/postinst"

# ── 9. Create prerm script (runs before uninstall) ────────────────────────────
cat > "${PKG_DIR}/DEBIAN/prerm" << 'EOF'
#!/bin/bash
set -e
# Nothing special needed — dpkg handles file removal
EOF

chmod 755 "${PKG_DIR}/DEBIAN/prerm"

# ── 10. Set correct permissions ───────────────────────────────────────────────
echo "==> Setting permissions..."

find "${PKG_DIR}/opt/veaja" -type f ! -type l -exec chmod 644 {} \;
find "${PKG_DIR}/opt/veaja" -type d -exec chmod 755 {} \;
# Only chmod real files in bin/, not symlinks
find "${PKG_DIR}/opt/veaja/venv/bin/" -type f ! -type l -exec chmod 755 {} \;
chmod 755 "${PKG_DIR}/opt/veaja/run_veaja.sh"

# ── 11. Build the .deb ────────────────────────────────────────────────────────
echo "==> Building .deb package..."

mkdir -p dist
dpkg-deb --build --root-owner-group "${PKG_DIR}" \
    "dist/${PKG_NAME}_${VERSION}_${ARCH}.deb"

# ── 12. Verify ────────────────────────────────────────────────────────────────
echo ""
echo "==> Package info:"
dpkg-deb --info "dist/${PKG_NAME}_${VERSION}_${ARCH}.deb"

echo ""
echo "==> Package contents (first 30 files):"
dpkg-deb --contents "dist/${PKG_NAME}_${VERSION}_${ARCH}.deb" | head -30

echo ""
echo "✅ Done!"
echo ""
echo "   Package: dist/${PKG_NAME}_${VERSION}_${ARCH}.deb"
echo ""
echo "   Install:   sudo dpkg -i dist/${PKG_NAME}_${VERSION}_${ARCH}.deb"
echo "   Or:        sudo apt install ./dist/${PKG_NAME}_${VERSION}_${ARCH}.deb"
echo ""
echo "   Uninstall: sudo apt remove veaja"
