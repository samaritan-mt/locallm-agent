import json
import re
from typing import Optional

TOOL_SCHEMAS = {}

def register_schemas(schemas: list[dict]):
    """Populate the validator registry from the loaded tool schemas."""
    for schema in schemas:
        name = schema.get("function", {}).get("name") or schema.get("name")
        if name:
            TOOL_SCHEMAS[name] = schema

def validate_tool_call(tool_call: dict) -> tuple[bool, Optional[str]]:
    """
    Returns (is_valid, error_message).
    Checks:
      1. tool_call has 'function.name' and 'function.arguments' keys.
      2. 'function.arguments' is valid JSON.
      3. All required parameters declared in the schema are present.
      4. No parameter value is None, empty string, or exceeds 32KB.
    """
    fn = tool_call.get("function", {})
    name = fn.get("name")
    raw_args = fn.get("arguments")

    if not name:
        return False, "Tool call is missing 'function.name'."

    if name not in TOOL_SCHEMAS:
        return False, f"Unknown tool: '{name}'. Registered tools: {list(TOOL_SCHEMAS.keys())}."

    if not raw_args:
        return False, f"Tool call for '{name}' is missing 'function.arguments'."

    # Parse arguments
    try:
        if isinstance(raw_args, str):
            args = json.loads(raw_args)
        else:
            args = raw_args
    except json.JSONDecodeError as e:
        return False, f"Tool call for '{name}' has malformed JSON arguments: {e}"

    # Get required parameters from schema
    schema = TOOL_SCHEMAS[name]
    fn_schema = schema.get("function", schema)
    params = fn_schema.get("parameters", {})
    required = params.get("required", [])

    for param in required:
        if param not in args:
            return False, f"Tool call for '{name}' is missing required parameter '{param}'."
        value = args[param]
        if value is None or value == "":
            return False, f"Tool call for '{name}' has empty value for required parameter '{param}'."
        if isinstance(value, str) and len(value) > 32_768:
            return False, f"Tool call for '{name}' parameter '{param}' exceeds 32KB limit."

    return True, None


def build_correction_prompt(error: str, tool_name: str) -> str:
    """Build a structured correction message to inject back into the conversation."""
    return (
        f"SYSTEM ERROR — Invalid tool call for '{tool_name}': {error}\n\n"
        f"You MUST retry using the native JSON Tool Calling API with all required parameters.\n"
        f"Do not output tool calls as markdown text. Do not omit required parameters.\n"
        f"Required parameters for '{tool_name}': "
        + _get_required_params(tool_name)
    )


def _get_required_params(tool_name: str) -> str:
    schema = TOOL_SCHEMAS.get(tool_name, {})
    fn_schema = schema.get("function", schema)
    required = fn_schema.get("parameters", {}).get("required", [])
    return ", ".join(f"'{p}'" for p in required) if required else "none declared"
