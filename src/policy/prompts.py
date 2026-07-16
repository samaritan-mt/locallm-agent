import os
import re

class PromptManager:
    """Loads and formats system prompts from markdown files."""
    
    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            # Default to the src/prompts directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.prompts_dir = os.path.join(base_dir, "prompts")
        else:
            self.prompts_dir = prompts_dir

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
