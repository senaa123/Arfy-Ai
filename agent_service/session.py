from collections import defaultdict
from typing import Dict, List

class SessionStore:
    def  __init__(self, max_turns: int = 12):

        #user+assistant pair count
        self.max_turns = max_turns

        #store structure
        self.store: Dict[str, List[dict]] = defaultdict(list)

    def add_user_message(self, session_id: str, text: str) -> None:
        #save a user msg into session history
        self.store[session_id].append({"role": "user", "content": text})
        self._trim(session_id)

    def add_assistant_message(self, session_id: str, text: str) -> None:
        # Save an assisteant msg into session history
        self.store[session_id].append({"role": "assistant", "content": text})
        self._trim(session_id)

    def get_history(self, session_id: str) -> List[dict]:
        #return chat history for a session
        return self.store.get(session_id, None)
    
    def rest(self, session_id: str) -> None:
        #Delete that session's history
        self.store.pop(session_id, None)

    def _trim(self, session_id: str) -> None:
        #keep only the newest msgs 
        if len(self.store[session_id]) > self.max_turns * 2:
            self.store[session_id] = self.store[session_id][-self.max_turns * 2]
