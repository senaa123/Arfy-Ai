from PyQt6.QtCore import Q_ARG, QMetaObject, Qt


class DesktopUIBridge:
    """
    Small thread-safe bridge for updating the Qt UI from runtime code.

    Why this file exists:
    - desktop_app/runtime.py runs the assistant loop
    - that loop should not repeat raw QMetaObject.invokeMethod(...) calls everywhere
    - this keeps UI update wiring in one place
    """

    def __init__(self, window):
        self.window = window

    def set_state(self, state: str):
        QMetaObject.invokeMethod(
            self.window,
            "set_state",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, state),
        )

    def add_chat(self, sender: str, message: str):
        QMetaObject.invokeMethod(
            self.window,
            "add_chat",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, sender),
            Q_ARG(str, message),
        )

    def show_input(self):
        QMetaObject.invokeMethod(
            self.window,
            "show_input",
            Qt.ConnectionType.QueuedConnection,
        )

    def hide_input(self):
        QMetaObject.invokeMethod(
            self.window,
            "hide_input",
            Qt.ConnectionType.QueuedConnection,
        )

    def set_mode_label(self, mode: str):
        QMetaObject.invokeMethod(
            self.window,
            "set_mode_label",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, mode),
        )