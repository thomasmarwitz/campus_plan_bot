from huggingface_hub import AsyncInferenceClient, InferenceClient
from loguru import logger

from campus_plan_bot.interfaces.interfaces import LLMClient, LLMRequestConfig

INSTITUTE_URL = "http://hiaisc.isl.iar.kit.edu/llm_generate"


class InstituteClient(LLMClient):
    """A client for the Institute API."""

    def __init__(self, default_request_config: LLMRequestConfig | None = None):
        self.client = InferenceClient(
            model=INSTITUTE_URL,
        )
        self.async_client = AsyncInferenceClient(
            model=INSTITUTE_URL,
        )
        self.request_config: LLMRequestConfig = (
            default_request_config
            or LLMRequestConfig(
                max_new_tokens=128,
                temperature=0.3,
            )
        )
        logger.debug(
            f"InstituteClient initialized with default request config: {self.request_config}"
        )

    def _process_response(self, response: str) -> str:
        # TODO: remove all between < and >
        return response.strip().removeprefix("assistant").strip()

    def query(self, prompt: str) -> str:
        answer = self.generate(prompt, self.request_config)
        answer = self._process_response(answer)
        return answer

    def generate(self, prompt: str, config: LLMRequestConfig) -> str:
        return self.client.text_generation(
            prompt=prompt,
            temperature=config["temperature"],
            max_new_tokens=config["max_new_tokens"],
            # return_full_text=True,
        )

    async def query_async(self, prompt: str) -> str:
        answer = await self.async_client.text_generation(
            prompt=prompt,
            temperature=self.request_config["temperature"],
            max_new_tokens=self.request_config["max_new_tokens"],
        )
        return self._process_response(answer)
