
import sys
import os
import keyboard
from datetime import datetime
 
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QTextEdit, QSlider, QLabel,
    QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QMetaObject, Q_ARG, pyqtSlot
from PyQt6.QtGui import QIcon, QPixmap, QColor
 
# Adds the parent directory (project/) to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import tts_engine
 
 
class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.window_visible = False
        self.is_reading = False
        self._manager = None  

        """speak_service the class atribute
            and .speak() is teammate emplement (TTSs pyttsx3)"""
        self.speech_service = tts_engine.TextToSpeech()
 
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint  # fully custom title bar
        )
        self._drag_pos = None
        self.UI()
        self.setup_tray()
 
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_change)
        keyboard.add_hotkey('ctrl+p', self.ctrl_p, suppress=False)
 
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 560, screen.height() - 260)
        self.setWindowTitle("VeaJa")
        self.setFixedSize(500, 160)

    def setup_tray(self):
        """System tray so the user knows the app is running and can quit it."""
        px = QPixmap(16, 16)
        px.fill(QColor("#4CAF50"))
        self.tray = QSystemTrayIcon(QIcon(px), self)
 
        menu = QMenu()
        show_action = menu.addAction("Show overlay")
        show_action.triggered.connect(self.show_window)
        menu.addSeparator()
        quit_action = menu.addAction("Quit VeaJa")
        quit_action.triggered.connect(self._request_quit)
 
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("VeaJa TTS — running")
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()
 
    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.window_visible:
                self.hide_window()
            else:
                self.show_window()

    def set_manager(self, manager):
        """Called by WindowManager after construction."""
        self._manager = manager
 
    def _request_quit(self):
        """Route quit through manager so both windows close cleanly."""
        if self._manager:
            self._manager.quit_app()
        else:
            self.tray.hide()
            QApplication.quit()
 
    def on_clipboard_change(self):
        text = self.clipboard.text()
        if not text or not text.strip():
            return
 
        QMetaObject.invokeMethod(
            self, "text_space",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, text),
            Q_ARG(str, 'open')
        )
 
    def ctrl_p(self):
        """Ctrl+P toggles visibility."""
        QMetaObject.invokeMethod(
            self, "text_space",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, ''),
            Q_ARG(str, 'toggle')
        )
 
    @pyqtSlot(str, str)
    def text_space(self, text, signal):
        if signal == 'open':
            self.text_input.setText(text)
            with open("History.txt", "a") as f:
                f.write(text + "\n")
                f.write(datetime.now().strftime("%H:%M:%S") + "\n\n")
 
            if not self.window_visible:
                self.show_window()
 
        elif signal == 'close':   
            self.hide_window()
 
        elif signal == 'toggle': 
            if self.window_visible:
                self.hide_window()
            else:
                self.show_window()
 
        elif signal == 'quit':   
            self._request_quit()
            return
 
        if self.window_visible:
            self.raise_()
            self.activateWindow()
 
    @pyqtSlot()
    def show_window(self):
        self.show()
        self.window_visible = True
        self.raise_()
        self.activateWindow()
 
    def hide_window(self):
        """Hide to tray — app keeps running."""
        self.hide()
        self.window_visible = False
        QApplication.processEvents()
 
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
 
    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
 
    def mouseReleaseEvent(self, event):
        self._drag_pos = None
 
    def toggle_read(self):
        self.is_reading = not self.is_reading
        if self.is_reading:
            self.read_btn.setText("Stop")
            self.read_btn.setStyleSheet(self.btn_style("#DC143C"))
            # Speak the text currently shown in the overlay
            text = self.text_input.toPlainText()
            if text.strip() and self.speech_service:
                self.speech_service.speak(text)
            self.is_reading = False
            self.read_btn.setText("Read")
            self.read_btn.setStyleSheet(self.btn_style("#4CAF50"))
        else:
            self.read_btn.setText("Read")
            self.read_btn.setStyleSheet(self.btn_style("#4CAF50"))
 
    def on_speed_change(self, value):
        self.speed_label.setText(f"Speed  {value / 10:.1f}x")
 
    def on_volume_change(self, value):
        self.volume_label.setText(f"Vol  {value}%")
 
    #Styles 
    def btn_style(self, color):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {color}CC; }}
        """
 
    def header_btn_style(self, hover_color):
        return f"""
            QPushButton {{
                background-color: transparent;
                color: #666;
                border: none;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ color: {hover_color}; }}
        """
 
    def slider_style(self):
        return """
            QSlider::groove:horizontal {
                height: 4px;
                background: #DADADA;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #555;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #555;
                border-radius: 2px;
            }
        """
 
    def UI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
 
        # ── Header ──
        header = QFrame()
        header.setFixedHeight(32)
        header.setStyleSheet(
            "background-color: #F0F0F0;"
            "border-bottom: 1px solid #DADADA;"
            "border-top-left-radius: 6px;"
            "border-top-right-radius: 6px;"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 0, 8, 0)
        header_layout.setSpacing(4)
 
        title = QLabel("VeaJa")
        title.setStyleSheet("font-size: 12px; font-weight: bold; color: #444;")
        header_layout.addWidget(title)
        header_layout.addStretch()
 
        # — Minimise to tray
        min_btn = QPushButton("—")
        min_btn.setFixedSize(24, 24)
        min_btn.setStyleSheet(self.header_btn_style("#888"))
        min_btn.setToolTip("Hide to tray (app keeps running)")
        min_btn.clicked.connect(self.hide_window)
 
        quit_btn = QPushButton("✕")
        quit_btn.setFixedSize(24, 24)
        quit_btn.setStyleSheet(self.header_btn_style("#DC143C"))
        quit_btn.setToolTip("Quit VeaJa")
        quit_btn.clicked.connect(self._request_quit)
 
        header_layout.addWidget(min_btn)
        header_layout.addWidget(quit_btn)
 
        # ── Text area ──
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Copy any text to see it here...")
        self.text_input.setReadOnly(True)
        self.text_input.setFixedHeight(60)
        self.text_input.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                color: #222;
                padding: 8px;
                border: none;
                font-size: 13px;
            }
        """)
 
        controls = QFrame()
        controls.setFixedHeight(68)
        controls.setStyleSheet(
            "background-color: #FAFAFA;"
            "border-top: 1px solid #DADADA;"
            "border-bottom-left-radius: 6px;"
            "border-bottom-right-radius: 6px;"
        )
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(10, 6, 10, 6)
        controls_layout.setSpacing(4)
 
        top_row = QHBoxLayout()
        top_row.setSpacing(12)
 
        self.read_btn = QPushButton("Read")
        self.read_btn.setFixedSize(70, 28)
        self.read_btn.setStyleSheet(self.btn_style("#4CAF50"))
        self.read_btn.clicked.connect(self.toggle_read)
 
        speed_col = QVBoxLayout()
        speed_col.setSpacing(2)
        self.speed_label = QLabel("Speed  1.0x")
        self.speed_label.setStyleSheet("font-size: 11px; color: #555;")
        speed_slider = QSlider(Qt.Orientation.Horizontal)
        speed_slider.setRange(5, 30)
        speed_slider.setValue(10)
        speed_slider.setFixedWidth(120)
        speed_slider.setStyleSheet(self.slider_style())
        speed_slider.valueChanged.connect(self.on_speed_change)
        speed_col.addWidget(self.speed_label)
        speed_col.addWidget(speed_slider)
 
        volume_col = QVBoxLayout()
        volume_col.setSpacing(2)
        self.volume_label = QLabel("Vol  100%")
        self.volume_label.setStyleSheet("font-size: 11px; color: #555;")
        volume_slider = QSlider(Qt.Orientation.Horizontal)
        volume_slider.setRange(0, 100)
        volume_slider.setValue(100)
        volume_slider.setFixedWidth(120)
        volume_slider.setStyleSheet(self.slider_style())
        volume_slider.valueChanged.connect(self.on_volume_change)
        volume_col.addWidget(self.volume_label)
        volume_col.addWidget(volume_slider)
 
        top_row.addWidget(self.read_btn)
        top_row.addLayout(speed_col)
        top_row.addLayout(volume_col)
        top_row.addStretch()
 
        controls_layout.addLayout(top_row)
 
        layout.addWidget(header)
        layout.addWidget(self.text_input)
        layout.addWidget(controls)
 
    def start(self):
        print("VeaJa TTS Overlay — running (tray icon active)")
 
 
if __name__ == "__main__":
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    open("History.txt", "a").close()
 
    window = OverlayWindow()
    window.start()
 
    app.exec()