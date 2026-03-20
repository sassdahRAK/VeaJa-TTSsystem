import sys
import os
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QApplication,
    QVBoxLayout,
    QPushButton,
    QTextEdit,
    QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core import tts_engine

base_dir = os.path.dirname(__file__)

dark_qss  = os.path.abspath(os.path.join(base_dir, "..", "styles", "dark.qss"))
light_qss = os.path.abspath(os.path.join(base_dir, "..", "styles", "light.qss"))


class MainWindow(QMainWindow):
    request_quit = pyqtSignal()   
    request_hide = pyqtSignal()   

    def __init__(self, speech_service=None):
        super().__init__()

        self.speech_service = tts_engine.TextToSpeech()

        self.setWindowTitle("VeaJa")
        self.setFixedSize(400, 533)

        self.dark_mode = True

        self.init_ui()

    def init_ui(self):
        """Create UI layout"""
        central_widget = QWidget()
        VerticalLayout = QVBoxLayout()

        # Settings / theme button
        self.theme = QPushButton("⚙️")
        self.theme.clicked.connect(self.toggle_theme)
        self.theme.setFixedSize(30, 24)
        self.theme.setParent(self)
        self.theme.move(350, 5)
        self.theme.show()

        # Title 
        self.title_lable = QLabel("Welcome to our TTS system.")
        VerticalLayout.addWidget(self.title_lable)

        # Text input
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Type text here...")
        VerticalLayout.addWidget(self.text_input, 1)

        # Speak button
        self.speak_button = QPushButton("🎧")
        self.speak_button.clicked.connect(self.speak_text)
        self.speak_button.setFixedSize(75, 75)
        VerticalLayout.addWidget(self.speak_button, 0)
        VerticalLayout.setAlignment(self.speak_button, Qt.AlignmentFlag.AlignCenter)

        central_widget.setLayout(VerticalLayout)
        self.setCentralWidget(central_widget)

    def showEvent(self, event):
        super().showEvent(event)
        self.theme.raise_()
        self.speak_button.raise_()

    def closeEvent(self, event):
        """
        Intercept the OS close (Alt+F4 or title bar X).
        Instead of actually closing, emit request_quit so
        WindowManager can shut everything down cleanly.
        """
        event.ignore()         
        self.request_quit.emit()

    def speak_text(self):
        """get text input and use speak service"""
        text = self.text_input.toPlainText()

        """speak_service the class atribute
            and .speak() is teammate emplement (TTSs pyttsx3)"""
        if self.speech_service:
            self.speech_service.speak(text)
        else:
            print("Speech service not connect yet.")

    def load_theme(self, app, theme):
        """to read .qss file from styles folder"""
        with open(theme, "r") as f:
            app.setStyleSheet(f.read())

    def toggle_theme(self):
        """to set dark mode / light mode"""
        app = QApplication.instance()
        if self.dark_mode:
            self.load_theme(app, dark_qss)
        else:
            self.load_theme(app, light_qss)
        self.dark_mode = not self.dark_mode

    def toggle_speak_button(self):
        """to style the speak button"""
        app = QApplication.instance()
        if ():
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    Window = MainWindow()
    Window.show()
    sys.exit(app.exec())