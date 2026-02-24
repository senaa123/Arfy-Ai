# ui/orb.py
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import QTimer, Qt
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import math
import time

class JarvisOrb(QOpenGLWidget):
    
    STATE_IDLE = "idle"
    STATE_LISTENING = "listening"
    STATE_SPEAKING = "speaking"
    STATE_THINKING = "thinking"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = self.STATE_IDLE
        self.angle = 0.0
        self.pulse = 0.0
        self.energy = 0.0
        self.rings = []
        self.particles = []
        self.start_time = time.time()

        self._init_rings()
        self._init_particles()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)  # 60fps

    def _init_rings(self):
        self.rings = [
            {"radius": 0.3, "tilt": 0, "speed": 0.8, "angle": 0},
            {"radius": 0.5, "tilt": 45, "speed": -0.5, "angle": 120},
            {"radius": 0.7, "tilt": 75, "speed": 0.6, "angle": 240},
            {"radius": 0.45, "tilt": 20, "speed": -0.9, "angle": 60},
            {"radius": 0.6, "tilt": 60, "speed": 0.4, "angle": 180},
        ]

    def _init_particles(self):
        self.particles = []
        for _ in range(80):
            angle = np.random.uniform(0, 2 * math.pi)
            radius = np.random.uniform(0.2, 0.8)
            speed = np.random.uniform(0.3, 1.2)
            self.particles.append({
                "angle": angle,
                "radius": radius,
                "speed": speed,
                "size": np.random.uniform(1, 3),
                "brightness": np.random.uniform(0.3, 1.0)
            })

    def set_state(self, state):
        self.state = state

    def get_speed_multiplier(self):
        if self.state == self.STATE_IDLE:
            return 0.5
        elif self.state == self.STATE_LISTENING:
            return 1.5
        elif self.state == self.STATE_SPEAKING:
            return 2.5
        elif self.state == self.STATE_THINKING:
            return 1.0
        return 1.0

    def get_glow_intensity(self):
        if self.state == self.STATE_IDLE:
            return 0.4
        elif self.state == self.STATE_LISTENING:
            return 0.8
        elif self.state == self.STATE_SPEAKING:
            return 1.0
        elif self.state == self.STATE_THINKING:
            return 0.6 + 0.3 * math.sin(time.time() * 5)
        return 0.5

    def update_animation(self):
        speed = self.get_speed_multiplier()
        self.angle += 0.5 * speed
        self.pulse = math.sin(time.time() * 2) * 0.5 + 0.5

        for ring in self.rings:
            ring["angle"] += ring["speed"] * speed

        for particle in self.particles:
            particle["angle"] += particle["speed"] * 0.01 * speed

        self.update()

    def initializeGL(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glClearColor(0.0, 0.02, 0.05, 1.0)

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
        glTranslatef(0, 0, -3)

        intensity = self.get_glow_intensity()

        # draw core glow
        self._draw_core(intensity)

        # draw rings
        for ring in self.rings:
            self._draw_ring(ring, intensity)

        # draw particles
        self._draw_particles(intensity)

        # draw outer energy field
        self._draw_energy_field(intensity)

    def _draw_core(self, intensity):
        glPushMatrix()
        glRotatef(self.angle, 0, 1, 0)

        # inner core
        for layer in range(5):
            alpha = intensity * (1.0 - layer * 0.15)
            scale = 0.1 + layer * 0.04 + self.pulse * 0.02
            r = 0.1 + layer * 0.05
            g = 0.5 + layer * 0.1
            b = 1.0
            glColor4f(r, g, b, alpha)
            self._draw_circle(scale, 32)

        glPopMatrix()

    def _draw_ring(self, ring, intensity):
        glPushMatrix()
        glRotatef(ring["tilt"], 1, 0, 0)
        glRotatef(ring["angle"], 0, 1, 0)

        glLineWidth(1.0)
        segments = 64
        glBegin(GL_LINE_LOOP)
        for i in range(segments):
            theta = 2 * math.pi * i / segments
            x = ring["radius"] * math.cos(theta)
            y = ring["radius"] * math.sin(theta)
            brightness = 0.5 + 0.5 * math.sin(theta * 3 + ring["angle"] * 0.1)
            glColor4f(0.0, brightness * 0.7 * intensity, intensity, brightness * intensity)
            glVertex3f(x, y, 0)
        glEnd()

        # ring glow dots
        glPointSize(2.0)
        glBegin(GL_POINTS)
        for i in range(0, segments, 4):
            theta = 2 * math.pi * i / segments
            x = ring["radius"] * math.cos(theta)
            y = ring["radius"] * math.sin(theta)
            glColor4f(0.3, 0.8, 1.0, intensity * 0.8)
            glVertex3f(x, y, 0)
        glEnd()

        glPopMatrix()

    def _draw_particles(self, intensity):
        glPointSize(2.0)
        glBegin(GL_POINTS)
        for p in self.particles:
            x = p["radius"] * math.cos(p["angle"])
            y = p["radius"] * math.sin(p["angle"]) * 0.5
            z = p["radius"] * math.sin(p["angle"] * 0.7)
            alpha = p["brightness"] * intensity
            glColor4f(0.2, 0.7, 1.0, alpha)
            glVertex3f(x, y, z)
        glEnd()

    def _draw_energy_field(self, intensity):
        glPushMatrix()
        glRotatef(self.angle * 0.3, 0, 1, 0)

        segments = 128
        for layer in range(3):
            radius = 0.85 + layer * 0.05 + self.pulse * 0.03
            glBegin(GL_LINE_LOOP)
            for i in range(segments):
                theta = 2 * math.pi * i / segments
                noise = 0.02 * math.sin(theta * 8 + self.angle * 0.05)
                r = (radius + noise) * math.cos(theta)
                y = (radius + noise) * math.sin(theta) * 0.6
                z = (radius + noise) * math.sin(theta) * 0.3
                alpha = (0.3 - layer * 0.08) * intensity
                glColor4f(0.0, 0.5, 1.0, alpha)
                glVertex3f(r, y, z)
            glEnd()

        glPopMatrix()

    def _draw_circle(self, radius, segments):
        glBegin(GL_LINE_LOOP)
        for i in range(segments):
            theta = 2 * math.pi * i / segments
            glVertex3f(radius * math.cos(theta), radius * math.sin(theta), 0)
        glEnd()