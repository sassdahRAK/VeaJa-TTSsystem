"""
Shared constants and utilities used by MainWindow and its mixin classes.
Kept in a separate module to avoid circular imports.
"""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")
STYLES = os.path.join(os.path.dirname(__file__), "..", "styles")


def _make_circle_pixmap(src: QPixmap) -> QPixmap:
    """Mask a square QPixmap into a circle (anti-aliased, HiDPI-correct)."""
    dpr = src.devicePixelRatio()
    size = src.width()                          # physical pixels
    logical = size / dpr if dpr else size       # logical pixels (painter coord space)
    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)
    result.setDevicePixelRatio(dpr)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, logical, logical)     # logical coords to match painter space
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, src)
    painter.end()
    return result


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
    # Scale so the shorter side fills phys (expanding), then centre-crop to
    # exactly phys×phys.  Without the crop, KeepAspectRatioByExpanding leaves
    # the longer side larger than phys, producing a non-square pixmap whose
    # logical height (after setDevicePixelRatio) exceeds `size` — causing the
    # blank white gap visible below portrait photos inside the profile frame.
    px = raw.scaled(phys, phys,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation)
    if px.width() != phys or px.height() != phys:
        x = (px.width()  - phys) // 2
        y = (px.height() - phys) // 2
        px = px.copy(x, y, phys, phys)
    px.setDevicePixelRatio(dpr)
    return px


# ── Cross-platform DPI-aware size helper ──────────────────────────────────────

def _dpi_scale() -> float:
    """
    Return a scale factor for UI sizing.

    Windows / macOS: use logicalDotsPerInch / 96 (OS handles DPI scaling).
    Linux: Qt reports logical DPI = 96 even on high-DPI laptop screens because
           most Linux desktops don't set a display scale factor by default.
           We therefore use physicalDotsPerInch / 96 as a floor so the UI
           is not tiny on ~140–160 DPI laptop panels.

    Examples:
      Windows 96 DPI  → 1.0   (normal desktop)
      Windows 120 DPI → 1.25  (125 % scaling)
      Linux 96 lDPI / 144 pDPI → max(96/96, 144/96) = 1.5
      Linux 96 lDPI / 96 pDPI  → 1.0  (external monitor at normal DPI)
    """
    try:
        from PyQt6.QtWidgets import QApplication
        import platform as _platform
        app = QApplication.instance()
        if app and app.primaryScreen():
            screen = app.primaryScreen()
            logical  = screen.logicalDotsPerInch()
            physical = screen.physicalDotsPerInch()
            logical_scale  = logical  / 96.0
            physical_scale = physical / 96.0
            if _platform.system() == "Linux":
                # On Linux take the larger of the two so high-DPI laptop
                # screens get a sensible size even without a compositor
                # scale factor configured.
                # Cap at 1.25 — beyond that the window becomes too large
                # for typical 1080p laptop screens.
                return min(max(logical_scale, physical_scale), 1.25)
            return logical_scale
    except Exception:
        pass
    return 1.0


def scaled(px: int) -> int:
    """Scale a logical pixel value by the current DPI factor."""
    return max(1, round(px * _dpi_scale()))
