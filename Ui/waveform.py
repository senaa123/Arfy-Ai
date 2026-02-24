from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPainter, QColor, QPen
import numpy as np
import math
import time

class WaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(50)
        self.active = False
        self.bars = 32
        self.heights = [0.0] * self.bars
        self.target_heights = [0.0] * self.bars

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_wave)
        self.timer.start(30)

    def set_active(self, active):
        self.active = active

    def update_wave(self):
        if self.active:
            self.target_heights = [
                abs(math.sin(time.time() * 3 + i * 0.5)) * 0.7 +
                abs(math.sin(time.time() * 7 + i * 0.3)) * 0.3
                for i in range(self.bars)
            ]
        else:
            self.target_heights = [0.05] * self.bars

        # smooth transition
        for i in range(self.bars):
            self.heights[i] += (self.target_heights[i] - self.heights[i]) * 0.3

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bar_width = w / self.bars
        center_y = h / 2

        for i, height in enumerate(self.heights):
            bar_h = height * (h * 0.8)
            x = i * bar_width + bar_width * 0.1
            bw = bar_width * 0.8

            # glow effect
            alpha = int(100 * height)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 100, 200, alpha))
            painter.drawRoundedRect(
                int(x), int(center_y - bar_h * 1.2),
                int(bw), int(bar_h * 2.4), 2, 2
            )

            # main bar
            painter.setBrush(QColor(0, 191, 255, 200))
            painter.drawRoundedRect(
                int(x), int(center_y - bar_h),
                int(bw), int(bar_h * 2), 2, 2
            )