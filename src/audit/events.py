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
    execution_enabled: bool = False
    success: bool
    
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-generate UTC ISO timestamp if not provided
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
class ProviderSwitchAuditEvent(BaseModel):
    timestamp: str = ""
    event: str = "provider_switch"
    from_provider: str
    to_provider: str
    model: str
    success: bool

    def __init__(self, **data):
        super().__init__(**data)
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def model_dump(self, **kwargs):
        # Serialize with the doc's field names ("from"/"to") without shadowing
        # the reserved `from` keyword as an actual Python attribute.
        data = super().model_dump(**kwargs)
        data["from"] = data.pop("from_provider")
        data["to"] = data.pop("to_provider")
        return data

    def model_dump_json(self, **kwargs):
        import json
        return json.dumps(self.model_dump())


class RemoteCallAuditEvent(BaseModel):
    timestamp: str = ""
    command: str = "agent"
    provider: str
    model: str
    input_chars: int
    output_tokens_estimate: int
    success: bool

    def __init__(self, **data):
        super().__init__(**data)
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class ToolExecutionEvent(BaseModel):
    timestamp: str = ""
    tool_name: str
    arguments: str
    user_approved: bool
    success: bool
    
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-generate UTC ISO timestamp if not provided
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()