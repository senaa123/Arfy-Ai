from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

from agent_service.models import MemoryItem, SessionMessage


class ToolContext(BaseModel):
    """
    Standard runtime input passed into every tool plugin.

    Why this exists:
    - every tool gets one consistent input shape
    - avoids random custom payloads for each tool
    - makes future HTTP tools easier later
    """

    # Current active session ID
    session_id: str

    # Original user text
    user_text: str

    # Data extracted by the router
    extracted_data: Dict[str, Any] = Field(default_factory=dict)

    # Long-term retrieved memories
    memories: List[MemoryItem] = Field(default_factory=list)

    # Live short-term history
    history: List[SessionMessage] = Field(default_factory=list)


class ToolSpec(BaseModel):
    """
    Static metadata that describes a tool/plugin.
    """

    # Unique internal name
    name: str

    # Human-readable description
    description: str

    # Local now, HTTP later if needed
    transport: Literal["local", "http"] = "local"

    # What intents this tool can handle
    supported_intents: List[str] = Field(default_factory=list)

    # Enable/disable without removing code
    enabled: bool = True

    # Soft timeout metadata
    timeout_seconds: int = 15


class ToolPlugin(ABC):
    """
    Base class for all Arfy tool plugins.
    """

    spec: ToolSpec

    def supports_intent(self, intent: str | None) -> bool:
        """
        Check whether this tool supports the given intent.
        """
        if intent is None:
            return False
        return intent in self.spec.supported_intents

    def health(self) -> dict[str, Any]:
        """
        Basic health response.
        """
        return {
            "success": True,
            "tool": self.spec.name,
            "enabled": self.spec.enabled,
            "transport": self.spec.transport,
        }

    @abstractmethod
    def execute(self, context: ToolContext) -> dict[str, Any]:
        """
        Execute the tool.
        Must return a normalized dict result.
        """
        raise NotImplementedError