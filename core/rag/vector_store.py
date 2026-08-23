import numpy as np
from .document import Document


class VectorStore:
    """
    High-performance in-memory Vector Store using pure NumPy cosine similarity.
    Replaces heavy C++ FAISS binaries while providing identical mathematical accuracy.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.documents = []
        self.vectors = np.empty((0, dimension), dtype="float32")

    def add(self, documents: list[Document], embeddings):
        if embeddings is None or len(embeddings) == 0:
            return

        new_vecs = np.array(embeddings, dtype="float32")
        if new_vecs.ndim == 1:
            new_vecs = new_vecs.reshape(1, -1)

        # L2 Normalize vectors for cosine similarity via dot product
        norms = np.linalg.norm(new_vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        new_vecs = new_vecs / norms

        if self.vectors.shape[0] == 0:
            self.vectors = new_vecs
        else:
            self.vectors = np.vstack([self.vectors, new_vecs])

        self.documents.extend(documents)

    def search(self, query_embedding, top_k: int = 3):
        if len(self.documents) == 0 or self.vectors.shape[0] == 0:
            return []

        q_vec = np.array(query_embedding, dtype="float32").flatten()
        norm = np.linalg.norm(q_vec)
        if norm > 0:
            q_vec = q_vec / norm

        # Cosine similarity via inner product of normalized vectors
        scores = np.dot(self.vectors, q_vec)

        # Get top-k highest scoring indices
        top_k = min(top_k, len(scores))
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if idx < len(self.documents):
                results.append((self.documents[idx], float(scores[idx])))

        return results