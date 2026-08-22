import ollama

from .base import LLM

class OllamaLLM(LLM):

    def __init__(self, model: str = "qwen3:8b"):
        self.model = model

    def generate(self, prompt: str) -> str:
        response = ollama.chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response["message"]["content"]