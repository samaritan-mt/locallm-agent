import requests
from typing import Union, List
from pydantic import BaseModel, Field
from policy.config import LLMRunTimePolicyConfig
from policy.prompts import DynamicPromptManager


class LLMParams(BaseModel):
    """Common request parameters shared by every provider.

    Providers that need knobs beyond these (e.g. OpenRouter's top_p,
    an API key, etc.) read them from `extra` instead of growing the
    shared interface per-provider.
    """
    model: str
    temperature: float = 0.2
    max_input_chars: int = 100_000
    allow_remote_endpoint: bool = False
    tools: List[dict] = Field(default_factory=list)
    extra: dict = Field(default_factory=dict)


class LLMProvider:

    # Config is an abstraction to be created from policy.py
    def __init__(self, config):
        self.config = config

    # Query compiles the messages + params into the payload expected by the provider
    def query(self, messages: Union[str, list], params: LLMParams) -> dict:
        raise NotImplementedError

    # Call executes the request against the provider's endpoint
    def call(self, payload: dict, endpoint: str, params: LLMParams) -> dict:
        raise NotImplementedError

    # Summarize is for internal use by the router to reduce token usage
    def summarize(self, tool_result: str, context: str, params: LLMParams) -> str:
        raise NotImplementedError


class LocalOllamaProvider(LLMProvider):

    def query(self, messages: Union[str, list], params: LLMParams) -> dict:
        if isinstance(messages, str) and len(messages) > params.max_input_chars:
            raise ValueError(
                f"Prompt size ({len(messages)} chars) exceeds maximum allowed size ({params.max_input_chars})"
            )

        if isinstance(messages, str):
            pm = DynamicPromptManager()
            system_prompt = pm.build_system_prompt(
                "ask",
                enabled_tools=[],
                max_input_chars=10_000_000
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": messages}
            ]

        payload = {
            "model": params.model,
            "messages": messages,
            "temperature": params.temperature,
            "stream": False,
        }
        if params.tools:
            payload["tools"] = params.tools
        return payload

    def call(self, payload: dict, endpoint: str, params: LLMParams) -> dict:
        # Enforce remote endpoint policy
        is_remote = not endpoint.startswith("http://127.0.0.1") and not endpoint.startswith("http://localhost")
        if is_remote and not params.allow_remote_endpoint:
            return {
                "role": "assistant",
                "content": "Error: Remote endpoint detected but --allow-remote-endpoint flag was not set. "
                           "Pass --allow-remote-endpoint to allow connections outside localhost."
            }

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

    def summarize(self, tool_result: str, context: str, params: LLMParams) -> str:
        try:
            prompt = (
                "The tool returned a very large output. Please summarize the following output, "
                f"extracting the key information relevant to our current task and the original user request: \n\n"
                f"Context: {context}\n\nTool Output: {tool_result[:30000]}"
            )
            summarize_params = params.model_copy(update={"tools": []})
            payload = self.query(prompt, summarize_params)
            response = self.call(payload, self.config.default_endpoint, summarize_params)
            return response.get("content", "")
        except Exception as e:
            raise ValueError(f"Could not summarize tool output: {e}")


# The concrete OpenRouterProvider lives in src/providers/openrouter_provider.py -
# it wraps the `openrouter` SDK and needs its own credential handling
# (RemoteCredentials) that this module has no reason to know about.


class LLMRouter:
    """Picks a provider and drives query -> call for it."""

    def __init__(self, provider: LLMProvider, config: LLMRunTimePolicyConfig = None):
        self.provider = provider
        self.config = config or LLMRunTimePolicyConfig()

    def ask(self, messages: Union[str, list], params: LLMParams) -> dict:
        payload = self.provider.query(messages, params)
        return self.provider.call(payload, self.config.default_endpoint, params)

    def summarize(self, tool_result: str, context: str, params: LLMParams) -> str:
        return self.provider.summarize(tool_result, context, params)
