def route_local_intent(text: str) -> dict | None:
    """
    Handle only a few instant desktop-local commands.

    Everything else should go to the agent service.
    """
    user_text = text.strip().lower()

    if user_text in {"stop listening", "stop"}:
        return {"type": "local_command", "command": "stop_listening"}

    if user_text in {"shutdown arfy", "shut down arfy", "exit arfy"}:
        return {"type": "local_command", "command": "shutdown_arfy"}

    if user_text in {"hide window", "hide arfy"}:
        return {"type": "local_command", "command": "hide_window"}

    if user_text in {"show window", "show arfy"}:
        return {"type": "local_command", "command": "show_window"}

    return None