import json
from dataclasses import dataclass
from typing import Union

import httpx
from openrouter import OpenRouter
from openrouter.errors import OpenRouterError, UnauthorizedResponseError, TooManyRequestsResponseError

from policy.config import OpenRouterRunTimePolicyConfig
from llm_router import LLMProvider, LLMParams


@dataclass
class RemoteCredentials:
    """Holds the OpenRouter API key in process memory only, for the lifetime
    of the session. Deliberately not an attribute of SecureChatSession -
    see docs/lab-26-openrouter-remote-provider.md Task 2. Owned by the REPL
    loop in src/main.py and discarded whenever the user switches to /ollama."""
    api_key: str


class OpenRouterProvider(LLMProvider):
    """Uses the official `openrouter` SDK (installed in the project venv) to
    talk to OpenRouter, rather than hand-rolled `requests` calls."""

    def __init__(self, config: OpenRouterRunTimePolicyConfig, credentials: RemoteCredentials):
        super().__init__(config)
        self.credentials = credentials
        self.client = OpenRouter(api_key=credentials.api_key)

    def query(self, messages: Union[str, list], params: LLMParams) -> dict:
        if isinstance(messages, str) and len(messages) > params.max_input_chars:
            raise ValueError(
                f"Prompt size ({len(messages)} chars) exceeds maximum allowed size ({params.max_input_chars})"
            )

        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        else:
            messages = self._sanitize_history(messages)

        payload = {
            "model": params.model,
            "messages": messages,
            "temperature": params.temperature,
            "max_tokens": params.extra.get("max_output_tokens", self.config.max_output_tokens),
        }
        if params.tools:
            payload["tools"] = params.tools
        return payload

    def call(self, payload: dict, endpoint: str, params: LLMParams) -> dict:
        # OpenRouter is inherently remote - route it through the same
        # --allow-remote-endpoint gate LocalOllamaProvider enforces for Ollama.
        # `endpoint` itself isn't passed to the SDK: the client always talks to
        # OpenRouter's own production servers, so there's no arbitrary-host risk
        # to guard against the way there is for Ollama's configurable endpoint.
        if not params.allow_remote_endpoint:
            return {
                "role": "assistant",
                "content": "Error: OpenRouter is a remote endpoint but --allow-remote-endpoint flag was not set. "
                           "Pass --allow-remote-endpoint to allow connections outside localhost."
            }

        try:
            response = self.client.chat.send(
                model=payload["model"],
                messages=payload["messages"],
                temperature=payload["temperature"],
                max_tokens=payload.get("max_tokens"),
                tools=payload.get("tools"),
            )
            return self._normalize_message(response.choices[0].message)
        except UnauthorizedResponseError:
            raise ValueError("OpenRouter rejected the API key.")
        except TooManyRequestsResponseError:
            raise ValueError(
                "OpenRouter rate limit hit (20 req/min or 50 req/day on the free tier). "
                "Wait and retry, or /ollama to switch back."
            )
        except OpenRouterError as e:
            raise ValueError(f"OpenRouter request failed: {e}")
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise ValueError(f"Could not reach OpenRouter: {e}")

    @staticmethod
    def _sanitize_history(messages: list) -> list:
        """session.messages is shared across providers and can be replayed to
        either backend as the conversation grows or the user toggles
        /ollama <-> /openrouter mid-session. Ollama tolerates tool_calls with
        dict-shaped `arguments` and tool-role messages with no `tool_call_id`
        (it produced that shape itself). OpenRouter's OpenAI-compatible schema
        is strict: `arguments` must serialize back to a JSON string, and every
        tool-role message must carry a `tool_call_id` matching a preceding
        assistant tool_call id. Build a wire-compliant copy here rather than
        mutating the shared history or teaching main.py/session.py about
        OpenRouter's format."""
        sanitized = []
        pending_tool_call_id = None

        for i, msg in enumerate(messages):
            msg = dict(msg)

            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                new_tool_calls = []
                for j, tc in enumerate(msg["tool_calls"]):
                    tc = dict(tc)
                    function = dict(tc.get("function", {}))
                    arguments = function.get("arguments")
                    if not isinstance(arguments, str):
                        arguments = json.dumps(arguments if arguments is not None else {})
                    function["arguments"] = arguments
                    tc["function"] = function
                    tc["id"] = tc.get("id") or f"call_{i}_{j}"
                    tc["type"] = tc.get("type", "function")
                    new_tool_calls.append(tc)
                msg["tool_calls"] = new_tool_calls
                pending_tool_call_id = new_tool_calls[0]["id"]
            elif msg.get("role") == "tool":
                if not msg.get("tool_call_id"):
                    msg["tool_call_id"] = pending_tool_call_id or f"call_{i}"
                pending_tool_call_id = None

            sanitized.append(msg)

        return sanitized

    @staticmethod
    def _normalize_message(message) -> dict:
        """Adapt the SDK's ChatAssistantMessage (a pydantic model) to the same
        plain dict shape LocalOllamaProvider returns, so main.py's tool-call
        loop doesn't need to know which provider answered. This also decodes
        each tool call's `arguments` out of the JSON string the OpenAI-
        compatible wire format uses - Ollama hands back an already-parsed
        dict there, and main.py assumes dict access (`args.get('command')`)."""
        tool_calls = None
        if message.tool_calls:
            tool_calls = []
            for tc in message.tool_calls:
                try:
                    arguments = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    arguments = tc.function.arguments
                tool_calls.append({
                    "id": tc.id,
                    "type": tc.type,
                    "function": {"name": tc.function.name, "arguments": arguments},
                })

        return {
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": tool_calls,
        }

    def validate(self) -> tuple[bool, str]:
        """One lightweight, low-token call to confirm the candidate key works
        before the session is allowed to switch providers (Task 5, step 3)."""
        params = LLMParams(
            model=self.config.allowed_models[0],
            temperature=0.0,
            allow_remote_endpoint=True,
            extra={"max_output_tokens": 1},
        )
        payload = self.query("ping", params)
        try:
            self.call(payload, self.config.base_url, params)
            return True, ""
        except ValueError as e:
            return False, str(e)

    def summarize(self, tool_result: str, context: str, params: LLMParams) -> str:
        try:
            prompt = (
                "The tool returned a very large output. Please summarize the following output, "
                f"extracting the key information relevant to our current task and the original user request: \n\n"
                f"Context: {context}\n\nTool Output: {tool_result[:30000]}"
            )
            summarize_params = params.model_copy(update={"tools": []})
            payload = self.query(prompt, summarize_params)
            response = self.call(payload, self.config.base_url, summarize_params)
            return response.get("content", "")
        except Exception as e:
            raise ValueError(f"Could not summarize tool output: {e}")
