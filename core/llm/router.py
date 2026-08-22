import os
from typing import Optional, List, Tuple
from dotenv import load_dotenv
from .base import LLM
from .gemini_llm import GeminiLLM
from .huggingface_llm import HuggingFaceLLM
from .ollama_llm import OllamaLLM


class LLMRouter(LLM):

    def __init__(self, primary_provider: Optional[str] = None):
        load_dotenv()
        self.default_provider = (primary_provider or os.getenv("LLM_PROVIDER", "gemini")).lower()
        self._providers: dict = {}

    def _get_provider(self, name: str) -> Optional[LLM]:
        name = name.lower()
        if name in self._providers:
            return self._providers[name]

        try:
            if name == "gemini":
                inst = GeminiLLM()
            elif name == "huggingface":
                inst = HuggingFaceLLM()
            elif name == "ollama":
                inst = OllamaLLM()
            else:
                return None
            self._providers[name] = inst
            return inst
        except Exception as e:
            print(f"[LLMRouter WARNING] Unable to initialize LLM provider '{name}': {e}")
            return None

    def select_provider(self, prompt: str, mode: Optional[str] = None) -> Tuple[str, List[str]]:
        if mode and mode.lower() == "offline":
            return "ollama", ["gemini", "huggingface"]

        p_lower = prompt.lower()
        is_complex = len(prompt) > 1500 or any(w in p_lower for w in ["compare", "synthesis", "evaluate", "limitations", "complex"])

        if self.default_provider == "gemini":
            return "gemini", ["huggingface", "ollama"]
        elif self.default_provider == "huggingface":
            return "huggingface", ["gemini", "ollama"]
        elif self.default_provider == "ollama":
            return "ollama", ["gemini", "huggingface"]

        if is_complex:
            return "gemini", ["huggingface", "ollama"]
        else:
            return "huggingface", ["gemini", "ollama"]

    def generate(self, prompt: str, mode: Optional[str] = None) -> str:
        primary_name, fallbacks = self.select_provider(prompt, mode=mode)
        provider_order = [primary_name] + [f for f in fallbacks if f != primary_name]

        last_error = None
        for prov_name in provider_order:
            provider = self._get_provider(prov_name)
            if provider is None:
                continue

            try:
                print(f"[LLMRouter] Generating response using provider: {prov_name}")
                response = provider.generate(prompt)
                if response and response.strip():
                    return response
            except Exception as e:
                print(f"[LLMRouter ERROR] Provider '{prov_name}' failed: {e}. Falling back...")
                last_error = e

        raise RuntimeError(f"All LLM providers failed to generate a response. Last error: {last_error}")
