<!--
name: 'Agent System Prompt'
description: 'Dynamic system prompt for the stateful agent REPL'
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