from PyQt6.QtWidgets import (
    QTextEdit,
    QLineEdit,
    QComboBox,
    QPushButton,
    QScrollBar,
    QMainWindow,
    QApplication
    )
import sys 
import os

# Adds the parent directory (project/) to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.main_window import MainWindow



if __name__ == "__main__":
    app = QApplication(sys.argv)
    Window = MainWindow()
    Window.show()
    sys.exit(app.exec())



