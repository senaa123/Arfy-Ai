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
    
    # Document picker method that blocks until the user picks a file or cancels
    def pick_document_file(self):
        """
        Open the native document picker on the Qt thread and return the path.

        Important:
        - runtime.py runs outside the UI thread
        - QFileDialog must open on the Qt/UI thread
        - BlockingQueuedConnection is intentional here so the runtime waits
          until the user finishes selecting or cancels the picker
        """
        self.window._last_picked_document_path = ""

        QMetaObject.invokeMethod(
            self.window,
            "open_document_picker",
            Qt.ConnectionType.BlockingQueuedConnection,
        )

        return getattr(self.window, "_last_picked_document_path", "")