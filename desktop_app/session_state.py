import uuid
from datetime import datetime


# Current live wake-session id.
# A new one is created every time Arfy wakes up.
def create_session_id() -> str:
    """
    Create a unique session id for each wake cycle.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_part = uuid.uuid4().hex[:8]
    return f"arfy_{timestamp}_{random_part}"