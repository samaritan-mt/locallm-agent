import os
import re

class DynamicPromptManager:
    """Loads and formats system prompts from markdown files."""
    
    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            # Default to the src/prompts directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.prompts_dir = os.path.join(base_dir, "prompts")
            self.partials_dir = os.path.join(self.prompts_dir, "partials")
        else:
            self.prompts_dir = prompts_dir
            self.partials_dir = os.path.join(self.prompts_dir, "partials")

    def _load_partials(self, relative_path: str):
        filepath = os.path.join(self.partials_dir, f"{relative_path}.md")
        if not os.path.exists(filepath):
            return ""
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()


    def load_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        Loads a prompt by name (e.g., 'ask' or 'agent'), 
        strips the frontmatter, and formats variables.
        """
        filepath = os.path.join(self.prompts_dir, f"{prompt_name}_system.md")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"System prompt file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Strip frontmatter (<!-- ... --> at the top of the file)
        content = re.sub(r'^<!--.*?-->\n?', '', content, flags=re.DOTALL).strip()

        # Format variables using str.format
        try:
            return content.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required template variable for {prompt_name}_system.md: {e}")


    NON_DETERMINISTIC_PATTERNS = [
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",  # ISO timestamps
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",  # UUIDs
    ]

    def build_system_prompt(self, template_name: str, enabled_tools: list, **kwargs) -> str:
        prompt = self._build_raw(template_name, enabled_tools, **kwargs)
        
        for pattern in self.NON_DETERMINISTIC_PATTERNS:
            if re.search(pattern, prompt):
                import warnings
                warnings.warn(
                    f"System prompt contains potentially non-deterministic content matching /{pattern}/. "
                    f"This will invalidate the Ollama KV cache on every call.",
                    RuntimeWarning,
                    stacklevel=2
                )
        
        return prompt

    def assert_deterministic(self, template_name: str, enabled_tools: list, **kwargs) -> str:
        """
        Builds the system prompt twice and asserts both outputs are identical.
        Use in tests only. Raises AssertionError if non-deterministic content is found.
        """
        first = self.build_system_prompt(template_name, enabled_tools, **kwargs)
        second = self.build_system_prompt(template_name, enabled_tools, **kwargs)
        if first != second:
            # Find first differing line for a useful error message
            for i, (a, b) in enumerate(zip(first.splitlines(), second.splitlines())):
                if a != b:
                    raise AssertionError(
                        f"System prompt is non-deterministic at line {i+1}:\n"
                        f"  First:  {a!r}\n"
                        f"  Second: {b!r}"
                    )
            raise AssertionError("System prompt outputs differ in length.")
        return first


    def _build_raw(self, template_name: str, enabled_tools: list[str], **kwargs):
        filepath = os.path.join(self.prompts_dir, f"{template_name}.md")

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        content = re.sub(r'^<!--.*?-->\n?', '', content, flags=re.DOTALL).strip()

        core_identity = self._load_partials("core_identity")
        communication_style = self._load_partials("communication_style")
        security_boundaries = self._load_partials("security_boundaries")
        reasoning_process = self._load_partials("reasoning_process")
        
        tool_instructions = ""

        if enabled_tools:
            tool_instructions = "You have access to the following tools: \n\n"
            for tool in enabled_tools:
                tool_doc = self._load_partials(f"tools/{tool}")
                if tool_doc:
                    tool_instructions += f"## Tool: {tool}\n{tool_doc}\n\n"
        else:
            tool_instructions = "You currently do not have access to any external tools."
        
        content = content.replace("{{ core_identity }}", core_identity)
        content = content.replace("{{ reasoning_process }}", reasoning_process)
        content = content.replace("{{ communication_style }}", communication_style)
        content = content.replace("{{ security_boundaries }}", security_boundaries)
        content = content.replace("{{ tool_instructions }}", tool_instructions.strip())

        try: 
            return content.format(**kwargs)
        except KeyError as e: 
            raise ValueError(f"Missing required template variable for {template_name}.md: {e}")
        

        