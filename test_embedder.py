import unittest
import numpy as np
from core.rag.embedder import Embedder


class TestEmbedder(unittest.TestCase):

    def test_embedding_cache_accuracy_and_metrics(self):
        embedder = Embedder()
        texts = [
            "Machine learning allows computers to learn from data.",
            "Deep learning uses neural networks.",
            "The weather is sunny today."
        ]

        # First request (uncached -> all misses)
        embeddings_first = embedder.embed(texts)
        stats1 = embedder.get_cache_stats()

        self.assertEqual(stats1["total_requests"], 3)
        self.assertEqual(stats1["cache_misses"], 3)
        self.assertEqual(stats1["cache_hits"], 0)

        # Second request (cached -> all hits)
        embeddings_second = embedder.embed(texts)
        stats2 = embedder.get_cache_stats()

        self.assertEqual(stats2["total_requests"], 6)
        self.assertEqual(stats2["cache_misses"], 3)
        self.assertEqual(stats2["cache_hits"], 3)
        self.assertEqual(stats2["cache_hit_rate"], 0.5)

        # VERIFY IDENTICAL EMBEDDINGS
        for emb1, emb2 in zip(embeddings_first, embeddings_second):
            self.assertTrue(np.allclose(emb1, emb2, atol=1e-6), "Cached embedding must be identical to uncached embedding!")


if __name__ == "__main__":
    unittest.main()