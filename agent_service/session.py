from collections import defaultdict
from typing import Dict, List
from langchain_core.messages import HumanMessage, AIMessage

class SessionStore:
    """
    Stores short-term memory in RAM.
    This is NOT long-term memory.
    Long-term memory belongs to memory_service.
    """

    def  __init__(self, max_turns: int = 12):

        #user+assistant pair count
        self.max_turns = max_turns

        #store structure
        self.store: Dict[str, List[dict]] = defaultdict(list)

    def add_user_message(self, session_id: str, text: str) -> None:
        #save a user msg into session history
        self.store[session_id].append(HumanMessage(content=text))
        self._trim(session_id)

        
    def add_ai_message(self, session_id: str, text: str) -> None:
        # Save Ai msg into session history
        self.store[session_id].append(AIMessage(content=text))
        self._trim(session_id)

    def get_history(self, session_id: str):
        #return chat history for a session
        return self.store.get(session_id, [])
    
    def reset(self, session_id: str):
        #Delete that session's history
        self.store.pop(session_id, None)

    def _trim(self, session_id: str):
        #keep only the latest msgs 
        if len(self.store[session_id]) > self.max_turns * 2:
            self.store[session_id] = self.store[session_id][-self.max_turns * 2]
