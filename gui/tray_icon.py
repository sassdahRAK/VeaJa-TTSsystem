"""
System tray icon for Veaja.
Renders the Veaja logo as a tray icon from SVG, with right-click menu.
"""

import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPainterPath, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QRectF
from PyQt6.QtSvg import QSvgRenderer

ASSETS = os.path.join(os.path.dirname(__file__), "..", "assets")


def _make_tray_icon(dark_mode: bool) -> QIcon:
    """Render the SVG logo into a 22×22 tray icon (circular, coloured)."""
    size = 22
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Try SVG  (dark mode → white-face logo; light mode → dark-face logo)
    svg_name = "logo_light.svg" if dark_mode else "logo_dark.svg"
    svg_path = os.path.join(ASSETS, svg_name)
    rendered = False
    if os.path.exists(svg_path):
        renderer = QSvgRenderer(svg_path)
        if renderer.isValid():
            clip = QPainterPath()
            clip.addEllipse(QRectF(0, 0, size, size))
            painter.setClipPath(clip)
            renderer.render(painter, QRectF(0, 0, size, size))
            rendered = True

    if not rendered:
        # Solid red circle fallback
        painter.setBrush(QBrush(QColor(229, 57, 53)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)

    painter.end()
    return QIcon(pixmap)


class TrayIcon(QObject):
    """
    Signals
    -------
    show_window_requested()
    quit_requested()
    """
    show_window_requested = pyqtSignal()
    quit_requested        = pyqtSignal()

    def __init__(self, dark_mode: bool = False, parent=None):
        super().__init__(parent)

        self._tray = QSystemTrayIcon(parent)
        self._tray.setIcon(_make_tray_icon(dark_mode))
        self._tray.setToolTip("Veaja — running")

        self._build_menu()
        self._tray.activated.connect(self._on_activated)
        self._tray.show()

    def _build_menu(self):
        menu = QMenu()
        menu.setStyleSheet(
            "QMenu { background:#2C2C2E; color:#F5F5F7; border-radius:8px; }"
            "QMenu::item:selected { background:#3A3A3C; }"
        )

        act_show = QAction("Show Veaja", self._tray)
        act_show.triggered.connect(self.show_window_requested)
        menu.addAction(act_show)

        menu.addSeparator()

        act_quit = QAction("Quit", self._tray)
        act_quit.triggered.connect(self.quit_requested)
        menu.addAction(act_quit)

        self._tray.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window_requested.emit()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click on some platforms
            self.show_window_requested.emit()

    def update_icon(self, dark_mode: bool):
        self._tray.setIcon(_make_tray_icon(dark_mode))

    def show_notification(self, title: str, message: str):
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._tray.showMessage(title, message,
                                   QSystemTrayIcon.MessageIcon.Information, 2000)

    def hide(self):
        self._tray.hide()
