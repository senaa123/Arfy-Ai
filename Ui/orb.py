from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import QTimer
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import time
import random

class JarvisOrb(QOpenGLWidget):

    STATE_IDLE = "idle"
    STATE_LISTENING = "listening"
    STATE_SPEAKING = "speaking"
    STATE_THINKING = "thinking"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = self.STATE_IDLE
        self.angle = 0.0
        self.start_time = time.time()
        self.nodes = []
        self._init_nodes()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(16)

    def _init_nodes(self):
        self.nodes = []
        for _ in range(50):
            theta = random.uniform(0, 2 * math.pi)
            phi = random.uniform(0, math.pi)
            r = random.uniform(0.3, 0.85)

            x = r * math.sin(phi) * math.cos(theta)
            y = r * math.sin(phi) * math.sin(theta) * 0.65
            z = r * math.cos(phi) * 0.5

            self.nodes.append({
                # original resting position
                "ox": x, "oy": y, "oz": z,
                # current position
                "x": x, "y": y, "z": z,
                # velocity
                "vx": 0.0, "vy": 0.0, "vz": 0.0,
                # unique motion personality
                "freq": random.uniform(0.2, 0.8),
                "phase": random.uniform(0, 2 * math.pi),
                "amp_idle": random.uniform(0.005, 0.015),
                "amp_listen": random.uniform(0.02, 0.04),
                "amp_speak": random.uniform(0.06, 0.12),
                "pulse_offset": random.uniform(0, 2 * math.pi),
                "brightness": random.uniform(0.6, 1.0),
                "size": random.uniform(2.0, 4.5),
                # trail
                "trail": [],
                "trail_max": 15,
            })

    def _get_connections(self):
        connections = []
        for i in range(len(self.nodes)):
            for j in range(i + 1, len(self.nodes)):
                n1 = self.nodes[i]
                n2 = self.nodes[j]
                dist = math.sqrt(
                    (n1["x"] - n2["x"]) ** 2 +
                    (n1["y"] - n2["y"]) ** 2 +
                    (n1["z"] - n2["z"]) ** 2
                )
                if dist < 0.5:
                    connections.append((i, j, dist))
        return connections

    def set_state(self, state):
        self.state = state

    def update_animation(self):
        t = time.time()

        # slow gentle rotation always
        if self.state == self.STATE_IDLE:
            self.angle += 0.08
        elif self.state == self.STATE_LISTENING:
            self.angle += 0.12
        elif self.state == self.STATE_SPEAKING:
            self.angle += 0.25
        elif self.state == self.STATE_THINKING:
            self.angle += 0.10

        for node in self.nodes:
            # save trail
            node["trail"].append((node["x"], node["y"], node["z"]))
            if len(node["trail"]) > node["trail_max"]:
                node["trail"].pop(0)

            ox, oy, oz = node["ox"], node["oy"], node["oz"]

            if self.state == self.STATE_IDLE:
                # barely breathing — tiny sine drift around origin
                amp = node["amp_idle"]
                node["x"] = ox + amp * math.sin(t * node["freq"] + node["phase"])
                node["y"] = oy + amp * math.cos(t * node["freq"] * 0.7 + node["phase"])
                node["z"] = oz + amp * math.sin(t * node["freq"] * 0.5 + node["phase"])

            elif self.state == self.STATE_LISTENING:
                # slightly more movement, aware but calm
                amp = node["amp_listen"]
                node["x"] = ox + amp * math.sin(t * node["freq"] * 1.5 + node["phase"])
                node["y"] = oy + amp * math.cos(t * node["freq"] * 1.2 + node["phase"])
                node["z"] = oz + amp * math.sin(t * node["freq"] + node["phase"] + 0.5)

            elif self.state == self.STATE_THINKING:
                # fold inward and stretch outward alternating
                fold = math.sin(t * 0.8 + node["phase"])  # -1 to 1
                if fold > 0:
                    # stretching outward
                    scale = 1.0 + fold * 0.4
                else:
                    # folding inward
                    scale = 1.0 + fold * 0.3

                amp = node["amp_listen"] * 1.5
                node["x"] = ox * scale + amp * math.sin(t * node["freq"] * 2 + node["phase"])
                node["y"] = oy * scale + amp * math.cos(t * node["freq"] * 1.5 + node["phase"])
                node["z"] = oz * scale + amp * math.sin(t * node["freq"] + node["phase"])

            elif self.state == self.STATE_SPEAKING:
                # active movement — particles travel around freely
                amp = node["amp_speak"]
                # fast organic wandering
                node["vx"] += amp * math.sin(t * node["freq"] * 3 + node["phase"]) * 0.08
                node["vy"] += amp * math.cos(t * node["freq"] * 2.5 + node["phase"]) * 0.08
                node["vz"] += amp * math.sin(t * node["freq"] * 2 + node["phase"] + 1) * 0.08

                # damping so they don't fly away
                node["vx"] *= 0.92
                node["vy"] *= 0.92
                node["vz"] *= 0.92

                # spring back toward origin loosely
                node["vx"] += (ox - node["x"]) * 0.015
                node["vy"] += (oy - node["y"]) * 0.015
                node["vz"] += (oz - node["z"]) * 0.015

                node["x"] += node["vx"]
                node["y"] += node["vy"]
                node["z"] += node["vz"]

            # pulse brightness
            node["brightness"] = 0.55 + 0.45 * math.sin(t * 1.5 + node["pulse_offset"])

        self.update()

    def get_global_brightness(self):
        t = time.time()
        if self.state == self.STATE_IDLE:
            return 0.35 + 0.08 * math.sin(t * 0.6)
        elif self.state == self.STATE_LISTENING:
            return 0.6 + 0.1 * math.sin(t * 2)
        elif self.state == self.STATE_SPEAKING:
            return 0.8 + 0.2 * math.sin(t * 10)
        elif self.state == self.STATE_THINKING:
            return 0.5 + 0.2 * math.sin(t * 4) * math.sin(t * 1.7)
        return 0.5

    def initializeGL(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glEnable(GL_LINE_SMOOTH)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
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
        glTranslatef(0, 0, -3)
        glRotatef(self.angle, 0, 1, 0.1)

        brightness = self.get_global_brightness()
        connections = self._get_connections()

        self._draw_trails(brightness)
        self._draw_connections(connections, brightness)
        self._draw_nodes(brightness)

    def _draw_trails(self, brightness):
        # only draw trails when speaking or thinking
        if self.state not in [self.STATE_SPEAKING, self.STATE_THINKING]:
            return

        for node in self.nodes:
            trail = node["trail"]
            if len(trail) < 2:
                continue

            glBegin(GL_LINE_STRIP)
            for idx, (tx, ty, tz) in enumerate(trail):
                progress = idx / len(trail)
                if self.state == self.STATE_SPEAKING:
                    alpha = brightness * progress * 0.35 * node["brightness"]
                else:
                    alpha = brightness * progress * 0.2 * node["brightness"]
                glColor4f(1.0, 1.0, 1.0, alpha)
                glVertex3f(tx, ty, tz)
            glEnd()

    def _draw_connections(self, connections, brightness):
        t = time.time()
        for i, j, dist in connections:
            n1 = self.nodes[i]
            n2 = self.nodes[j]

            base_alpha = brightness * (1.0 - dist / 0.5) * 0.45

            if self.state == self.STATE_IDLE:
                alpha = base_alpha * 0.6
            elif self.state == self.STATE_LISTENING:
                alpha = base_alpha * 0.8
            elif self.state == self.STATE_SPEAKING:
                alpha = base_alpha * (0.5 + 0.5 * math.sin(t * 18 + dist * 12))
            elif self.state == self.STATE_THINKING:
                alpha = base_alpha * (0.4 + 0.6 * abs(math.sin(t * 3 + dist * 6)))
            else:
                alpha = base_alpha

            glLineWidth(0.7)
            glBegin(GL_LINES)
            glColor4f(1.0, 1.0, 1.0, alpha)
            glVertex3f(n1["x"], n1["y"], n1["z"])
            glColor4f(1.0, 1.0, 1.0, alpha * 0.2)
            glVertex3f(n2["x"], n2["y"], n2["z"])
            glEnd()

    def _draw_nodes(self, brightness):
        t = time.time()
        for node in self.nodes:
            alpha = brightness * node["brightness"]
            size = node["size"]

            if self.state == self.STATE_SPEAKING:
                size *= 1.4 + 0.4 * math.sin(t * 10 + node["pulse_offset"])
            elif self.state == self.STATE_LISTENING:
                size *= 1.1 + 0.1 * math.sin(t * 4 + node["pulse_offset"])
            elif self.state == self.STATE_THINKING:
                size *= 1.0 + 0.3 * abs(math.sin(t * 2 + node["pulse_offset"]))

            # soft outer glow
            glPointSize(size * 3.5)
            glBegin(GL_POINTS)
            glColor4f(1.0, 1.0, 1.0, alpha * 0.05)
            glVertex3f(node["x"], node["y"], node["z"])
            glEnd()

            # mid glow
            glPointSize(size * 2)
            glBegin(GL_POINTS)
            glColor4f(1.0, 1.0, 1.0, alpha * 0.15)
            glVertex3f(node["x"], node["y"], node["z"])
            glEnd()

            # bright core
            glPointSize(size * 0.8)
            glBegin(GL_POINTS)
            glColor4f(1.0, 1.0, 1.0, alpha)
            glVertex3f(node["x"], node["y"], node["z"])
            glEnd()