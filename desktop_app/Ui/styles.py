MAIN_STYLE = """
QMainWindow, QWidget#mainWidget {
    background-color: #000510;
    border: 1px solid #003366;
    border-radius: 5px;
}

QWidget {
    background-color: transparent;
    color: #00BFFF;
    font-family: 'Courier New', monospace;
}

QLabel#titleLabel {
    color: #00BFFF;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 4px;
}

QLabel#statusLabel {
    color: #0088CC;
    font-size: 11px;
    letter-spacing: 3px;
}

QTextEdit#chatBox, QWidget#chatBox {
    background-color: #000D1A;
    border: 1px solid #003366;
    border-radius: 4px;
    color: #00BFFF;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    padding: 8px;
}

QScrollBar:vertical {
    background: #000510;
    width: 4px;
    border-radius: 2px;
}

QScrollBar::handle:vertical {
    background: #003366;
    border-radius: 2px;
}

QPushButton#closeBtn {
    background-color: transparent;
    border: 1px solid #003366;
    border-radius: 10px;
    color: #00BFFF;
    font-size: 12px;
    min-width: 20px;
    min-height: 20px;
    max-width: 20px;
    max-height: 20px;
}

QPushButton#closeBtn:hover {
    background-color: #CC0000;
    border-color: #CC0000;
    color: white;
}

QPushButton#minimizeBtn {
    background-color: transparent;
    border: 1px solid #003366;
    border-radius: 10px;
    color: #00BFFF;
    font-size: 12px;
    min-width: 20px;
    min-height: 20px;
    max-width: 20px;
    max-height: 20px;
}

QPushButton#minimizeBtn:hover {
    background-color: #003366;
    color: #00BFFF;
}
QLineEdit#textInput {
    background-color: #000D1A;
    border: 1px solid #003366;
    border-radius: 4px;
    color: #00BFFF;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    padding: 6px 8px;
}

QLineEdit#textInput:focus {
    border: 1px solid #00BFFF;
}

QPushButton#sendBtn {
    background-color: #003366;
    border: 1px solid #00BFFF;
    border-radius: 4px;
    color: #00BFFF;
    font-size: 14px;
    min-width: 30px;
    min-height: 28px;
    max-width: 30px;
    max-height: 28px;
}

QPushButton#sendBtn:hover {
    background-color: #00BFFF;
    color: #000510;
}
"""