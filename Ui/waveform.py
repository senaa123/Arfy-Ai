from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import QTimer
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import time
import random

STATE_CONFIGS = {
    "idle":      {"displace": 0.0,   "jitter": 0.0,    "breathe": 0.005, "speed": 0.0,  "pulse": 0.0},
    "listening": {"displace": 0.015, "jitter": 0.003,  "breathe": 0.008, "speed": 0.4,  "pulse": 0.01},
    "speaking":  {"displace": 0.06,  "jitter": 0.015,  "breathe": 0.015, "speed": 1.2,  "pulse": 0.03},
    "thinking":  {"displace": 0.03,  "jitter": 0.006,  "breathe": 0.01,  "speed": 0.7,  "pulse": 0.02},
}

class JarvisOrb(QOpenGLWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = "idle"
        self.start_time = time.time()
        self.particles = []
        self.cfg = dict(STATE_CONFIGS["idle"])
        self.tgt = dict(STATE_CONFIGS["idle"])
        self._init_particles()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(16)

    def _init_particles(self):
        self.particles = []
        count = 2000
        golden_angle = math.pi * (3 - math.sqrt(5))

        for i in range(count):
            y = 1 - (i / (count - 1)) * 2
            theta = golden_angle * i
            phi = math.acos(max(-1.0, min(1.0, y)))

            self.particles.append({
                "theta": theta,
                "phi": phi,
                "base_r": 0.95 + random.random() * 0.1,
                "seed1": random.random() * 100,
                "seed2": random.random() * 100,
                "seed3": random.random() * 100,
                "size": 0.8 + random.random() * 1.2,
                "brightness": 0.4 + random.random() * 0.6,
            })

    def set_state(self, state):
        self.state = state
        self.tgt = dict(STATE_CONFIGS.get(state, STATE_CONFIGS["idle"]))

    def _lerp(self, a, b, t):
        return a + (b - a) * t

    def initializeGL(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        glClearColor(0.0, 0.0, 0.0, 1.0)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = w / h if h != 0 else 1
        gluPerspective(45, aspect, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0, 0, -2.8)

        t = time.time() - self.start_time

        # smooth config transition
        for key in self.cfg:
            self.cfg[key] = self._lerp(self.cfg[key], self.tgt[key], 0.03)

        cfg = self.cfg
        speed = cfg["speed"]
        breathe = 1.0 + math.sin(t * 0.8) * cfg["breathe"]

        # collect projected particles
        projected = []

        for p in self.particles:
            sin_phi = math.sin(p["phi"])
            cos_phi = math.cos(p["phi"])
            cos_theta = math.cos(p["theta"])
            sin_theta = math.sin(p["theta"])

            # base sphere position
            px = sin_phi * cos_theta
            py = cos_phi
            pz = sin_phi * sin_theta

            # state displacement
            displace = cfg["displace"]
            dx = math.sin(t * speed * 0.7 + p["seed1"]) * displace
            dy = math.sin(t * speed * 0.9 + p["seed2"]) * displace
            dz = math.sin(t * speed * 0.6 + p["seed3"]) * displace

            # jitter
            jitter = cfg["jitter"]
            jx = math.sin(t * 12 + p["seed1"] * 7) * jitter
            jy = math.sin(t * 14 + p["seed2"] * 7) * jitter
            jz = math.sin(t * 11 + p["seed3"] * 7) * jitter

            # pulse wave
            pulse_phase = t * 2 + p["phi"] * 2
            pulse = math.sin(pulse_phase) * cfg["pulse"]

            r = p["base_r"] * breathe + pulse

            x3 = (px + dx + jx) * r
            y3 = (py + dy + jy) * r
            z3 = (pz + dz + jz) * r

            # depth based brightness
            normal_brightness = (pz + 1) * 0.5
            edge_fade = 1 - abs(pz) ** 3 * 0.3
            final_brightness = p["brightness"] * normal_brightness * edge_fade

            projected.append((x3, y3, z3, final_brightness, p["size"]))

        # sort back to front
        projected.sort(key=lambda p: p[2])

        # draw particles
        for x3, y3, z3, brightness, size in projected:
            depth_norm = (z3 + 1) * 0.5
            alpha = brightness * (0.2 + depth_norm * 0.8) * 0.85
            sz = size * (0.6 + depth_norm * 0.6) * 0.008

            if alpha < 0.03:
                continue

            glPointSize(max(1.0, sz * 100))
            glBegin(GL_POINTS)
            lum = 0.5 + brightness * 0.45
            glColor4f(lum, lum, lum, alpha)
            glVertex3f(x3, y3, z3)
            glEnd()

        # outer glow
        self._draw_glow(breathe)

    def _draw_glow(self, breathe):
        glPushMatrix()
        segments = 64
        cfg = self.cfg

        if self.state == "idle":
            glow_alpha = 0.03
        elif self.state == "listening":
            glow_alpha = 0.06
        elif self.state == "speaking":
            glow_alpha = 0.12
        else:
            glow_alpha = 0.08

        for layer in range(3):
            r = (1.0 + layer * 0.2) * breathe
            alpha = glow_alpha * (1.0 - layer * 0.3)
            glBegin(GL_LINE_LOOP)
            for i in range(segments):
                theta = 2 * math.pi * i / segments
                x = r * math.cos(theta)
                y = r * math.sin(theta) * 0.65
                glColor4f(1.0, 1.0, 1.0, alpha)
                glVertex3f(x, y, 0)
            glEnd()

        glPopMatrix()