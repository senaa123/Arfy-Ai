from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter
from PyQt6.QtCore import Qt

class ArfyTray(QSystemTrayIcon):
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window

        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(0, 191, 255))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 24, 24)
        painter.end()

        self.setIcon(QIcon(pixmap))
        self.setToolTip("Arfy AI")

        menu = QMenu()
        show_action = menu.addAction("Show Arfy")
        show_action.triggered.connect(self.window.show)
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self._quit)

        self.setContextMenu(menu)
        self.activated.connect(self._on_click)
        self.show()

    def _on_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.window.isVisible():
                self.window.hide()
            else:
                self.window.show()

    def _quit(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()