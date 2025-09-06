import sys, os
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize
from gui import MainWindow
from backend import CoreBackend

if __name__ == "__main__":
    app = QApplication(sys.argv)

    app_icon = QIcon()
    icon_loc = os.path.join(os.path.dirname(__file__),
                            'logo.png')
    app_icon.addFile(icon_loc, QSize(16, 16))
    app.setWindowIcon(app_icon)

    # Optional: a light Fusion style
    app.setStyle("Fusion")
    # Tiny app-wide stylesheet
    app.setStyleSheet(
        "QPushButton { padding: 2px 8px; border-radius: 3px; font-size: 10pt; }"
        "QPushButton:hover { background-color: #e0e0e0; }"
    )

    backend = CoreBackend()

    main_window = MainWindow(backend)
    
    main_window.show()

    sys.exit(app.exec())
