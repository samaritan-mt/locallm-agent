from pydantic import BaseModel, Field
from enum import Enum
class AllowedModels(str, Enum):
    QWEN = "qwen2.5:7b"
    LLAMA = "llama3.1:8b"
    MISTRAL = "mistral:7b"
    DEEPSEEK = "deepseek-coder:6.7b"
class LLMRunTimePolicyConfig(BaseModel):
    # Security: Using 127.0.0.1 as per agent.md security guidelines
    default_endpoint: str = Field(default="http://127.0.0.1:11434", description="The local Ollama API endpoint")
    default_model: AllowedModels = Field(default=AllowedModels.QWEN, description="Default model for localai ask")
    
    # Validation: Ensure temperature stays within safe logical boundaries
    default_temperature: float = Field(default=0.2, ge=0.0, le=1.0, description="LLM creativity temperature")
    default_stream: bool = False

class SessionPolicyConfig(BaseModel):
    # Security: All boundaries default to False as per the architecture spec
    can_read_files: bool = False
    can_write_files: bool = False
    can_execute_commands: bool = False
    can_access_secrets: bool = False
    can_access_network: bool = False
    can_access_memory: bool = False

    def is_allowed(self, action: str) -> bool:
        # Future implementation could map string actions to the boolean fields dynamically
        # E.g. return getattr(self, f"can_{action}", False)
        
        return False



