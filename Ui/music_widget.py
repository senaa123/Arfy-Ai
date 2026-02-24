from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSlider
from PyQt6.QtCore import Qt, pyqtSignal

class MusicWidget(QWidget):
    prev_clicked = pyqtSignal()
    play_pause_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    volume_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("musicWidget")
        self.is_playing = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # song label
        self.song_label = QLabel("♫ No music playing")
        self.song_label.setObjectName("songLabel")
        self.song_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.song_label)

        # controls
        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.prev_btn = QPushButton("⏮")
        self.play_btn = QPushButton("⏸")
        self.next_btn = QPushButton("⏭")

        for btn in [self.prev_btn, self.play_btn, self.next_btn]:
            btn.setObjectName("musicBtn")

        self.prev_btn.clicked.connect(self.prev_clicked.emit)
        self.play_btn.clicked.connect(self._toggle_play)
        self.next_btn.clicked.connect(self.next_clicked.emit)

        controls.addStretch()
        controls.addWidget(self.prev_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.next_btn)
        controls.addStretch()
        layout.addLayout(controls)

        # volume
        vol_layout = QHBoxLayout()
        vol_icon = QLabel("🔊")
        vol_icon.setFixedWidth(20)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.valueChanged.connect(self.volume_changed.emit)

        vol_layout.addWidget(vol_icon)
        vol_layout.addWidget(self.volume_slider)
        layout.addLayout(vol_layout)

    def _toggle_play(self):
        self.is_playing = not self.is_playing
        self.play_btn.setText("⏸" if self.is_playing else "▶")
        self.play_pause_clicked.emit()

    def update_song(self, song_name):
        self.song_label.setText(f"♫ {song_name}")
        self.is_playing = True
        self.play_btn.setText("⏸")