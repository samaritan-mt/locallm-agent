# Tool Usage Constraints

**CRITICAL ACTION RULE:**
1. You are STRICTLY FORBIDDEN from outputting markdown code blocks (e.g., ```bash ... ``` or ```python ... ```) to describe actions you want to perform.
2. DO NOT write tool calls as plain text (e.g. `execute_os_command({{...}})`). 
3. You MUST use the native JSON Tool Calling API provided by the platform to invoke tools. If you output tool names in markdown blocks, it will fail.