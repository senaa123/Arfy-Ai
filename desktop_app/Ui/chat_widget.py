from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class ChatWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chatBox")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("chatBox")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(8)
        self.content_layout.addStretch()

        # awaiting input label
        self.empty_label = QLabel("AWAITING INPUT...")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(
            "color: #333333; font-size: 10px; letter-spacing: 2px;"
        )
        self.content_layout.addWidget(self.empty_label)

        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)

        self.message_count = 0

    def add_message(self, sender, message):
        # remove empty label on first message
        if self.message_count == 0:
            self.empty_label.hide()

        self.message_count += 1

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(2)

        # sender label
        if sender == "You":
            sender_color = "#FFFFFF"
            prefix = "▶ YOU"
        else:
            sender_color = "#888888"
            prefix = "◈ ARFY"

        sender_label = QLabel(prefix)
        sender_label.setStyleSheet(
            f"color: {sender_color}; font-size: 9px; "
            f"letter-spacing: 3px; font-family: 'Courier New';"
        )

        # message text
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(
            "color: #DDDDDD; font-size: 11px; "
            "font-family: 'Courier New'; line-height: 1.4;"
        )

        container_layout.addWidget(sender_label)
        container_layout.addWidget(msg_label)

        # insert before stretch
        self.content_layout.insertWidget(
            self.content_layout.count() - 1, container
        )

        # scroll to bottom
        self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        )