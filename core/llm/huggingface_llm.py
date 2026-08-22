import os

from dotenv import load_dotenv
from huggingface_hub import InferenceClient

from .base import LLM


class HuggingFaceLLM(LLM):

    def __init__(self):
        load_dotenv()

        token = os.getenv("HUGGINGFACE_TOKEN")

        if not token:
            raise ValueError(
                "HUGGINGFACE_TOKEN was not found."
            )

        self.client = InferenceClient(
            api_key=token,
            provider="auto"
        )

        self.model = "meta-llama/Llama-3.1-8B-Instruct"

    def generate(self, prompt: str) -> str:

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response.choices[0].message.content