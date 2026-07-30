def ollama_json_schema():
    return  {
      "type": "function",
      "function": {
        "name": "execute_os_command",
        "description": "Execute a shell command inside a sandboxed Docker container running python:3.11-alpine. The user's current directory is mounted at /workspace. You have full access to read and modify project files in this directory. If you need external Python packages like nltk, you must pip install them first.",
        "parameters": {
          "type": "object",
          "properties": {
            "thought": {
              "type": "string",
              "description": "Your internal reasoning. You MUST structure this using your dynamically chosen framework (e.g., STAR, OODA) with strict headings: Framework Selection, Structured Execution, and Outcome Prediction. ALWAYS provide this before executing."
            },
            "command": {
              "type": "string",
              "description": "The exact shell command to execute inside the Alpine container."
            }
          },
          "required": ["thought", "command"]
        }
      }
    }



def write_file_schema():
    return {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file on the user's local filesystem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "Your reasoning using the dynamic framework (STAR, OODA). ALWAYS provide this."
                    },
                    "filepath": {
                        "type": "string",
                        "description": "The path to the file to create or overwrite (e.g., analyze.py)."
                    },
                    "content": {
                        "type": "string",
                        "description": "The raw string content to write to the file."
                    }
                },
                "required": ["thought", "filepath", "content"]
            }
        }
    }

def read_file_schema():
    return {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the text contents of a file from the local workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "Your internal reasoning using your dynamically chosen framework (e.g. STAR, OODA). ALWAYS provide this."
                    },
                    "filepath": {
                        "type": "string",
                        "description": "The relative path to the file to read (e.g., README.md, tokenize_readme.py)."
                    }
                },
                "required": ["thought", "filepath"]
            }
        }
    }