from pydantic import BaseModel
from datetime import datetime, timezone

class AskAuditEvent(BaseModel):
    timestamp: str = ""
    command: str = "ask"
    model: str
    input_chars: int
    endpoint_type: str = "local"
    success: bool
    
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-generate UTC ISO timestamp if not provided
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

class SessionAuditEvent(BaseModel):
    timestamp: str = ""
    command: str = "agent"
    model: str
    input_chars: int
    output_chars: int
    total_turns: int
    endpoint_type: str = "local"
    success: bool
    
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-generate UTC ISO timestamp if not provided
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        