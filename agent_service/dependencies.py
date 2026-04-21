# agent_service/dependencies.py

from fastapi import Request


def get_graph(request: Request):
    """
    Return the compiled LangGraph instance stored on app.state.

    Why this file exists in Phase 4B:
    - route files should not import bootstrap globals from main.py
    - app runtime objects should be read from one shared place
    """
    return request.app.state.graph


def get_session_store(request: Request):
    """
    Return the in-memory session store stored on app.state.
    """
    return request.app.state.session_store