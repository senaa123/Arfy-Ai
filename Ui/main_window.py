from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QLabel, QPushButton)
from PyQt6.QtCore import Qt, QPoint, pyqtSlot
from PyQt6.QtGui import QPainter, QColor, QPen
from Ui.orb import JarvisOrb
from Ui.chat_widget import ChatWidget
from Ui.styles import MAIN_STYLE

class HUDFrame(QWidget):
    """Draws Jarvis-style corner brackets around the window"""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(255, 255, 255, 120))  # white corners
        pen.setWidth(2)
        painter.setPen(pen)

        w, h = self.width(), self.height()
        size = 20  # corner bracket size

        # top left
        painter.drawLine(0, 0, size, 0)
        painter.drawLine(0, 0, 0, size)

        # top right
        painter.drawLine(w - size, 0, w, 0)
        painter.drawLine(w, 0, w, size)

        # bottom left
        painter.drawLine(0, h - size, 0, h)
        painter.drawLine(0, h, size, h)

        # bottom right
        painter.drawLine(w - size, h, w, h)
        painter.drawLine(w, h - size, w, h)

        # subtle scan line effect
        pen.setWidth(1)
        pen.setColor(QColor(0, 191, 255, 20))
        painter.setPen(pen)
        for y in range(0, h, 4):
            painter.drawLine(0, y, w, y)


class ArfyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(MAIN_STYLE)
        self.setFixedSize(380, 520)
        self._drag_pos = QPoint()
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("mainWidget")
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # HUD frame overlay
        self.hud = HUDFrame(central)
        self.hud.setGeometry(0, 0, 380, 520)
        self.hud.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # title bar
        title_bar = QHBoxLayout()

        title = QLabel("◈ A R F Y  A I")
        title.setObjectName("titleLabel")

        # HUD style indicators
        indicator = QLabel("● SYS ONLINE")
        indicator.setStyleSheet("color: #FFFFFF; font-size: 9px; letter-spacing: 2px;")

        min_btn = QPushButton("─")
        min_btn.setObjectName("minimizeBtn")
        min_btn.clicked.connect(self.showMinimized)

        close_btn = QPushButton("×")
        close_btn.setObjectName("closeBtn")
        close_btn.clicked.connect(self.hide)

        title_bar.addWidget(title)
        title_bar.addStretch()
        title_bar.addWidget(indicator)
        title_bar.addWidget(min_btn)
        title_bar.addWidget(close_btn)
        layout.addLayout(title_bar)

        # status label
        self.status_label = QLabel("STANDBY MODE")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # orb
        self.orb = JarvisOrb()
        self.orb.setFixedHeight(250)
        layout.addWidget(self.orb)

        # HUD bottom info bar
        info_bar = QHBoxLayout()
        self.fps_label = QLabel("SYS: ACTIVE")
        self.fps_label.setStyleSheet("color: #444444; font-size: 9px; letter-spacing: 1px;")

        version_label = QLabel("ARFY v1.0")
        version_label.setStyleSheet("color: #444444; font-size: 9px; letter-spacing: 1px;")

        info_bar.addWidget(self.fps_label)
        info_bar.addStretch()
        info_bar.addWidget(version_label)
        layout.addLayout(info_bar)

        # chat
        self.chat = ChatWidget()
        layout.addWidget(self.chat)

    @pyqtSlot(str)
    def set_state(self, state):
        self.orb.set_state(state)
        states = {
            "idle": ("STANDBY MODE", "SYS: ACTIVE"),
            "listening": ("── LISTENING ──", "SYS: AUDIO INPUT"),
            "speaking": ("── SPEAKING ──", "SYS: AUDIO OUTPUT"),
            "thinking": ("── PROCESSING ──", "SYS: COMPUTING")
        }
        label, sys_label = states.get(state, ("STANDBY MODE", "SYS: ACTIVE"))
        self.status_label.setText(label)
        self.fps_label.setText(sys_label)

    @pyqtSlot(str, str)
    def add_chat(self, sender, message):
        self.chat.add_message(sender, message)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)