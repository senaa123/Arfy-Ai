MAIN_STYLE = """
QMainWindow, QWidget#mainWidget {
    background-color: #000000;
    border: 1px solid #222222;
    border-radius: 5px;
}

QWidget {
    background-color: transparent;
    color: #FFFFFF;
    font-family: 'Courier New', monospace;
}

QLabel#titleLabel {
    color: #FFFFFF;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 4px;
}

QLabel#statusLabel {
    color: #AAAAAA;
    font-size: 11px;
    letter-spacing: 3px;
}

QTextEdit#chatBox {
    background-color: #0A0A0A;
    border: 1px solid #222222;
    border-radius: 4px;
    color: #FFFFFF;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    padding: 8px;
}

QScrollBar:vertical {
    background: #000000;
    width: 4px;
    border-radius: 2px;
}

QScrollBar::handle:vertical {
    background: #333333;
    border-radius: 2px;
}

QPushButton#closeBtn {
    background-color: transparent;
    border: 1px solid #333333;
    border-radius: 10px;
    color: #FFFFFF;
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
    border: 1px solid #333333;
    border-radius: 10px;
    color: #FFFFFF;
    font-size: 12px;
    min-width: 20px;
    min-height: 20px;
    max-width: 20px;
    max-height: 20px;
}

QPushButton#minimizeBtn:hover {
    background-color: #333333;
    color: white;
}
"""