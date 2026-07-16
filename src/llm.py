import requests
from policy.config import AllowedModels, LLMRunTimePolicyConfig


def query_local_llm(model: AllowedModels, temperature: float, max_input_chars: int, allow_remote_endpoint: bool, prompt: str):
    config = LLMRunTimePolicyConfig()
    
    # 1. Validation
    if len(prompt) > max_input_chars:
        raise ValueError(f"Prompt size ({len(prompt)} chars) exceeds maximum allowed size ({max_input_chars})")
    
    # 2. Construct Payload
    # Extract the string value from the Enum
    model_name = model.value if isinstance(model, AllowedModels) else model
    payload = construct_payload(model_name, temperature, prompt)
    
    # 3. Call LLM
    endpoint = config.default_endpoint
    return call_local_llm(payload, endpoint)

def construct_payload(model_name: str, temperature: float, prompt: str):
    # CRITICAL: This bounds the AI and prevents prompt injection
    system_prompt = (
        "You are LocalSec Agent, a local-first assistant for security engineering workflows.\n\n"
        "You answer questions and provide explanations only.\n\n"
        "You cannot execute commands.\n"
        "You cannot access files.\n"
        "You cannot inspect environment variables.\n"
        "You cannot access credentials.\n"
        "You cannot access the network.\n"
        "You cannot perform actions on the user's computer.\n\n"
        "If the user asks you to perform an action, explain what command or process they could run manually, and highlight security risks.\n\n"
        "If the user asks about a potentially destructive command, warn clearly.\n\n"
        "Never claim that you performed an action.\n"
        "Never claim that you inspected local files unless their content was explicitly provided in the prompt."
    )
    
    return {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "stream": False
    }

def call_local_llm(payload: dict, endpoint: str):
    try: 
        # Using strict timeouts as per the architecture document
        response = requests.post(f"{endpoint}/api/chat", json=payload, timeout=(5, 120))
        response.raise_for_status()
        
        # Correctly parsing Ollama's Chat API response
        return response.json()["message"]["content"]


        
    except requests.exceptions.ConnectionError:
        raise ValueError(f"Could not connect to Ollama at {endpoint}. Check that Ollama is running: `ollama serve`")
    except requests.exceptions.Timeout:
        raise ValueError("The request to Ollama timed out.")
