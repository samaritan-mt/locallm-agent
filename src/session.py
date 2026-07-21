import typer
import shlex
MAX_INPUT_CHARS = 1000000
MAX_HISTORY_LENGTH = 200
from tools.schemas import ollama_json_schema, write_file_schema, read_file_schema
from policy.prompts import DynamicPromptManager

class SecureChatSession:
    def __init__(self):
        pm = DynamicPromptManager()

        enabled_tools = [ollama_json_schema(), write_file_schema(), read_file_schema()]

        dynamic_enabled_tools = [schema["function"]["name"] for schema in enabled_tools]

        self.system_prompt = pm.build_system_prompt(
    template_name="base_agent",
    enabled_tools=dynamic_enabled_tools,
    max_input_chars=10000
        )
        self.messages = [{"role": "system", "content": self.system_prompt}]
    
    def add_user_message(self, prompt: str):
        if len(prompt) > MAX_INPUT_CHARS:
            raise ValueError("Input prompt exceeds maximum length")
        self.messages.append({"role": "user", "content": prompt})
        
    
    def add_assistant_message(self, response: str):
        self.messages.append({"role": "assistant", "content": response})
        
    def add_tool_message(self, result: str):
        self.messages.append({"role": "tool", "content": result})
    
    def get_context(self):
        if len(self.messages) > MAX_HISTORY_LENGTH:
            # Keep the newest messages, but make sure to preserve the system prompt at the very beginning
            self.messages = self.messages[-MAX_HISTORY_LENGTH:]
            # Ensure the first message is the system prompt if it was truncated
            if self.messages[0].get("role") != "system":
                self.messages.insert(0, {"role": "system", "content": self.system_prompt})
        return self.messages
    
    def clear(self):
        self.messages = [{"role": "system", "content": self.system_prompt}]
    
    def output_message(self, message: str): 
        # message = message.encode(encoding="utf-8",errors="backslashreplace").decode(encoding="utf-8",errors="ignore")
        message = shlex.quote(message) 
        typer.echo(message, nl=True)
    