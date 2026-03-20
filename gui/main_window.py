from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QApplication,
    QVBoxLayout,
    QPushButton,
    QTextEdit,
    QLabel
)
import sys
from core import tts_engine
class MainWindow(QMainWindow):
    def __init__(self, speech_service = None):
        super().__init__()

        self.speech_service = tts_engine.TextToSpeech()

        self.setWindowTitle("VeaJa")
        self.setFixedSize(400,533)

        self.init_ui()

    def init_ui(self):
        """Create UI layout"""
        central_widget = QWidget()
        layout = QVBoxLayout()

        self.title_lable = QLabel("Welcome to our TTS system.")
        layout.addWidget(self.title_lable)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Type text here...")
        layout.addWidget(self.text_input)

        self.speak_button = QPushButton("Speak")
        self.speak_button.clicked.connect(self.speak_text)
        layout.addWidget(self.speak_button)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def speak_text(self):
        """get text input and use speak service"""
        text = self.text_input.toPlainText()

        """speak_service the class atribute
            and .speak() is teammate emplement (TTSs pyttsx3)"""
        if self.speech_service:
            self.speech_service.speak(text)
        else: print("Speech service not connect yet.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    Window = MainWindow()
    Window.show()
    sys.exit(app.exec())