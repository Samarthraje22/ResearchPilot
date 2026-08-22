import os

from dotenv import load_dotenv
from google import genai

from .base import LLM


class GeminiLLM(LLM):

    def __init__(self, model: str = "gemini-3.1-flash-lite-preview"):
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY was not found."
            )

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(self, prompt: str) -> str:

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )

        return response.text