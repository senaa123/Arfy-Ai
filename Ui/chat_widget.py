from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import Qt

class ChatWidget(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chatBox")
        self.setReadOnly(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def add_message(self, sender, message):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        if sender == "You":
            color = "#00BFFF"
            prefix = "▶ YOU"
        else:
            color = "#0055AA"
            prefix = "◈ ARFY"

        html = f'<p style="color:{color}; font-family: Courier New; font-size: 11px; margin: 4px 0;"><b>{prefix}:</b> {message}</p>'
        cursor.insertHtml(html)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()