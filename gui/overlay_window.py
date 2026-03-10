import pyperclip
import keyboard

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QMetaObject, Q_ARG, pyqtSlot
class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.signal = None
        self.window_visible = False
        self.UI()
        self.listening_hotkey()
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 1000, screen.height() - 400)
        self.setWindowTitle("Vea-cha")
        self.setFixedSize(500, 180)

        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

    def listening_hotkey(self):
        keyboard.add_hotkey('ctrl+c', self.crtl_c, suppress=False)
        keyboard.add_hotkey('ctrl+p', self.crtl_p, suppress=False)    
        
    def crtl_c(self):
        self.signal = 'open'
        text = pyperclip.paste()
        if text and text.strip():
            QMetaObject.invokeMethod(
                self, "text_space",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, text)
            )
            
    def crtl_p(self):
        self.signal = 'close'
        text = pyperclip.paste()
        if text and text.strip():
            QMetaObject.invokeMethod(
                self, "text_space",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, text)
            )

    @pyqtSlot(str)
    def text_space(self, text):
        if not self.window_visible and self.signal == 'open':
            self.show()
            self.window_visible = True
        elif self.signal == 'close':
            self.hide_window()  
        self.raise_()
        self.activateWindow()

    def hide_window(self):
        self.hide()
        self.window_visible = False
    
    def UI(self):
        layout = QVBoxLayout(self)
        header = QFrame()
        header.setFixedHeight(36)
        header.setStyleSheet("background-color: #343131;")
        header_layout = QHBoxLayout(header)
        hide_btn = QPushButton("X")
        hide_btn.clicked.connect(self.hide_window)
        header_layout.addStretch()
        header_layout.addWidget(hide_btn)
        layout.addWidget(header)

    def start(self):
        print("  Vea-cha TTS Overlay ")


if __name__ == "__main__":
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False) 

    window = OverlayWindow()
    window.start()

    app.exec()
