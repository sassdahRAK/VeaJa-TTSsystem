"""
Shared constants and utilities used by MainWindow and its mixin classes.
Kept in a separate module to avoid circular imports.
"""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
STYLES = os.path.join(os.path.dirname(__file__), "..", "styles")


def _make_square_pixmap(path: str, size: int) -> QPixmap | None:
    """Scale image to fill a logical square of `size` px, HiDPI-aware.
    SVG files are rendered via svg_pixmap_raw for crisp vector output."""
    if path.lower().endswith(".svg"):
        from gui.icon_utils import svg_pixmap_raw
        return svg_pixmap_raw(path, size)
    raw = QPixmap(path)
    if raw.isNull():
        return None
    # Render at physical resolution so Retina screens stay sharp
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        dpr = app.primaryScreen().devicePixelRatio() if app and app.primaryScreen() else 1.0
    except Exception:
        dpr = 1.0
    phys = int(size * dpr)
    px = raw.scaled(phys, phys,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation)
    px.setDevicePixelRatio(dpr)
    return px
