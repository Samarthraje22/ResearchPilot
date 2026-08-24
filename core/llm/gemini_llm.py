import os
from dotenv import load_dotenv
from .base import LLM


class GeminiLLM(LLM):
    def __init__(self, model: str = "gemini-2.5-flash"):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY was not found.")

        try:
            from google import genai
            self.client = genai.Client(api_key=api_key)
        except ImportError:
            raise RuntimeError("google-genai SDK is not installed in this environment.")
        self.model = model

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        return response.text