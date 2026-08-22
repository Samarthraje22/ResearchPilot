import os

from dotenv import load_dotenv

from .ollama_llm import OllamaLLM
from .gemini_llm import GeminiLLM
from .huggingface_llm import HuggingFaceLLM


def get_llm():
    load_dotenv()

    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == "ollama":
        return OllamaLLM()

    elif provider == "gemini":
        return GeminiLLM()

    elif provider == "huggingface":
        return HuggingFaceLLM()

    else:
        raise ValueError(
            f"Unknown LLM provider: {provider}"
        )