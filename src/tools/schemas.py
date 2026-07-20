
def ollama_json_schema():
    return  {
  "type": "function",
  "function": {
    "name": "execute_os_command",
    "description": "Execute a shell command on the user's macOS system.",
    "parameters": {
      "type": "object",
      "properties": {
        "command": {
          "type": "string",
          "description": "The exact shell command to execute."
        }
      },
      "required": ["command"]
    }
  }
}