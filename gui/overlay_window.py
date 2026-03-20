import keyboard
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QTextEdit, QSlider, QLabel
)
from PyQt6.QtCore import Qt, QMetaObject, Q_ARG, pyqtSlot

class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.window_visible = False
        self.is_reading = False
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.UI()
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_change)
        keyboard.add_hotkey('ctrl+p', self.crtl_p, suppress=False)

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 600, screen.height() - 250)
        self.setWindowTitle("Vea-cha")
        self.setFixedSize(500, 160)

    def on_clipboard_change(self):
        text = self.clipboard.text()
        if text and text.strip():
            QMetaObject.invokeMethod(
                self, "text_space",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, text),
                Q_ARG(str, 'open')
            )

    def crtl_p(self):
        QMetaObject.invokeMethod(
                self, "text_space",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, ''),
                Q_ARG(str, 'close')
            )

    @pyqtSlot(str, str)
    def text_space(self, text, signal):
        if signal == 'open':
            self.text_input.setText(text)
            with open("History.txt", "a") as file:
                file.write(text + "\n")
                current_time_string = datetime.now().strftime("%H:%M:%S")
                file.write(current_time_string + "\n\n")
            if not self.window_visible:
                self.show()
                self.window_visible = True
        elif signal == 'close':
            self.hide_window()
        self.raise_()
        self.activateWindow()

    def hide_window(self):
        self.hide()
        self.window_visible = False

    def toggle_read(self):
        self.is_reading = not self.is_reading
        if self.is_reading:
            self.read_btn.setText("Stop")
            self.read_btn.setStyleSheet(self.btn_style("#DC143C"))
        else:
            self.read_btn.setText("Read")
            self.read_btn.setStyleSheet(self.btn_style("#4CAF50"))

    def on_speed_change(self, value):
        self.speed_label.setText(f"Speed  {value / 10:.1f}x")

    def on_volume_change(self, value):
        self.volume_label.setText(f"Vol  {value}%")

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
            QPushButton:hover {{
                opacity: 0.85;
            }}
        """

    def slider_style(self):
        return """
            QSlider::groove:horizontal {
                height: 4px;
                background: #DADADA;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #555555;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #555555;
                border-radius: 2px;
            }
        """

    def UI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(32)
        header.setStyleSheet("background-color: #F0F0F0; border-bottom: 1px solid #DADADA;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 0, 8, 0)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #555; border: none; font-size: 12px; }
            QPushButton:hover { color: #DC143C; }
        """)
        close_btn.clicked.connect(self.hide_window)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)

        # Text Input Area
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Copy any text to see it here...")
        self.text_input.setReadOnly(True)
        self.text_input.setFixedHeight(60)
        self.text_input.setStyleSheet("""
            QTextEdit {
                background-color: #FFFFFF;
                color: #222222;
                padding: 8px;
                border: none;
                font-size: 13px;
            }
        """)

        # Control Menu
        controls = QFrame()
        controls.setFixedHeight(68)
        controls.setStyleSheet("background-color: #FAFAFA; border-top: 1px solid #DADADA;")
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
        print("Vea-cha TTS Overlay")


if __name__ == "__main__":
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    open("History.txt", "a").close()

    window = OverlayWindow()
    window.start()

    app.exec()
