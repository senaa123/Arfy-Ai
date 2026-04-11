from collections import defaultdict
from typing import Dict, List
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage


class SessionStore:
    """
    Stores short-term memory in RAM.
    This is NOT long-term memory.
    Long-term memory belongs to memory_service.
    """

    def __init__(self, max_turns: int = 12):
        # user + assistant pair count
        self.max_turns = max_turns

        # store structure:
        # {
        #   "session_id": [HumanMessage(...), AIMessage(...), ...]
        # }
        self.store: Dict[str, List[BaseMessage]] = defaultdict(list)

    def add_user_message(self, session_id: str, text: str) -> None:
        # save a user msg into session history
        self.store[session_id].append(HumanMessage(content=text))
        self._trim(session_id)

    def add_ai_message(self, session_id: str, text: str) -> None:
        # save AI msg into session history
        self.store[session_id].append(AIMessage(content=text))
        self._trim(session_id)

    def get_history(self, session_id: str) -> List[BaseMessage]:
        # return chat history for a session
        return self.store.get(session_id, [])

    def reset(self, session_id: str) -> None:
        # delete that session's history
        self.store.pop(session_id, None)

    def _trim(self, session_id: str) -> None:
        """
        Keep only the latest messages.

        max_turns means user+assistant pairs,
        so total messages allowed = max_turns * 2
        """
        max_messages = self.max_turns * 2

        if len(self.store[session_id]) > max_messages:
            self.store[session_id] = self.store[session_id][-max_messages:]