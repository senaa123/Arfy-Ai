from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

from agent_service.models import PendingAction, SessionMessage


class SessionStore:
    """
    Keeps only the active short-term session memory in RAM.

    Design:
    - Each wake cycle gets its own session_id
    - Only the latest N turns stay in RAM
    - Older messages can be archived elsewhere when they overflow
    - One pending follow-up action can be stored per session
    """

    def __init__(self, max_turns: int = 12):
        # max_turns means user+assistant pairs
        self.max_turns = max_turns

        # Active in-memory messages for each session
        self.store: Dict[str, List[SessionMessage]] = defaultdict(list)

        # Track when a session started
        self.started_at: Dict[str, str] = {}

        # NEW:
        # Stores one pending follow-up action per session.
        # Example: pending weather check for Balangoda
        self.pending_actions: Dict[str, PendingAction] = {}

    def _now_iso(self) -> str:
        """
        Return UTC timestamp in ISO format.
        """
        return datetime.now(timezone.utc).isoformat()

    def _ensure_session_started(self, session_id: str) -> None:
        """
        Create a session start timestamp if it does not exist yet.
        """
        if session_id not in self.started_at:
            self.started_at[session_id] = self._now_iso()

    def add_user_message(self, session_id: str, text: str) -> List[SessionMessage]:
        """
        Add a user message to RAM.
        Returns any overflowed messages that should be archived.
        """
        self._ensure_session_started(session_id)

        self.store[session_id].append(
            SessionMessage(
                role="user",
                content=text,
                timestamp=self._now_iso(),
            )
        )
        return self._trim(session_id)

    def add_ai_message(self, session_id: str, text: str) -> List[SessionMessage]:
        """
        Add an assistant message to RAM.
        Returns any overflowed messages that should be archived.
        """
        self._ensure_session_started(session_id)

        self.store[session_id].append(
            SessionMessage(
                role="assistant",
                content=text,
                timestamp=self._now_iso(),
            )
        )
        return self._trim(session_id)

    def get_history(self, session_id: str) -> List[SessionMessage]:
        """
        Return the current in-memory session history.
        """
        return list(self.store.get(session_id, []))

    def get_started_at(self, session_id: str) -> Optional[str]:
        """
        Return when this session started.
        """
        return self.started_at.get(session_id)

    # -------------------------
    # NEW: pending action helpers
    # -------------------------
    def set_pending_action(self, session_id: str, action: PendingAction) -> None:
        """
        Save a follow-up action that is waiting for confirmation.
        """
        self.pending_actions[session_id] = action

    def get_pending_action(self, session_id: str) -> Optional[PendingAction]:
        """
        Return the pending action for the session, if any.
        """
        return self.pending_actions.get(session_id)

    def clear_pending_action(self, session_id: str) -> None:
        """
        Remove the pending action for the session.
        """
        self.pending_actions.pop(session_id, None)

    def end_session(self, session_id: str) -> dict:
        """
        Return all remaining session data, then clear it from RAM.
        """
        payload = {
            "session_id": session_id,
            "session_started_at": self.started_at.get(session_id),
            "session_ended_at": self._now_iso(),
            "messages": list(self.store.get(session_id, [])),
        }

        self.reset(session_id)
        return payload

    def reset(self, session_id: str) -> None:
        """
        Delete the in-memory session.
        """
        self.store.pop(session_id, None)
        self.started_at.pop(session_id, None)
        self.pending_actions.pop(session_id, None)

    def _trim(self, session_id: str) -> List[SessionMessage]:
        """
        Keep only the latest messages in RAM.
        """
        max_messages = self.max_turns * 2
        overflowed: List[SessionMessage] = []

        while len(self.store[session_id]) > max_messages:
            remove_count = 2 if len(self.store[session_id]) >= 2 else 1
            overflowed.extend(self.store[session_id][:remove_count])
            self.store[session_id] = self.store[session_id][remove_count:]

        return overflowed