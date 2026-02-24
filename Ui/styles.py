MAIN_STYLE = """
QMainWindow, QWidget#mainWidget {
    background-color: #000510;
    border: 1px solid #003366;
    border-radius: 15px;
}

QWidget {
    background-color: transparent;
    color: #00BFFF;
    font-family: 'Courier New', monospace;
}

QLabel#titleLabel {
    color: #00BFFF;
    font-size: 14px;
    font-weight: bold;
    letter-spacing: 4px;
    text-transform: uppercase;
}

QLabel#statusLabel {
    color: #0088CC;
    font-size: 11px;
    letter-spacing: 2px;
}

/* Chat History */
QTextEdit#chatBox {
    background-color: #000D1A;
    border: 1px solid #003366;
    border-radius: 8px;
    color: #00BFFF;
    font-family: 'Courier New', monospace;
    font-size: 11px;
    padding: 8px;
}

QScrollBar:vertical {
    background: #000510;
    width: 6px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #003366;
    border-radius: 3px;
}

/* Music Controls */
QWidget#musicWidget {
    background-color: #000D1A;
    border: 1px solid #003366;
    border-radius: 8px;
    padding: 5px;
}

QLabel#songLabel {
    color: #00BFFF;
    font-size: 11px;
    letter-spacing: 1px;
}

QPushButton#musicBtn {
    background-color: transparent;
    border: 1px solid #003366;
    border-radius: 15px;
    color: #00BFFF;
    font-size: 16px;
    min-width: 30px;
    min-height: 30px;
    max-width: 30px;
    max-height: 30px;
}

QPushButton#musicBtn:hover {
    background-color: #003366;
    border: 1px solid #00BFFF;
}

QPushButton#musicBtn:pressed {
    background-color: #00BFFF;
    color: #000510;
}

/* Close/Minimize buttons */
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
    border-color: #00BFFF;
}

/* Slider for volume */
QSlider::groove:horizontal {
    background: #003366;
    height: 4px;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #00BFFF;
    width: 10px;
    height: 10px;
    border-radius: 5px;
    margin: -3px 0;
}

QSlider::sub-page:horizontal {
    background: #00BFFF;
    border-radius: 2px;
}
"""