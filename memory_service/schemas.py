from typing import Any, Optional, List
from pydantic import BaseModel

class MemorySaveRequest(BaseModel):
    category: str
    key: str
    value: Any

class MemoryRetrieveRequest(BaseModel):
    query: str
    limit: int = 5

class ActionLogRequest(BaseModel):
    action: str
    type: str
    success: bool = True

class MemoryItemResponse(BaseModel):
    category: str
    key: str
    value: Any
    score: Optional[float] = None

class  ActionHistoryitem(BaseModel):
    action: str
    type: str
    success: bool
    timestamp: str