import hashlib
import time
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer


class Embedder:

    def __init__(self):
        self.model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        self._cache = {}
        # Metrics tracking
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_embedding_time_sec = 0.0

    def embed(self, texts: List[str]):
        if not texts:
            return np.array([])

        start_time = time.time()
        self.total_requests += len(texts)

        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []

        for i, text in enumerate(texts):
            # Compute MD5 hash of text as cache key
            key = hashlib.md5(text.encode('utf-8')).hexdigest()
            if key in self._cache:
                results[i] = self._cache[key]
                self.cache_hits += 1
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
                self.cache_misses += 1

        if uncached_texts:
            embeddings = self.model.encode(uncached_texts)
            for idx, text, emb in zip(uncached_indices, uncached_texts, embeddings):
                key = hashlib.md5(text.encode('utf-8')).hexdigest()
                self._cache[key] = emb
                results[idx] = emb

        elapsed = time.time() - start_time
        self.total_embedding_time_sec += elapsed
        return np.array(results)

    def get_cache_stats(self):
        hit_rate = round(self.cache_hits / float(self.total_requests), 4) if self.total_requests > 0 else 0.0
        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": hit_rate,
            "total_embedding_time_sec": round(self.total_embedding_time_sec, 3)
        }