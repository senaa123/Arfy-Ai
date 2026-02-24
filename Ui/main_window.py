from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QLabel, QPushButton)
from PyQt6.QtCore import Qt, QPoint, pyqtSlot
from PyQt6.QtGui import QFont
from Ui.orb import JarvisOrb
from Ui.waveform import WaveformWidget
from Ui.chat_widget import ChatWidget
from Ui.music_widget import MusicWidget
from Ui.styles import MAIN_STYLE

class ArfyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(MAIN_STYLE)
        self.setFixedSize(380, 600)

        self._drag_pos = QPoint()
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("mainWidget")
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # title bar
        title_bar = QHBoxLayout()
        title = QLabel("◈ A R F Y  A I")
        title.setObjectName("titleLabel")

        min_btn = QPushButton("─")
        min_btn.setObjectName("minimizeBtn")
        min_btn.clicked.connect(self.showMinimized)

        close_btn = QPushButton("×")
        close_btn.setObjectName("closeBtn")
        close_btn.clicked.connect(self.hide)  # hide to tray instead of closing

        title_bar.addWidget(title)
        title_bar.addStretch()
        title_bar.addWidget(min_btn)
        title_bar.addWidget(close_btn)
        layout.addLayout(title_bar)

        # status
        self.status_label = QLabel("STANDBY MODE")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # orb
        self.orb = JarvisOrb()
        self.orb.setFixedHeight(220)
        layout.addWidget(self.orb)

        # waveform
        self.waveform = WaveformWidget()
        self.waveform.setFixedHeight(50)
        layout.addWidget(self.waveform)

        # chat
        self.chat = ChatWidget()
        self.chat.setFixedHeight(160)
        layout.addWidget(self.chat)

        # music
        self.music = MusicWidget()
        self.music.setFixedHeight(100)
        layout.addWidget(self.music)

        # connect music signals
        self.music.prev_clicked.connect(self._prev_song)
        self.music.next_clicked.connect(self._next_song)
        self.music.play_pause_clicked.connect(self._play_pause)
        self.music.volume_changed.connect(self._volume_change)

    @pyqtSlot(str)
    def set_state(self, state):
        self.orb.set_state(state)
        states = {
            "idle": ("STANDBY MODE", False),
            "listening": ("LISTENING...", True),
            "speaking": ("SPEAKING...", True),
            "thinking": ("PROCESSING...", False)
        }
        label, wave_active = states.get(state, ("STANDBY MODE", False))
        self.status_label.setText(label)
        self.waveform.set_active(wave_active)

    @pyqtSlot(str, str)
    def add_chat(self, sender, message):
        self.chat.add_message(sender, message)

    @pyqtSlot(str)
    def update_song(self, song_name):
        self.music.update_song(song_name)

    # drag window
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def _prev_song(self):
        from spotify import previous_song
        previous_song()

    def _next_song(self):
        from spotify import next_song
        next_song()

    def _play_pause(self):
        from spotify import pause_music, resume_music
        if self.music.is_playing:
            resume_music()
        else:
            pause_music()

    def _volume_change(self, value):
        try:
            from spotify import sp
            sp.volume(value)
        except:
            pass