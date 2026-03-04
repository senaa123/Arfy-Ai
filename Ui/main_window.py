from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QLabel, QPushButton,
                              QLineEdit)
from PyQt6.QtCore import Qt, QPoint, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen
from Ui.orb import JarvisOrb
from Ui.chat_widget import ChatWidget
from Ui.styles import MAIN_STYLE


class HUDFrame(QWidget):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(QColor(0, 191, 255, 80))
        pen.setWidth(1)
        painter.setPen(pen)

        w, h = self.width(), self.height()
        size = 18

        painter.drawLine(0, 0, size, 0)
        painter.drawLine(0, 0, 0, size)
        painter.drawLine(w - size, 0, w, 0)
        painter.drawLine(w, 0, w, size)
        painter.drawLine(0, h - size, 0, h)
        painter.drawLine(0, h, size, h)
        painter.drawLine(w - size, h, w, h)
        painter.drawLine(w, h - size, w, h)

        pen.setColor(QColor(0, 191, 255, 6))
        painter.setPen(pen)
        for y in range(0, h, 4):
            painter.drawLine(0, y, w, y)


class ArfyWindow(QMainWindow):

    text_submitted = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(MAIN_STYLE)
        self.setFixedSize(380, 560)
        self._drag_pos = QPoint()
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("mainWidget")
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        # HUD overlay
        self.hud = HUDFrame(central)
        self.hud.setGeometry(0, 0, 380, 560)
        self.hud.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # title bar
        title_bar = QHBoxLayout()

        title = QLabel("◈ A R F Y  A I")
        title.setObjectName("titleLabel")

        indicator = QLabel("● SYS ONLINE")
        indicator.setStyleSheet(
            "color: #00BFFF; font-size: 9px; letter-spacing: 2px;"
        )

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

        # status + mode label row
        status_row = QHBoxLayout()

        self.status_label = QLabel("STANDBY MODE")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.mode_label = QLabel("● VOICE MODE")
        self.mode_label.setStyleSheet(
            "color: #00BFFF; font-size: 9px; letter-spacing: 2px;"
        )
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        status_row.addWidget(self.status_label)
        status_row.addWidget(self.mode_label)
        layout.addLayout(status_row)

        # orb
        self.orb = JarvisOrb()
        self.orb.setFixedHeight(250)
        layout.addWidget(self.orb)

        # bottom info
        info_bar = QHBoxLayout()

        self.sys_label = QLabel("SYS: ACTIVE")
        self.sys_label.setStyleSheet(
            "color: #003366; font-size: 9px; letter-spacing: 1px;"
        )

        version_label = QLabel("ARFY v1.0")
        version_label.setStyleSheet(
            "color: #003366; font-size: 9px; letter-spacing: 1px;"
        )

        info_bar.addWidget(self.sys_label)
        info_bar.addStretch()
        info_bar.addWidget(version_label)
        layout.addLayout(info_bar)

        # chat
        self.chat = ChatWidget()
        layout.addWidget(self.chat)

        # input field — hidden and disabled by default
        self.input_widget = QWidget()
        self.input_widget.setObjectName("inputWidget")
        input_bar = QHBoxLayout(self.input_widget)
        input_bar.setContentsMargins(0, 0, 0, 0)
        input_bar.setSpacing(6)

        self.text_input = QLineEdit()
        self.text_input.setObjectName("textInput")
        self.text_input.setPlaceholderText("type here...")
        self.text_input.setEnabled(False)
        self.text_input.returnPressed.connect(self._on_submit)

        self.send_btn = QPushButton("→")
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(self._on_submit)

        input_bar.addWidget(self.text_input)
        input_bar.addWidget(self.send_btn)

        self.input_widget.hide()
        layout.addWidget(self.input_widget)

    def _on_submit(self):
        text = self.text_input.text().strip()
        if text:
            self.text_submitted.emit(text)
            self.text_input.clear()

    @pyqtSlot()
    def show_input(self):
        self.input_widget.show()
        self.text_input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.text_input.setFocus()

    @pyqtSlot()
    def hide_input(self):
        self.input_widget.hide()
        self.text_input.setEnabled(False)
        self.send_btn.setEnabled(False)
        self.text_input.clear()

    @pyqtSlot(str)
    def set_mode_label(self, mode):
        if mode == "INPUT MODE":
            self.mode_label.setText("● INPUT MODE")
            self.mode_label.setStyleSheet(
                "color: #00FF88; font-size: 9px; letter-spacing: 2px;"
            )
        else:
            self.mode_label.setText("● VOICE MODE")
            self.mode_label.setStyleSheet(
                "color: #00BFFF; font-size: 9px; letter-spacing: 2px;"
            )

    @pyqtSlot(str)
    def set_state(self, state):
        self.orb.set_state(state)
        states = {
            "idle":      ("STANDBY MODE",     "SYS: ACTIVE"),
            "listening": ("── LISTENING ──",  "SYS: AUDIO INPUT"),
            "speaking":  ("── SPEAKING ──",   "SYS: AUDIO OUTPUT"),
            "thinking":  ("── PROCESSING ──", "SYS: COMPUTING"),
        }
        label, sys = states.get(state, ("STANDBY MODE", "SYS: ACTIVE"))
        self.status_label.setText(label)
        self.sys_label.setText(sys)

    @pyqtSlot(str, str)
    def add_chat(self, sender, message):
        self.chat.add_message(sender, message)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)