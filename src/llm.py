import requests
from typing import Union, List
from policy.config import AllowedModels, LLMRunTimePolicyConfig
from policy.prompts import PromptManager


def query_local_llm(model: AllowedModels, 
temperature: float, 
max_input_chars: int, 
allow_remote_endpoint: bool, 
prompt: Union[str, list],
tools: list=[]):
    config = LLMRunTimePolicyConfig()

   
    # 1. Validation
    if isinstance(prompt, str) and len(prompt) > max_input_chars:
        raise ValueError(f"Prompt size ({len(prompt)} chars) exceeds maximum allowed size ({max_input_chars})")
    
    # 2. Construct Payload
    # Extract the string value from the Enum
    model_name = model.value if isinstance(model, AllowedModels) else model
    payload = construct_payload(model_name, temperature, prompt)
    if len(tools) > 0:
        payload["tools"] = tools
    
    # 3. Call LLM
    endpoint = config.default_endpoint
    return call_local_llm(payload, endpoint)

def construct_payload(model_name: str, temperature: float, prompt: Union[str, list]):
    if isinstance(prompt, str):
        pm = PromptManager()
        system_prompt = pm.load_prompt("ask")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    else:
        messages = prompt
        
    return {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "stream": False
    }

def call_local_llm(payload: dict, endpoint: str):
    try: 
        # Enforce strict 600s timeout to allow large context evaluation
        response = requests.post(f"{endpoint}/api/chat", json=payload, timeout=(5, 600))
        response.raise_for_status()
        
        # Correctly parsing Ollama's Chat API response to include tool_calls
        return response.json()["message"]


        
    except requests.exceptions.ConnectionError:
        raise ValueError(f"Could not connect to Ollama at {endpoint}. Check that Ollama is running: `ollama serve`")
    except requests.exceptions.Timeout:
        raise ValueError("The request to Ollama timed out.")

def summarize_tool_output(tool_result: str, context: str):
    try: 
        prompt = f"The tool returned a very large output. Please summarize the following output, extracting the key information relevant to our current task and the original user request: \n\nContext: {context}\n\nTool Output: {tool_result}"
        response = query_local_llm(AllowedModels.QWEN, 0.2, 8000, False, prompt)
        return response.get('content', '')
    except Exception as e:
        raise ValueError(f"Could not summarize tool output: {e}")
