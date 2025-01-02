from typing import NotRequired, Any, TypedDict

class Thread(TypedDict):
    """
    Represents a chat thread
    """
    
    id: str
    title: str
    created_at: str
    state: NotRequired[Any]  # This will store the agent's state
