"""
SVG icon rendering utility for Veaja.
Renders SVG assets to QPixmap/QIcon with a given fill color.
Falls back silently if PyQt6-Qt6-Svg is not installed.
"""

import os
from PyQt6.QtGui import QPixmap, QPainter, QIcon
from PyQt6.QtCore import Qt, QByteArray, QSize

try:
    from PyQt6.QtSvg import QSvgRenderer
    _SVG_AVAILABLE = True
except ImportError:
    _SVG_AVAILABLE = False


def _device_pixel_ratio() -> float:
    """Return the primary screen DPR (2.0 on Retina, 1.0 otherwise)."""
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            screen = app.primaryScreen()
            if screen:
                return screen.devicePixelRatio()
    except Exception:
        pass
    return 1.0


def svg_pixmap(path: str, color: str, size: int) -> QPixmap | None:
    """
    Load an SVG file, recolor every fill to `color`, and render
    to a HiDPI-aware transparent QPixmap of the given logical square size.
    Returns None if SVG support is unavailable or the file is missing.
    """
    if not _SVG_AVAILABLE or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            svg = f.read()

        # Replace common black fill declarations
        for old in ('fill="#000000"', "fill='#000000'",
                    'fill="black"', "fill='black'"):
            svg = svg.replace(old, f'fill="{color}"')

        # For stroke-based icons that never declare fill,
        # inject a fill on the outermost <svg> element
        if f'fill="{color}"' not in svg and 'fill=' not in svg:
            svg = svg.replace("<svg ", f'<svg fill="{color}" ', 1)

        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        if not renderer.isValid():
            return None

        # Render at physical pixel size so Retina displays stay sharp
        dpr  = _device_pixel_ratio()
        phys = int(size * dpr)
        px = QPixmap(phys, phys)
        px.fill(Qt.GlobalColor.transparent)
        painter = QPainter(px)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter)
        painter.end()
        px.setDevicePixelRatio(dpr)
        return px
    except Exception:
        return None


def svg_pixmap_raw(path: str, size: int) -> QPixmap | None:
    """
    Render an SVG file as-is (no colour changes) to a HiDPI-aware QPixmap.
    Used for full-colour logo assets.
    """
    if not _SVG_AVAILABLE or not os.path.exists(path):
        return None
    try:
        renderer = QSvgRenderer(path)
        if not renderer.isValid():
            return None

        dpr  = _device_pixel_ratio()
        phys = int(size * dpr)
        px = QPixmap(phys, phys)
        px.fill(Qt.GlobalColor.transparent)
        painter = QPainter(px)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter)
        painter.end()
        px.setDevicePixelRatio(dpr)
        return px
    except Exception:
        return None


def svg_icon(path: str, color: str, size: int) -> QIcon:
    """Convenience wrapper — returns a QIcon (empty if SVG fails)."""
    px = svg_pixmap(path, color, size)
    return QIcon(px) if px else QIcon()
