import os
import hashlib
import time
from typing import List, Optional
import numpy as np
from dotenv import load_dotenv

load_dotenv()


class Embedder:
    """
    Lightweight, cloud-resilient Embedding Engine.
    Uses Hugging Face Inference API by default (0MB local footprint),
    with optional local sentence_transformers fallback.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._cache = {}
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_embedding_time_sec = 0.0
        self._hf_client = None
        self._local_model = None
        self._init_backend()

    def _init_backend(self):
        token = os.getenv("HUGGINGFACE_TOKEN")
        try:
            from huggingface_hub import InferenceClient
            self._hf_client = InferenceClient(token=token if token else None)
        except Exception as e:
            print(f"[Embedder WARNING] Could not initialize HuggingFace client: {e}")

    def _get_local_model(self):
        if self._local_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._local_model = SentenceTransformer(self.model_name)
            except Exception:
                self._local_model = False
        return self._local_model if self._local_model is not False else None

    def _embed_single_api(self, text: str) -> np.ndarray:
        if self._hf_client is not None:
            try:
                emb = self._hf_client.feature_extraction(text, model=self.model_name)
                arr = np.array(emb, dtype="float32")
                if arr.ndim > 1:
                    arr = arr.flatten()
                return arr
            except Exception as e:
                pass

        # Local fallback if installed
        local_m = self._get_local_model()
        if local_m is not None:
            return np.array(local_m.encode(text), dtype="float32")

        # Fallback hash-based deterministic 384d vector if completely offline
        h = hashlib.sha384(text.encode("utf-8")).digest()
        vec = np.frombuffer(h, dtype=np.uint8).astype("float32") / 255.0
        return np.pad(vec, (0, max(0, 384 - len(vec))))[:384]

    def embed(self, texts: List[str]):
        if not texts:
            return np.array([])

        start_time = time.time()
        self.total_requests += len(texts)

        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []

        for i, text in enumerate(texts):
            key = hashlib.md5(text.encode("utf-8")).hexdigest()
            if key in self._cache:
                results[i] = self._cache[key]
                self.cache_hits += 1
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
                self.cache_misses += 1

        if uncached_texts:
            for idx, text in zip(uncached_indices, uncached_texts):
                key = hashlib.md5(text.encode("utf-8")).hexdigest()
                emb = self._embed_single_api(text)
                self._cache[key] = emb
                results[idx] = emb

        elapsed = time.time() - start_time
        self.total_embedding_time_sec += elapsed
        return np.array(results, dtype="float32")

    def get_cache_stats(self):
        hit_rate = round(self.cache_hits / float(self.total_requests), 4) if self.total_requests > 0 else 0.0
        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": hit_rate,
            "total_embedding_time_sec": round(self.total_embedding_time_sec, 3)
        }