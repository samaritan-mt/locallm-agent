import typer
import shlex
MAX_INPUT_CHARS = 10000
MAX_HISTORY_LENGTH = 20

class SecureChatSession:
    def __init__(self):
        self.system_prompt = "You are a helpful assistant."
        self.messages = [{"role": "system", "content": self.system_prompt}]
    
    def add_user_message(self, prompt: str):
        if len(prompt) > MAX_INPUT_CHARS:
            raise ValueError("Input prompt exceeds maximum length")
        self.messages.append({"role": "user", "content": prompt})
        
    
    def add_assistant_message(self, response: str):
        self.messages.append({"role": "assistant", "content": response})
    
    def get_context(self):
        if len(self.messages) > MAX_HISTORY_LENGTH:
            self.messages = self.messages[:MAX_HISTORY_LENGTH]
            self.messages.insert(0, {"role": "system", "content": self.system_prompt})
        return self.messages
    
    def clear(self):
        self.messages = [{"role": "system", "content": self.system_prompt}]
    
    def output_message(self, message: str): 
        # message = message.encode(encoding="utf-8",errors="backslashreplace").decode(encoding="utf-8",errors="ignore")
        message = shlex.quote(message) 
        typer.echo(message, nl=True)
    