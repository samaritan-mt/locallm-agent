<!--
name: 'Agent System Prompt'
description: 'Dynamic system prompt for the stateful agent REPL'
-->
<!--
CACHING CONTRACT:
This template is rendered once per SecureChatSession and must be fully deterministic.
Do NOT inject:
  - Timestamps (datetime.now(), time.time())
  - Random values (uuid4(), random.random())
  - Session-specific runtime state (turn count, user name)

Any runtime state that varies per-turn must be passed via the conversation history
(user/assistant/tool messages), never via the system prompt.

The Ollama KV cache reuses prefix computation when the system prompt string is identical
across requests. Changing the system prompt — even by one character — invalidates the cache
and increases first-token latency for the entire session.

EXCEPTION (Lab 26): /openrouter appends a system message disclosing the remote provider
instead of rebuilding this template, so the determinism guarantee above is documented as
void for OpenRouter-active sessions only. Ollama-only sessions are unaffected.
-->
{{ core_identity }}

# Reasoning Process

{{ reasoning_process }}
# Communication Style
{{ communication_style }}

# Security Boundaries
{{ security_boundaries }}

# Tool Capabilities
{{ tool_instructions }}

# Session Management
The user's input may be truncated or sliding-windowed if it exceeds {max_input_chars} characters to prevent context overflow. Focus on the most recent context while referencing established history where necessary.