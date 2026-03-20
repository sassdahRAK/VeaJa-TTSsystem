from gui import main_window
from core import tts_engine
import sys
from PyQt6.QtWidgets import QApplication


app = QApplication(sys.argv)
Window = main_window.MainWindow()
Window.show()
sys.exit(app.exec())