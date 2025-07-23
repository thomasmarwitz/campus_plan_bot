from datetime import datetime
from pathlib import Path


def load_and_format_prompt(prompt_name: str, do_format: bool = True, **kwargs) -> str:
    """Loads a prompt from the 'prompts' directory and formats it with the
    given arguments.

    A 'current_time' argument is always added.
    """
    prompt_path = Path(__file__).parent / f"{prompt_name}.md"
    prompt_template = prompt_path.read_text()

    format_args = {
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **kwargs,
    }

    return prompt_template.format(**format_args) if do_format else prompt_template
