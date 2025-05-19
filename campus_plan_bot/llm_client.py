from huggingface_hub import InferenceClient

from campus_plan_bot.interfaces import LLMClient, LLMRequestConfig

INSTITUTE_URL = "http://hiaisc.isl.iar.kit.edu/llm_generate"


class InstituteClient(LLMClient):
    """A client for the Institute API."""

    def __init__(self, default_request_config: LLMRequestConfig | None = None):
        self.client = InferenceClient(
            model=INSTITUTE_URL,
        )
        self.request_config: LLMRequestConfig = (
            default_request_config
            or LLMRequestConfig(
                max_new_tokens=128,
                temperature=0.3,
            )
        )

    def query(self, prompt: str) -> str:
        return self.generate(prompt, self.request_config)

    def generate(self, prompt: str, config: LLMRequestConfig) -> str:
        return self.client.text_generation(
            prompt=prompt,
            temperature=config["temperature"],
            max_new_tokens=config["max_new_tokens"],
        )
